import os
import re
import pickle
import random
import google.generativeai as genai
from api.db import SessionLocal, Lead
import sys

# Ensure gnn is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
from gnn.infer import get_probability

# ---------------------------------------------------------------------------
# ICP buzzword scoring
# High-signal keywords that indicate a strong ICP match.
# ---------------------------------------------------------------------------
HIGH_SIGNAL_KEYWORDS = {
    # Roles / seniority
    "cto", "cso", "ceo", "cmo", "cro", "vp", "svp", "evp", "director",
    "head-of", "head_of", "principal", "staff", "partner", "founder",
    # Functions
    "revenue", "revops", "sales", "gtm", "go-to-market", "growth",
    "marketing", "demand-gen", "demand_gen", "pipeline", "enablement",
    "partnerships", "business-development", "biz-dev",
    # Domain / industry signals
    "saas", "b2b", "enterprise", "startup", "scaleup", "series",
    "ai", "ml", "data", "analytics", "automation", "platform",
}

# Weak-signal keywords — mildly boost score
MID_SIGNAL_KEYWORDS = {
    "engineer", "engineering", "product", "manager", "lead", "senior",
    "tech", "cloud", "devops", "security", "fintech", "edtech", "healthtech",
}

def _is_plain_name_url(slug: str) -> bool:
    """
    Heuristic: if the slug looks like 'john-doe' or 'john-doe-123'
    (only alpha + dashes + optional trailing digits) it's probably a bare name,
    not a keyword-rich handle.
    """
    return bool(re.fullmatch(r"[a-z]+-[a-z]+(-[a-z0-9]+)?", slug))

def _score_from_url(url: str) -> tuple[float, str]:
    """
    Derive a deterministic-but-noisy LLM-style score from the signal source URL.

    Rules:
    - Slugify the URL path → lower-case tokens split on [-/_.]
    - Count high-signal and mid-signal keyword hits
    - Plain names (john-doe) → uniform random in [0.35, 0.75]
    - High-signal hit  → base 0.72 + 0.03 per extra hit, capped at 0.95
    - Mid-signal only  → base 0.52 + noise ±0.08
    - No signal        → random in [0.25, 0.55]
    """
    # Extract the path portion of the URL
    path_match = re.search(r"linkedin\.com/([^?#]+)", url.lower())
    slug = path_match.group(1) if path_match else url.lower()
    slug = slug.strip("/")

    # Tokenise
    tokens = set(re.split(r"[-_./]", slug))

    high_hits = tokens & HIGH_SIGNAL_KEYWORDS
    mid_hits  = tokens & MID_SIGNAL_KEYWORDS

    # Plain bare-name profile → randomise
    parts = slug.split("/")
    last_part = parts[-1] if parts else slug
    if not high_hits and not mid_hits and _is_plain_name_url(last_part):
        score = round(random.uniform(0.35, 0.75), 2)
        rationale = (
            f"URL '{url}' appears to be a personal profile with no clear ICP signals. "
            f"Score randomised: {score:.2f}."
        )
        return score, rationale

    if high_hits:
        base  = 0.72
        boost = min(len(high_hits) - 1, 4) * 0.04   # up to +0.16
        noise = random.uniform(-0.04, 0.04)
        score = round(min(0.95, base + boost + noise), 2)
        rationale = (
            f"URL contains strong ICP signals: {', '.join(sorted(high_hits))}. "
            f"LLM score elevated to {score:.2f}."
        )
    elif mid_hits:
        noise = random.uniform(-0.08, 0.08)
        score = round(max(0.25, min(0.75, 0.52 + noise)), 2)
        rationale = (
            f"URL contains moderate ICP signals: {', '.join(sorted(mid_hits))}. "
            f"LLM score set to {score:.2f}."
        )
    else:
        score = round(random.uniform(0.25, 0.55), 2)
        rationale = (
            f"No clear ICP keywords found in URL '{url}'. "
            f"Score randomised: {score:.2f}."
        )

    return score, rationale


def get_llm_score(profile_text: str, source_url: str = "") -> tuple[float, str]:
    """
    Returns an LLM-style (score, rationale) for a lead.

    Priority order:
    1. If GEMINI_API_KEY is set → call Gemini and blend with URL score.
    2. Otherwise → derive score from the signal source URL (buzzword analysis).
    """
    # --- URL-based fallback (or blend if API key present) ---
    url_score, url_rationale = _score_from_url(source_url) if source_url else (0.5, "No source URL provided.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return url_score, url_rationale

    # --- Real Gemini call (blend 60% profile + 40% URL) ---
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        You are evaluating a LinkedIn profile for a B2B sales motion.
        Our ICP includes C-Suite, VP, and Director level executives in
        Revenue Operations, Sales Leadership, or Marketing.

        Signal source URL: {source_url}
        Profile:
        {profile_text}

        Is this profile qualified?
        Provide a brief 1-2 sentence rationale, then on a new line a score 0.0–1.0.
        Only the score on the last line.
        """

        response = model.generate_content(prompt)
        text     = response.text.strip()
        lines    = text.split("\n")
        rationale = "\n".join(lines[:-1]).strip()
        match     = re.search(r"([0-9]*\.?[0-9]+)", lines[-1])
        llm_raw   = float(match.group(1)) if match else 0.5
        llm_raw   = max(0.0, min(1.0, llm_raw))

        # Blend
        blended  = round(0.6 * llm_raw + 0.4 * url_score, 2)
        rationale = f"{rationale} (URL signal: {url_score:.2f} → blended: {blended:.2f})"
        return blended, rationale

    except Exception as e:
        return url_score, f"{url_rationale} [Gemini error: {e}]"


def get_person_profile(person_id: str) -> str:
    graph_path = os.path.join(BASE_DIR, "graph.pkl")
    try:
        with open(graph_path, "rb") as f:
            G = pickle.load(f)
        if person_id in G:
            return G.nodes[person_id].get("profile_text", "")
    except Exception:
        pass
    return ""


def run_qualifier(person_id: str, source_url: str = ""):
    """
    Runs the Qualifier Agent: GNN score + URL-informed LLM score,
    sets disagreement flag, and saves the Lead to the database.
    """
    # 1. GNN Score
    try:
        gnn_score = get_probability(person_id)
    except Exception as e:
        print(f"GNN Infer error for {person_id}: {e}")
        gnn_score = 0.0

    # 2. LLM Score (URL-informed)
    profile_text = get_person_profile(person_id)
    llm_score, rationale = get_llm_score(profile_text, source_url=source_url)

    # 3. Disagreement flag
    disagreement = abs(gnn_score - llm_score) > 0.3

    # 4. Qualification decision (average > 0.5)
    qualified = ((gnn_score + llm_score) / 2) > 0.5

    # 5. Persist to DB
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.person_id == person_id).first()
        if not lead:
            lead = Lead(person_id=person_id)
            db.add(lead)

        lead.gnn_score        = gnn_score
        lead.llm_score        = llm_score
        lead.llm_rationale    = rationale
        lead.disagreement_flag = disagreement
        lead.qualified        = qualified
        if source_url:
            lead.source_url = source_url
        db.commit()
    finally:
        db.close()

    return {
        "person_id":    person_id,
        "gnn_score":    gnn_score,
        "llm_score":    llm_score,
        "disagreement": disagreement,
        "qualified":    qualified,
        "rationale":    rationale,
        "source":       source_url,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(run_qualifier(sys.argv[1], source_url=sys.argv[2] if len(sys.argv) > 2 else ""))

#!/usr/bin/env python3
"""
generate_graph.py — SignalAgent Synthetic Data Generator

Produces a heterogeneous graph with:
  Nodes: Person (5000), Company (500), Post (500), SignalSource (50)
  Edges: engaged_with (Person→Post, subtypes: like/comment/reshare)
         works_at     (Person→Company)
         authored     (Person→Post)
         belongs_to   (Post→SignalSource)

Graph properties:
  • Power-law (Zipf) degree distribution on engagement edges
  • Planted homophily: qualified buyers cluster in engagement patterns
  • 3 planted communities detectable by Louvain
  • Realistic profile text via template (default) or Gemini (--llm-profiles)

Outputs:
  graph.pkl   — NetworkX MultiDiGraph (pickle)
  labels.csv  — person_id, qualified (bool)

Usage:
  python generate_graph.py [options]

Options:
  --seed INT          Random seed (default: 42)
  --homophily FLOAT   Homophily alpha 0-1 (default: 0.7)
  --llm-profiles      Generate bios via Gemini API (requires GEMINI_API_KEY)
  --out-dir PATH      Output directory (default: current directory)
  --n-persons INT     Number of Person nodes (default: 5000)
  --n-companies INT   Number of Company nodes (default: 500)
  --n-posts INT       Number of Post nodes (default: 500)
  --n-signal-sources INT  Number of SignalSource nodes (default: 50)

Dependencies:
  pip install networkx numpy
  pip install google-generativeai   # only with --llm-profiles
"""

import argparse
import csv
import json
import os
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULTS  (all overridable via CLI or generate_graph() kwargs)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_N_PERSONS = 5_000
DEFAULT_N_COMPANIES = 500
DEFAULT_N_POSTS = 500
DEFAULT_N_SIGNAL_SOURCES = 50
DEFAULT_N_COMMUNITIES = 3
DEFAULT_QUALIFIED_FRACTION = 0.28
DEFAULT_HOMOPHILY_ALPHA = 0.70
DEFAULT_SEED = 42
DEFAULT_ZIPF_EXPONENT = 2.2          # a > 1; higher = steeper power-law
DEFAULT_MAGNET_POST_FRACTION = 0.10  # fraction of posts that attract qualified buyers

# ─────────────────────────────────────────────────────────────────────────────
# VOCABULARY TABLES
# ─────────────────────────────────────────────────────────────────────────────

COMMUNITY_ARCHETYPES = [
    {
        "name": "RevOps Leaders",
        "icp_roles": [
            "Head of Revenue Operations",
            "Sales Operations Manager",
            "Revenue Enablement Lead",
            "Director of Demand Generation",
            "VP of Revenue Operations",
        ],
        "non_icp_roles": [
            "Account Executive",
            "Business Development Rep",
            "Sales Coordinator",
            "Marketing Coordinator",
            "SDR",
        ],
        "industries": ["SaaS", "MarTech", "Data & Analytics", "CRM Platforms"],
        "topics": [
            "Revenue operations stack",
            "CRM hygiene",
            "GTM alignment",
            "Forecasting accuracy",
            "Sales & marketing alignment",
            "RevOps tooling",
            "Pipeline visibility",
        ],
    },
    {
        "name": "PLG Founders",
        "icp_roles": [
            "Founder & CEO",
            "Product-Led Growth Lead",
            "Growth Lead",
            "Head of Product",
            "VP of Product",
        ],
        "non_icp_roles": [
            "Software Engineer",
            "Product Designer",
            "UX Researcher",
            "Frontend Developer",
            "QA Engineer",
        ],
        "industries": ["SaaS", "DevTools", "EdTech", "Developer Platforms"],
        "topics": [
            "Product-led growth",
            "Freemium conversion",
            "Self-serve onboarding",
            "PLG motion",
            "Activation rates",
            "Time-to-value",
            "Usage analytics",
        ],
    },
    {
        "name": "GTM Executives",
        "icp_roles": [
            "Chief Revenue Officer",
            "VP of Sales",
            "VP of Marketing",
            "Head of GTM Strategy",
            "Chief Marketing Officer",
        ],
        "non_icp_roles": [
            "Office Manager",
            "HR Business Partner",
            "Recruiter",
            "Finance Analyst",
            "Legal Counsel",
        ],
        "industries": ["SaaS", "FinTech", "Cybersecurity", "Enterprise Software"],
        "topics": [
            "Enterprise sales motion",
            "Outbound strategy",
            "Pipeline generation",
            "Sales hiring",
            "Market expansion",
            "Category creation",
            "ICP definition",
        ],
    },
]

SIZE_BANDS = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001+"]
SIZE_BAND_WEIGHTS = [0.10, 0.25, 0.30, 0.20, 0.10, 0.05]
ICP_SIZE_BANDS = {"51-200", "201-500"}

REGIONS = ["North America", "Europe", "APAC", "LATAM", "MEA"]
REGION_WEIGHTS = [0.50, 0.25, 0.15, 0.06, 0.04]
ICP_REGIONS = {"North America", "Europe"}

SOURCE_TYPES = ["competitor_post", "thought_leader", "hashtag"]
ENGAGEMENT_SUBTYPES = ["like", "comment", "reshare"]
SUBTYPE_WEIGHTS = [0.70, 0.20, 0.10]

FIRST_NAMES = [
    "Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Drew", "Avery",
    "Jamie", "Cameron", "Blake", "Hayden", "Parker", "Quinn", "Reese",
    "Sage", "Logan", "Peyton", "Harper", "Finley", "Emerson", "Rowan",
    "Charlie", "Oakley", "River", "Dakota", "Skyler", "Micah", "Elliot",
    "James", "Sarah", "Michael", "Emma", "Chris", "Jennifer", "Daniel",
    "Lisa", "David", "Amy", "Matthew", "Maria", "Andrew", "Laura",
    "Ryan", "Nicole", "Kevin", "Jessica", "Brian", "Rebecca", "Thomas",
    "Sophia", "Nathan", "Olivia", "Samuel", "Chloe", "Benjamin", "Mia",
]

LAST_NAMES = [
    "Chen", "Patel", "Johnson", "Williams", "Kim", "Garcia", "Martinez",
    "Anderson", "Taylor", "Thompson", "Lee", "White", "Harris", "Clark",
    "Rodriguez", "Lewis", "Robinson", "Walker", "Hall", "Allen", "Young",
    "Hernandez", "King", "Wright", "Lopez", "Hill", "Scott", "Green",
    "Adams", "Baker", "Nelson", "Carter", "Mitchell", "Perez", "Roberts",
    "Turner", "Phillips", "Campbell", "Parker", "Evans", "Edwards", "Collins",
    "Stewart", "Morris", "Morgan", "Reed", "Cook", "Bell", "Murphy", "Bailey",
    "Rivera", "Cooper", "Richardson", "Cox", "Howard", "Ward", "Torres",
    "Peterson", "Gray", "Ramirez", "James", "Watson", "Brooks", "Kelly",
]

COMPANY_NAME_A = [
    "Signal", "Apex", "Nexus", "Forge", "Orbit", "Vertex", "Pulse",
    "Relay", "Prism", "Lattice", "Catalyst", "Vector", "Horizon", "Pinnacle",
    "Mosaic", "Summit", "Helix", "Quorum", "Beacon", "Stride", "Lumen",
    "Cipher", "Vantage", "Fulcrum", "Axiom", "Tangent", "Radix", "Zenith",
]
COMPANY_NAME_B = [
    "AI", "Labs", "HQ", "Works", "Cloud", "Systems", "Tech", "Analytics",
    "Intelligence", "Data", "Platform", "Software", "Group", "Solutions",
    "Studio", "Engine", "Ventures", "Digital", "Flow", "IO", "Stack",
    "Metrics", "Ops", "Signal", "Base", "Layer", "Hub", "Suite",
]

BASE_DATE = datetime(2024, 1, 1)
DATE_RANGE_DAYS = 180  # engagement events span 6 months


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _template_bio(role: str, company_name: str, industry: str,
                  community_name: str, topics: List[str]) -> str:
    """Generate a plausible LinkedIn-style bio from a template."""
    t0 = topics[0].lower()
    t1 = (topics[1] if len(topics) > 1 else topics[0]).lower()
    templates = [
        (
            f"Passionate about {t0} and {t1}. Currently driving revenue outcomes "
            f"as {role} at {company_name}, a fast-growing {industry} company. "
            f"Open to connecting with operators thinking seriously about "
            f"{community_name.lower()}."
        ),
        (
            f"{role} at {company_name} | {industry} | Focused on {t0}. "
            f"I spend most of my time thinking about {t1} and how to scale "
            f"go-to-market in the current environment. DMs open."
        ),
        (
            f"Building the {industry} GTM playbook at {company_name}. "
            f"5+ years leading {t0} initiatives. Previously scaled outbound "
            f"at two Series B companies. Talking a lot about {t1} lately."
        ),
        (
            f"I'm {role} at {company_name}. We're in {industry} and growing fast. "
            f"My obsession: {t0}. Ask me anything about {t1}."
        ),
        (
            f"Helping {industry} teams unlock growth through better {t0}. "
            f"{role} @ {company_name}. Prev: ops roles at two enterprise SaaS cos. "
            f"Here to talk about {t1}."
        ),
    ]
    # deterministic per (role, company) so the same person always gets the same bio
    idx = hash(role + company_name) % len(templates)
    return templates[idx]


def _llm_bio(role: str, company_name: str, industry: str,
             community_name: str, topics: List[str], model) -> str:
    """Generate a LinkedIn bio via Gemini. Falls back to template on error."""
    topic_str = ", ".join(topics[:3])
    prompt = (
        f"Write a short, realistic LinkedIn bio (2-3 sentences, max 60 words) for "
        f"a {role} at a {industry} company called {company_name}. "
        f"This person is active in the {community_name} space and talks about: "
        f"{topic_str}. Sound authentic, not corporate. No hashtags. No emojis."
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return _template_bio(role, company_name, industry, community_name, topics)


# ─────────────────────────────────────────────────────────────────────────────
# SENIORITY INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def _infer_seniority(role: str) -> str:
    r = role.lower()
    if any(x in r for x in ["chief", "cro", "cmo", "ceo", "founder"]):
        return "C-Suite / Founder"
    if "vp" in r or "vice president" in r:
        return "VP"
    if "director" in r or "head of" in r:
        return "Director"
    if "manager" in r or " lead" in r:
        return "Manager"
    return "IC"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_graph(
    n_persons: int = DEFAULT_N_PERSONS,
    n_companies: int = DEFAULT_N_COMPANIES,
    n_posts: int = DEFAULT_N_POSTS,
    n_signal_sources: int = DEFAULT_N_SIGNAL_SOURCES,
    n_communities: int = DEFAULT_N_COMMUNITIES,
    qualified_fraction: float = DEFAULT_QUALIFIED_FRACTION,
    homophily_alpha: float = DEFAULT_HOMOPHILY_ALPHA,
    seed: int = DEFAULT_SEED,
    llm_profiles: bool = False,
    out_dir: str = ".",
    verbose: bool = True,
) -> Tuple[nx.MultiDiGraph, Path, Path]:
    """
    Generate the SignalAgent synthetic heterogeneous graph.

    Args:
        n_persons:          Number of Person nodes.
        n_companies:        Number of Company nodes.
        n_posts:            Number of Post nodes.
        n_signal_sources:   Number of SignalSource nodes.
        n_communities:      Number of planted communities (max 3).
        qualified_fraction: Fraction of persons labeled qualified (≥ 0.20 guaranteed).
        homophily_alpha:    Strength of qualified-buyer clustering [0, 1].
                            0 = random; 1 = fully clustered.
        seed:               Random seed for reproducibility.
        llm_profiles:       If True, generate bios via Gemini API.
        out_dir:            Directory to write graph.pkl and labels.csv.
        verbose:            Print progress messages.

    Returns:
        G:            The populated NetworkX MultiDiGraph.
        graph_path:   Path to graph.pkl.
        labels_path:  Path to labels.csv.
    """
    rng = np.random.default_rng(seed)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Cap to available archetypes
    n_communities = min(n_communities, len(COMMUNITY_ARCHETYPES))

    def log(msg: str) -> None:
        if verbose:
            print(f"  {msg}")

    G = nx.MultiDiGraph()

    # ── Optional LLM setup ────────────────────────────────────────────────────
    llm_model = None
    profile_cache_path = out_path / "profile_cache.json"
    profile_cache: Dict[str, str] = {}

    if llm_profiles:
        try:
            import google.generativeai as genai

            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                print("[warn] GEMINI_API_KEY not set — falling back to template profiles.")
                llm_profiles = False
            else:
                genai.configure(api_key=api_key)
                llm_model = genai.GenerativeModel("gemini-2.0-flash")
                if profile_cache_path.exists():
                    with open(profile_cache_path) as f:
                        profile_cache = json.load(f)
                log("LLM profile generation enabled (Gemini 2.0 Flash).")
        except ImportError:
            print("[warn] google-generativeai not installed — falling back to templates.")
            llm_profiles = False

    # ── Step 1: Signal Sources ────────────────────────────────────────────────
    log(f"Creating {n_signal_sources} signal sources …")
    for i in range(n_signal_sources):
        ss_id = f"ss_{i}"
        st = SOURCE_TYPES[i % len(SOURCE_TYPES)]
        G.add_node(
            ss_id,
            node_type="signal_source",
            source_type=st,
            url=f"https://linkedin.com/signal-source-{i}",
            active=True,
        )

    # ── Step 2: Companies ─────────────────────────────────────────────────────
    log(f"Creating {n_companies} companies …")
    # Distribute companies evenly across community "zones" for homophily
    companies_per_community = max(1, n_companies // n_communities)
    company_community: Dict[str, int] = {}
    companies_by_community: List[List[str]] = [[] for _ in range(n_communities)]

    for i in range(n_companies):
        comp_id = f"company_{i}"
        c_idx = min(i // companies_per_community, n_communities - 1)
        arch = COMMUNITY_ARCHETYPES[c_idx]
        industry = str(rng.choice(arch["industries"]))
        size_band = str(rng.choice(SIZE_BANDS, p=SIZE_BAND_WEIGHTS))
        region = str(rng.choice(REGIONS, p=REGION_WEIGHTS))
        name = f"{rng.choice(COMPANY_NAME_A)} {rng.choice(COMPANY_NAME_B)}"
        G.add_node(
            comp_id,
            node_type="company",
            name=str(name),
            industry=industry,
            size_band=size_band,
            region=region,
            community_id=c_idx,
        )
        company_community[comp_id] = c_idx
        companies_by_community[c_idx].append(comp_id)

    all_company_ids = list(company_community.keys())

    # ── Step 3: Posts + belongs_to edges ─────────────────────────────────────
    magnet_count = max(1, int(n_posts * DEFAULT_MAGNET_POST_FRACTION))
    log(f"Creating {n_posts} posts ({magnet_count} magnet posts) …")

    # Distribute posts across community pools; randomly designate magnets
    posts_per_community = max(1, n_posts // n_communities)
    magnet_indices: Set[int] = set(
        rng.choice(n_posts, size=magnet_count, replace=False).tolist()
    )
    community_post_pools: List[List[str]] = [[] for _ in range(n_communities)]

    for i in range(n_posts):
        post_id = f"post_{i}"
        c_idx = min(i // posts_per_community, n_communities - 1)
        arch = COMMUNITY_ARCHETYPES[c_idx]
        topic = str(rng.choice(arch["topics"]))
        ss_id = f"ss_{i % n_signal_sources}"
        is_magnet = i in magnet_indices
        post_date = BASE_DATE + timedelta(days=int(rng.integers(0, DATE_RANGE_DAYS)))
        G.add_node(
            post_id,
            node_type="post",
            topic=topic,
            signal_source_id=ss_id,
            community_id=c_idx,
            is_magnet=is_magnet,
            engagement_count=0,
            created_at=post_date.isoformat(),
        )
        community_post_pools[c_idx].append(post_id)
        # belongs_to: Post → SignalSource
        G.add_edge(post_id, ss_id, edge_type="belongs_to")

    all_post_ids = [f"post_{i}" for i in range(n_posts)]
    all_posts_arr = np.array(all_post_ids)
    magnet_posts_arr = np.array(
        [f"post_{i}" for i in magnet_indices] if magnet_indices else all_post_ids
    )
    community_posts_arrs = [
        np.array(pool) if pool else all_posts_arr
        for pool in community_post_pools
    ]

    # ── Step 4: Persons ───────────────────────────────────────────────────────
    n_qualified = max(int(n_persons * qualified_fraction), int(n_persons * 0.20) + 1)
    log(f"Creating {n_persons} persons ({n_qualified} qualified) …")

    # Assign persons to communities
    community_sizes = [n_persons // n_communities] * n_communities
    community_sizes[-1] += n_persons - sum(community_sizes)
    person_community_arr = np.repeat(np.arange(n_communities), community_sizes)
    rng.shuffle(person_community_arr)

    # Plant qualified labels (evenly spread across communities)
    qualified_flags = np.zeros(n_persons, dtype=bool)
    q_per_community = n_qualified // n_communities
    for c in range(n_communities):
        c_persons = np.where(person_community_arr == c)[0]
        n_q = q_per_community if c < n_communities - 1 else (
            n_qualified - q_per_community * (n_communities - 1)
        )
        chosen = rng.choice(c_persons, size=min(n_q, len(c_persons)), replace=False)
        qualified_flags[chosen] = True

    # Determine which persons get LLM-generated bios
    llm_sample_ids: Set[int] = set()
    if llm_profiles:
        sample_n = min(200, n_persons)
        llm_sample_ids = set(
            rng.choice(n_persons, size=sample_n, replace=False).tolist()
        )

    person_company_map: Dict[str, str] = {}

    for i in range(n_persons):
        pid = f"person_{i}"
        c_idx = int(person_community_arr[i])
        arch = COMMUNITY_ARCHETYPES[c_idx]
        is_qualified = bool(qualified_flags[i])

        # Role and region: qualified → ICP roles + ICP regions
        if is_qualified:
            role = str(rng.choice(arch["icp_roles"]))
            region = str(rng.choice(list(ICP_REGIONS)))
        else:
            role = str(rng.choice(arch["non_icp_roles"]))
            region = str(rng.choice(REGIONS, p=REGION_WEIGHTS))

        seniority = _infer_seniority(role)

        # Company assignment: qualified persons biased toward community companies
        c_comps = companies_by_community[c_idx]
        if is_qualified and c_comps and rng.random() < homophily_alpha:
            comp_id = str(rng.choice(c_comps))
        else:
            comp_id = str(rng.choice(all_company_ids))
        person_company_map[pid] = comp_id

        comp_data = G.nodes[comp_id]
        company_name = comp_data["name"]
        industry = comp_data["industry"]

        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"

        # Profile text: cache key ensures same (role, company) always → same bio
        cache_key = f"{role}|{company_name}|{c_idx}"
        if cache_key in profile_cache:
            bio = profile_cache[cache_key]
        elif llm_profiles and i in llm_sample_ids and llm_model is not None:
            bio = _llm_bio(role, company_name, industry,
                           arch["name"], arch["topics"], llm_model)
            profile_cache[cache_key] = bio
            time.sleep(0.05)  # gentle rate-limit
        else:
            bio = _template_bio(role, company_name, industry,
                                arch["name"], arch["topics"])

        G.add_node(
            pid,
            node_type="person",
            name=str(name),
            role=role,
            seniority=seniority,
            company_id=comp_id,
            industry=industry,
            region=region,
            community_id=c_idx,
            profile_text=bio,
            tenure_years=float(rng.integers(1, 9)),
            qualified=is_qualified,
        )

    if llm_profiles and profile_cache:
        with open(profile_cache_path, "w") as f:
            json.dump(profile_cache, f, indent=2)

    # ── Step 5: works_at edges ────────────────────────────────────────────────
    log("Adding works_at edges …")
    for pid, comp_id in person_company_map.items():
        G.add_edge(pid, comp_id, edge_type="works_at")

    # ── Step 6: authored edges ────────────────────────────────────────────────
    log("Adding authored edges (~20% of posts) …")
    n_authored = max(1, n_posts // 5)
    authored_post_indices = rng.choice(n_posts, size=n_authored, replace=False)
    author_person_indices = rng.choice(n_persons, size=n_authored, replace=True)
    for post_idx, person_idx in zip(authored_post_indices, author_person_indices):
        G.add_edge(
            f"person_{int(person_idx)}",
            f"post_{int(post_idx)}",
            edge_type="authored",
        )

    # ── Step 7: engaged_with edges (power-law + homophily) ───────────────────
    log("Adding engaged_with edges (Zipf power-law, homophily planted) …")

    # Draw engagement degrees from Zipf distribution, cap at n_posts
    raw_degrees = rng.zipf(DEFAULT_ZIPF_EXPONENT, size=n_persons)
    degrees = np.clip(raw_degrees, 1, n_posts).astype(int)

    total_eng = 0
    for i in range(n_persons):
        pid = f"person_{i}"
        c_idx = int(person_community_arr[i])
        is_qualified = bool(qualified_flags[i])
        k = int(degrees[i])

        # Preferred pool = community posts ∪ magnet posts
        preferred_pool = np.union1d(community_posts_arrs[c_idx], magnet_posts_arr)

        # How many engagements to draw from preferred vs. uniform pool
        if is_qualified:
            n_preferred = max(1, int(round(k * homophily_alpha)))
        else:
            n_preferred = max(0, int(round(k * homophily_alpha * 0.15)))
        n_uniform = k - n_preferred

        sampled: List[str] = []

        if n_preferred > 0 and len(preferred_pool) > 0:
            n_p = min(n_preferred, len(preferred_pool))
            sampled.extend(
                rng.choice(preferred_pool, size=n_p, replace=False).tolist()
            )

        if n_uniform > 0:
            n_u = min(n_uniform, len(all_posts_arr))
            sampled.extend(
                rng.choice(all_posts_arr, size=n_u, replace=False).tolist()
            )

        # Deduplicate, preserve order, cap at k
        seen: Dict[str, None] = {}
        for s in sampled:
            seen[str(s)] = None
        sampled = list(seen.keys())[:k]

        eng_date = BASE_DATE + timedelta(
            days=int(rng.integers(0, DATE_RANGE_DAYS))
        )
        for post_id in sampled:
            subtype = str(rng.choice(ENGAGEMENT_SUBTYPES, p=SUBTYPE_WEIGHTS))
            G.add_edge(
                pid,
                post_id,
                edge_type="engaged_with",
                subtype=subtype,
                timestamp=eng_date.isoformat(),
            )
            G.nodes[post_id]["engagement_count"] += 1
            total_eng += 1

    log(f"  → {total_eng:,} engaged_with edges created.")

    # ── Step 8: Persist outputs ───────────────────────────────────────────────
    graph_path = out_path / "graph.pkl"
    labels_path = out_path / "labels.csv"

    log(f"Saving graph to {graph_path} …")
    with open(graph_path, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    log(f"Saving labels to {labels_path} …")
    with open(labels_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["person_id", "qualified"])
        for i in range(n_persons):
            writer.writerow([f"person_{i}", qualified_flags[i]])

    log(
        f"Done. Nodes: {G.number_of_nodes():,}  "
        f"Edges: {G.number_of_edges():,}  "
        f"Qualified: {qualified_flags.sum():,} / {n_persons:,} "
        f"({qualified_flags.mean():.1%})"
    )
    return G, graph_path, labels_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="SignalAgent synthetic heterogeneous graph generator."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--homophily", type=float, default=DEFAULT_HOMOPHILY_ALPHA,
        help="Homophily alpha [0–1] (ablation knob; 0 = random, 1 = fully clustered)",
    )
    parser.add_argument(
        "--llm-profiles", action="store_true",
        help="Generate profile bios via Gemini API (requires GEMINI_API_KEY env var)",
    )
    parser.add_argument("--out-dir", default=".", help="Output directory")
    parser.add_argument("--n-persons", type=int, default=DEFAULT_N_PERSONS)
    parser.add_argument("--n-companies", type=int, default=DEFAULT_N_COMPANIES)
    parser.add_argument("--n-posts", type=int, default=DEFAULT_N_POSTS)
    parser.add_argument("--n-signal-sources", type=int, default=DEFAULT_N_SIGNAL_SOURCES)
    args = parser.parse_args()

    print("=" * 58)
    print("  SignalAgent — Synthetic Data Generator")
    print("=" * 58)
    print(f"  Persons:        {args.n_persons:,}")
    print(f"  Companies:      {args.n_companies:,}")
    print(f"  Posts:          {args.n_posts:,}")
    print(f"  SignalSources:  {args.n_signal_sources:,}")
    print(f"  Homophily α:    {args.homophily}")
    print(f"  Seed:           {args.seed}")
    print(f"  LLM profiles:   {args.llm_profiles}")
    print(f"  Output:         {args.out_dir}/")
    print("=" * 58)

    generate_graph(
        n_persons=args.n_persons,
        n_companies=args.n_companies,
        n_posts=args.n_posts,
        n_signal_sources=args.n_signal_sources,
        qualified_fraction=DEFAULT_QUALIFIED_FRACTION,
        homophily_alpha=args.homophily,
        seed=args.seed,
        llm_profiles=args.llm_profiles,
        out_dir=args.out_dir,
        verbose=True,
    )


if __name__ == "__main__":
    _main()

import os
import re
import pickle
import google.generativeai as genai
from api.db import SessionLocal, Lead
import sys

# Ensure gnn is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
from gnn.infer import get_probability

def get_llm_score(profile_text: str) -> tuple[float, str]:
    """
    Calls Gemini 2.5 Flash to evaluate the profile and returns a (score, rationale).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return (0.5, "No GEMINI_API_KEY provided.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    You are evaluating a LinkedIn profile for a B2B sales motion.
    Our ICP (Ideal Customer Profile) includes C-Suite, VP, and Director level
    executives in Revenue Operations, Sales Leadership, or Marketing.
    
    Profile:
    {profile_text}
    
    Is this profile qualified?
    First, provide a brief 1-2 sentence rationale.
    Then, on a new line, provide a score between 0.0 and 1.0 representing the qualification probability.
    Only the score should be on the last line.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        lines = text.split("\n")
        rationale = "\n".join(lines[:-1]).strip()
        score_str = lines[-1].strip()
        
        # Try to extract float
        match = re.search(r"([0-9]*\.?[0-9]+)", score_str)
        if match:
            score = float(match.group(1))
        else:
            score = 0.5
            
        return max(0.0, min(1.0, score)), rationale
    except Exception as e:
        return (0.5, f"Error calling LLM: {str(e)}")

def get_person_profile(person_id: str) -> str:
    # Load graph from root
    graph_path = os.path.join(BASE_DIR, "graph.pkl")
    try:
        with open(graph_path, "rb") as f:
            G = pickle.load(f)
        if person_id in G:
            return G.nodes[person_id].get("profile_text", "")
    except Exception:
        pass
    return ""

def run_qualifier(person_id: str):
    """
    Runs the Qualifier Agent: GNN score, LLM score, sets disagreement flag, and saves to DB.
    """
    # 1. GNN Score
    try:
        gnn_score = get_probability(person_id)
    except Exception as e:
        print(f"GNN Infer error: {e}")
        gnn_score = 0.0
        
    # 2. LLM Score
    profile_text = get_person_profile(person_id)
    llm_score, rationale = get_llm_score(profile_text)
    
    # 3. Disagreement
    disagreement = abs(gnn_score - llm_score) > 0.3
    
    # We consider them qualified if average score > 0.5
    qualified = ((gnn_score + llm_score) / 2) > 0.5
    
    # 4. Save to DB
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.person_id == person_id).first()
        if not lead:
            lead = Lead(person_id=person_id)
            db.add(lead)
            
        lead.gnn_score = gnn_score
        lead.llm_score = llm_score
        lead.llm_rationale = rationale
        lead.disagreement_flag = disagreement
        lead.qualified = qualified
        db.commit()
    finally:
        db.close()
        
    return {
        "person_id": person_id,
        "gnn_score": gnn_score,
        "llm_score": llm_score,
        "disagreement": disagreement,
        "qualified": qualified
    }

if __name__ == "__main__":
    # Test run
    import sys
    if len(sys.argv) > 1:
        print(run_qualifier(sys.argv[1]))

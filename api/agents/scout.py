import os
import random
import pickle
from api.agents.qualifier import run_qualifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_scout_agent(signal_source_id: int, source_url: str):
    """
    Simulates the Scout Agent by finding 5-10 random people who engaged with
    posts in the synthetic graph, then runs the Qualifier Agent on each.
    The source URL is passed through to inform the LLM scoring logic.
    """
    graph_path = os.path.join(BASE_DIR, "graph.pkl")
    try:
        with open(graph_path, "rb") as f:
            G = pickle.load(f)
    except Exception as e:
        print(f"Scout Error loading graph: {e}")
        return

    # Collect all person nodes
    persons = [n for n, d in G.nodes(data=True) if d.get("node_type") == "person"]
    if not persons:
        print("Scout Error: No person nodes found in graph.")
        return

    # Sample 5-10 engagers to simulate the Scout discovering them from the source
    num_leads = random.randint(5, 10)
    selected_persons = random.sample(persons, min(num_leads, len(persons)))

    print(f"Scout Agent [{source_url}]: Discovered {len(selected_persons)} engagers. Running qualifier...")

    for pid in selected_persons:
        try:
            result = run_qualifier(pid, source_url=source_url)
            print(
                f"Scout Agent: Qualified {pid} — "
                f"GNN={result['gnn_score']:.2f}, LLM={result['llm_score']:.2f}, "
                f"Qualified={result['qualified']}"
            )
        except Exception as e:
            print(f"Error running qualifier for {pid}: {e}")

    print("Scout Agent: Finished qualifying leads.")

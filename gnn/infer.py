import torch
import pickle
from gnn.model import PersonClassifier
from gnn.train import load_data

# Cache the loaded data and model so we don't reload on every inference call
_DATA_CACHE = None
_MODEL_CACHE = None

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_probability(person_id: str) -> float:
    """
    Given a person_id, returns predicted probability of being qualified.
    """
    global _DATA_CACHE, _MODEL_CACHE
    
    if _DATA_CACHE is None:
        data, num_roles, id_maps = load_data()
        
        with open(os.path.join(BASE_DIR, "meta.pkl"), "rb") as f:
            metadata = pickle.load(f)
            
        model = PersonClassifier(hidden_dim=32, num_roles=metadata["num_roles"], edge_types=metadata["edge_types"])
        model.load_state_dict(torch.load(os.path.join(BASE_DIR, "model.pt"), weights_only=True))
        model.eval()
        
        _DATA_CACHE = (data, id_maps)
        _MODEL_CACHE = model

    data, id_maps = _DATA_CACHE
    model = _MODEL_CACHE
    
    if person_id not in id_maps["person"]:
        raise ValueError(f"Person ID '{person_id}' not found in the graph.")
        
    idx = id_maps["person"][person_id]
    
    with torch.no_grad():
        x_dict = {
            "person_role": data["person"].person_role,
            "person_seniority": data["person"].person_seniority,
            "person_tenure": data["person"].person_tenure,
            "post_engagement": data["post"].post_engagement,
            "post_topic": data["post"].post_topic,
            "company": data["company"].company,
            "signal_source": data["signal_source"].signal_source,
        }
        logits = model(x_dict, data.edge_index_dict)
        prob = torch.sigmoid(logits[idx]).item()
        
    return prob

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pid = sys.argv[1]
        try:
            print(f"Probability for {pid}: {get_probability(pid):.4f}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python infer.py <person_id>")

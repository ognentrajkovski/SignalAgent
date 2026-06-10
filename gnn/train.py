import pickle
import csv
import torch
import torch.nn.functional as F
import numpy as np
import torch_geometric.transforms as T
from torch_geometric.data import HeteroData
from gnn.model import PersonClassifier

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_data():
    with open(os.path.join(BASE_DIR, "graph.pkl"), "rb") as f:
        G = pickle.load(f)

    labels = {}
    with open(os.path.join(BASE_DIR, "labels.csv"), "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[row["person_id"]] = (row["qualified"].strip().lower() in ("true", "1"))

    # Parse node features
    nodes_by_type = {"person": [], "company": [], "post": [], "signal_source": []}
    for n, d in G.nodes(data=True):
        nodes_by_type[d["node_type"]].append(n)

    id_maps = {ntype: {n: i for i, n in enumerate(nodes)} for ntype, nodes in nodes_by_type.items()}
    
    # Build Role Vocab
    roles = []
    for n in nodes_by_type["person"]:
        roles.append(str(G.nodes[n].get("role", "unknown")))
    unique_roles = list(set(roles))
    role_to_idx = {r: i for i, r in enumerate(unique_roles)}

    # Person Features
    person_role_idx = []
    person_seniority = []
    person_tenure = []
    person_y = []
    
    seniority_map = {"C-Suite / Founder": 5, "VP": 4, "Director": 3, "Manager": 2, "IC": 1}

    for n in nodes_by_type["person"]:
        d = G.nodes[n]
        person_role_idx.append(role_to_idx[str(d.get("role", "unknown"))])
        sen_str = str(d.get("seniority", "IC"))
        person_seniority.append(float(seniority_map.get(sen_str, 1)))
        person_tenure.append(float(d.get("tenure_years", 1.0)))
        person_y.append(1.0 if labels.get(n, False) else 0.0)

    # Post Features
    post_eng = []
    post_topic = [] # 16-dim random
    for n in nodes_by_type["post"]:
        d = G.nodes[n]
        post_eng.append(float(d.get("engagement_count", 0)))
        post_topic.append(np.random.randn(16))

    data = HeteroData()
    data["person"].person_role = torch.tensor(person_role_idx, dtype=torch.long)
    data["person"].person_seniority = torch.tensor(person_seniority, dtype=torch.float)
    data["person"].person_tenure = torch.tensor(person_tenure, dtype=torch.float)
    data["person"].y = torch.tensor(person_y, dtype=torch.float)
    
    data["post"].post_engagement = torch.tensor(post_eng, dtype=torch.float)
    data["post"].post_topic = torch.tensor(np.array(post_topic), dtype=torch.float)
    
    # Dummy features for the rest
    data["company"].company = torch.ones(len(nodes_by_type["company"]), 1)
    data["signal_source"].signal_source = torch.ones(len(nodes_by_type["signal_source"]), 1)

    # Edges
    edges_by_type = {}
    for u, v, d in G.edges(data=True):
        u_type = G.nodes[u]["node_type"]
        v_type = G.nodes[v]["node_type"]
        edge_type = d["edge_type"]
        
        edge_key = (u_type, edge_type, v_type)
        edges_by_type.setdefault(edge_key, [[], []])
        edges_by_type[edge_key][0].append(id_maps[u_type][u])
        edges_by_type[edge_key][1].append(id_maps[v_type][v])

    for edge_key, (sources, targets) in edges_by_type.items():
        data[edge_key].edge_index = torch.tensor([sources, targets], dtype=torch.long)

    data = T.ToUndirected()(data)
    
    # 80/20 train/val split
    num_persons = len(nodes_by_type["person"])
    indices = np.random.permutation(num_persons)
    split_idx = int(num_persons * 0.8)
    
    train_mask = torch.zeros(num_persons, dtype=torch.bool)
    val_mask = torch.zeros(num_persons, dtype=torch.bool)
    
    train_mask[indices[:split_idx]] = True
    val_mask[indices[split_idx:]] = True
    
    data["person"].train_mask = train_mask
    data["person"].val_mask = val_mask
    
    return data, len(unique_roles), id_maps

def train():
    data, num_roles, _ = load_data()
    
    # We collect only edge types that exist in the edge_index_dict
    edge_types = list(data.edge_index_dict.keys())
    
    model = PersonClassifier(hidden_dim=32, num_roles=num_roles, edge_types=edge_types)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    print("Training 2-Layer R-GCN...")
    for epoch in range(1, 101):
        model.train()
        optimizer.zero_grad()
        
        # Prepare x_dict
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
        train_mask = data["person"].train_mask
        
        loss = F.binary_cross_entropy_with_logits(logits[train_mask], data["person"].y[train_mask])
        loss.backward()
        optimizer.step()
        
        model.eval()
        with torch.no_grad():
            val_mask = data["person"].val_mask
            val_logits = logits[val_mask]
            val_preds = (torch.sigmoid(val_logits) > 0.5).float()
            val_y = data["person"].y[val_mask]
            acc = (val_preds == val_y).float().mean().item()
            
        if epoch % 10 == 0:
            print(f"Epoch {epoch:03d} | Loss: {loss.item():.4f} | Val Accuracy: {acc:.4f}")

    torch.save(model.state_dict(), "model.pt")
    
    # Save metadata for inference
    metadata = {
        "num_roles": num_roles,
        "edge_types": edge_types
    }
    with open("meta.pkl", "wb") as f:
        pickle.dump(metadata, f)

if __name__ == "__main__":
    train()

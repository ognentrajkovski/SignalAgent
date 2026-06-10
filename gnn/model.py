import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, SAGEConv

class PersonClassifier(nn.Module):
    def __init__(self, hidden_dim: int, num_roles: int, edge_types: list):
        super().__init__()
        
        # Person features: role embedding (16-dim), seniority (1-dim), tenure (1-dim)
        self.role_emb = nn.Embedding(num_roles, 16)
        
        # Initial feature projections to hidden_dim
        # Person: 16 (role) + 1 (seniority) + 1 (tenure) = 18 dims
        self.lin_person = nn.Linear(18, hidden_dim)
        
        # Post: 1 (engagement_count) + 16 (topic embedding) = 17 dims
        self.lin_post = nn.Linear(17, hidden_dim)
        
        # Dummy projections for other node types to keep dimensions consistent
        self.lin_company = nn.Linear(1, hidden_dim)
        self.lin_source = nn.Linear(1, hidden_dim)
        
        # 2-Layer R-GCN via HeteroConv
        self.conv1 = HeteroConv({
            edge_type: SAGEConv(hidden_dim, hidden_dim) for edge_type in edge_types
        }, aggr='sum')
        
        self.conv2 = HeteroConv({
            edge_type: SAGEConv(hidden_dim, hidden_dim) for edge_type in edge_types
        }, aggr='sum')
        
        # Classification head for Person nodes (qualified / unqualified)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(self, x_dict, edge_index_dict):
        # 1. Feature processing
        person_x = torch.cat([
            self.role_emb(x_dict["person_role"]), 
            x_dict["person_seniority"].unsqueeze(1), 
            x_dict["person_tenure"].unsqueeze(1)
        ], dim=-1)
        
        post_x = torch.cat([
            x_dict["post_engagement"].unsqueeze(1),
            x_dict["post_topic"]
        ], dim=-1)
        
        h_dict = {
            "person": F.relu(self.lin_person(person_x)),
            "post": F.relu(self.lin_post(post_x)),
            "company": F.relu(self.lin_company(x_dict["company"])),
            "signal_source": F.relu(self.lin_source(x_dict["signal_source"]))
        }
        
        # 2. Message Passing Layer 1
        h_dict = self.conv1(h_dict, edge_index_dict)
        h_dict = {k: F.relu(v) for k, v in h_dict.items()}
        
        # 3. Message Passing Layer 2
        h_dict = self.conv2(h_dict, edge_index_dict)
        h_dict = {k: F.relu(v) for k, v in h_dict.items()}
        
        # 4. Classification
        logits = self.classifier(h_dict["person"])
        return logits.squeeze(-1)

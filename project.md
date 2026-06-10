# SignalAgent — Relational, Agent-Driven GTM for LinkedIn Signals

## What It Is

SignalAgent is a go-to-market platform that turns LinkedIn engagement signals into autonomous, context-aware outreach. You point it at signal sources — competitor posts, thought-leader accounts, hashtags — and a layered system of agents harvests engagers, qualifies them against your ICP using both LLM reasoning and a relational machine learning model trained on the engagement graph, then runs a personalized outreach playbook for each qualified lead. A Strategy Agent watches the whole operation and updates the plan based on what's working.

The core thesis: outreach grounded in a **relational model** of who-engages-with-what produces better targeting, better messaging, and better insights than the row-based tooling (Clay, HeyReach, Apollo) the market currently runs on.

---

## User-Facing Surfaces

### 1. Signal Sources Panel
The entry point. Users declare what to watch:
- LinkedIn post URLs, accounts, or hashtags
- An ICP definition: industry, company size band, role keywords, seniority, geography

The ICP supports natural-language clauses; these become both LLM prompt context and features for the relational model.

### 2. Lead Pipeline
A ranked list of qualified leads with full signal provenance:
- Lead identity and role
- Which signal source surfaced them
- Cross-signal engagement count (how many watched posts they touched)
- Relational model score + LLM qualifier score, side by side
- A "Disagreements" filter highlighting cases where one head overrode the other — the highest-value leads to inspect

Clicking a lead opens that lead's **agent timeline**.

### 3. Strategy Dashboard
Aggregate operational state:
- Which signal sources are converting and at what rates
- Which message angles are generating replies
- Lookalike signal source recommendations (accounts/posts not yet watched but embedding-close to converting ones)
- Emergent buyer communities detected in the engagement graph

### 4. Graph View *(demo centerpiece)*
A force-directed rendering of the engagement graph:
- Qualified leads highlighted
- Communities shaded
- Lookalike recommendations pulsing

Not required for the product to function, but makes the relational thesis immediately legible in a screenshot.

---

## Agent Architecture

Three bounded agent classes, each with a well-defined job.

### Scout Agent
- Runs on a schedule against each signal source
- Returns: `(person, post, engagement_type, timestamp)` events
- Writes new **nodes and edges** into the graph store
- In the demo: mocked against a synthetic dataset (LinkedIn scraping is fragile, legally murky, and orthogonal to the thesis)

### Qualifier Agent *(main intellectual move)*
A deliberately two-headed system:

| Head | Mechanism | What it sees |
|---|---|---|
| **LLM Head** | Prompt-based reasoning over enriched profile (Apollo data, bio, recent posts) | Profile-level signals |
| **Relational Head** | GNN over the heterogeneous engagement graph | Neighborhood structure — who else engaged with the same posts, how that engagement pattern compares to known qualified buyers |

Outputs are combined via a **weighted blend** (weights are a tunable hyperparameter for ablation). Disagreements — "LLM rejected, GNN accepted" — are surfaced in the UI; these are exactly the cases where the relational signal adds value over profile-only reasoning.

### Lead Agent
Spawned per qualified lead. Owns that lead end-to-end.

- **Memory**: full history of everything known and every move made
- **Toolset**: `like_post`, `draft_connection_request`, `send_email`, `wait`, `escalate_to_human`
- **Planning loop**: given current state → what's the next move?
- **Grounding**: before committing to a move, the agent queries the **reply-prediction model** to estimate reply probability for the proposed message, given sender + lead + graph context. The agent picks the move with the best expected outcome, not just the move the LLM finds most natural.
- Full reasoning trace visible in the lead timeline.

### Strategy Agent
Runs on a slower cadence (daily in the demo). Produces three outputs:

1. **Performance attribution** — which signal sources, message angles, and ICP segments are converting at what rates
2. **Lookalike recommendations** — using GNN node embeddings, finds un-watched accounts/posts that sit near the embedding centroid of converting sources; recommends adding them to the watch list
3. **Community insights** — applies Louvain / embedding k-means to surface emergent buyer segments not currently targeted, with LLM-generated labels (e.g., "RevOps tooling enthusiasts, 73% ICP match")

---

## Relational ML Core

One heterogeneous GNN, four downstream tasks — all wired into the agent loop. This is the defensible core of the project.

### The Graph Schema

**Nodes (typed):**

| Node Type | Key Features |
|---|---|
| `Person` | Role embedding, seniority, tenure, profile text embedding |
| `Company` | Industry, size band, region |
| `Post` | Topic embedding, engagement counts |
| `Message` | Channel, length, personalization signals |
| `SignalSource` | Source type, watch-list membership |

**Edges (typed):**

| Edge | Direction | Subtypes |
|---|---|---|
| `engaged_with` | Person → Post | like / comment / reshare |
| `works_at` | Person → Company | — |
| `authored` | Person → Post | — |
| `received` | Person → Message | — |
| `replied_to` | Person → Message | — |
| `belongs_to` | Post → SignalSource | — |

This is a **heterogeneous information network**, which dictates the model family.

---

### Model 1 — Lead Qualification (Node Classification)

- **Architecture**: Heterogeneous GNN — R-GCN or HGT (Heterogeneous Graph Transformer)
- **Task**: Predict `qualified` label on `Person` nodes
- **Training**: Bootstrapped from a hand-labeled seed set + weak supervision
  - Positives: known closed-won leads in synthetic dataset
  - Negatives: leads explicitly rejected by ICP rules
  - Unlabeled: handled with positive-unlabeled (PU) learning or self-training
- **What it learns**: Engagement neighborhoods predict qualification. A person whose engaged-with posts overlap heavily with posts engaged by known qualified buyers is likely qualified — even if their profile alone is ambiguous. This is the pattern the LLM-only qualifier structurally cannot see.

### Model 2 — Lookalike Expansion (Embedding Similarity / Link Prediction)

- Once the GNN is trained, every node has a learned embedding
- For **signal source recommendation**: take the centroid of embeddings for posts/accounts that produced qualified leads → find nearest neighbors among un-watched candidates
- For **lookalike leads**: find people who embed near closed-won customers but aren't yet in the pipeline
- This is the relational version of ICP — geometric matching in a space learned from actual engagement behavior, not rule matching

### Model 3 — Reply Prediction (Edge Prediction)

- **Task**: Predict probability of a `replied_to` edge forming between a candidate `Message` and a target `Person`
- **Conditioning**: sender + lead embeddings + message features (channel, length, personalization, signal context)
- Can share the GNN encoder with a separate prediction head
- Lead Agents query this model during planning; even on synthetic data it discriminates clearly: cold connection requests score ~0.12 vs. warm openers referencing the lead's specific engagement ~0.38

### Model 4 — Community Detection (Segment Discovery)

- **Methods**: Louvain on the engagement subgraph, or k-means on learned node embeddings
- **LLM labeling**: each cluster is summarized by an LLM reading the top posts and profiles in the cluster
- **Strategy Agent use**: surfaces clusters with high ICP-match density that are under-represented in the current pipeline

---

## Synthetic Data Generator

The believability of the entire demo hinges on this. It is a first-class component.

**Generated graph properties:**
- **Scale**: ~5,000 Person nodes, ~500 Posts, ~50 SignalSources, ~50,000 engagement edges
- **Power-law degree distribution**: most people engage rarely, a few engage constantly
- **Homophily**: qualified buyers cluster together in engagement patterns
- **Planted communities**: so community detection has real structure to find
- **"Magnet" posts**: a small set that disproportionately attracts qualified leads, so signal-source recommendation has something to discover
- **Realistic profile text**: generated by an LLM conditioned on assigned role and company

**Parameterized for ablation**: turn off homophily → GNN loses its advantage over the LLM. This produces a clean ablation chart for the writeup.

---

## What's Built vs. Mocked

| Component | Status | Rationale |
|---|---|---|
| Heterogeneous graph store + schema | **Built** | Core thesis |
| Synthetic data generator | **Built** | Core thesis |
| GNN (qualification + embedding + reply-prediction heads) | **Built** | Core thesis |
| Community detection + LLM labeling pipeline | **Built** | Core thesis |
| Qualifier Agent (two-headed + disagreement surfacing) | **Built** | Core thesis |
| Lead Agent planning loop + reply-prediction grounding | **Built** | Core thesis |
| Strategy Agent attribution + recommendation logic | **Built** | Core thesis |
| Lead timeline UI | **Built** | Core thesis |
| Graph visualization (Graph View) | **Built** | Core thesis |
| Real LinkedIn scraping | **Mocked** | Fragile, legally murky, orthogonal to thesis |
| Real LinkedIn/email sending | **Mocked** | Lead Agents record moves only — no account integration |
| Apollo enrichment | **Mocked** | Thin wrapper returning synthetic-but-plausible firmographic data |
| Authentication + multi-tenancy | **Mocked** | Single-user demo only |

The mocked pieces are all things existing tools (HeyReach, Clay, Apollo) already do well. Every built piece is something they don't do at all.

---

## Demo Run Narrative (5–7 min)

1. **Empty state** — ICP defined: mid-market SaaS RevOps leaders, North America, 50–500 employees
2. **Paste 3 competitor post URLs + 1 thought-leader account → Activate**
3. **Scout populates ~150 engagers** — visible in real-time on the Graph View
4. **Qualifier runs** — 47 qualified, 103 rejected; both heads' scores visible
5. **"Disagreements" filter** — 3 leads where GNN overrode LLM; click one, walk through the neighborhood reasoning
6. **Lead Agent timeline** — step through planned sequence; pause on reply-prediction: generic opener (0.12) vs. post-referencing opener (0.38); agent picks the latter
7. **Strategy Dashboard** — 2 lookalike signal sources discovered; 2 emergent communities found; click one: "Founders discussing PLG motion, 73% ICP match"
8. **Ablation chart** — GNN+LLM outperforms LLM-only by N% on held-out labels

**Narrative arc**: signals in → relational reasoning → grounded outreach → strategic learning back out

---

## Tech Stack

### Backend
| Layer | Choice |
|---|---|
| API + orchestration | Python, FastAPI |
| GNN | PyTorch Geometric or DGL |
| Community detection | NetworkX |
| Graph store | Postgres (sufficient at this scale) or Neo4j (cleaner query story for writeup) |
| LLM calls | Anthropic API |

### Frontend
| Layer | Choice |
|---|---|
| Framework | React |
| Agent timeline | React Flow |
| Graph visualization | Cytoscape.js or Sigma.js |

### Agent Framework
use LangGraph for orchestration primitives, this will make it easier to manage the state and flow of the agents and make our agents more robust and reliable.

---

## Writeup Thesis

**Claim**: Agent-based GTM systems benefit measurably from grounding their decisions in a relational model of the engagement graph — for lead qualification and for action selection — in ways that profile-only LLM reasoning cannot replicate.

**Evidence**:
- Architecture and working system
- Ablations on synthetic data: GNN+LLM vs. LLM-only baseline
- Qualitative demo: agent reasoning becomes more grounded with the relational model in the loop

**Honest limitation**: Small synthetic data, no real deployment. The path to real-world validation is clear: deploy, collect interaction data, retrain.

---

## Competitive Positioning

| Capability | Clay / Apollo / HeyReach | SignalAgent |
|---|---|---|
| Signal harvesting | Manual list import | Scheduled Scout agents |
| Lead qualification | Rule-based + basic LLM | Two-headed: LLM + relational GNN |
| Outreach planning | Template-driven | Agent planning loop grounded by reply prediction |
| ICP expansion | Manual | Embedding-based lookalike expansion |
| Buyer community discovery | None | Graph community detection + LLM labeling |
| Attribution | Basic | Signal-source + message-angle + segment attribution |

The shared weakness of existing tools is that they are **row-based** — each lead is a row. SignalAgent's core advantage is that every decision is made in the context of the **relational structure** of who-engages-with-what.

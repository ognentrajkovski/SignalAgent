import os
import pickle
from collections import Counter
from api.db import SessionLocal, Lead, AgentAction, SignalSource

_GRAPH_CACHE = None

try:
    from generate_graph import COMMUNITY_ARCHETYPES
except ImportError:
    COMMUNITY_ARCHETYPES = [
        {
            "name": "RevOps Leaders",
            "topics": [
                "Revenue operations stack", "CRM hygiene", "GTM alignment",
                "Forecasting accuracy", "Sales & marketing alignment",
                "RevOps tooling", "Pipeline visibility",
            ],
        },
        {
            "name": "PLG Founders",
            "topics": [
                "Product-led growth", "Freemium conversion", "Self-serve onboarding",
                "PLG motion", "Activation rates", "Time-to-value", "Usage analytics",
            ],
        },
        {
            "name": "GTM Executives",
            "topics": [
                "Enterprise sales motion", "Outbound strategy", "Pipeline generation",
                "Sales hiring", "Market expansion", "Category creation", "ICP definition",
            ],
        },
    ]

def get_graph():
    """Load and cache the NetworkX engagement graph from graph.pkl."""
    global _GRAPH_CACHE
    if _GRAPH_CACHE is None:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        graph_path = os.path.join(BASE_DIR, "graph.pkl")
        if os.path.exists(graph_path):
            with open(graph_path, "rb") as f:
                _GRAPH_CACHE = pickle.load(f)
    return _GRAPH_CACHE

def get_strategy_report():
    db = SessionLocal()
    try:
        G = get_graph()

        # --- Top Signal Sources ---
        sources = db.query(SignalSource).order_by(SignalSource.added_at.desc()).all()
        source_urls = {source.url for source in sources}

        source_stats = {
            source.url: {"lead_count": 0, "qualified_count": 0}
            for source in sources
        }

        if source_urls:
            leads = db.query(Lead).filter(Lead.source_url.in_(source_urls)).all()
            for lead in leads:
                stats = source_stats.get(lead.source_url)
                if not stats:
                    continue
                stats["lead_count"] += 1
                if lead.qualified:
                    stats["qualified_count"] += 1

        top_sources = []
        for index, source in enumerate(sources):
            stats = source_stats[source.url]
            lead_count = stats["lead_count"]
            qualified_count = stats["qualified_count"]
            top_sources.append({
                "id": source.id,
                "url": source.url,
                "lead_count": lead_count,
                "qualified_count": qualified_count,
                "conversion_rate": qualified_count / lead_count if lead_count else 0,
                "_sort_index": index,
            })

        top_sources = sorted(
            top_sources,
            key=lambda s: (-s["lead_count"], -s["qualified_count"], s["_sort_index"])
        )
        top_sources = [
            {k: v for k, v in s.items() if k != "_sort_index"}
            for s in top_sources
        ]

        # --- Lookalike Recommendations ---
        lookalikes = []
        try:
            lookalike_leads = (
                db.query(Lead)
                .filter(Lead.qualified == False)  # noqa: E712
                .order_by(Lead.gnn_score.desc())
                .limit(2)
                .all()
            )
            for l in lookalike_leads:
                node_data = G.nodes.get(l.person_id, {}) if G else {}
                role = node_data.get("role", "professional")
                c_id = node_data.get("community_id", 0)
                if isinstance(c_id, int) and 0 <= c_id < len(COMMUNITY_ARCHETYPES):
                    community_name = COMMUNITY_ARCHETYPES[c_id]["name"]
                else:
                    community_name = "similar buyers"

                suggested_url = (
                    l.source_url
                    or f"linkedin.com/in/{l.person_id.replace('_', '-')}"
                )
                reason = (
                    f"GNN score {l.gnn_score:.2f} \u2014 {role} with engagement patterns "
                    f"closely matching the {community_name} cluster."
                )
                lookalikes.append({
                    "suggested_url": suggested_url,
                    "reason": reason,
                    "person_id": l.person_id,
                    "gnn_score": l.gnn_score,
                })
        except Exception as e:
            print(f"Error finding lookalikes: {e}")

        # --- Dynamic Community Summaries ---
        community_summaries = []
        try:
            if G is not None:
                db_leads = db.query(Lead).all()
                lead_map = {l.person_id: l for l in db_leads}

                communities = {0: [], 1: [], 2: []}
                for node_id, data in G.nodes(data=True):
                    if data.get("node_type") == "person":
                        c_id = data.get("community_id")
                        if c_id in communities:
                            communities[c_id].append((node_id, data))

                for c_id, members in communities.items():
                    archetype = COMMUNITY_ARCHETYPES[c_id]
                    name = archetype["name"]

                    c_leads = [lead_map[node_id] for node_id, _ in members if node_id in lead_map]
                    size = len(c_leads)

                    if c_leads:
                        engagement = sum((l.gnn_score + l.llm_score) / 2 for l in c_leads) / len(c_leads)
                    else:
                        engagement = 0.0

                    topic_counts = Counter()
                    for lead in c_leads:
                        profile = G.nodes[lead.person_id].get("profile_text", "").lower()
                        for topic in archetype["topics"]:
                            if topic.lower() in profile:
                                topic_counts[topic] += 1

                    extracted = [t for t, _ in topic_counts.most_common(3)]
                    for t in archetype["topics"]:
                        if t not in extracted:
                            extracted.append(t)
                        if len(extracted) >= 3:
                            break

                    if c_leads:
                        roles = [G.nodes[l.person_id].get("role") for l in c_leads if G.nodes[l.person_id].get("role")]
                        if roles:
                            top_topics = extracted[:3] + [Counter(roles).most_common(1)[0][0]]
                        else:
                            top_topics = extracted[:3]
                    else:
                        top_topics = extracted[:3]

                    community_summaries.append({
                        "name": name,
                        "size": size,
                        "top_topics": top_topics,
                        "engagement": round(engagement, 2),
                    })
            else:
                community_summaries = [
                    {"name": "RevOps Leaders", "size": 466, "top_topics": ["Revenue operations stack", "CRM hygiene", "GTM alignment"], "engagement": 0.74},
                    {"name": "PLG Founders",  "size": 466, "top_topics": ["Product-led growth", "Freemium conversion", "Self-serve onboarding"], "engagement": 0.88},
                    {"name": "GTM Executives", "size": 468, "top_topics": ["Enterprise sales motion", "Outbound strategy", "Pipeline generation"], "engagement": 0.61},
                ]
        except Exception as e:
            print(f"Error calculating dynamic communities: {e}")
            community_summaries = [
                {"name": "RevOps Leaders", "size": 466, "top_topics": ["Revenue operations stack", "CRM hygiene", "GTM alignment"], "engagement": 0.74},
                {"name": "PLG Founders",  "size": 466, "top_topics": ["Product-led growth", "Freemium conversion", "Self-serve onboarding"], "engagement": 0.88},
                {"name": "GTM Executives", "size": 468, "top_topics": ["Enterprise sales motion", "Outbound strategy", "Pipeline generation"], "engagement": 0.61},
            ]

        total_actions = db.query(AgentAction).count()

        return {
            "top_sources": top_sources,
            "top_performing_sources": top_sources,
            "lookalike_recommendations": lookalikes,
            "total_agent_actions": total_actions,
            "community_summaries": community_summaries,
        }

    finally:
        db.close()

if __name__ == "__main__":
    print(get_strategy_report())

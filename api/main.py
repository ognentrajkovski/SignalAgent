from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db import SessionLocal, init_db, SignalSource, Lead, AgentAction
from api.agents.qualifier import run_qualifier
from api.agents.lead_agent import run_lead_agent
from api.agents.strategy import get_strategy_report, get_graph
from api.agents.scout import run_scout_agent

app = FastAPI(title="SignalAgent API")

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Models
class SignalSourceCreate(BaseModel):
    url: str

class SignalSourceResponse(BaseModel):
    id: int
    url: str
    lead_count: int = 0
    
    class Config:
        from_attributes = True

# --- Routes ---

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/signal-sources", response_model=list[SignalSourceResponse])
def get_signal_sources(db: Session = Depends(get_db)):
    """
    Returns watched signal sources with the number of leads currently attributed
    to each source URL.
    """
    lead_counts = dict(
        db.query(Lead.source_url, func.count(Lead.id))
        .filter(Lead.source_url.isnot(None))
        .group_by(Lead.source_url)
        .all()
    )

    sources = db.query(SignalSource).order_by(SignalSource.added_at.desc()).all()
    return [
        {
            "id": source.id,
            "url": source.url,
            "lead_count": lead_counts.get(source.url, 0),
        }
        for source in sources
    ]

@app.post("/signal-sources", response_model=SignalSourceResponse)
def add_signal_source(source: SignalSourceCreate, db: Session = Depends(get_db)):
    """
    Adds a LinkedIn post URL or account to watch.
    """
    db_source = db.query(SignalSource).filter(SignalSource.url == source.url).first()
    if db_source:
        raise HTTPException(status_code=400, detail="Source already exists")
        
    new_source = SignalSource(url=source.url)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    # Run synchronously since it takes <1s, avoiding UI race conditions
    run_scout_agent(new_source.id, new_source.url)
    
    # Calculate actual leads found by the scout agent
    leads_found = db.query(Lead).filter(Lead.source_url == source.url).count()
    
    return {
        "id": new_source.id,
        "url": new_source.url,
        "lead_count": leads_found,
    }

@app.delete("/signal-sources/{source_id}", status_code=204)
def delete_signal_source(source_id: int, db: Session = Depends(get_db)):
    """
    Removes a watched source and all leads generated from that source URL.
    """
    source = db.query(SignalSource).filter(SignalSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    leads = db.query(Lead).filter(Lead.source_url == source.url).all()
    for lead in leads:
        db.delete(lead)

    db.delete(source)
    db.commit()
    return

def _enrich_lead_with_graph(lead, G):
    """Pull real name/role/company from graph.pkl for a Lead ORM object."""
    node_data = G.nodes.get(lead.person_id, {}) if G else {}
    company_id = node_data.get("company_id", "")
    company_name = (
        G.nodes.get(company_id, {}).get("name", "")
        if G and company_id else ""
    )
    return {
        "name": node_data.get("name") or None,
        "role": node_data.get("role") or None,
        "company": company_name or None,
        "community_id": node_data.get("community_id"),
    }

@app.get("/leads")
def get_leads(db: Session = Depends(get_db)):
    """
    Returns ranked leads with LLM and GNN scores,
    enriched with real name/role/company from the engagement graph.
    """
    leads = db.query(Lead).order_by(
        Lead.qualified.desc(),
        (Lead.gnn_score + Lead.llm_score).desc()
    ).all()

    G = get_graph()

    return [
        {
            "id": l.id,
            "person_id": l.person_id,
            **_enrich_lead_with_graph(l, G),
            "gnn_score": l.gnn_score,
            "llm_score": l.llm_score,
            "disagreement_flag": l.disagreement_flag,
            "qualified": l.qualified,
            "source": l.source_url,
            "signal": l.source_url,
        } for l in leads
    ]

@app.get("/leads/{lead_id}")
def get_lead_timeline(lead_id: int, db: Session = Depends(get_db)):
    """
    Returns a lead's full agent timeline, enriched with graph profile data.
    Also triggers the LeadAgent to run an action if no actions exist yet.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    if lead.qualified and not lead.actions:
        run_lead_agent(lead.id, lead.person_id)
        db.refresh(lead)

    G = get_graph()
    graph_profile = _enrich_lead_with_graph(lead, G)

    actions = [
        {
            "id": a.id,
            "action_type": a.action_type,
            "rationale": a.rationale,
            "timestamp": a.timestamp,
            "approved": a.approved,
        } for a in lead.actions
    ]
    
    return {
        "lead_id": lead.id,
        "person_id": lead.person_id,
        **graph_profile,
        "gnn_score": lead.gnn_score,
        "llm_score": lead.llm_score,
        "qualified": lead.qualified,
        "source": lead.source_url,
        "signal": lead.source_url,
        "timeline": actions,
    }

@app.patch("/leads/{lead_id}/actions/{action_id}/approve", status_code=200)
def approve_action(lead_id: int, action_id: int, db: Session = Depends(get_db)):
    """
    Marks a lead's agent action as approved, persisted to the database.
    """
    action = db.query(AgentAction).filter(
        AgentAction.id == action_id,
        AgentAction.lead_id == lead_id,
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.approved = True
    db.commit()
    db.refresh(action)
    return {
        "id": action.id,
        "action_type": action.action_type,
        "rationale": action.rationale,
        "timestamp": action.timestamp,
        "approved": action.approved,
    }

@app.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """
    Permanently removes a lead and all its agent actions from the database.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return

@app.get("/graph")
def get_graph_data(db: Session = Depends(get_db)):
    """
    Returns Cytoscape-compatible node/edge data built from real DB leads
    and their attributes in graph.pkl.
    Nodes: one person node per lead + one source node per unique source URL.
    Edges: engaged_with (lead to source) + co_engaged (leads sharing a source).
    """
    leads = db.query(Lead).all()
    G = get_graph()

    nodes = []
    edges = []
    seen_sources = set()

    for lead in leads:
        node_data = G.nodes.get(lead.person_id, {}) if G else {}
        company_id = node_data.get("company_id", "")
        company_name = (
            G.nodes.get(company_id, {}).get("name", "")
            if G and company_id else ""
        )

        full_name = node_data.get("name", "")
        label = full_name.split()[0] if full_name else lead.person_id

        nodes.append({
            "id": lead.person_id,
            "type": "person",
            "label": label,
            "full_name": full_name or lead.person_id,
            "role": node_data.get("role", ""),
            "company": company_name,
            "community_id": node_data.get("community_id", 0),
            "qualified": lead.qualified or False,
            "gnn_score": lead.gnn_score or 0.0,
            "llm_score": lead.llm_score or 0.0,
            "disagreement_flag": lead.disagreement_flag or False,
            "source_url": lead.source_url or "",
            "lead_id": lead.id,
        })

        if lead.source_url and lead.source_url not in seen_sources:
            seen_sources.add(lead.source_url)
            raw = lead.source_url.replace("https://", "").replace("http://", "")
            short_label = raw[:40] + "\u2026" if len(raw) > 40 else raw
            nodes.append({
                "id": f"source::{lead.source_url}",
                "type": "source",
                "label": short_label,
                "source_url": lead.source_url,
            })

    for lead in leads:
        if lead.source_url:
            edges.append({
                "id": f"eng-{lead.person_id}",
                "source": lead.person_id,
                "target": f"source::{lead.source_url}",
                "type": "engaged_with",
            })

    by_source = defaultdict(list)
    for lead in leads:
        if lead.source_url:
            by_source[lead.source_url].append(lead.person_id)

    edge_idx = 0
    for pids in by_source.values():
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                edges.append({
                    "id": f"co-{edge_idx}",
                    "source": pids[i],
                    "target": pids[j],
                    "type": "co_engaged",
                })
                edge_idx += 1

    return {"nodes": nodes, "edges": edges}

@app.get("/strategy")
def get_strategy():
    report = get_strategy_report()
    return report

@app.post("/demo/qualify/{person_id}")
def demo_qualify_person(person_id: str):
    result = run_qualifier(person_id)
    return result

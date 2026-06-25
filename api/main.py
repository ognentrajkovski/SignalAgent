from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db import SessionLocal, init_db, SignalSource, Lead, AgentAction
from api.agents.qualifier import run_qualifier
from api.agents.lead_agent import run_lead_agent
from api.agents.strategy import get_strategy_report
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
def add_signal_source(source: SignalSourceCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
    
    # Run the scout agent in the background to populate leads
    background_tasks.add_task(run_scout_agent, new_source.id, new_source.url)
    
    return {
        "id": new_source.id,
        "url": new_source.url,
        "lead_count": 0,
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

@app.get("/leads")
def get_leads(db: Session = Depends(get_db)):
    """
    Returns ranked qualified leads with both LLM and GNN scores.
    """
    # Sort by qualified first, then by combined score descending
    leads = db.query(Lead).order_by(
        Lead.qualified.desc(),
        (Lead.gnn_score + Lead.llm_score).desc()
    ).all()
    
    return [
        {
            "id": l.id,
            "person_id": l.person_id,
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
    Returns a lead's full agent timeline.
    Also triggers the LeadAgent to run an action if no actions exist yet,
    for demonstration purposes.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Trigger the LeadAgent only for qualified leads. Rejected leads should stop
    # at qualification and not receive placeholder outreach actions.
    if lead.qualified and not lead.actions:
        run_lead_agent(lead.id, lead.person_id)
        # Refresh from DB
        db.refresh(lead)
        
    actions = [
        {
            "action_type": a.action_type,
            "rationale": a.rationale,
            "timestamp": a.timestamp
        } for a in lead.actions
    ]
    
    return {
        "lead_id": lead.id,
        "person_id": lead.person_id,
        "gnn_score": lead.gnn_score,
        "llm_score": lead.llm_score,
        "qualified": lead.qualified,
        "source": lead.source_url,
        "signal": lead.source_url,
        "timeline": actions
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

@app.get("/strategy")
def get_strategy():
    """
    Returns the Strategy Agent report.
    """
    report = get_strategy_report()
    return report

# --- Demo Route to Trigger Qualifier ---
@app.post("/demo/qualify/{person_id}")
def demo_qualify_person(person_id: str):
    """
    Manually triggers the QualifierAgent for a person.
    """
    result = run_qualifier(person_id)
    return result

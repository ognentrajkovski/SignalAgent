from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from api.db import SessionLocal, init_db, SignalSource, Lead, AgentAction
from api.agents.qualifier import run_qualifier
from api.agents.lead_agent import run_lead_agent
from api.agents.strategy import get_strategy_report

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
    
    class Config:
        from_attributes = True

# --- Routes ---

@app.on_event("startup")
def startup_event():
    init_db()

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
    return new_source

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
            "qualified": l.qualified
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
        
    # Trigger lead agent if it hasn't acted recently (demo logic)
    if not lead.actions:
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
        "timeline": actions
    }

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

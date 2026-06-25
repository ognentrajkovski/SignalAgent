import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signaldb.sqlite")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SignalSource(Base):
    __tablename__ = "signal_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String, unique=True, index=True, nullable=False)
    source_url = Column(Text, nullable=True)
    gnn_score = Column(Float, nullable=True)
    llm_score = Column(Float, nullable=True)
    llm_rationale = Column(Text, nullable=True)
    disagreement_flag = Column(Boolean, default=False)
    qualified = Column(Boolean, default=False)
    
    actions = relationship("AgentAction", back_populates="lead", cascade="all, delete-orphan")

class AgentAction(Base):
    __tablename__ = "agent_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    action_type = Column(String, nullable=False)
    rationale = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    lead = relationship("Lead", back_populates="actions")

def init_db():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    lead_columns = {column["name"] for column in inspector.get_columns("leads")}
    if "source_url" not in lead_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE leads ADD COLUMN source_url TEXT"))

if __name__ == "__main__":
    init_db()
    print("Database initialized.")

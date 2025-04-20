# app/db.py
import os
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Ensure data directory exists
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# SQLite DB URL
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'workflows.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # only for SQLite
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --- Workflow Definitions ---
class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    task_sequence = Column(String, nullable=False)
    results = relationship("TaskResult", back_populates="workflow")

class TaskResult(Base):
    __tablename__ = "task_results"
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    task_key = Column(String, index=True)
    output = Column(JSON)
    workflow = relationship("Workflow", back_populates="results")

# --- Dynamic (User-Defined) Tasks ---
class CustomTask(Base):
    __tablename__ = "custom_tasks"
    key = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    prompt_template = Column(Text, nullable=False)

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

# Auto-create tables on import
init_db()

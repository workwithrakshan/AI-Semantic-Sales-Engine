from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
# FIXED: Changed import to match your root structure
from master_agent import match_service, generate_email, save_outreach
from app.models import Outreach, Lead, Service
from sqlalchemy import or_

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get the DB session correctly
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OutreachRequest(BaseModel):
    company_name: str
    company_description: str

@app.post("/generate-outreach")
def generate_outreach(data: OutreachRequest, db: Session = Depends(get_db)):
    """Matches a service and generates a customized AI pitch."""
    # 1. Match Service (Needs DB session)
    service = match_service(db, data.company_description)
    if not service:
        raise HTTPException(status_code=404, detail="No matching services found in database.")

    # 2. Generate Email via AnythingLLM
    email = generate_email(data.company_name, data.company_description, service)
    if not email:
        raise HTTPException(status_code=500, detail="AI Agent failed to generate content. Check if AnythingLLM is running.")

    # 3. Save to Outreach table (Needs DB session)
    saved = save_outreach(db, data.company_name, service.name, email)

    return {
        "outreach_id": saved.id,
        "matched_service": service.name,
        "email": email
    }

@app.get("/leads")
def get_all_leads(db: Session = Depends(get_db)):
    """View the leads stored in your database."""
    return db.query(Lead).all()

@app.get("/all-outreach")
def all_outreach(db: Session = Depends(get_db)):
    """Retrieve all generated email drafts."""
    return db.query(Outreach).all()

@app.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Live dashboard showing actionable vs missing email leads."""
    total_leads = db.query(Lead).count()
    
    unreachable_leads = db.query(Lead).filter(
        or_(
            Lead.contact_email == None,
            Lead.contact_email == "",
            Lead.contact_email == "Email missing",
            Lead.contact_email == "discovery@pending.com",
            Lead.contact_email == "not_found@company.com"
        )
    ).count()
    
    reachable_leads = total_leads - unreachable_leads
    drafts_completed = db.query(Lead).filter(Lead.is_pitched == True).count()
    remaining_to_draft = reachable_leads - drafts_completed

    return {
        "Total Leads Harvested": total_leads,
        "Reachable (Has Email)": reachable_leads,
        "Unreachable (Missing Email)": unreachable_leads,
        "AI Drafts Completed": drafts_completed,
        "Remaining to Draft": remaining_to_draft
    }
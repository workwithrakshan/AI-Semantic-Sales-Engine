from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import Base, engine, SessionLocal
from app.agent import match_service, generate_email, save_outreach
from app.models import Outreach, Service, Lead
from sqlalchemy import or_

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

class OutreachRequest(BaseModel):
    company_name: str
    company_description: str

@app.post("/generate-outreach")
def generate_outreach(data: OutreachRequest):
    """Matches a service and generates a customized AI pitch."""
    service = match_service(data.company_description)
    if not service:
        raise HTTPException(status_code=404, detail="No services found in database.")

    email = generate_email(data.company_name, data.company_description, service)
    saved = save_outreach(data.company_name, service.name, email)

    return {
        "outreach_id": saved.id,
        "matched_service": service.name,
        "email": email
    }

@app.get("/leads")
def get_all_leads():
    """View the 65 unique leads stored in your database."""
    db = SessionLocal()
    try:
        leads = db.query(Lead).all()
        return leads
    finally:
        db.close()

@app.get("/all-outreach")
def all_outreach():
    """Retrieve all generated email drafts."""
    db = SessionLocal()
    try:
        records = db.query(Outreach).all()
        return records
    finally:
        db.close()

@app.get("/dashboard-stats")
def get_dashboard_stats():
    """Live dashboard showing actionable vs missing email leads."""
    db = SessionLocal()
    try:
        total_leads = db.query(Lead).count()
        
        # Count leads with missing or placeholder emails
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
        
        # Count how many AI drafts are completed
        drafts_completed = db.query(Lead).filter(Lead.is_pitched == True).count()
        remaining_to_draft = reachable_leads - drafts_completed

        return {
            "Total Leads Harvested": total_leads,
            "Reachable (Has Email)": reachable_leads,
            "Unreachable (Missing Email)": unreachable_leads,
            "AI Drafts Completed": drafts_completed,
            "Remaining to Draft": remaining_to_draft
        }
    finally:
        db.close()
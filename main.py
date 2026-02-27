from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import Base, engine, SessionLocal
from app.agent import match_service, generate_email, save_outreach
from app.models import Outreach, Service, Lead

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
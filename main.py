from fastapi import FastAPI
from pydantic import BaseModel
from app.database import Base, engine, SessionLocal
# Cleaned up imports to match the actual agent.py functions
from app.agent import match_service, generate_email, save_outreach
from app.models import Outreach, Service , Lead
from app.embedding import generate_embedding

Base.metadata.create_all(bind=engine)

app = FastAPI()

class ServiceCreate(BaseModel):
    name: str
    description: str

class OutreachRequest(BaseModel):
    company_name: str
    company_description: str

@app.post("/services")
def add_service(service: ServiceCreate):
    db = SessionLocal()
    embedding = generate_embedding(service.description)
    new_service = Service(
        name=service.name,
        description=service.description,
        embedding=embedding
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    db.close()
    return {"id": new_service.id, "name": new_service.name}

@app.get("/services")
def list_services():
    try:
        db = SessionLocal()
        services = db.query(Service).all()
        result = [{"id": s.id, "name": s.name, "description": s.description} for s in services]
        db.close()
        return result
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate-outreach")
def generate_outreach(data: OutreachRequest):
    try:
        service = match_service(data.company_description)
        if not service:
            return {"error": "No service found in database. Add one via /services first."}

        email = generate_email(data.company_name, data.company_description, service)
        saved = save_outreach(data.company_name, service.name, email)

        return {
            "outreach_id": saved.id,
            "matched_service": service.name,
            "email": email
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/all-outreach")
def all_outreach():
    db = SessionLocal()
    records = db.query(Outreach).all()
    db.close()
    return records

@app.get("/leads")
def get_all_leads():
    db = SessionLocal()
    try:
        leads = db.query(Lead).all()
        result = []
        for lead in leads:
            result.append({
                "id": lead.id,
                "company_name": lead.company_name,
                "website": lead.website_url,
                "scraped_bio": lead.company_description,
                "email": lead.contact_email,
                "is_pitched": lead.is_pitched
            })
        return result
    finally:
        db.close()
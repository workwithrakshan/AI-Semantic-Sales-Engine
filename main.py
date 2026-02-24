from fastapi import FastAPI
from app.database import Base, engine, SessionLocal
from app.agent import match_service, generate_email, generate_followup, save_outreach
from app.models import Outreach

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.post("/generate-outreach")
def generate_outreach(data: dict):
    company_name = data["company_name"]
    company_description = data["company_description"]

    service = match_service(company_description)

    email = generate_email(company_name, company_description, service)

    saved = save_outreach(company_name, service.name, email)

    return {
        "outreach_id": saved.id,
        "matched_service": service.name,
        "email": email
    }


@app.post("/generate-followup/{outreach_id}")
def followup(outreach_id: int):
    db = SessionLocal()
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()

    followup_email = generate_followup(record.email_content)
    record.followup_content = followup_email
    db.commit()
    db.close()

    return {"followup": followup_email}


@app.post("/mark-sent/{outreach_id}")
def mark_sent(outreach_id: int):
    db = SessionLocal()
    record = db.query(Outreach).filter(Outreach.id == outreach_id).first()

    record.status = "sent"
    db.commit()
    db.close()

    return {"status": "sent"}


@app.get("/all-outreach")
def all_outreach():
    db = SessionLocal()
    records = db.query(Outreach).all()
    db.close()

    return records
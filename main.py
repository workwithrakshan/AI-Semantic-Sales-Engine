from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import Base, engine, SessionLocal
from app.agent import match_service, generate_email, save_outreach, analyze_reply_and_respond
from app.models import Outreach

Base.metadata.create_all(bind=engine)

app = FastAPI()

class LeadData(BaseModel):
    company_name: str
    company_description: str

class ReplyData(BaseModel):
    outreach_id: int
    reply_text: str

@app.post("/generate-outreach")
def generate_outreach(data: LeadData):
    # 1. Analyst Agent matches service
    service = match_service(data.company_description)
    if not service:
        raise HTTPException(status_code=404, detail="No matching service found in vector DB.")

    # 2. Pitch Agent writes email
    email = generate_email(data.company_name, data.company_description, service)

    # 3. Save to DB
    saved = save_outreach(data.company_name, service.name, email)

    return {
        "outreach_id": saved.id,
        "matched_service": service.name,
        "email": email
    }

@app.post("/process-reply")
def process_reply(data: ReplyData):
    db = SessionLocal()
    record = db.query(Outreach).filter(Outreach.id == data.outreach_id).first()
    
    if not record:
        db.close()
        raise HTTPException(status_code=404, detail="Outreach record not found.")

    # 4. Closer Agent analyzes sentiment and drafts response
    sentiment, next_email = analyze_reply_and_respond(data.reply_text)
    
    # Update DB state based on predictive classification
    if sentiment.lower() == "positive":
        record.status = "meeting_scheduled"
    else:
        record.status = "not_interested"
        
    record.followup_content = next_email
    db.commit()
    db.close()

    return {
        "sentiment_detected": sentiment,
        "generated_response": next_email,
        "new_status": record.status
    }
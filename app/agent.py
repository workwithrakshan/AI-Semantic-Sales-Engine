from app.database import SessionLocal
from app.models import Service, Outreach
from app.embedding import generate_embedding
from google.genai import client as genai_client
import os
from dotenv import load_dotenv

load_dotenv()

client = genai_client.Client(api_key=os.getenv("GEMINI_API_KEY"))


def match_service(company_description: str):
    db = SessionLocal()
    query_embedding = generate_embedding(company_description)

    result = db.query(Service).first()
    db.close()
    return result


def generate_email(company_name, company_description, service):
    prompt = f"""
Write a professional B2B outreach email (150 words).

Company: {company_name}
Description: {company_description}
Our Service: {service.name}
Service Details: {service.description}

End asking for 15-min meeting.
"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt
    )
    return response.text.strip()


def generate_followup(original_email):
    prompt = f"""
Write a polite follow-up email to this outreach:

{original_email}

Short and professional.
"""

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=prompt
    )
    return response.text.strip()


def save_outreach(company_name, service_name, email_content):
    db = SessionLocal()

    new_entry = Outreach(
        company_name=company_name,
        service_name=service_name,
        email_content=email_content,
        status="draft"
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    db.close()

    return new_entry
import os
import requests
from app.database import SessionLocal
from app.models import Service, Outreach, Lead
from dotenv import load_dotenv

load_dotenv()

ANYTHINGLLM_URL = "http://192.168.1.38:3001/api/v1"
ANYTHINGLLM_TOKEN = os.getenv("ANYTHINGLLM_TOKEN", "21Y0K2Q-DEDM82D-GRBGH34-W8GGAQX")

def call_local_llm(prompt: str, company_name: str) -> str:
    headers = {
        "Authorization": f"Bearer {ANYTHINGLLM_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"message": prompt, "mode": "chat"}
    
    try:
        response = requests.post(
            f"{ANYTHINGLLM_URL}/workspace/my-workspace/chat",
            headers=headers, json=payload, timeout=90000
        )
        if response.status_code == 200:
            text = response.json().get("textResponse", "")
            if '<think>' in text:
                text = text.split('</think>')[-1].strip()
            
            # Print to terminal for a clean live view
            print("\n" + "📧 " + "="*60)
            print(f"STRATEGIC PITCH FOR: {company_name}")
            print("-" * 60)
            print(text) 
            print("="*60 + "\n")

            # Save a backup text file automatically
            safe_name = "".join(x for x in company_name if x.isalnum())
            with open(f"pitch_{safe_name}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            return text
        return f"Error: LLM returned status {response.status_code}"
    except Exception as e:
        return f"Error calling local LLM: {str(e)}"

def match_service(company_description: str):
    db = SessionLocal()
    try:
        # Fetches the service you inserted via insert_service.py
        return db.query(Service).first()
    finally:
        db.close()

def generate_email(company_name, company_description, service):
    prompt = f"""
    ### INSTRUCTIONS:
    You are a Senior IT Solutions Architect. Write a professional outreach email to {company_name}.
    Target Bio: {company_description}
    Our Service: {service.name} - {service.description}
    
    Length: 200-300 words. Output ONLY the email content.
    """
    return call_local_llm(prompt, company_name)

def save_outreach(company_name, service_name, email_content):
    db = SessionLocal()
    try:
        new_entry = Outreach(
            company_name=company_name,
            service_name=service_name,
            email_content=email_content,
            status="draft"
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry
    finally:
        db.close()
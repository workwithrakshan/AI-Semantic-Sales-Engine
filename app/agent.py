import os
import requests
from app.database import SessionLocal
from app.models import Service, Outreach
from dotenv import load_dotenv

load_dotenv()

# LOCAL ANYTHINGLLM CONFIGURATION
# Using 127.0.0.1 is usually more stable than the local IP unless you are calling from a different machine
ANYTHING_LLM_BASE_URL = "http://192.168.1.38:3001"
ANYTHING_LLM_API_KEY = "21Y0K2Q-DEDM82D-GRBGH34-W8GGAQX"

def call_local_llm(prompt: str, company_name: str) -> str:
    # Use the Developer API endpoint - most robust for automation
    url = f"{ANYTHING_LLM_BASE_URL}/api/v1/workspace/my-workspace/chat"
    headers = {
        "Authorization": f"Bearer {ANYTHING_LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": prompt,
        "mode": "chat" # or "query" if you have a specific workspace context
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            # The Developer API returns 'content', NOT 'textResponse'
            text = data.get("content", "").strip()
            
            if not text:
                # Fallback check for different versions
                text = data.get("textResponse", "").strip()

            print(f"✅ Local AI Generated Pitch for {company_name} successfully.")
            return text
        else:
            return f"Error: Local LLM returned status {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error calling Local AnythingLLM: {str(e)}"

def match_service(company_description: str):
    db = SessionLocal()
    try:
        return db.query(Service).first()
    finally:
        db.close()

def generate_email(company_name, company_description, service):
    # This is the 'Super Prompt' logic applied to your local model
    prompt = f"""
    ROLE: Senior B2B Growth Architect. 
    Write a professional outreach email to {company_name}.
    Company Context: {company_description}
    Our Service: {service.name} - {service.description}
    
    GUIDELINES:
    - Start with a direct business observation.
    - No 'I hope this finds you well'.
    - Focus on the value of {service.name}.
    - End with a clear call to action.
    - Output ONLY the email body.
    """
    return call_local_llm(prompt, company_name)

def save_outreach(company_name, service_name, email_content):
    db = SessionLocal()
    try:
        new_entry = Outreach(
            company_name=company_name,
            matched_service=service_name, # Corrected to match your database schema
            email_content=email_content,
            status="draft"
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry
    except Exception as e:
        print(f"❌ Database Save Error: {e}")
        db.rollback()
    finally:
        db.close()
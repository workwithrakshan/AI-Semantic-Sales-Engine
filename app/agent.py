import sys
import os
import requests

# 🛠️ Fixes the path so 'app' module can be found from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import Service, Outreach, Lead
from dotenv import load_dotenv

load_dotenv()

# AnythingLLM configuration
ANYTHINGLLM_URL = "http://192.168.1.38:3001/api/v1"
ANYTHINGLLM_TOKEN = os.getenv("ANYTHINGLLM_TOKEN", "21Y0K2Q-DEDM82D-GRBGH34-W8GGAQX")

def call_local_llm(prompt: str, company_name: str) -> str:
    """Calls local LLM, prints clean output to terminal, and saves a .txt file."""
    headers = {
        "Authorization": f"Bearer {ANYTHINGLLM_TOKEN}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {"message": prompt, "mode": "chat"}
    
    try:
        # High timeout (90s) for high-quality 300-word generations
        response = requests.post(
            f"{ANYTHINGLLM_URL}/workspace/my-workspace/chat",
            headers=headers,
            json=payload,
            timeout=90000 
        )
        
        if response.status_code == 200:
            data = response.json()
            text = data.get("textResponse", data.get("response", ""))
            
            # Clean up <think> tags if the model uses reasoning/CoT
            if '<think>' in text:
                text = text.split('</think>')[-1].strip()
            
            # --- 🖥️ TERMINAL OUTPUT (Solves the \n issue) ---
            print("\n" + "📧 " + "="*60)
            print(f"STRATEGIC PITCH FOR: {company_name}")
            print("-" * 60)
            print(text) 
            print("="*60 + "\n")

            # --- 💾 SAVE TO TEXT FILE ---
            # Remove special characters from filename for OS safety
            safe_name = "".join(x for x in company_name if x.isalnum())
            file_path = f"pitch_{safe_name}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"✅ Draft saved to: {file_path}")

            return text
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def generate_email(company_name: str, company_description: str, service) -> str:
    """Generates the professional pitch using the Senior Architect persona."""
    prompt = f"""
### INSTRUCTIONS:
You are a Senior IT Solutions Architect. Write a sophisticated, professional outreach email to {company_name}.

### DATA CONTEXT:
Target Company Bio: {company_description}
Our Service: {service.name} - {service.description}

### EMAIL STRUCTURE (STRICT):
1. Professional Subject Line.
2. Hook: Reference a specific technical/business detail from their bio.
3. Gap & Solution: Why they need {service.name} based on their current operations.
4. CTA: 10-minute introduction call.

### FORMATTING:
- Length: 200 to 300 words.
- Tone: Executive and consultative.
- Output ONLY the email content. No conversational filler.
"""
    return call_local_llm(prompt, company_name)

if __name__ == "__main__":
    print("🧠 ANALYST AGENT STARTING...")
    db = SessionLocal()
    
    try:
        # 🎯 STEP 1: Get leads with emails that have NOT been pitched yet
        leads = db.query(Lead).filter(
            Lead.contact_email != "discovery@pending.com",
            Lead.contact_email != "not_found@company.com",
            Lead.is_pitched == False  # This ensures we don't repeat work
        ).all()

        # 🎯 STEP 2: Fetch your business service details
        service = db.query(Service).first()
        
        if not leads:
            print("✨ All leads have been processed! No new emails to generate.")
        elif not service:
            print("❌ No service found. Please add your service details in Swagger (POST /services).")
        else:
            print(f"🎯 Found {len(leads)} NEW leads. Starting AI Generations...")
            print("-" * 30)
            
            for lead in leads:
                # Generate and save the email
                result = generate_email(lead.company_name, lead.company_description, service)
                
                # If generation was successful, mark as pitched in database
                if "Error" not in result:
                    lead.is_pitched = True
                    db.commit()
                    print(f"✔️ {lead.company_name} marked as 'Drafted' in DB.")
                
    except Exception as e:
        print(f"💥 Critical Error: {e}")
    finally:
        db.close()
        print("\n🚀 Mission Complete. Check your project folder for .txt files.")
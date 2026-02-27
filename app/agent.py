import os
import requests
from app.database import SessionLocal
from app.models import Service, Outreach
from dotenv import load_dotenv

load_dotenv()

# Your valid OpenRouter API Key
OPENROUTER_API_KEY = "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"

def call_openrouter_llm(prompt: str, company_name: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "X-Title": "AI Semantic Sales Engine",
        "Content-Type": "application/json"
    }
    
    payload = {
        # Using a highly stable and permanently free model
        "model": "openai/gpt-4", 
        "messages": [
            {"role": "system", "content": "You are a Senior IT Solutions Architect."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90000)
        
        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            
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
        else:
            return f"Error: OpenRouter returned status {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error calling OpenRouter API: {str(e)}"

def match_service(company_description: str):
    db = SessionLocal()
    try:
        return db.query(Service).first()
    finally:
        db.close()

def generate_email(company_name, company_description, service):
    prompt = f"""
    ### ROLE:
    You are a world-class Senior B2B Growth Architect and IT Solutions Specialist with 20 years of experience in strategic outreach. Your tone is professional, authoritative, yet helpful and low-pressure.

    ### TARGET DATA:
    - Target Company: {company_name}
    - Company Bio/Context: {company_description}

    ### OUR OFFERING:
    - Service Name: {service.name}
    - Service Value Proposition: {service.description}

    ### STRATEGY (PAS FRAMEWORK):
    1. **Problem**: Identify a specific pain point or inefficiency {company_name} likely faces based on their bio.
    2. **Agitation**: Briefly explain the cost of ignoring this problem (lost revenue, technical debt, or inefficiency).
    3. **Solution**: Introduce our {service.name} as the precise bridge to solve that problem.

    ### STRICT GUIDELINES:
    - **No Fluff**: Avoid "I hope this email finds you well" or "My name is...". Start with a direct observation about their business.
    - **Personalization**: Reference specific elements from the "Company Bio" so it doesn't feel like a template.
    - **Call to Action (CTA)**: End with a soft, "interest-based" CTA (e.g., "Would you be open to a 10-minute brief on how we can implement this for you?").
    - **Formatting**: Output ONLY the email body. No subject lines, no [Bracketed Text], and no labels like "Greeting:" or "Body:".
    - **Length**: 200-300 words. Use short, punchy paragraphs.

    ### OUTPUT:
    Write the email content now.
    """
    return call_openrouter_llm(prompt, company_name)

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
import os
import google.generativeai as genai
from app.database import SessionLocal
from app.models import Service, Outreach
from app.embedding import generate_embedding

# Initialize Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro')

def match_service(company_description: str):
    """The Analyst Agent: Finds the best IT service to pitch."""
    db = SessionLocal()
    query_embedding = generate_embedding(company_description)
    
    # Cosine distance search using pgvector
    best_match = db.query(Service).order_by(
        Service.embedding.cosine_distance(query_embedding)
    ).first()
    db.close()
    return best_match

def generate_email(company_name: str, company_description: str, service) -> str:
    """The Pitch Agent: Writes the personalized cold email."""
    prompt = f"""
    You are an expert IT Business Development Executive. 
    Write a highly personalized, concise cold email to {company_name}.
    Company Context: {company_description}
    The service we are pitching: {service.name} - {service.description}
    
    Keep it under 150 words. Focus on their specific pain points. End with a soft call to action for a quick chat.
    """
    response = model.generate_content(prompt)
    return response.text

def save_outreach(company_name: str, service_name: str, email: str):
    """Helper to save to DB."""
    db = SessionLocal()
    new_outreach = Outreach(
        company_name=company_name,
        matched_service=service_name,
        email_content=email
    )
    db.add(new_outreach)
    db.commit()
    db.refresh(new_outreach)
    db.close()
    return new_outreach

def analyze_reply_and_respond(reply_text: str):
    """The Closer Agent: Analyzes sentiment and handles scheduling."""
    prompt = f"""
    You are an AI Sales Closer. Read the following email reply from a prospect:
    "{reply_text}"
    
    Task 1: Determine the sentiment. Is it 'Positive' (they want to talk/know more) or 'Negative' (not interested/stop)?
    Task 2: If Positive, write a short, polite response proposing a Google Meet and include the placeholder link [INSERT_GMEET_LINK].
    Task 3: If Negative, write a very brief, polite sign-off acknowledging their pass.
    
    Format your response EXACTLY like this:
    SENTIMENT: [Positive/Negative]
    RESPONSE: [Your email response]
    """
    response = model.generate_content(prompt)
    
    # Simple parser to extract the agent's decisions
    lines = response.text.split('\n')
    sentiment = "Negative"
    email_response = ""
    
    for line in lines:
        if line.startswith("SENTIMENT:"):
            sentiment = line.split(":")[1].strip()
        elif line.startswith("RESPONSE:"):
            email_response = line.split(":", 1)[1].strip()
            
    return sentiment, email_response
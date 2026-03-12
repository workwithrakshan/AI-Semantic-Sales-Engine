import spacy
import re
from app.database import SessionLocal
from app.models import Lead
from app.embedding import generate_embedding

# Load the AI model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("⚠️ Model not found. Run: python -m spacy download en_core_web_sm")

def extract_lead_with_ai(blob):
    """Uses Natural Language Processing to identify entities"""
    # 1. Regex for the Mail ID
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', blob)
    email = email_match.group(0) if email_match else "unknown@domain.com"
    
    # 2. Use the Model to find the Organization (Company)
    doc = nlp(blob)
    company_name = "Unknown Company"
    
    # Find words the model recognizes as an 'ORG'
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    if orgs:
        company_name = orgs[0]
    
    # 3. Clean the remaining text for the Bio
    bio = blob.replace(email, "").replace(company_name, "").strip(", |")
    
    return company_name, bio, email

def seed_with_model(messy_blobs):
    db = SessionLocal()
    print("🤖 AI Model is analyzing unstructured data...")

    for blob in messy_blobs:
        name, bio, email = extract_lead_with_ai(blob)
        print(f"📍 AI Recognized -> Name: {name} | Email: {email}")
        
        # Store in Vector DB
        vector = generate_embedding(bio)
        
        new_lead = Lead(
            company_name=name,
            company_description=bio,
            website_url="https://linkedin.com",
            description_embedding=vector,
            contact_email=email,
            is_pitched=False
        )
        db.add(new_lead)
    
    db.commit()
    db.close()
    print("\n✅ Leads successfully parsed by AI and stored in Vector DB!")

if __name__ == "__main__":
    # Test with names that have NO indicator words
    messy_data = [
        "Reach out to Reliance in Mumbai they need AWS migration at tech@reliance.com",
        "hr@tata.com is looking for Tata digital transformation projects in Bangalore",
        "Infosys contact@infosys.com needs cloud-native scaling for their US clients",
        "KriyaTec "
    ]
    seed_with_model(messy_data)
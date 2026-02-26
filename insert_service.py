from app.database import SessionLocal
from app.models import Service
from app.embedding import generate_embedding

def reset_and_insert_services():
    db = SessionLocal()
    
    # 1. CLEANUP: Delete existing services to ensure a fresh start
    print("🧹 Cleaning up old services...")
    db.query(Service).delete()
    db.commit()

    # 2. DEFINE FULL IT SERVICE CATALOG
    # We provide detailed descriptions so the Analyst Agent can match them accurately.
    services_to_add = [
        {
            "name": "Cloud Infrastructure",
            "description": "Enterprise cloud hosting, AWS/Azure migration, server management, and scalable infrastructure for high-traffic platforms."
        },
        {
            "name": "AI Chatbot Development",
            "description": "Custom AI chatbots and automated customer support agents using LLMs to handle routine inquiries and boost conversions."
        },
        {
            "name": "Cybersecurity & Compliance",
            "description": "End-to-end security audits, penetration testing, threat detection, and regulatory compliance (GDPR, HIPAA, SOC2)."
        },
        {
            "name": "Data Analytics & Business Intelligence",
            "description": "Predictive modeling, data visualization dashboards, and big data processing to drive business decision-making."
        },
        {
            "name": "Custom Software Development",
            "description": "Bespoke web and mobile application development using modern frameworks like React, Node.js, and Python."
        },
        {
            "name": "Managed IT Support",
            "description": "24/7 helpdesk support, network maintenance, and hardware management for small to medium-sized enterprises."
        },
        {
            "name": "DevOps & Automation",
            "description": "CI/CD pipeline setup, infrastructure as code (Terraform), and workflow automation to speed up deployment cycles."
        }
    ]
    
    print(f"🚀 Injecting {len(services_to_add)} services into the database...")
    
    for item in services_to_add:
        # Generate the vector embedding for the description
        embedding = generate_embedding(item["description"])
        
        new_service = Service(
            name=item["name"],
            description=item["description"],
            description_embedding=embedding
        )
        db.add(new_service)
    
    db.commit()
    db.close()
    print("✅ DATABASE READY: All IT services have been vectorized and stored.")

if __name__ == "__main__":
    reset_and_insert_services()
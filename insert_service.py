from app.database import SessionLocal
from app.models import Service
from app.embedding import generate_embedding

db = SessionLocal()

name = "AI Chatbot Development"
description = "We build intelligent AI chatbots for businesses"

embedding = generate_embedding(description)

service = Service(
    name=name,
    description=description,
    embedding=embedding
)

db.add(service)
db.commit()
db.close()

print("Service inserted successfully")
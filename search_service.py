from app.database import SessionLocal
from app.models import Service
from app.embedding import generate_embedding
from sqlalchemy import select

db = SessionLocal()

query = "Build chatbot for my website"

query_embedding = generate_embedding(query)

results = db.query(Service).order_by(
    Service.embedding.cosine_distance(query_embedding)
).limit(5).all()

for r in results:
    print(f"Matched Service: {r.name}")
    print(f"Description: {r.description}")
    print("-----")

db.close()
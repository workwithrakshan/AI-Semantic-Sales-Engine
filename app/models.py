from sqlalchemy import Column, Integer, String, Text
from pgvector.sqlalchemy import Vector
from app.database import Base

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    embedding = Column(Vector(384)) # Ensure this matches your embedding model's dimension

class Outreach(Base):
    __tablename__ = "outreach"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    matched_service = Column(String)
    email_content = Column(Text)
    followup_content = Column(Text, nullable=True)
    status = Column(String, default="draft") # States: draft, sent, positive_reply, negative_reply
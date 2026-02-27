from sqlalchemy import Column, Integer, String, Text, Boolean
from pgvector.sqlalchemy import Vector
from app.database import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    # Dimension 384 matches the 'all-MiniLM-L6-v2' model used in embedding.py
    embedding = Column(Vector(384)) 

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String)
    company_description = Column(Text)
    website_url = Column(String)
    contact_email = Column(String)
    is_pitched = Column(Boolean, default=False)

class Outreach(Base):
    __tablename__ = "outreach"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String)
    service_name = Column(String) # Ensure this matches agent.py save_outreach
    email_content = Column(Text)
    followup_content = Column(Text, nullable=True)
    status = Column(String, default="draft")
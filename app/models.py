from sqlalchemy import Column, Integer, String, Text, Boolean
from pgvector.sqlalchemy import Vector
from app.database import Base

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    embedding = Column(Vector(384))

class Outreach(Base):
    __tablename__ = "outreach"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    matched_service = Column(String)
    email_content = Column(Text)
    followup_content = Column(Text, nullable=True)
    status = Column(String, default="draft") 

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    website_url = Column(String)
    company_description = Column(Text)
    description_embedding = Column(Vector(384))
    contact_email = Column(String, nullable=True)
    is_pitched = Column(Boolean, default=False)
from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    embedding = Column(Text)  # keep as text if you're storing JSON string


class Outreach(Base):
    __tablename__ = "outreach"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String)
    service_name = Column(String)
    email_content = Column(Text)
    followup_content = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft | sent | replied
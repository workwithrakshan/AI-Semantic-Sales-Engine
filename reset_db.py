from app.database import engine
from app.models import Base

print("Dropping old tables...")
Base.metadata.drop_all(bind=engine)

print("Creating new tables with updated dimensions...")
Base.metadata.create_all(bind=engine)

print("Database reset successfully!")
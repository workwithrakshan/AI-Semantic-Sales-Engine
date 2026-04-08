import sys
import os

# Ensure the 'app' module is found
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Lead

def show_dashboard():
    db = SessionLocal()
    
    # 1. TOTALS
    total_leads = db.query(Lead).count()
    
    # 2. EMAIL STATUS
    with_email = db.query(Lead).filter(
        Lead.contact_email != "discovery@pending.com",
        Lead.contact_email != "not_found@company.com"
    ).count()
    
    missing_email = total_leads - with_email
    
    # 3. PITCH STATUS (Using your new 'is_pitched' logic)
    drafted = db.query(Lead).filter(Lead.is_pitched == True).count()
    remaining = with_email - drafted

    print("\n" + "📊 " + "═"*40)
    print("       SALES ENGINE REAL-TIME STATS")
    print("═"*42)
    
    print(f" Total Leads Harvested:   {total_leads}")
    print(f" Leads with Emails:       {with_email} (Ready)")
    print(f" Missing Emails:         {missing_email} (Need manual search)")
    
    print("-" * 42)
    
    print(f" AI Drafts Completed:     {drafted}")
    print(f"Remaining to Draft:      {remaining}")
    
    print("═"*42)
    
    if remaining > 0:
        print(f" Action: Run 'python app/agent.py' to process the next {remaining} leads.")
    else:
        print(" Action: Run 'python master_agent.py' to find new target companies.")
    print("\n")

    db.close()

if __name__ == "__main__":
    show_dashboard()
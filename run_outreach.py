import sys
import os

# Fix path so 'app' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal
from app.models import Lead, Service
from app.agent import generate_email

def run_outreach_generation():
    """Generate professional emails for all leads with valid email addresses."""
    print("\n" + "="*70)
    print("🚀 AI OUTREACH GENERATION ENGINE")
    print("="*70 + "\n")
    
    db = SessionLocal()
    
    try:
        # Get all leads with valid emails that haven't been pitched yet
        leads = db.query(Lead).filter(
            Lead.contact_email != "discovery@pending.com",
            Lead.contact_email != "not_found@company.com",
            Lead.contact_email.isnot(None),
            Lead.is_pitched == False
        ).all()
        
        # Get the service to pitch
        service = db.query(Service).first()
        
        if not service:
            print("❌ ERROR: No service found in database!")
            print("   Please add your service using POST /services endpoint in Swagger")
            return
        
        if not leads:
            print("✨ All leads with valid emails have been processed!")
            print("   No new emails to generate.")
            return
        
        print(f"📊 Found {len(leads)} leads with valid emails")
        print(f"🎯 Service to pitch: {service.name}")
        print("-" * 70 + "\n")
        
        success_count = 0
        error_count = 0
        
        for idx, lead in enumerate(leads, 1):
            print(f"\n[{idx}/{len(leads)}] Processing: {lead.company_name}")
            print(f"   📧 Email: {lead.contact_email}")
            print(f"   📝 Bio: {lead.company_description[:100]}...")
            
            try:
                # Generate the email
                email_content = generate_email(
                    lead.company_name,
                    lead.company_description,
                    service
                )
                
                # Check if generation was successful
                if "Error" not in email_content:
                    # Mark as pitched
                    lead.is_pitched = True
                    db.commit()
                    success_count += 1
                    print(f"   ✅ Email generated and saved to file")
                else:
                    error_count += 1
                    print(f"   ❌ Generation failed: {email_content[:50]}")
                    
            except Exception as e:
                error_count += 1
                print(f"   ❌ Error: {str(e)}")
                continue
        
        print("\n" + "="*70)
        print(f"📊 SUMMARY:")
        print(f"   ✅ Successfully generated: {success_count}")
        print(f"   ❌ Failed: {error_count}")
        print(f"   📁 Check your project folder for .txt files")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_outreach_generation()

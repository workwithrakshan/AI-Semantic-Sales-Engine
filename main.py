from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import Base, engine, SessionLocal
from master_agent import match_service, generate_email, save_outreach
from app.models import Outreach, Lead, Service
import subprocess
import sys
import os
print("Python being used:", sys.executable)
# Initialize database tables
from sqlalchemy import text
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────
# YOUR EXISTING ENDPOINTS (unchanged)
# ─────────────────────────────────────────────

class OutreachRequest(BaseModel):
    company_name: str
    company_description: str

@app.post("/generate-outreach")
def generate_outreach(data: OutreachRequest, db: Session = Depends(get_db)):
    """Matches a service and generates a customized AI pitch."""
    service = match_service(db, data.company_description)
    if not service:
        raise HTTPException(status_code=404, detail="No matching services found in database.")
    email = generate_email(data.company_name, data.company_description, service)
    if not email:
        raise HTTPException(status_code=500, detail="AI Agent failed to generate content. Check if AnythingLLM is running.")
    saved = save_outreach(db, data.company_name, service.name, email)
    return {
        "outreach_id": saved.id,
        "matched_service": service.name,
        "email": email
    }

@app.get("/leads")
def get_all_leads(db: Session = Depends(get_db)):
    """View the leads stored in your database."""
    return db.query(Lead).all()

@app.get("/all-outreach")
def all_outreach(db: Session = Depends(get_db)):
    """Retrieve all generated email drafts."""
    return db.query(Outreach).all()

@app.get("/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Live dashboard showing actionable vs missing email leads."""
    total_leads = db.query(Lead).count()
    unreachable_leads = db.query(Lead).filter(
        or_(
            Lead.contact_email == None,
            Lead.contact_email == "",
            Lead.contact_email == "Email missing",
            Lead.contact_email == "discovery@pending.com",
            Lead.contact_email == "not_found@company.com"
        )
    ).count()
    reachable_leads = total_leads - unreachable_leads
    drafts_completed = db.query(Lead).filter(Lead.is_pitched == True).count()
    remaining_to_draft = reachable_leads - drafts_completed
    return {
        "Total Leads Harvested": total_leads,
        "Reachable (Has Email)": reachable_leads,
        "Unreachable (Missing Email)": unreachable_leads,
        "AI Drafts Completed": drafts_completed,
        "Remaining to Draft": remaining_to_draft
    }

# ─────────────────────────────────────────────
# NEW: n8n PIPELINE ENDPOINTS
# ─────────────────────────────────────────────

# Track background job statuses
scrape_status = {"running": False, "message": "idle", "leads_found": 0}
enrich_status = {"running": False, "message": "idle", "enriched": 0}

# --- STAGE 1: SCRAPE ---

class ScrapeRequest(BaseModel):
    industry: str

def run_scraper(industry: str):
    global scrape_status
    scrape_status = {"running": True, "message": f"Scraping: {industry}", "leads_found": 0}
    try:
        with open("scraper_log.txt", "w", encoding="utf-8") as f:
            subprocess.run(
                [sys.executable, "master_agent.py", industry],
                stdout=f,
                stderr=f,
                timeout=600,
                cwd="D:\\AI_Semantic_Sales_Engine",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
        db = SessionLocal()
        count = db.query(Lead).count()
        db.close()
        scrape_status = {"running": False, "message": "Scraping complete", "leads_found": count}
    except subprocess.TimeoutExpired:
        scrape_status = {"running": False, "message": "Timed out", "leads_found": 0}
    except Exception as e:
        scrape_status = {"running": False, "message": f"Error: {str(e)}", "leads_found": 0}

        
@app.post("/pipeline/stage1/scrape")
def stage1_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    """n8n: Start LinkedIn scraping for an industry keyword."""
    if scrape_status["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(run_scraper, req.industry)
    return {"status": "started", "industry": req.industry}

@app.get("/pipeline/stage1/status")
def stage1_status():
    """n8n: Poll this until running=false."""
    return scrape_status

# --- STAGE 2: ENRICH ---

def run_enrichment():
    global enrich_status
    enrich_status = {"running": True, "message": "Enriching emails...", "enriched": 0}
    log_file = "enrichment_log.txt"
    try:
        with open(log_file, "w") as f:
            subprocess.run(
                [sys.executable, "enrichment_agent.py"],
                stdout=f,
                stderr=f,
                timeout=600,
                cwd="D:\\AI_Semantic_Sales_Engine"
            )
        db = SessionLocal()
        enriched = db.query(Lead).filter(
            Lead.contact_email != "discovery@pending.com",
            Lead.contact_email != "not_found@company.com",
            Lead.contact_email != "not_found@website.com",
            Lead.contact_email.isnot(None)
        ).count()
        db.close()
        enrich_status = {"running": False, "message": "Enrichment complete", "enriched": enriched}
    except Exception as e:
        enrich_status = {"running": False, "message": f"Error: {str(e)}", "enriched": 0}

@app.post("/pipeline/stage2/enrich")
def stage2_enrich(background_tasks: BackgroundTasks):
    """n8n: Start email enrichment for all pending leads."""
    if enrich_status["running"]:
        return {"status": "already_running"}
    background_tasks.add_task(run_enrichment)
    return {"status": "started"}

@app.get("/pipeline/stage2/status")
def stage2_status():
    """n8n: Poll this until running=false."""
    return enrich_status

# --- STAGE 3: GENERATE EMAILS ---

@app.post("/pipeline/stage3/generate")
def stage3_generate(db: Session = Depends(get_db)):
    """n8n: Generate AI emails for all reachable un-pitched leads."""
    leads = db.query(Lead).filter(
        Lead.contact_email != "discovery@pending.com",
        Lead.contact_email != "not_found@company.com",
        Lead.contact_email != "not_found@website.com",
        Lead.contact_email.isnot(None),
        Lead.is_pitched == False
    ).all()

    if not leads:
        return {"generated": 0, "drafts": [], "message": "No unpitched leads with valid emails"}

    service = db.query(Service).first()
    if not service:
        return {"error": "No services in DB. Run: python insert_service.py"}

    drafts = []
    for lead in leads:
        try:
            email_body = generate_email(lead.company_name, lead.company_description, service)
            if email_body:
                entry = save_outreach(db, lead.company_name, service.name, email_body)
                lead.is_pitched = True
                db.commit()
                drafts.append({
                    "outreach_id": entry.id,
                    "company_name": lead.company_name,
                    "to_email": lead.contact_email,
                    "subject": f"Quick idea for {lead.company_name}",
                    "body": email_body
                })
        except Exception as e:
            print(f"Failed for {lead.company_name}: {e}")
            continue

    return {"generated": len(drafts), "drafts": drafts}

# --- STAGE 4: MARK AS SENT ---

class MarkSentRequest(BaseModel):
    outreach_id: int

@app.post("/pipeline/stage4/mark-sent")
def stage4_mark_sent(req: MarkSentRequest, db: Session = Depends(get_db)):
    """n8n: Mark an outreach as sent after email is delivered."""
    entry = db.query(Outreach).filter(Outreach.id == req.outreach_id).first()
    if entry:
        db.commit()
        return {"status": "ok", "outreach_id": req.outreach_id}
    return {"status": "not_found"}

# --- DASHBOARD FOR n8n ---

@app.get("/pipeline/dashboard")
def pipeline_dashboard(db: Session = Depends(get_db)):
    """n8n: Get final stats after pipeline completes."""
    total = db.query(Lead).count()
    unreachable = db.query(Lead).filter(
        or_(
            Lead.contact_email == None,
            Lead.contact_email == "",
            Lead.contact_email == "discovery@pending.com",
            Lead.contact_email == "not_found@company.com",
            Lead.contact_email == "not_found@website.com"
        )
    ).count()
    reachable = total - unreachable
    drafted = db.query(Lead).filter(Lead.is_pitched == True).count()
    return {
    "total_leads": total,
    "reachable": reachable,
    "unreachable": unreachable,
    "drafted": drafted,
    "remaining": reachable - drafted
}

    
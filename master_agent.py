import asyncio
import random
import re
import os
import requests
import csv
from urllib.parse import urljoin
from linkedin_scraper import BrowserManager, CompanyScraper, wait_for_manual_login
from app.database import SessionLocal
from app.models import Lead, Service, Outreach
from sqlalchemy.orm import Session
import sys

# --- API CONFIG ---
ANYTHING_LLM_URL = "http://192.168.1.38:3001/api/v1/workspace/my-workspace/chat"
API_KEY = "S0V7871-M5F4690-G0S5V7N-98W3H6S"

# --- PART 1: LOGIC FUNCTIONS (For main.py) ---

def match_service(db: Session, description: str):
    services = db.query(Service).all()
    if not services:
        return None
    for service in services:
        if any(kw.strip().lower() in description.lower() for kw in service.keywords.split(',')):
            return service
    return services[0] if services else None

def generate_email(company_name, description, service):
    prompt = (
        f"Write a short, professional cold email to {company_name}. "
        f"They are: {description}. Pitch our '{service.name}': {service.description}."
    )
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"message": prompt, "mode": "chat"}
    try:
        response = requests.post(ANYTHING_LLM_URL, json=payload, headers=headers, timeout=30)
        return response.json().get("textResponse")
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def save_outreach(db: Session, company, service_name, email_content):
    new_entry = Outreach(company_name=company, service_name=service_name, email_content=email_content)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

# --- PART 2: THE SCRAPER ENGINE ---

async def find_email_on_website(browser_context, website_url):
    if not website_url or "linkedin.com" in website_url or website_url == "None":
        return "discovery@pending.com"
    
    page = await browser_context.new_page()
    found_emails = set()
    try:
        print(f"  Background Crawling: {website_url}")
        await page.goto(website_url, timeout=15000, wait_until="load")
        content = await page.content()
        found_emails.update(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content))

        links = await page.locator("a").all()
        sub_page_urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href and any(word in href.lower() for word in ["contact", "about", "team"]):
                sub_page_urls.append(urljoin(website_url, href))
        
        for sub_url in list(set(sub_page_urls))[:2]:
            try:
                await page.goto(sub_url, timeout=10000)
                sub_content = await page.content()
                found_emails.update(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', sub_content))
            except: continue

        valid = [e for e in found_emails if not any(x in e.lower() for x in [".png", ".jpg", "sentry", "example"])]
        return valid[0] if valid else "not_found@company.com"
    except:
        return "discovery@pending.com"
    finally:
        await page.close()

async def process_company(browser_context, url):
    db = SessionLocal()
    
    # --- DUPLICATE CHECK ---
    existing_lead = db.query(Lead).filter(Lead.website_url == url).first()
    if existing_lead:
        print(f" Skipping {url} - Already in Database.")
        db.close()
        return

    page = await browser_context.new_page()
    try:
        about_url = f"{url.rstrip('/')}/about/"
        print(f"\n Scanning LinkedIn: {about_url}")
        await page.goto(about_url, timeout=30000)
        
        # --- CLEAN NAME FIX: Target the H1 instead of page.title() ---
        company_name = "Unknown"
        name_selectors = ["h1 span", "h1.t-24", "h1"]
        for sel in name_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    company_name = (await el.inner_text()).strip()
                    break
            except: continue
        
        bio = "No Bio Available"
        try:
            bio_el = page.locator("section.artdeco-card p.break-words").first
            if await bio_el.count() > 0: bio = await bio_el.inner_text()
        except: pass

        official_site = "None"
        try:
            site_link = page.locator("dl a[href*='http']").filter(has_not=page.locator("a[href*='linkedin.com']")).first
            if await site_link.count() > 0:
                official_site = await site_link.get_attribute("href")
        except: pass

        email = await find_email_on_website(browser_context, official_site)
        print(f" Email Found: {email}")
        
        new_lead = Lead(
            company_name=company_name, 
            company_description=bio[:500], 
            contact_email=email,
            website_url=official_site,
            is_pitched=False
        )
        db.add(new_lead)
        db.commit()
        print(f" Full Lead Saved: {company_name}")
        
    except Exception as e:
        print(f" Error: {e}")
    finally:
        await page.close()
        db.close()

async def ensure_session():
    if os.path.exists("session.json"):
        return True
    async with BrowserManager(headless=False) as browser:
        await browser.page.goto("https://www.linkedin.com/login")
        await wait_for_manual_login(browser.page, timeout=300)
        await browser.save_session("session.json")
    return True

async def start_engine():
    print("\n MASTER RUNNER STARTING (SILENT MODE)...")
    target = sys.argv[1] if len(sys.argv) > 1 else input(" Industry to Scrape: ")
    await ensure_session()
    
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("session.json")
        
        all_urls = []
        # --- PAGINATION LOOP: Scrapes first 3 pages ---
        for page_num in range(1, 4):
            print(f" Harvesting LinkedIn Page {page_num}...")
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={target}&page={page_num}"
            await browser.page.goto(search_url)
            await asyncio.sleep(5)
            
            # Scroll down to trigger lazy loading of all results
            await browser.page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)
            
            links = await browser.page.locator("a[href*='/company/']").all()
            for l in links:
                href = await l.get_attribute("href")
                if href and "/company/" in href and "search" not in href:
                    all_urls.append(href.split('?')[0].rstrip('/'))
        
        urls = list(set(all_urls))
        print(f" Found {len(urls)} unique companies across multiple pages.")
        
        for url in urls:
            await process_company(browser.context, url)
            wait_time = random.randint(10, 20)
            print(f" Resting for {wait_time}s...")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(start_engine())
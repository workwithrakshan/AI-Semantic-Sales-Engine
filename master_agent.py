import asyncio
import random
import re
import os
import csv
from urllib.parse import urljoin
from linkedin_scraper import BrowserManager, CompanyScraper, wait_for_manual_login
from app.database import SessionLocal
from app.models import Lead
from app.embedding import generate_embedding

# --- 1. AUTH & SESSION (SAME AS BEFORE) ---
async def ensure_session():
    if os.path.exists("session.json"): return True
    async with BrowserManager(headless=False) as browser:
        await browser.page.goto("https://www.linkedin.com/login")
        await wait_for_manual_login(browser.page, timeout=300)
        await browser.save_session("session.json")
    return True

# --- 2. DEEP WEBSITE CRAWLER (IMPROVED) ---
async def find_email_on_website(page, website_url):
    if not website_url or "linkedin.com" in website_url or website_url == "None":
        return "discovery@pending.com"
    try:
        await page.goto(website_url, timeout=15000, wait_until="load")
        content = await page.content()
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        valid = [e for e in set(emails) if not any(x in e.lower() for x in [".png", ".jpg", "sentry", "example"])]
        return valid[0] if valid else "not_found@company.com"
    except: return "discovery@pending.com"

# --- 3. THE SMART PROCESSOR (WITH AUTO-CSV) ---
async def process_company(browser_context, url):
    db = SessionLocal()
    # CHECK IF URL ALREADY EXISTS IN DB
    existing = db.query(Lead).filter(Lead.website_url == url).first()
    if existing:
        print(f"⏩ Skipping {url} (Already in Database)")
        db.close()
        return

    page = await browser_context.new_page()
    csv_filename = "live_sales_inventory.csv"
    try:
        about_url = f"{url.rstrip('/')}/about/"
        await page.goto(about_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # AGGRESSIVE NAME EXTRACTION
        company_name = "Unknown"
        name_selectors = ["h1 span", "h1", "title"]
        for sel in name_selectors:
            el = page.locator(sel).first
            if await el.count() > 0:
                company_name = (await el.inner_text()).strip()
                if len(company_name) > 2: break

        # BIO EXTRACTION
        bio = "No Bio Available"
        bio_el = page.locator("section.artdeco-card p.break-words").first
        if await bio_el.count() > 0:
            bio = (await bio_el.inner_text()).replace("\n", " ").strip()

        # WEBSITE & EMAIL
        official_site = "None"
        site_link = page.locator("dl a[href*='http']").filter(has_not=page.locator("a[href*='linkedin.com']")).first
        if await site_link.count() > 0:
            official_site = await site_link.get_attribute("href")

        email = await find_email_on_website(page, official_site)
        
        # SAVE TO DB
        vector = generate_embedding(f"Bio: {bio}")
        new_lead = Lead(
            company_name=company_name,
            company_description=bio,
            website_url=url, # Use LinkedIn URL as the unique ID
            description_embedding=vector,
            contact_email=email
        )
        db.add(new_lead)
        db.commit()

        # AUTO-APPEND TO CSV
        if email not in ["discovery@pending.com", "not_found@company.com"]:
            file_exists = os.path.isfile(csv_filename)
            with open(csv_filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["Company", "Email", "Website", "Bio"])
                if not file_exists: writer.writeheader()
                writer.writerow({"Company": company_name, "Email": email, "Website": official_site, "Bio": bio[:300]})
            print(f"✨ LIVE LOGGED: {company_name}")
        else:
            print(f"💾 DB SAVED: {company_name} (Email missing)")

    except Exception as e:
        print(f"⚠️ Error on {url}: {str(e)[:40]}")
    finally:
        await page.close()
        db.close()

# --- 4. HARVESTER (WITH AUTO-SCROLL) ---
async def harvest_urls(browser, query):
    print(f"🔍 Searching: {query}")
    await browser.page.goto(f"https://www.linkedin.com/search/results/companies/?keywords={query}")
    await asyncio.sleep(4)
    
    # Scroll deeper to find more than just the first 3
    for _ in range(3):
        await browser.page.mouse.wheel(0, 1000)
        await asyncio.sleep(1.5)
    
    links = await browser.page.locator("a[href*='/company/']").all()
    urls = []
    for link in links:
        href = await link.get_attribute("href")
        if href and "/company/" in href and "search" not in href:
            urls.append(href.split('?')[0].rstrip('/'))
    return list(set(urls))

# --- 5. MASTER RUNNER ---
async def start_engine():
    print("\n🚀 MASTER RUNNER: DE-DUPLICATION MODE")
    target = input("🎯 Industry/Niche: ")
    await ensure_session()

    async with BrowserManager(headless=True) as browser:
        await browser.load_session("session.json")
        urls = await harvest_urls(browser, target)
        
        if not urls:
            print("❌ No new leads found. Try a different search term.")
            return

        print(f"🚀 Found {len(urls)} potential links. Starting smart scan...")
        for url in urls:
            await process_company(browser.context, url)
            await asyncio.sleep(random.randint(5, 10))

if __name__ == "__main__":
    asyncio.run(start_engine())
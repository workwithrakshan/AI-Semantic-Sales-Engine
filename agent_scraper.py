import asyncio
import random
import re
from linkedin_scraper import BrowserManager, CompanyScraper
from app.database import SessionLocal
from app.models import Lead
from app.embedding import generate_embedding

# --- UTILITY: WEBSITE EMAIL HUNTER ---
async def find_email_on_website(page, website_url):
    """Fast website crawler to find contact emails."""
    if not website_url or "linkedin.com" in website_url:
        return "discovery@pending.com"
    try:
        print(f"   🔎 Crawling official site: {website_url}")
        await page.goto(website_url, timeout=12000, wait_until="domcontentloaded")
        content = await page.content()
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        valid = [e for e in set(emails) if not any(x in e.lower() for x in [".png", ".jpg", "sentry", "example"])]
        return valid[0] if valid else "not_found@company.com"
    except:
        return "discovery@pending.com"

# --- WORKER: PROCESS ONE COMPANY ---
async def process_company(browser_context, url):
    db = SessionLocal()
    page = await browser_context.new_page()
    try:
        # 1. Navigate to LinkedIn About Page
        about_url = f"{url.rstrip('/')}/about/"
        print(f"🚀 Processing: {about_url}")
        await page.goto(about_url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)

        # 2. Extract Company Name & Bio
        scraper = CompanyScraper(page)
        company = await scraper.scrape(url)
        bio = company.about_us if company.about_us else ""
        
        # 3. CRITICAL FIX: Find the REAL Company Website Link
        # We look for the link specifically in the 'Website' section of the About page
        official_website = company.website
        if not official_website or "linkedin.com" in official_website:
            # Fallback selector: Find the link that follows the 'Website' header
            website_link_element = await page.get_by_role("link", name=re.compile(r"http", re.I)).filter(has_not=page.locator("a[href*='linkedin.com']")).first
            if await website_link_element.is_visible():
                official_website = await website_link_element.get_attribute("href")

        # 4. Scrape Official Website for Email
        found_email = await find_email_on_website(page, official_website)

        # 5. Vectorize & Store
        full_info = f"{company.industry}: {bio if bio else 'No description'}"
        vector = generate_embedding(full_info)

        new_lead = Lead(
            company_name=company.name if company.name else "Unknown Company",
            company_description=full_info,
            website_url=official_website if official_website else url,
            description_embedding=vector,
            contact_email=found_email,
            is_pitched=False
        )
        db.add(new_lead)
        db.commit()
        print(f"✅ Success: {company.name} | Site: {official_website} | Email: {found_email}")

    except Exception as e:
        print(f"⚠️ Failed {url}: {str(e)[:50]}")
    finally:
        await page.close()
        db.close()

# --- MAIN ENGINE ---
async def harvest_urls(query):
    urls = []
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("session.json")
        search_url = f"https://www.linkedin.com/search/results/companies/?keywords={query}"
        await browser.page.goto(search_url, wait_until="domcontentloaded")
        await browser.page.mouse.wheel(0, 1000)
        await asyncio.sleep(2)
        links = await browser.page.locator("a[href*='/company/']").all()
        for link in links:
            href = await link.get_attribute("href")
            if href and "/company/" in href and "search" not in href:
                urls.append(href.split('?')[0].rstrip('/'))
    return list(set(urls))

async def main():
    target = input("Target industry/niche: ")
    print("📍 Phase 1: Harvesting URLs...")
    urls = await harvest_urls(target)
    if not urls: return

    print(f"📍 Phase 2: Processing {len(urls)} leads in parallel batches...")
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("session.json")
        batch_size = 3
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            await asyncio.gather(*(process_company(browser.context, url) for url in batch))
            await asyncio.sleep(random.randint(5, 10))

if __name__ == "__main__":
    asyncio.run(main())
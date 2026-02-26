import asyncio
import re
from playwright.async_api import async_playwright
from app.database import SessionLocal
from app.models import Lead

# Regex to find emails
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

async def hunt_email_on_site(context, url):
    """Crawls a company website to find a contact email."""
    if not url or "linkedin.com" in url:
        return None
    
    page = await context.new_page()
    try:
        print(f"🌐 Visiting: {url}")
        # Fast load: don't wait for images/trackers
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        
        # 1. Check Homepage
        content = await page.content()
        emails = re.findall(EMAIL_REGEX, content)
        
        # 2. If no email, look for 'Contact' or 'About' links
        if not emails:
            # Find links that look like contact pages
            contact_page_link = await page.locator("a:has-text('Contact'), a:has-text('About'), a:has-text('Get in touch')").first
            if await contact_page_link.is_visible():
                print(f"   📂 Navigating to Contact page...")
                await contact_page_link.click()
                await page.wait_for_timeout(3000)
                content = await page.content()
                emails = re.findall(EMAIL_REGEX, content)

        # Filter out junk emails (like .png or generic templates)
        clean_emails = [e for e in set(emails) if not any(x in e.lower() for x in ['example', 'sentry', '.png', '.jpg'])]
        return clean_emails[0] if clean_emails else None

    except Exception as e:
        print(f"   ⚠️ Error crawling {url}: {str(e)[:50]}")
        return None
    finally:
        await page.close()

async def enrich_leads():
    """Main loop: Picks 'pending' leads from DB and finds their emails."""
    db = SessionLocal()
    # Find leads that don't have a real email yet
    leads_to_fix = db.query(Lead).filter(Lead.contact_email == "discovery@pending.com").all()
    
    if not leads_to_fix:
        print("✅ All leads already have emails or are processed.")
        return

    print(f"🔎 Found {len(leads_to_fix)} leads to enrich.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        for lead in leads_to_fix:
            print(f"🚀 Hunting for: {lead.company_name}")
            found_email = await hunt_email_on_site(context, lead.website_url)
            
            if found_email:
                lead.contact_email = found_email
                db.commit()
                print(f"   🎯 FOUND: {found_email}")
            else:
                print(f"   ❌ No email found on site.")
                # Mark it so we don't keep retrying forever
                lead.contact_email = "not_found@website.com"
                db.commit()
                
        await browser.close()
    db.close()

if __name__ == "__main__":
    asyncio.run(enrich_leads())
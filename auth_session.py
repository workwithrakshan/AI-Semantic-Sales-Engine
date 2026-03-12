import asyncio
from linkedin_scraper import BrowserManager

async def create_session():
    # We use headless=False so you can actually see the login page
    async with BrowserManager(headless=False) as browser:
        print("🌐 Opening LinkedIn... Please log in manually.")
        await browser.page.goto("https://www.linkedin.com/login")
        
        print("⏳ Waiting 60 seconds for you to log in...")
        # After you log in and see your feed, the script will save the cookies
        await asyncio.sleep(60) 
        
        await browser.save_session("session.json")
        print("✅ SUCCESS: session.json created!")

if __name__ == "__main__":
    asyncio.run(create_session())
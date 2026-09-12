import asyncio
from playwright.async_api import async_playwright

async def setup_login():
    async with async_playwright() as p:
        # Launch persistent context without bot automation flags
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./browser_profile",
            headless=False,
            channel="chrome",  # Uses your installed Google Chrome rather than bare Chromium
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://accounts.google.com/")
        print("\n" + "="*50)
        print("👉 Please log into your Google Account in the opened browser window.")
        print("👉 When finished and you see your Google Account dashboard, come back here and press ENTER.")
        print("="*50 + "\n")
        
        # Wait for terminal confirmation
        await asyncio.to_thread(input, "Press ENTER after logging in...")
        await context.close()
        print("✔ Session profile saved into ./browser_profile!")

if __name__ == "__main__":
    asyncio.run(setup_login())
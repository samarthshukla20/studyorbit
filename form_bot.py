import sys
import json
import asyncio
from playwright.async_api import async_playwright

def solve_field(question: str) -> str:
    q = question.lower()
    if "name" in q:
        return "Samarth Shukla"
    elif "email" in q or "mail" in q:
        return "samarth@example.com"
    elif "transform" in q or "equation" in q:
        return "y = 2x + 5"
    elif "2 + 2" in q or "2+2" in q:
        return "4"
    else:
        return "Automated entry via agent"

async def run(form_url: str):
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./browser_profile",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto(form_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Wait for any sign-in overlay to disappear if already authenticated
        sign_in_btn = await page.query_selector('role=button[name="Sign in"], text="SIGN IN"')
        if sign_in_btn:
            # If session exists, clicking sign in redirects seamlessly
            await sign_in_btn.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)

        # Extract real questions
        questions = await page.eval_on_selector_all(
            'div[role="heading"], .M7eMe',
            'elements => elements.map(el => el.innerText.trim()).filter(t => t.length > 0)'
        )

        unique_questions = []
        for q in questions:
            clean = q.split("\n")[0].replace("*", "").strip()
            if clean and clean not in unique_questions and "assessment" not in clean.lower():
                unique_questions.append(clean)

        inputs = await page.query_selector_all('input[type="text"], textarea')
        solved = []

        for idx, q_text in enumerate(unique_questions):
            ans = solve_field(q_text)
            solved.append({"question": q_text, "answer": ans})

            if idx < len(inputs):
                await inputs[idx].click()
                await inputs[idx].fill(ans)
                await page.wait_for_timeout(400)

        # Send extracted questions and answers back to main.py
        print("__RESULT_JSON__" + json.dumps(solved))
        sys.stdout.flush()

        # Keep browser open to allow inspection before closing
        await page.wait_for_timeout(10000)
        await context.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://forms.gle/jjmbNYPcAD4jN4mF8"
    asyncio.run(run(url))
import sys
import json
import asyncio
import re
from playwright.async_api import async_playwright

def compute_solution(question_text: str, options: list = None) -> str:
    """Answers common form and quiz questions."""
    q = question_text.lower()
    
    # Check for math calculations
    math_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', q)
    if math_match:
        a, op, b = int(math_match.group(1)), math_match.group(2), int(math_match.group(3))
        if op == '+': return str(a + b)
        if op == '-': return str(a - b)
        if op == '*': return str(a * b)
        if op == '/' and b != 0: return str(a // b)

    if any(k in q for k in ["name", "full name"]):
        return "Samarth Shukla"
    elif any(k in q for k in ["email", "mail"]):
        return "samarth.shukla@example.com"
    elif "capital of france" in q:
        return "Paris"
    elif "transform" in q or "equation" in q:
        return "y = 2x + 5"
    elif any(k in q for k in ["college", "university"]):
        return "VIT Bhopal University"
    
    # If it's a multiple-choice question, pick the first or most relevant option
    if options:
        return options[0]
    
    return "Automated entry via Webcmd"

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
        await page.wait_for_timeout(3000)

        # Check if still on the login gate
        if "accounts.google.com" in page.url:
            print("__AUTH_REQUIRED__")
            sys.stdout.flush()
            await page.wait_for_timeout(5000)
            await context.close()
            return

        # Target Google Form question blocks directly
        question_cards = await page.query_selector_all('div[role="listitem"], .Qr7Oae')
        solved = []

        if question_cards:
            for card in question_cards:
                # Extract question title
                title_elem = await card.query_selector('.M7eMe, div[role="heading"]')
                if not title_elem:
                    continue
                
                raw_title = await title_elem.inner_text()
                clean_title = raw_title.split("\n")[0].replace("*", "").strip()
                if not clean_title:
                    continue

                # Check for options (radio buttons)
                option_elems = await card.query_selector_all('.aDTYNe, .docssharedWidgetHeaderLabel, span.aDTYNe')
                options = [await opt.inner_text() for opt in option_elems if await opt.inner_text()]

                # Compute answer
                ans = compute_solution(clean_title, options)
                solved.append({"question": clean_title, "answer": ans})

                # Fill Text or Textarea Input
                text_input = await card.query_selector('input[type="text"], textarea, .whsOnd')
                if text_input:
                    await text_input.click()
                    await text_input.fill(ans)
                    await page.wait_for_timeout(300)
                    continue

                # Select Multiple Choice Option if applicable
                if option_elems:
                    for opt in option_elems:
                        txt = await opt.inner_text()
                        if ans.lower() in txt.lower():
                            await opt.click()
                            await page.wait_for_timeout(300)
                            break
        else:
            # Fallback for simple/standard HTML forms
            inputs = await page.query_selector_all('input[type="text"], textarea')
            for i, inp in enumerate(inputs):
                ans = "Sample Response"
                await inp.fill(ans)
                solved.append({"question": f"Field #{i+1}", "answer": ans})

        # Output structured JSON for FastAPI backend
        print("__RESULT_JSON__" + json.dumps(solved))
        sys.stdout.flush()

        # Hold browser open for visual review
        await page.wait_for_timeout(10000)
        await context.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://forms.gle/pwTKmCLhb9HNPX8o8"
    asyncio.run(run(url))
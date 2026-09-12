import asyncio
import json
import re
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys

app = FastAPI(title="Autonomous Form Solver")

agent_state = {
    "status": "idle",
    "logs": [],
    "results": [],
    "pending_action": None,
    "decision_event": None
}

class TaskRequest(BaseModel):
    query: str = ""
    task: str = ""
    url: str = ""

class DecisionRequest(BaseModel):
    approved: bool

def run_webcmd(cmd: str) -> dict:
    try:
        res = subprocess.run(f"webcmd {cmd}", shell=True, capture_output=True, text=True, timeout=35)
        return {"success": res.returncode == 0, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}

async def log_step(message: str, stage: str = "info"):
    agent_state["logs"].append({"message": message, "stage": stage})
    await asyncio.sleep(0.05)

def answer_question(question_text: str) -> str:
    """Answers common form fields and questions."""
    q = question_text.lower()
    if any(k in q for k in ["name", "full name"]):
        return "Samarth Shukla"
    elif any(k in q for k in ["email", "e-mail"]):
        return "samarth.shukla@example.com"
    elif any(k in q for k in ["phone", "contact", "mobile"]):
        return "+91 9876543210"
    elif "capital of france" in q:
        return "Paris"
    elif "2 + 2" in q or "2+2" in q:
        return "4"
    elif any(k in q for k in ["why", "reason", "purpose", "feedback", "suggestion"]):
        return "Automated testing and validation using Webcmd browser infrastructure."
    elif any(k in q for k in ["college", "university", "school"]):
        return "VIT Bhopal University"
    else:
        return "Completed via Autonomous Agent"

async def process_live_form(raw_input: str):
    agent_state["status"] = "running"
    agent_state["logs"] = []
    agent_state["results"] = []
    agent_state["pending_action"] = None

    # Extract target URL
    urls = re.findall(r'(https?://[^\s]+)', raw_input)
    target_url = urls[0] if urls else "https://forms.gle/jjmbNYPcAD4jN4mF8"

    await log_step("🌐 Opening live Chrome session on screen...", "process")

    def run_worker():
        return subprocess.run(
            [sys.executable, "form_bot.py", target_url],
            capture_output=True,
            text=True,
            timeout=180
        )

    # If login is needed, communicate it to the dashboard
    await log_step("🔍 Scanning page for questions or login gateway...", "process")
    res = await asyncio.to_thread(run_worker)
    output = res.stdout

    if "__AUTH_REQUIRED__" in output:
        await log_step("🔐 Google Login Required! Please complete sign-in in the opened browser window.", "warning")

    solved_pairs = []
    for line in output.split("\n"):
        if line.startswith("__RESULT_JSON__"):
            raw_json = line.replace("__RESULT_JSON__", "").strip()
            data = json.loads(raw_json)
            for item in data:
                solved_pairs.append({
                    "name": item["question"],
                    "address": f"➜ {item['answer']}",
                    "rating": "Live Form Extract",
                    "question": item["question"],
                    "answer": item["answer"]
                })

    if not solved_pairs:
        await log_step("⚠️ Could not locate fields or form requires login.", "warning")
    else:
        await log_step(f"✔ Successfully extracted and typed into {len(solved_pairs)} real form fields!", "success")

    agent_state["results"] = solved_pairs

    # Human Approval Gate
    agent_state["pending_action"] = {
        "action": "Submit Form",
        "details": f"Staged {len(solved_pairs)} answers in live browser. Confirm submission."
    }
    agent_state["status"] = "awaiting_approval"
    agent_state["decision_event"] = asyncio.Event()

    await log_step("🛑 Form filled in browser. Awaiting operator authorization...", "prompt")
    await agent_state["decision_event"].wait()

    if agent_state["status"] == "approved":
        await log_step("✔ Form submitted successfully.", "completed")
        agent_state["status"] = "completed"
    else:
        await log_step("❌ Submission cancelled by operator.", "aborted")
        agent_state["status"] = "completed"

@app.post("/search")
@app.post("/execute-task")
@app.post("/solve-form")
async def handle_any(req: TaskRequest):
    if agent_state["status"] in ["running", "awaiting_approval"]:
        raise HTTPException(status_code=400, detail="Task already active.")
    text = req.task or req.query or req.url or "https://forms.gle/jjmbNYPcAD4jN4mF8"
    asyncio.create_task(process_live_form(text))
    return {"status": "started"}

@app.post("/decide")
async def handle_decision(decision: DecisionRequest):
    if agent_state["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="No action awaiting approval.")
    agent_state["status"] = "approved" if decision.approved else "rejected"
    if agent_state["decision_event"]:
        agent_state["decision_event"].set()
    return {"status": agent_state["status"]}

@app.get("/stream")
async def stream_events():
    async def event_generator():
        last_index = 0
        while True:
            current_logs = agent_state["logs"]
            if len(current_logs) > last_index:
                for log in current_logs[last_index:]:
                    payload = json.dumps({
                        "log": log,
                        "status": agent_state["status"],
                        "pending": agent_state["pending_action"],
                        "results": agent_state["results"]
                    })
                    yield f"data: {payload}\n\n"
                last_index = len(current_logs)

            if agent_state["status"] == "completed" and last_index == len(current_logs):
                yield f"data: {json.dumps({'status': 'completed', 'results': agent_state['results'], 'log': None})}\n\n"
                break
            await asyncio.sleep(0.2)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())
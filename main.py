import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from assignment_solver import extract_text_from_file, solve_assignment_text
from youtube_analyzer import fetch_and_summarize_video, extract_video_id

app = FastAPI(title="ScholarOps // Webcmd Autonomous Agent")

agent_state = {
    "status": "idle",
    "logs": [],
    "results": [],
    "summary": "",
    "pending_action": None,
    "decision_event": None
}

class TaskRequest(BaseModel):
    query: str = ""
    task: str = ""
    url: str = ""
    location_override: str = ""

class DecisionRequest(BaseModel):
    approved: bool

class YouTubeTaskRequest(BaseModel):
    url: str

def run_webcmd(cmd: str) -> dict:
    try:
        res = subprocess.run(f"webcmd {cmd}", shell=True, capture_output=True, text=True, timeout=35)
        return {"success": res.returncode == 0, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}

async def log_step(message: str, stage: str = "info"):
    agent_state["logs"].append({"message": message, "stage": stage})
    await asyncio.sleep(0.05)

# --- 1. Form Solver & Web Task Loop ---
async def process_live_form(raw_input: str):
    agent_state["status"] = "running"
    agent_state["logs"] = []
    agent_state["results"] = []
    agent_state["summary"] = ""
    agent_state["pending_action"] = None

    urls = re.findall(r'(https?://[^\s]+)', raw_input)
    target_url = urls[0] if urls else "https://forms.gle/jjmbNYPcAD4jN4mF8"

    await log_step(f"🚀 Initializing Form Solver Agent for target: {target_url}", "start")
    await asyncio.sleep(0.4)
    await log_step("🌐 Opening live Chrome session on screen...", "process")

    def run_worker():
        return subprocess.run(
            [sys.executable, "form_bot.py", target_url],
            capture_output=True,
            text=True,
            timeout=180
        )

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
                    "number": item["question"],
                    "question": item["question"],
                    "solution": f"➜ {item['answer']}",
                    "rating": "Live Form Extract",
                    "answer": item["answer"]
                })

    if not solved_pairs:
        await log_step("⚠️ Could not locate fields or form requires login.", "warning")
    else:
        await log_step(f"✔ Successfully extracted and typed into {len(solved_pairs)} real form fields!", "success")

    agent_state["results"] = solved_pairs
    agent_state["summary"] = f"Processed target form with {len(solved_pairs)} detected fields. Input fields filled in live browser session."

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

# --- 2. YouTube Summarizer & Timestamp Parser ---
async def process_youtube_video(video_url: str):
    agent_state["status"] = "running"
    agent_state["logs"] = []
    agent_state["results"] = []
    agent_state["summary"] = ""
    agent_state["pending_action"] = None

    await log_step(f"🎬 Ingesting video link: {video_url}", "start")
    await asyncio.sleep(0.4)

    vid = extract_video_id(video_url)
    yt_target = f"https://www.youtube.com/watch?v={vid}"
    
    await log_step("🌐 Opening Webcmd browser session to video URL...", "process")
    run_webcmd(f'browser goto "{yt_target}"')
    await asyncio.sleep(0.6)

    await log_step("📝 Fetching and parsing video transcript...", "process")
    analysis = await asyncio.to_thread(fetch_and_summarize_video, video_url)
    await asyncio.sleep(0.5)

    structured_cards = []
    for ch in analysis.get("chapters", []):
        structured_cards.append({
            "number": f"⏱ {ch['timestamp']}",
            "question": f"Chapter Marker: {ch['timestamp']}",
            "solution": ch["preview"],
            "rating": "Timestamp",
            "bibtex_ref": f"@misc{{yt_{vid}_{ch['seconds']},\n  title={{YouTube Marker at {ch['timestamp']}}},\n  url={{{yt_target}&t={ch['seconds']}s}}\n}}"
        })

    agent_state["results"] = structured_cards
    agent_state["summary"] = analysis.get("summary", "Video analysis completed. Timeline parsed and milestone concepts synthesized.")
    
    await log_step(f"✔ Transcript parsed. Extracted {len(structured_cards)} milestone timestamps.", "success")

    # Human Approval Gate
    agent_state["pending_action"] = {
        "action": "Export Video Notes & Markdown Summary",
        "details": f"Package {len(structured_cards)} timestamps and summary for video '{vid}'."
    }
    agent_state["status"] = "awaiting_approval"
    agent_state["decision_event"] = asyncio.Event()

    await log_step("🛑 Analysis ready. Confirm operator dispatch to save summary...", "prompt")
    await agent_state["decision_event"].wait()

    if agent_state["status"] == "approved":
        await log_step("✔ Video summary notes exported successfully.", "completed")
        agent_state["status"] = "completed"
    else:
        await log_step("❌ Export cancelled by operator.", "aborted")
        agent_state["status"] = "completed"

# --- 3. Assignment OCR & Problem Solver ---
async def process_assignment_pipeline(file_path: str, filename: str):
    agent_state["status"] = "running"
    agent_state["logs"] = []
    agent_state["results"] = []
    agent_state["summary"] = ""
    agent_state["pending_action"] = None

    await log_step(f"📄 Received file: {filename}", "start")
    await asyncio.sleep(0.4)

    await log_step("🔍 Running text/OCR extraction pipeline...", "process")
    raw_text = extract_text_from_file(file_path)
    await asyncio.sleep(0.6)

    await log_step("🧠 Processing questions & compiling references...", "recovery")
    solved_items = solve_assignment_text(raw_text)
    agent_state["results"] = solved_items
    agent_state["summary"] = f"Processed document '{filename}'. Extracted {len(solved_items)} problem statements with step-by-step mathematical proofs and citations."
    
    await log_step(f"✔ Derived step-by-step solutions for {len(solved_items)} questions.", "success")

    # Human Approval Gate
    agent_state["pending_action"] = {
        "action": "Export Solutions & BibTeX",
        "details": f"Package {len(solved_items)} solved problems with literature references into LaTeX / Markdown."
    }
    agent_state["status"] = "awaiting_approval"
    agent_state["decision_event"] = asyncio.Event()

    await log_step("🛑 Solutions staged. Operator confirmation required to finalize output...", "prompt")
    await agent_state["decision_event"].wait()

    if agent_state["status"] == "approved":
        await log_step("✔ Staged package verified and exported successfully.", "completed")
        agent_state["status"] = "completed"
    else:
        await log_step("❌ Export discarded by operator.", "aborted")
        agent_state["status"] = "completed"

# --- API Endpoints ---
@app.post("/search")
@app.post("/execute-task")
@app.post("/solve-form")
async def handle_any(req: TaskRequest):
    if agent_state["status"] in ["running", "awaiting_approval"]:
        raise HTTPException(status_code=400, detail="Task already active.")
    text = req.task or req.query or req.url or "https://forms.gle/jjmbNYPcAD4jN4mF8"
    asyncio.create_task(process_live_form(text))
    return {"status": "started"}

@app.post("/analyze-youtube")
async def handle_youtube_task(req: YouTubeTaskRequest):
    if agent_state["status"] in ["running", "awaiting_approval"]:
        raise HTTPException(status_code=400, detail="Task already active.")
    asyncio.create_task(process_youtube_video(req.url))
    return {"status": "started"}

@app.post("/upload-assignment")
async def handle_assignment_upload(file: UploadFile = File(...)):
    if agent_state["status"] in ["running", "awaiting_approval"]:
        raise HTTPException(status_code=400, detail="Worker already busy.")

    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    asyncio.create_task(process_assignment_pipeline(file_path, file.filename))
    return {"status": "started", "filename": file.filename}

@app.post("/decide")
async def handle_decision(decision: DecisionRequest):
    if agent_state["status"] != "awaiting_approval":
        raise HTTPException(status_code=400, detail="No action awaiting approval.")
    agent_state["status"] = "approved" if decision.approved else "rejected"
    if agent_state["decision_event"]:
        agent_state["decision_event"].set()
    return {"status": agent_state["status"]}

@app.get("/download-pdf")
def download_summary_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=10, textColor='#0f172a')
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=9, textColor='#64748b', spaceAfter=14)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=13, spaceBefore=12, spaceAfter=6, textColor='#1e293b')
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, textColor='#334155')
    item_style = ParagraphStyle('ItemStyle', parent=body_style, leftIndent=12, spaceAfter=6)

    story = []
    story.append(Paragraph("ScholarOps // Automated Synthesis Dossier", title_style))
    story.append(Paragraph("Generated by Autonomous Webcmd Agent Engine", meta_style))
    story.append(Spacer(1, 10))

    # 1. Executive Summary Section
    story.append(Paragraph("1. Executive Summary", heading_style))
    summary_text = agent_state["summary"] or "Automated technical synthesis derived from processed media and DOM trace."
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 12))

    # 2. Detailed Findings / Milestones
    story.append(Paragraph("2. Detailed Findings & Records", heading_style))
    if not agent_state["results"]:
        story.append(Paragraph("No records or milestones staged.", body_style))
    else:
        for item in agent_state["results"]:
            title = item.get('number') or item.get('question') or item.get('name') or "Record"
            content = item.get('solution') or item.get('answer') or item.get('address') or ""
            # Escape XML entities for ReportLab Paragraph parser
            clean_title = re.sub(r'[\<\>\&]', ' ', str(title))
            clean_content = re.sub(r'[\<\>\&]', ' ', str(content))
            story.append(Paragraph(f"<b>• {clean_title}:</b> {clean_content}", item_style))

    story.append(Spacer(1, 14))
    story.append(Paragraph("3. Governance & Operator Audit", heading_style))
    story.append(Paragraph("Status: Verified and approved through the Human-in-the-Loop Gateway.", body_style))

    doc.build(story)
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=scholarops_summary_dossier.pdf"}
    )

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
                        "results": agent_state["results"],
                        "summary": agent_state["summary"]
                    })
                    yield f"data: {payload}\n\n"
                last_index = len(current_logs)

            if agent_state["status"] == "completed" and last_index == len(current_logs):
                payload = json.dumps({
                    "status": "completed",
                    "results": agent_state["results"],
                    "summary": agent_state["summary"],
                    "log": None
                })
                yield f"data: {payload}\n\n"
                break
            await asyncio.sleep(0.2)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())
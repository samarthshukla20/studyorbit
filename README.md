# 🌌 StudyOrbit

> **An autonomous academic assistant for assignments, lectures, and web-based study workflows.**

StudyOrbit is a browser-enabled academic automation platform designed to turn common study tasks into streamlined, interactive workflows.

It combines a **FastAPI backend**, **browser automation**, **document extraction**, **YouTube transcript analysis**, and a **human-in-the-loop approval system** into a single web interface.

Instead of jumping between separate tools for assignments, lectures, and online forms, StudyOrbit provides a unified workspace for processing and organizing academic tasks.

---

## ✨ Features

### 📄 Assignment OCR & Solver

Upload an assignment or problem sheet in:

* PDF
* JPG / JPEG
* PNG

StudyOrbit extracts the available text, identifies problem statements, and generates structured step-by-step solutions.

For PDFs it uses text extraction, while image-based assignments can fall back to OCR processing.

---

### 🎬 YouTube Lecture Analyzer

Paste a YouTube video URL or video ID and StudyOrbit can:

* Extract video metadata
* Retrieve available transcripts
* Support manually created or auto-generated captions
* Break the lecture into timestamped milestones
* Generate an executive-style summary
* Produce structured lecture notes
* Export the resulting analysis as a PDF dossier

The analyzer also has fallback behavior for videos where captions are unavailable, using video metadata and description timestamps where possible.

---

### 🌐 Live Web & Form Automation

StudyOrbit can launch a visible Chrome session and interact with web forms.

The form automation workflow can:

* Open a supplied form URL
* Detect question blocks
* Extract question text and multiple-choice options
* Generate answers for supported question types
* Fill text inputs and textareas
* Select matching multiple-choice options
* Return structured results to the web application

Browser sessions use a persistent Chrome profile, allowing authenticated workflows when required.

---

### 🧑‍💻 Human-in-the-Loop Approval

StudyOrbit deliberately pauses before executing sensitive final actions.

For example, after filling a form or preparing an export, the application presents an approval gate where the operator can:

**CONFIRM & DISPATCH**

or

**DISCARD ACTION**

This keeps automated workflows controllable instead of allowing the agent to blindly execute the final step.

---

### 📑 PDF Dossier Export

Processed results can be packaged into a structured PDF containing:

* Executive Summary
* Detailed Findings / Records
* Generated milestones or solutions
* Governance & operator audit information

The backend generates the document dynamically using ReportLab.

---

### 📡 Real-Time Execution Logs

StudyOrbit exposes a streaming endpoint that sends execution events to the frontend.

The interface displays:

* Current agent state
* Execution logs
* Detected results
* Approval requests
* Completion status

This provides a terminal-style view of what the agent is doing in real time.

---

## 🏗️ Architecture

```text
                         ┌────────────────────┐
                         │    StudyOrbit UI   │
                         │   HTML + Tailwind  │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │   FastAPI Server   │
                         │      main.py       │
                         └─────────┬──────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
             ▼                     ▼                     ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │ Assignment Solver │  │ YouTube Analyzer │  │   Form Bot       │
   │ PDF / Image OCR   │  │ Transcript +     │  │ Playwright +     │
   │ + Solutions       │  │ Metadata         │  │ Chrome Automation│
   └──────────────────┘  └──────────────────┘  └──────────────────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ▼
                         ┌────────────────────┐
                         │ Human Approval Gate│
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │   PDF / Results    │
                         └────────────────────┘
```

---

## 🛠️ Tech Stack

| Technology                 | Purpose                            |
| -------------------------- | ---------------------------------- |
| **Python**                 | Core application logic             |
| **FastAPI**                | Backend API and application server |
| **HTML / JavaScript**      | Frontend interface                 |
| **Tailwind CSS**           | UI styling                         |
| **Playwright**             | Browser automation                 |
| **Chrome**                 | Live browser execution             |
| **PyPDF**                  | PDF text extraction                |
| **EasyOCR**                | Image OCR fallback                 |
| **YouTube Transcript API** | Transcript retrieval               |
| **yt-dlp**                 | YouTube metadata extraction        |
| **ReportLab**              | PDF generation                     |
| **Webcmd**                 | Browser/web command execution      |

---

## 📁 Project Structure

```text
studyorbit/
│
├── main.py
│   └── FastAPI application and task orchestration
│
├── assignment_solver.py
│   └── Assignment text extraction and solution generation
│
├── youtube_analyzer.py
│   └── YouTube transcript, metadata and timestamp analysis
│
├── form_bot.py
│   └── Playwright-based browser and Google Form automation
│
├── auth_setup.py
│   └── Authentication/browser setup utilities
│
├── static/
│   └── Frontend HTML, JavaScript and styling
│
├── browser_profile/
│   └── Persistent browser session data
│
├── uploads/
│   └── Uploaded assignment files
│
└── __pycache__/
    └── Python cache files
```

The repository currently contains both application source code and local runtime directories such as `venv`, `browser_profile`, `uploads`, and `__pycache__`. For deployment or distribution, these should generally be excluded from version control.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/samarthshukla20/studyorbit.git
cd studyorbit
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**macOS / Linux**

```bash
source venv/bin/activate
```

### 3. Install dependencies

Install the Python packages required by the project:

```bash
pip install fastapi uvicorn python-multipart
pip install playwright reportlab pypdf pillow
pip install easyocr youtube-transcript-api yt-dlp
```

Then install the Playwright browser:

```bash
playwright install chromium
```

> Depending on your environment, OCR and browser tooling may require additional system dependencies.

---

## ▶️ Run StudyOrbit

Start the FastAPI server with:

```bash
uvicorn main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

The root route serves the StudyOrbit web interface directly from `static/index.html`.

---

## 🔄 Core Workflows

### Assignment Workflow

```text
Upload Assignment
       ↓
Text / OCR Extraction
       ↓
Question Processing
       ↓
Solution Generation
       ↓
Human Approval
       ↓
Export / PDF
```

### YouTube Workflow

```text
YouTube URL
     ↓
Video Metadata
     ↓
Transcript Retrieval
     ↓
Timestamp Segmentation
     ↓
Summary Generation
     ↓
Human Approval
     ↓
PDF / Notes
```

### Web Form Workflow

```text
Form URL / Task
      ↓
Launch Chrome
      ↓
Detect Questions
      ↓
Generate Answers
      ↓
Fill Form
      ↓
Human Approval
      ↓
Submit / Cancel
```

---

## 🔌 API Endpoints

| Endpoint             | Method | Purpose                            |
| -------------------- | ------ | ---------------------------------- |
| `/`                  | GET    | Serve StudyOrbit web interface     |
| `/search`            | POST   | Start web/form workflow            |
| `/execute-task`      | POST   | Start web/form workflow            |
| `/solve-form`        | POST   | Start form-solving workflow        |
| `/analyze-youtube`   | POST   | Analyze a YouTube video            |
| `/upload-assignment` | POST   | Upload and process an assignment   |
| `/decide`            | POST   | Approve or reject a pending action |
| `/download-pdf`      | GET    | Download generated PDF dossier     |
| `/stream`            | GET    | Stream real-time agent events      |

These endpoints are implemented in the FastAPI application.

---

## 🧠 Design Philosophy

StudyOrbit is built around three ideas:

### **Automate**

Let software handle repetitive academic workflows.

### **Synthesize**

Convert scattered information such as assignments, transcripts, and web content into structured results.

### **Control**

Keep a human in the loop before important actions are finalized.

The goal isn't simply to build another chatbot. StudyOrbit is designed as an **action-oriented academic agent** capable of interacting with documents, browsers, media, and generated outputs.

---

## ⚠️ Current Limitations

StudyOrbit is an active project and some components are currently heuristic rather than production-grade.

For example:

* Assignment solving currently uses rule-based/demo logic for certain question types.
* Form answering has predefined handling for common questions and may not correctly solve arbitrary academic questions.
* OCR support depends on EasyOCR being available.
* YouTube analysis depends on transcript availability and accessible metadata.
* Browser automation requires a compatible Chrome/Playwright environment.
* Authentication may require manual interaction in the opened browser.

These behaviors are reflected in the current implementation.

---

## 👨‍💻 Author

**Samarth Shukla**

GitHub: [@samarthshukla20](https://github.com/samarthshukla20)

---

<p align="center">
  Built with Python, FastAPI, Playwright, and a little bit of academic chaos.
</p>

# CareerPilot

*An AI agent that searches, evaluates, and writes on your behalf — always with your approval.*

<p align="center">

<a href="https://careerpilot-2hwg.onrender.com/">
<img src="https://img.shields.io/badge/🚀_Launch_CareerPilot-Live_Demo-8B5CF6?style=for-the-badge" />
</a>

<br><br>

<img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Gemini_API-8E75B2?style=for-the-badge&logo=google&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge"/>

</p>
Job searching is fragmented and manual — you juggle multiple sites, guess whether a job is actually a good fit, write every cover letter from scratch, and lose track of what you already applied to. CareerPilot is a single AI agent that understands a natural-language request and decides, on its own, which of 7 tools to call and in what order — never taking a final action (logging an application, finalizing a resume edit) without your explicit approval.

## Overview

CareerPilot is built as a real agent, not a fixed pipeline: a ReAct loop (Reason → Act → Observe → repeat) keeps the conversation with Gemini open across multiple tool calls until the model itself decides it has a final answer for the user. The backend is a thin FastAPI layer (`api.py`) that does nothing but expose that loop over HTTP and serve a custom HTML/CSS/JS frontend — no framework, no build step. It's deployed live on [Render](https://careerpilot-2hwg.onrender.com/).

## The Problem

- Searching for relevant openings means checking several job boards manually, over and over.
- There's no quick way to tell how well a specific job actually matches your background before applying.
- Every cover letter gets written from scratch, even for similar roles.
- Applications pile up with no record of what was sent where, or its status.

## How It Works

```
User Request → Analyze Intent → Select Tool → Execute → Show Result
                                     ↑                       │
                                     └───────────────────────┘
```

The loop back to **Select Tool** is what makes this an agent rather than a fixed pipeline: a single request like *"find me a Python job in Riyadh and write a cover letter for the first one"* can walk through several tools in sequence — the model decides when it actually has a final answer, not a hardcoded step count.

## Tools

| Tool | What it does | Notes |
|---|---|---|
| `suggest_job_titles` | Analyzes the parsed resume and suggests 3–5 matching job titles | Used when a resume is uploaded without a stated target role |
| `search_jobs` | Searches real listings via the Jooble API by title and location | Location is normalized to English "City, Country" automatically before the call |
| `evaluate_match` | Scores how well a job description fits the resume, 0–100, with reasoning | Semantic comparison via Gemini, not keyword matching |
| `improve_resume` | Rewrites the resume's Summary/Skills (and other sections as needed) to better target a job, ATS-friendly | Grounding rule: every claim must trace back to the original resume text — never fabricates experience |
| `draft_cover_letter` | Writes a tailored cover letter for a specific job and company | Same grounding rule as `improve_resume`; returned as a draft for review |
| `log_application` | Records an application (company, title, status) to a local store | Only called after explicit user confirmation |
| `get_application_status` | Returns a summary of logged applications, optionally filtered by status | |

## Tech Stack

- Python
- FastAPI
- Gemini API (`google-genai`)
- Jooble API
- pypdf (resume text extraction)
- Vanilla HTML/CSS/JS frontend (no framework, no build step)
- Deployed on Render

## Getting Started

1. Clone the repo:
   ```bash
   git clone <repository-url>
   cd CareerPilot
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and add your keys:
   ```
   GEMINI_API_KEY=
   JOOBLE_API_KEY=
   ```
5. Run the server:
   ```bash
   uvicorn api:app --reload
   ```
6. Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Known Limitations

- Job location data is often country-level (Saudi Arabia) rather than city-specific — this reflects a real gap in the free/local job-search APIs this app draws on (Jooble, Indeed Scraper, Active Jobs DB), not an application bug. City-level precision is shown whenever the underlying source actually provides it.
- Every result links directly to the original job posting, so you can always click through and verify the exact location yourself.
- Match scores from `evaluate_match` are LLM-generated and therefore non-deterministic — the same job/resume pair can score slightly differently across runs.
- Each session allows one resume upload and a capped number of messages, by design — this is a demo deployment, not a persistent multi-resume workspace.

## Roadmap

- Daily automated job search delivered via email
- LinkedIn integration
- Skill-gap analysis against target roles
- Integrate additional local/regional job platforms as free API access becomes available, to improve city-level location accuracy over time

## License

Not currently licensed — a `LICENSE` file will be added here once one is chosen.

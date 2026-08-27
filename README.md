# Resume Studio

React (Vite + TS + **Mantine**) frontend, FastAPI backend, OpenAI function-calling agent,
LaTeX resume as the source of truth compiled server-side, plus a job crawler + auto-apply
flow (Playwright).

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium   # for the job auto-apply flow
cp ../.env.example ../.env  # fill in OPENAI_API_KEY when ready
uvicorn app.main:app --reload
```

Run the backend tests with `pip install -r requirements-dev.txt && pytest`.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 — it should show the backend health status.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

## Job crawler + auto-apply

The **Jobs** tab discovers roles, ranks them against your resume, and fills
application forms for your review.

### Sources

- **Company** — pick from a curated list of well-known companies (searchable),
  mapped to their Greenhouse / Lever / Ashby board.
- **Board URL** — paste any board URL (`boards.greenhouse.io/<co>`) or `provider:slug`.
- **LinkedIn** — a keyword + location search via LinkedIn's public guest endpoints
  (unofficial, rate-limited).
- **Apply from a URL** — paste any single job URL; the fill-then-review flow runs on
  whatever form is on that page.

Board/company discovery uses the providers' official public JSON APIs — no listing
pages are scraped.

### Flow

1. Fill the **Profile** tab (name, email, links, work authorization) and attach a
   resume PDF — from the current resume session or an upload.
2. **Run crawl** — postings are fetched and scored 0–100 against your resume
   (`gpt-4o-mini`), streamed as progress into a ranked table.
3. Open a job → **Prepare application**. Playwright opens the form, fills every
   field it can (identity fields from your profile, free-text/screening answers
   generated from your resume + the JD), attaches your resume, screenshots it, and
   **stops**.
4. Review the screenshot + editable field table, adjust anything, then **Submit**
   (confirm-gated). Nothing is ever submitted without that click; CAPTCHA-guarded
   forms are flagged for manual submission.

### Connected accounts (LinkedIn / Wellfound)

These sites have no usable anonymous API and prohibit automated applying. Under
**Connections**, click **Connect** — a visible browser opens, you log in, then click
**I've logged in** to save the session locally. Applying to a LinkedIn/Wellfound job
then opens Easy Apply *in that visible browser* with page 1 pre-filled; you review and
submit there yourself. **This needs a local run** (headful Chromium — not available in
Docker).

Backend lives under `app/services/jobs/` (`ats/` clients incl. `linkedin.py` /
`wellfound.py` / `registry.py`, `matcher.py`, `crawl.py`, `apply/` incl.
`connected.py`); API under `/api/jobs` in `app/api/routes/jobs.py`. State is in-memory
(`crawl_store.py`) except the profile (`.data/jobs/profile.json`) and connected
sessions (`.data/jobs/sessions/`).

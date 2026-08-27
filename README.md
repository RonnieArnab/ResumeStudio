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
- **Apply from a URL** — paste any single job URL. A visible **Google Chrome** window
  opens and is driven through the flow: accept cookies → click *Apply* → pass an email /
  terms pre-step → fill each wizard step, screenshotting every step. It stops at the
  review/submit step (or at a CAPTCHA) and hands the window to you. Handles multi-step
  ATSs like Oracle Recruiting Cloud (`*.oraclecloud.com/hcmUI/CandidateExperience`).

Board/company discovery uses the providers' official public JSON APIs — no listing
pages are scraped.

### Flow

1. The **Profile** tab fills itself in from your uploaded resume (name, email, phone,
   location, years of experience — URLs are only kept if they literally appear in the
   resume). "Fill from résumé" re-runs it; you can still edit any field.
2. **Run crawl** — set **Posted** (past 24h / 3 days / week …) and **Target experience
   (years)** (prefilled from your resume). Postings are filtered by age, then scored
   0–100 against your resume (`gpt-4o-mini`, which also penalises roles far off your
   level); recent postings get a ranking boost. LinkedIn searches also pass the
   equivalent `f_TPR` / `f_E` filters.
3. Open a job → **Prepare application**. Playwright opens the form, fills every
   field it can (identity fields from your profile, free-text/screening answers
   generated from your resume + the JD), attaches your resume, screenshots it, and
   **stops**.
4. Review the step-by-step walkthrough + editable field table, adjust anything, then
   **Submit** (confirm-gated). Nothing is ever submitted without that click; CAPTCHA-guarded
   and multi-step forms are handed back to you in the open browser.
5. The **Applied** tab is an application tracker — preparing or submitting a job logs it
   automatically (status `interested → preparing → applied → interviewing → offer → …`,
   editable inline); add rows manually too. Persisted to `.data/jobs/applications.json`.

### Use your own Chrome (recommended)

Under **Connections → Use your own Chrome**, quit all Chrome windows and run the printed
command (copy button provided):

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-remote-profile" --no-first-run
```

The backend attaches to that Chrome over the DevTools Protocol
(`chromium.connect_over_cdp`). Every apply flow (paste-URL **and** LinkedIn/Wellfound) then
runs in a tab of your real browser — your logins are already there, you watch it happen and
take over at any point, and it never closes your browser. Port overridable via
`CHROME_CDP_PORT`.

### Connected accounts (fallback)

When CDP is connected, **Connections** shows **Google / LinkedIn / Wellfound** buttons that
open that site's sign-in as a new tab in your running Chrome — sign into Google once and
the "Continue with Google" flow on LinkedIn/Wellfound is one click.

If you'd rather not run Chrome yourself: under **Connections**, click **Connect** — a
visible Google Chrome window opens, you log in, then click **I've logged in** to save the
session locally.

## Editing the resume

Sections render as a clean formatted document (Formatted / PDF toggle). Click a section to
edit it with the agent; **Add section** at the bottom creates a new empty one (e.g.
Certifications) for the agent to fill, and each section has a remove button. Applying to a LinkedIn/Wellfound job
then opens Easy Apply *in that visible browser* with page 1 pre-filled; you review and
submit there yourself. **This needs a local run** (headful Chromium — not available in
Docker).

Backend lives under `app/services/jobs/` (`ats/` clients incl. `linkedin.py` /
`wellfound.py` / `registry.py`, `matcher.py`, `crawl.py`, `apply/` incl.
`connected.py`); API under `/api/jobs` in `app/api/routes/jobs.py`. State is in-memory
(`crawl_store.py`) except the profile (`.data/jobs/profile.json`) and connected
sessions (`.data/jobs/sessions/`).

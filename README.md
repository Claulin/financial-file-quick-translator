# Filing Translation Engine (MVP)

Local-first prototype:
- Python 3.11 + FastAPI
- SQLite
- Server-rendered HTML (Jinja2)
- Simple responsive CSS (iPhone-friendly)
- SEC EDGAR: fetch most recent S-1 or S-1/A in **HTML only**
- LLM: structured JSON extraction + summarization
- Caching: if a report exists for a filing, return it instantly (no LLM call)

---

## 1) Setup (Windows)

### Create virtual environment
```powershell
python -m venv .venv
```

### Activate
```powershell
.venv\Scripts\activate
```

### Install packages
```powershell
pip install -r requirements.txt
```

### Configure environment
Copy `.env.example` to `.env` and fill in values:

- `SEC_USER_AGENT` is REQUIRED (SEC requires contact info)
- `OPENAI_API_KEY` enables AI extraction (optional, but needed for the full flow)

Example:
```env
SEC_USER_AGENT=FilingTranslationEngine (your-email@example.com)
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-4o-mini
```

---

## 2) Run server (Windows)

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open on laptop:
- http://127.0.0.1:8000

---

## 3) Access from iPhone (same Wi-Fi)

### Find your Windows laptop IP
In PowerShell / Command Prompt:
```powershell
ipconfig
```

Look for your active adapter (Wi-Fi) and copy the `IPv4 Address`, e.g. `192.168.1.25`.

### Open on iPhone Safari
Type:
- `http://LAPTOP_IP:8000`

Example:
- http://192.168.1.25:8000

---

## 4) Allow port 8000 through Windows Firewall

### Option A (GUI)
1. Open **Windows Security**
2. Go to **Firewall & network protection**
3. Click **Advanced settings**
4. Click **Inbound Rules** → **New Rule...**
5. Rule Type: **Port**
6. TCP → Specific local ports: **8000**
7. Allow the connection
8. Apply to Domain/Private/Public as appropriate (usually Private)
9. Name: `FilingTranslationEngine 8000`

### Option B (PowerShell as Administrator)
```powershell
New-NetFirewallRule -DisplayName "FilingTranslationEngine 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## 5) Remote access option (ngrok)

If you want to access from outside your local network:

1. Install ngrok and authenticate it (per ngrok instructions)
2. Start your FastAPI server on port 8000
3. In another terminal:
```powershell
ngrok http 8000
```

ngrok will print a public URL you can open from your phone anywhere.

---

## 6) Product flow (what it does)

1. Homepage: enter ticker or CIK
2. App resolves ticker→CIK using SEC’s ticker map
3. Fetches most recent S-1 or S-1/A from SEC submissions
4. Builds the HTML filing URL (HTML only; consults `index.json` if needed)
5. Parses HTML → readable text
6. Calls LLM to generate structured JSON (temperature 0.1; JSON only; never guesses numbers)
7. Stores report in SQLite
8. Report page displays exactly the required sections

Caching rule:
- If `reports` already has a row for that filing, it returns instantly (no AI call)

---

## 7) Database schema

Tables created automatically at startup:

- `companies (id, name, ticker, cik)`
- `filings (id, company_id, accession_number, filing_date, html_url, parsed_text)`
- `reports (id, filing_id, status, report_json, created_at)`

---

## 8) Notes / troubleshooting

- If `OPENAI_API_KEY` is missing, the app still works end-to-end but produces a placeholder report with `MANUAL_REVIEW_REQUIRED`.
- SEC may block requests if your `SEC_USER_AGENT` is missing or not descriptive.
- If you get timeouts, re-try: EDGAR can be slow during peak.


---

## Deploy to the Internet (Render - always on)

This repo includes a `render.yaml` Blueprint so you can deploy with a stable public link.

### 1) Push to GitHub
1. Create a new GitHub repo
2. Commit & push this project (keep `render.yaml` at the repo root)

### 2) Create the Render service (Blueprint)
1. Render → **New** → **Blueprint**
2. Select your GitHub repo
3. Render will read `render.yaml` and create:
   - A web service (FastAPI)
   - A persistent disk mounted at `/var/data` for SQLite

### 3) Set secrets in Render
In the created service → **Environment**:
- `SEC_USER_AGENT` = `FilingTranslationEngine (your-email@example.com)`
- `OPENAI_API_KEY` = your key

After deploy, you’ll get a public URL like:
`https://filing-translation-engine.onrender.com`

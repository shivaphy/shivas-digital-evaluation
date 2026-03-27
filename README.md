# 🚀 SHIVA'S Digital Evaluation — GitHub Deployment Guide

## Project Structure

```
shivas-digital-evaluation/
├── frontend/
│   └── index.html          ← Main app (single-file, all roles + admin)
├── backend/
│   ├── main.py             ← FastAPI backend
│   ├── schema.sql          ← PostgreSQL schema
│   ├── requirements.txt    ← Python dependencies
│   └── .env.template       ← Environment variables template
├── .gitignore
└── README.md
```

---

## STEP 1 — Prepare Your Local Files

Arrange your files into the folder structure above.

Create a `.gitignore` file with:
```
# Python
__pycache__/
*.pyc
*.pyo
venv/
.env           ← NEVER commit your real .env

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

## STEP 2 — Create a GitHub Repository

1. Go to **https://github.com** and sign in (or create a free account).
2. Click the **"+"** icon (top-right) → **"New repository"**.
3. Fill in:
   - **Repository name:** `shivas-digital-evaluation`
   - **Description:** Tri-Phase Digital Evaluation Portal
   - **Visibility:** Private (recommended) or Public
   - **Do NOT** initialise with README (you'll push your own).
4. Click **"Create repository"**.

---

## STEP 3 — Push Your Code to GitHub

Open your terminal/command prompt inside the project folder:

```bash
# Initialise git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: SHIVA'S Digital Evaluation v2.0"

# Connect to your GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/shivas-digital-evaluation.git

# Push to GitHub
git branch -M main
git push -u origin main
```

✅ Your code is now on GitHub.

---

## STEP 4A — Deploy the Frontend (GitHub Pages — FREE)

GitHub Pages hosts static HTML files for free at:
`https://YOUR_USERNAME.github.io/shivas-digital-evaluation/`

**Enable GitHub Pages:**
1. On your repo page → **Settings** → **Pages** (left sidebar).
2. Under **"Source"** → select **"Deploy from a branch"**.
3. Branch: `main` | Folder: `/` (root) or `/frontend`.
4. Click **Save**.
5. Wait ~2 minutes. Your site will be live at the URL shown.

> ⚠️ **Important:** The frontend connects to `http://127.0.0.1:8000`.
> When deployed publicly, update `const API = 'http://127.0.0.1:8000'` 
> in `index.html` to your deployed backend URL (see Step 4B).

---

## STEP 4B — Deploy the Backend

### Option A: Render.com (FREE tier)

1. Go to **https://render.com** → Sign up with GitHub.
2. Click **"New +"** → **"Web Service"**.
3. Connect your GitHub repo.
4. Fill in:
   - **Name:** `shivas-eval-api`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **"Environment Variables"**, add:
   ```
   GEMINI_API_KEY   = your_actual_gemini_key
   DATABASE_URL     = your_postgres_url
   ```
6. Click **"Create Web Service"**.
7. Your API will be live at: `https://shivas-eval-api.onrender.com`

### Option B: Railway.app (Easiest, FREE tier)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Inside your backend/ folder:
cd backend
railway init
railway up
```

Add environment variables on the Railway dashboard.

### Option C: Run Locally (Development)

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in your keys
cp .env.template .env
# Edit .env with your GEMINI_API_KEY and DATABASE_URL

# Start the API
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open `frontend/index.html` directly in your browser.

---

## STEP 5 — Set Up the Database (PostgreSQL)

### Free PostgreSQL options:
- **Supabase** (https://supabase.com) — Free, generous limits
- **Neon** (https://neon.tech) — Free serverless Postgres
- **ElephantSQL** (https://elephantsql.com) — 20MB free

**After creating your database:**
1. Copy the connection string (looks like `postgresql://user:pass@host/dbname`).
2. Add it as `DATABASE_URL` in your backend's environment variables.
3. Run the schema:
```bash
psql $DATABASE_URL -f schema.sql
```

---

## STEP 6 — Update Frontend API URL

Once your backend is deployed, update the API constant in `index.html`:

```javascript
// Change this line (around line 5 of the <script> section):
const API = 'http://127.0.0.1:8000';

// To your deployed backend URL:
const API = 'https://shivas-eval-api.onrender.com';
```

Then commit and push:
```bash
git add frontend/index.html
git commit -m "chore: update API URL to production backend"
git push
```

GitHub Pages will automatically redeploy within ~1 minute.

---

## STEP 7 — Get Your Gemini API Key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with a Google account.
3. Click **"Create API Key"**.
4. Copy the key and add it to your backend environment variables as `GEMINI_API_KEY`.

The app works in **demo/mock mode** even without a key — it returns realistic simulated AI scores.

---

## Security Checklist Before Going Live

- [ ] Change `ADMIN_PW = 'admin@123'` in `index.html` to a strong password
- [ ] Change the demo passwords in `USER_DB` inside `main.py`
- [ ] Never commit your `.env` file (it's in `.gitignore`)
- [ ] Set `allow_origins` in FastAPI CORS to your specific frontend domain (not `"*"`)
- [ ] Enable HTTPS on your backend (Render and Railway do this automatically)
- [ ] Add rate limiting to the `/token` endpoint

---

## Quick Command Reference

```bash
# Push updates to GitHub
git add .
git commit -m "update: describe your change here"
git push

# View GitHub Pages site
open https://YOUR_USERNAME.github.io/shivas-digital-evaluation/

# Check backend logs (Render)
# Go to Render dashboard → your service → Logs tab
```

---

## Architecture Summary

```
Browser (GitHub Pages)
       │  HTTPS
       ▼
  index.html  ──────────────────────────────────────────────┐
  (All roles: Faculty, HoD, Student, Admin)                  │
                                                             │ fetch()
                                                             ▼
                                                    FastAPI Backend
                                                    (Render / Railway)
                                                             │
                                              ┌──────────────┴─────────────┐
                                              ▼                            ▼
                                       PostgreSQL DB              Gemini Vision API
                                      (Supabase/Neon)          (AI Answer Analysis)
```

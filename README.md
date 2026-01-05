# AI Usage Tracker

WorkBoard's Internal AI Usage and Impact Catalog

## Quick Start with Claude Code

### 1. Install Claude Code

```bash
# Install via npm (requires Node.js)
npm install -g @anthropic-ai/claude-code

# Or via Homebrew (macOS)
brew install claude-code
```

### 2. Download This Project

Download the `ai-usage-tracker` folder to your local machine.

### 3. Open in Claude Code

```bash
# Navigate to project folder
cd ai-usage-tracker

# Start Claude Code
claude

# Claude Code will automatically read CLAUDE.md for context
```

### 4. First Commands to Run

Once in Claude Code, say:

```
Read CLAUDE.md and build the complete FastAPI backend with all endpoints, 
database setup, and modify the HTML files to connect to the API.
```

Or step by step:

```
1. "Create the FastAPI application with database setup"
2. "Create all the API endpoints for config and responses"
3. "Modify the form.html to fetch config and submit to API"
4. "Modify dashboard.html to fetch real data from API"
5. "Create requirements.txt and deployment configs"
```

## Project Structure

```
ai-usage-tracker/
├── CLAUDE.md            # Full project context (Claude Code reads this)
├── README.md            # This file
├── app/
│   └── static/
│       ├── index.html   # Overview/preview dashboard
│       ├── form.html    # Intake form
│       └── dashboard.html # Live dashboard
└── (Claude Code will create the rest)
```

## What Claude Code Will Build

- `app/main.py` - FastAPI application
- `app/database.py` - SQLite setup
- `app/models.py` - Pydantic models
- `app/crud.py` - Database operations
- `app/routes/config.py` - Config API endpoints
- `app/routes/responses.py` - CRUD endpoints
- `requirements.txt` - Python dependencies
- `railway.json` - Deployment config

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000

# Open in browser
# Dashboard: http://localhost:8000
# Form: http://localhost:8000/form
# API Docs: http://localhost:8000/docs
```

## Deployment

### Railway (Recommended)

1. Push to GitHub
2. Connect Railway to your repo
3. Railway auto-deploys

### Render (Alternative)

1. Push to GitHub
2. Create new Web Service on Render
3. Connect to repo

## Tech Stack

- **Backend:** Python FastAPI
- **Database:** SQLite
- **Frontend:** React (via CDN), Tailwind CSS
- **Hosting:** Railway/Render (free tier)

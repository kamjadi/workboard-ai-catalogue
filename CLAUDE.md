# AI Usage Tracker - Project Context for Claude Code

## Project Overview

**Project Name:** WorkBoard Internal AI Usage and Impact Catalogue  
**Goal:** Track AI adoption across teams and measure business impact  
**Status:** UI prototypes complete, need to build full-stack application

## What We're Building

A web application to:
1. Collect data about how employees use AI tools (intake form)
2. Display aggregated insights (dashboard)
3. Allow configuration via Excel upload (functions, teams, tools)
4. Provide full CRUD capabilities for submissions

## Architecture Decision

**Stack:**
- **Backend:** Python FastAPI
- **Database:** SQLite (portable, easy migration later)
- **Frontend:** Static HTML/React (already built)
- **Hosting:** Railway or Render (free tier)
- **Config:** Excel file upload to populate lookup tables

```
ai-usage-tracker/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # SQLite connection and setup
│   ├── models.py            # Pydantic models for validation
│   ├── crud.py              # Database operations
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── config.py        # GET config data, POST Excel upload
│   │   └── responses.py     # Full CRUD for AI usage submissions
│   └── static/
│       ├── index.html       # Overview/preview dashboard
│       ├── form.html        # Intake form
│       ├── dashboard.html   # Live dashboard
│       └── assets/          # Any additional CSS/JS
├── data/
│   └── database.db          # SQLite database (created at runtime)
├── uploads/
│   └── config.xlsx          # Uploaded config file
├── requirements.txt
├── railway.json             # Railway deployment config
├── render.yaml              # Render deployment config (alternative)
├── README.md
└── CLAUDE.md                # This file
```

## Design Specifications

### Brand Colors (WorkBoard)
```javascript
const COLORS = {
  primary: '#52bad5',      // WorkBoard main teal
  primaryDark: '#3a9cb8',  // Darker teal
  primaryLight: '#7fcce3', // Lighter teal
  secondary: '#2d7a8c',    // Deep teal
  accent1: '#45a5c0',      // Mid teal
  accent2: '#8fd4e8',      // Soft teal
  accent3: '#1e5c6b',      // Dark teal
  success: '#3dad7a',      // Green (cost savings)
  warning: '#e8a838',      // Amber (new capability)
  purple: '#7b68a6',       // Purple (quality)
  slate: '#64748b'         // Neutral gray
};
```

### Typography
- Font Family: 'DM Sans', system-ui, sans-serif
- Import: `https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap`

### UI Theme
- Light theme (gray-50 background)
- White cards with gray-200 borders
- Rounded corners (rounded-xl, rounded-2xl)
- Subtle shadows (shadow-sm)

## Database Schema

### Config Tables (populated from Excel)

```sql
-- Functions (e.g., Sales, Marketing, Engineering)
CREATE TABLE functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams (linked to functions)
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (function_id) REFERENCES functions(id),
    UNIQUE(function_id, name)
);

-- AI Tools (e.g., ChatGPT, Claude, Gemini)
CREATE TABLE tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Capabilities (e.g., Drafting, Summarizing, Coding)
CREATE TABLE capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Responses Table (user submissions)

```sql
CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Organization
    function_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    
    -- AI Method
    method_type TEXT NOT NULL CHECK(method_type IN ('workflow', 'task', 'experiment')),
    capability_id INTEGER NOT NULL,
    capability_other TEXT,  -- If "other" selected
    description TEXT NOT NULL,
    
    -- Tools (stored as JSON array of tool IDs)
    tools_used TEXT NOT NULL,  -- JSON: [1, 2, 5] or ["ChatGPT", "Claude"]
    other_tools TEXT,  -- JSON for custom tool names
    
    -- Impact 1 (Primary - required for workflow/task)
    impact1_type TEXT CHECK(impact1_type IN ('cost_savings', 'time_savings', 'quality', 'new_capability')),
    impact1_value REAL,  -- Dollar amount or hours
    impact1_frequency TEXT CHECK(impact1_frequency IN ('one_time', 'daily', 'weekly', 'monthly')),
    impact1_time_unit TEXT,  -- For time savings: 'hrs_day', 'hrs_week', etc.
    impact1_annual_value REAL,  -- Calculated annual value
    impact1_description TEXT,  -- For quality/new_capability
    
    -- Impact 2 (Optional)
    impact2_type TEXT,
    impact2_value REAL,
    impact2_frequency TEXT,
    impact2_time_unit TEXT,
    impact2_annual_value REAL,
    impact2_description TEXT,
    
    -- Impact 3 (Optional)
    impact3_type TEXT,
    impact3_value REAL,
    impact3_frequency TEXT,
    impact3_time_unit TEXT,
    impact3_annual_value REAL,
    impact3_description TEXT,
    
    -- Impact 4 (Optional)
    impact4_type TEXT,
    impact4_value REAL,
    impact4_frequency TEXT,
    impact4_time_unit TEXT,
    impact4_annual_value REAL,
    impact4_description TEXT,
    
    -- Metadata
    submitted_by TEXT,  -- Email or name (optional for now)
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (function_id) REFERENCES functions(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (capability_id) REFERENCES capabilities(id)
);
```

## API Endpoints

### Config Endpoints
```
GET  /api/config                    # Get all config (functions, teams, tools, capabilities)
GET  /api/config/functions          # List all functions
GET  /api/config/teams              # List all teams (optional ?function_id=X filter)
GET  /api/config/tools              # List all tools
GET  /api/config/capabilities       # List all capabilities
POST /api/config/upload             # Upload Excel to update config
```

### Response Endpoints (CRUD)
```
GET    /api/responses               # List all responses (with filters)
GET    /api/responses/{id}          # Get single response
POST   /api/responses               # Create new response
PUT    /api/responses/{id}          # Update response
DELETE /api/responses/{id}          # Delete response
```

### Dashboard Endpoints
```
GET /api/dashboard/summary          # Aggregated stats for dashboard
GET /api/dashboard/by-function      # Breakdown by function
GET /api/dashboard/by-team          # Breakdown by team
```

### Static Pages
```
GET /                               # Overview page (preview dashboard)
GET /form                           # Intake form
GET /dashboard                      # Live dashboard
GET /admin                          # Admin page (optional: manage responses)
```

## Excel Config Format

The config Excel file should have these sheets:

### Sheet: "Functions"
| Name |
|------|
| Sales |
| Marketing |
| Engineering |
| Customer Success |
| Support |
| Product |
| Finance |
| HR |
| Partners |

### Sheet: "Teams"
| Function | Team |
|----------|------|
| Sales | NA |
| Sales | EMEA |
| Sales | APAC |
| Marketing | Brand |
| Marketing | Demand Gen |
| Engineering | Backend |
| Engineering | Frontend |
| ... | ... |

### Sheet: "Tools"
| Name |
|------|
| ChatGPT |
| Claude |
| Gemini |
| Gong |
| Copilot |

### Sheet: "Capabilities"
| Name | Icon |
|------|------|
| Drafting | ✍️ |
| Summarizing | 📝 |
| Analyzing | 📊 |
| Q&A | 🔍 |
| Coding | 💻 |
| Automation | ⚙️ |
| Classifying | 🏷️ |
| Vibe Coding | 🎯 |

## Existing UI Files

The following HTML files have been created and should be used as the frontend:

### 1. Overview/Preview Dashboard
- **File:** `static/index.html` (copy from ai-dashboard-preview.html)
- **Features:**
  - Collapsible instruction sections (default closed)
  - Navigation buttons: Overview, Instructions, Live Dashboard, Enter Your AI Use Cases
  - Sample data visualization
  - Footer: "The data in this dashboard is not real."

### 2. Live Dashboard  
- **File:** `static/dashboard.html` (copy from ai-dashboard-live.html)
- **Features:**
  - Same layout as preview but connects to real API
  - Fetches data from `/api/dashboard/summary` and `/api/responses`
  - No instruction sections

### 3. Intake Form
- **File:** `static/form.html` (copy from ai-intake-form-preview.html)
- **Features:**
  - 4 sections: Organization, AI Method, Tools, Impact
  - AI Method Type as clickable cards (Workflow, Task, Experiment)
  - Impact section hidden when Experiment selected
  - 4 impact entry fields (Primary + 3 optional)
  - Auto-calculates annual cost/time savings
  - Submits to `/api/responses`

## Key UI Behaviors to Preserve

### Intake Form Logic
1. **Function → Team cascade:** Team dropdown populated based on Function selection
2. **AI Method Type cards:** Visual selection (Workflow, Task, Experiment)
3. **Experiment hides Impact:** When "Experiment" selected, hide entire Impact section
4. **Impact calculations:**
   - Cost Savings: `amount × frequency_multiplier = annual_value`
   - Time Savings: `hours × time_unit_multiplier × frequency_multiplier = annual_hours`
   - Frequency multipliers: one_time=1, daily=260, weekly=52, monthly=12
5. **Tools:** Multi-select checkboxes with "Other" text input fields

### Dashboard Logic
1. **Summary cards:** Total methods, Cost savings, Time savings, Quality count, New capability count
2. **Charts by Function:** Cost savings, Time savings, Quality impact, New capability, Total methods (stacked)
3. **Category cards:** Workflows, Tasks, Experiments with impact breakdowns
4. **Expandable function rows:** Click to see team breakdown

## Development Tasks

### Phase 1: Backend Setup
- [ ] Create FastAPI application structure
- [ ] Set up SQLite database with schema
- [ ] Implement config endpoints
- [ ] Implement CRUD for responses
- [ ] Implement Excel upload parsing
- [ ] Implement dashboard aggregation endpoints

### Phase 2: Frontend Integration
- [ ] Copy existing HTML files to static folder
- [ ] Modify form to fetch config from API
- [ ] Modify form to POST to API
- [ ] Modify live dashboard to fetch from API
- [ ] Add loading states and error handling

### Phase 3: Deployment
- [ ] Create requirements.txt
- [ ] Create Railway/Render config
- [ ] Deploy to free tier
- [ ] Test end-to-end

### Phase 4: Enhancements (Later)
- [ ] Add authentication
- [ ] Add admin page for managing responses
- [ ] Add data export (CSV/Excel)
- [ ] Add email notifications

## Sample Data for Testing

Use this sample data to seed the database for testing:

```python
SAMPLE_FUNCTIONS = ["Sales", "Marketing", "Engineering", "Customer Success", "Support", "Product", "Finance", "HR"]

SAMPLE_TEAMS = {
    "Sales": ["NA", "EMEA", "APAC", "Enterprise", "SMB"],
    "Marketing": ["Brand", "Demand Gen", "Content", "Product Marketing"],
    "Engineering": ["Backend", "Frontend", "DevOps", "QA"],
    "Customer Success": ["Enterprise CS", "SMB CS", "Onboarding"],
    "Support": ["Tier 1", "Tier 2", "Technical Support"],
    "Product": ["Core Product", "Analytics", "Growth"],
    "Finance": ["FP&A", "Accounting"],
    "HR": ["Recruiting", "People Ops"]
}

SAMPLE_TOOLS = ["ChatGPT", "Claude", "Gemini", "Gong", "Copilot"]

SAMPLE_CAPABILITIES = [
    ("Drafting", "✍️"),
    ("Summarizing", "📝"),
    ("Analyzing", "📊"),
    ("Q&A", "🔍"),
    ("Coding", "💻"),
    ("Automation", "⚙️"),
    ("Classifying", "🏷️"),
    ("Vibe Coding", "🎯")
]
```

## Commands Reference

```bash
# Local development
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Database reset
rm data/database.db
python -c "from app.database import init_db; init_db()"

# Run with sample data
python scripts/seed_data.py
```

## Environment Variables (for production)

```
DATABASE_URL=sqlite:///./data/database.db  # Or PostgreSQL URL later
SECRET_KEY=your-secret-key-here            # For sessions if needed
CORS_ORIGINS=https://your-domain.com       # Allowed origins
```

## Notes for IT Deployment

When ready for internal deployment:
1. **Database:** Can migrate from SQLite to PostgreSQL/SQL Server
2. **Auth:** Add Azure AD / SAML integration
3. **Hosting:** Docker container, can run on any server
4. **Data:** All data in single SQLite file, easy to backup/migrate

## Reference Files

The original UI files created in Claude.ai are:
- `ai-dashboard-preview.html` - Overview dashboard with instructions
- `ai-dashboard-live.html` - Clean dashboard for live data
- `ai-intake-form-preview.html` - Intake form

These should be copied to the `app/static/` folder and modified to connect to the API.

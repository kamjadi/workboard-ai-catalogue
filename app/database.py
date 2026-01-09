import sqlite3
import os
import secrets
from pathlib import Path

# Database path - use DATABASE_DIR env var for Railway volume, fallback to local ./data
DATABASE_DIR = os.environ.get("DATABASE_DIR", str(Path(__file__).parent.parent / "data"))
DATABASE_PATH = Path(DATABASE_DIR) / "database.db"


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize the database with schema."""
    os.makedirs(DATABASE_PATH.parent, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Functions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS functions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            function_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (function_id) REFERENCES functions(id),
            UNIQUE(function_id, name)
        )
    """)

    # Tools table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Capabilities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS capabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Responses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Organization
            function_id INTEGER NOT NULL,
            team_id INTEGER,

            -- AI Method
            method_type TEXT NOT NULL CHECK(method_type IN ('workflow', 'task', 'experiment')),
            capability_id INTEGER NOT NULL,
            capability_other TEXT,
            description TEXT NOT NULL,

            -- Tools (stored as JSON array of tool IDs)
            tools_used TEXT NOT NULL,
            other_tools TEXT,

            -- Impact 1 (Primary)
            impact1_type TEXT CHECK(impact1_type IN ('cost_savings', 'time_savings', 'quality', 'new_capability', NULL)),
            impact1_value REAL,
            impact1_frequency TEXT CHECK(impact1_frequency IN ('one_time', 'daily', 'weekly', 'monthly', NULL)),
            impact1_time_unit TEXT,
            impact1_annual_value REAL,
            impact1_description TEXT,

            -- Impact 2 (Optional)
            impact2_type TEXT CHECK(impact2_type IN ('cost_savings', 'time_savings', 'quality', 'new_capability', NULL)),
            impact2_value REAL,
            impact2_frequency TEXT CHECK(impact2_frequency IN ('one_time', 'daily', 'weekly', 'monthly', NULL)),
            impact2_time_unit TEXT,
            impact2_annual_value REAL,
            impact2_description TEXT,

            -- Impact 3 (Optional)
            impact3_type TEXT CHECK(impact3_type IN ('cost_savings', 'time_savings', 'quality', 'new_capability', NULL)),
            impact3_value REAL,
            impact3_frequency TEXT CHECK(impact3_frequency IN ('one_time', 'daily', 'weekly', 'monthly', NULL)),
            impact3_time_unit TEXT,
            impact3_annual_value REAL,
            impact3_description TEXT,

            -- Impact 4 (Optional)
            impact4_type TEXT CHECK(impact4_type IN ('cost_savings', 'time_savings', 'quality', 'new_capability', NULL)),
            impact4_value REAL,
            impact4_frequency TEXT CHECK(impact4_frequency IN ('one_time', 'daily', 'weekly', 'monthly', NULL)),
            impact4_time_unit TEXT,
            impact4_annual_value REAL,
            impact4_description TEXT,

            -- Metadata
            submitted_by TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (function_id) REFERENCES functions(id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (capability_id) REFERENCES capabilities(id)
        )
    """)

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
            active BOOLEAN DEFAULT 1,
            must_change_password BOOLEAN DEFAULT 0,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def seed_sample_data():
    """Seed the database with sample data for testing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Sample functions
    functions = ["Sales", "Marketing", "Engineering", "Customer Success", "Support", "Product", "Finance", "HR"]
    for func in functions:
        cursor.execute("INSERT OR IGNORE INTO functions (name) VALUES (?)", (func,))

    # Sample teams
    teams = {
        "Sales": ["NA", "EMEA", "APAC", "Enterprise", "SMB"],
        "Marketing": ["Brand", "Demand Gen", "Content", "Product Marketing"],
        "Engineering": ["Backend", "Frontend", "DevOps", "QA"],
        "Customer Success": ["Enterprise CS", "SMB CS", "Onboarding"],
        "Support": ["Tier 1", "Tier 2", "Technical Support"],
        "Product": ["Core Product", "Analytics", "Growth"],
        "Finance": ["FP&A", "Accounting"],
        "HR": ["Recruiting", "People Ops"]
    }

    for func_name, team_list in teams.items():
        cursor.execute("SELECT id FROM functions WHERE name = ?", (func_name,))
        func_row = cursor.fetchone()
        if func_row:
            func_id = func_row["id"]
            for team_name in team_list:
                cursor.execute(
                    "INSERT OR IGNORE INTO teams (function_id, name) VALUES (?, ?)",
                    (func_id, team_name)
                )

    # Sample tools (Other should always be last and is a special entry for custom tools)
    tools = ["ChatGPT", "Claude", "Gemini", "Gong", "Copilot", "Other"]
    for tool in tools:
        cursor.execute("INSERT OR IGNORE INTO tools (name) VALUES (?)", (tool,))

    # Sample capabilities
    capabilities = ["Drafting", "Summarizing", "Analyzing", "Q&A", "Coding", "Automation", "Classifying", "Vibe Coding", "Other"]
    for name in capabilities:
        cursor.execute("INSERT OR IGNORE INTO capabilities (name) VALUES (?)", (name,))

    conn.commit()
    conn.close()


def create_initial_admin():
    """Create initial admin user if no users exist."""
    try:
        import bcrypt
    except ImportError:
        print("Warning: bcrypt not installed, skipping admin creation")
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if any users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    if count == 0:
        # Get initial password from env var or use default
        initial_password = os.environ.get("INITIAL_ADMIN_PASSWORD", "changeme")
        password_hash = bcrypt.hashpw(initial_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (username, password_hash, role, must_change_password)
            VALUES (?, ?, 'admin', 1)
        """, ("admin", password_hash))

        conn.commit()
        conn.close()
        print(f"Initial admin user created (username: admin, password: {initial_password})")
        return True

    conn.close()
    return False


if __name__ == "__main__":
    init_db()
    seed_sample_data()
    create_initial_admin()
    print("Database initialized and seeded successfully!")

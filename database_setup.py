"""SQLite connections, additive schema migrations, and first-run initialization."""

import os
import sqlite3
import tempfile

from seed_data import seed_demo_events

DB_FILE = "planqira.db"


def get_db_path() -> str:
    """Returns the database file path, allowing dynamic test isolation and Vercel serverless /tmp write access."""
    if os.getenv("PLANQIRA_DB_PATH"):
        return os.getenv("PLANQIRA_DB_PATH")
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return os.path.join(tempfile.gettempdir(), "planqira.db")
    return DB_FILE


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back the transaction, then release the file handle."""

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, factory=ClosingConnection, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 268435456;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initializes tables idempotently, applies non-destructive migrations, and seeds demo events if empty."""
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            event_type TEXT NOT NULL,
            city TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT NOT NULL DEFAULT '15:00',
            duration_hours REAL NOT NULL DEFAULT 5.0,
            timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
            setting TEXT NOT NULL DEFAULT 'outdoor',
            guest_count INTEGER NOT NULL,
            target_budget_paise INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            contingency_bps INTEGER NOT NULL DEFAULT 1000,
            active_scenario_version INTEGER NOT NULL DEFAULT 1,
            preferences_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            guest_count INTEGER NOT NULL,
            target_budget_paise INTEGER NOT NULL,
            setting TEXT NOT NULL DEFAULT 'outdoor',
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS budget_items (
            id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            pricing_model TEXT NOT NULL,
            unit_cost_paise INTEGER NOT NULL,
            step_capacity INTEGER NOT NULL DEFAULT 1,
            tax_rate_bps INTEGER NOT NULL DEFAULT 0,
            approval_state TEXT NOT NULL DEFAULT 'ESTIMATED',
            deposit_required_paise INTEGER NOT NULL DEFAULT 0,
            paid_amount_paise INTEGER NOT NULL DEFAULT 0,
            deposit_due_date TEXT,
            superseded_by_id TEXT,
            notes TEXT,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS vendor_commitments (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            category TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            approval_state TEXT NOT NULL DEFAULT 'QUOTED',
            total_quote_paise INTEGER NOT NULL,
            deposit_required_paise INTEGER NOT NULL DEFAULT 0,
            paid_amount_paise INTEGER NOT NULL DEFAULT 0,
            deposit_due_date TEXT,
            hidden_fee_question TEXT,
            negotiation_script TEXT,
            raw_quote_text TEXT,
            is_reviewed INTEGER NOT NULL DEFAULT 0,
            needs_reconfirmation INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            title TEXT NOT NULL,
            owner TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            depends_on_guests INTEGER NOT NULL DEFAULT 0,
            due_date TEXT NOT NULL,
            reverification_reason TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS task_dependencies (
            parent_task_id TEXT NOT NULL,
            child_task_id TEXT NOT NULL,
            PRIMARY KEY (parent_task_id, child_task_id)
        );

        CREATE TABLE IF NOT EXISTS runbook_cues (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            front_of_house TEXT NOT NULL,
            back_of_house TEXT NOT NULL,
            lead_role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS themes (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            name TEXT NOT NULL,
            tagline TEXT NOT NULL,
            palette_hex TEXT NOT NULL,
            sensory_hook TEXT NOT NULL,
            signature_moment TEXT NOT NULL,
            diy_swap TEXT NOT NULL,
            is_selected INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            commitment_id TEXT,
            budget_item_id TEXT,
            amount_paise INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            reference_note TEXT NOT NULL,
            paid_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            resolution TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            previous_value TEXT,
            new_value TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        );
        """)

        # Non-destructive migrations for existing databases
        _apply_migrations(conn)

        # Check if events already exist
        cursor = conn.execute("SELECT COUNT(*) as count FROM events;")
        count = cursor.fetchone()["count"]
        if count == 0:
            seed_demo_events(conn)


_TABLE_INFO_QUERIES = {
    "events": "PRAGMA table_info(events);",
    "scenarios": "PRAGMA table_info(scenarios);",
    "budget_items": "PRAGMA table_info(budget_items);",
    "vendor_commitments": "PRAGMA table_info(vendor_commitments);",
    "tasks": "PRAGMA table_info(tasks);",
    "payments": "PRAGMA table_info(payments);",
}

_STATIC_MIGRATIONS = [
    ("events", "start_time", "ALTER TABLE events ADD COLUMN start_time TEXT NOT NULL DEFAULT '15:00';"),
    ("events", "duration_hours", "ALTER TABLE events ADD COLUMN duration_hours REAL NOT NULL DEFAULT 5.0;"),
    ("events", "timezone", "ALTER TABLE events ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata';"),
    ("events", "setting", "ALTER TABLE events ADD COLUMN setting TEXT NOT NULL DEFAULT 'outdoor';"),
    ("events", "preferences_json", "ALTER TABLE events ADD COLUMN preferences_json TEXT DEFAULT '{}';"),
    ("scenarios", "setting", "ALTER TABLE scenarios ADD COLUMN setting TEXT NOT NULL DEFAULT 'outdoor';"),
    ("scenarios", "event_date", "ALTER TABLE scenarios ADD COLUMN event_date TEXT;"),
    ("budget_items", "deposit_required_paise", "ALTER TABLE budget_items ADD COLUMN deposit_required_paise INTEGER NOT NULL DEFAULT 0;"),
    ("budget_items", "superseded_by_id", "ALTER TABLE budget_items ADD COLUMN superseded_by_id TEXT;"),
    ("budget_items", "is_tax_inclusive", "ALTER TABLE budget_items ADD COLUMN is_tax_inclusive INTEGER NOT NULL DEFAULT 0;"),
    ("budget_items", "obligation_id", "ALTER TABLE budget_items ADD COLUMN obligation_id TEXT;"),
    ("vendor_commitments", "deposit_required_paise", "ALTER TABLE vendor_commitments ADD COLUMN deposit_required_paise INTEGER NOT NULL DEFAULT 0;"),
    ("vendor_commitments", "needs_reconfirmation", "ALTER TABLE vendor_commitments ADD COLUMN needs_reconfirmation INTEGER NOT NULL DEFAULT 0;"),
    ("vendor_commitments", "idempotency_key", "ALTER TABLE vendor_commitments ADD COLUMN idempotency_key TEXT;"),
    ("vendor_commitments", "request_fingerprint", "ALTER TABLE vendor_commitments ADD COLUMN request_fingerprint TEXT;"),
    ("tasks", "reverification_reason", "ALTER TABLE tasks ADD COLUMN reverification_reason TEXT;"),
    ("payments", "idempotency_key", "ALTER TABLE payments ADD COLUMN idempotency_key TEXT;"),
]

_STATIC_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_event_idempotency_unique ON payments(event_id, idempotency_key);",
    "CREATE INDEX IF NOT EXISTS idx_scenarios_event_status ON scenarios (event_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_items_scenario ON budget_items (scenario_id);",
    "CREATE INDEX IF NOT EXISTS idx_vendors_event ON vendor_commitments (event_id);",
    "CREATE INDEX IF NOT EXISTS idx_tasks_event_due ON tasks (event_id, due_date);",
    "CREATE INDEX IF NOT EXISTS idx_runbook_event ON runbook_cues (event_id);",
    "CREATE INDEX IF NOT EXISTS idx_themes_event ON themes (event_id);",
    "CREATE INDEX IF NOT EXISTS idx_payments_event_date ON payments (event_id, paid_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_incidents_event_date ON incidents (event_id, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_logs_event_id ON audit_logs (event_id, id DESC);",
]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Adds missing columns gracefully if migrating an earlier schema version without dynamic SQL formatting."""
    columns_by_table: dict[str, set[str]] = {}
    for table, query in _TABLE_INFO_QUERIES.items():
        columns_by_table[table] = {row["name"] for row in conn.execute(query)}

    for table, col, ddl in _STATIC_MIGRATIONS:
        if col not in columns_by_table.get(table, set()):
            conn.execute(ddl)
            columns_by_table[table].add(col)

    for index_ddl in _STATIC_INDEXES:
        conn.execute(index_ddl)

    # Backfill scenarios.event_date from events.event_date where null
    conn.execute("""
        UPDATE scenarios 
        SET event_date = (SELECT event_date FROM events WHERE events.id = scenarios.event_id)
        WHERE event_date IS NULL;
    """)

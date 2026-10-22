"""SQLite connections, additive schema migrations, and first-run initialization."""

import os
import sqlite3

from seed_data import seed_demo_events

DB_FILE = "planqira.db"


def get_db_path() -> str:
    """Returns the database file path, allowing dynamic test isolation and Vercel serverless /tmp write access."""
    if os.getenv("PLANQIRA_DB_PATH"):
        return os.getenv("PLANQIRA_DB_PATH")
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/planqira.db"
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


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Adds missing columns gracefully if migrating an earlier schema version."""
    migrations = [
        ("events", "start_time", "TEXT NOT NULL DEFAULT '15:00'"),
        ("events", "duration_hours", "REAL NOT NULL DEFAULT 5.0"),
        ("events", "timezone", "TEXT NOT NULL DEFAULT 'Asia/Kolkata'"),
        ("events", "setting", "TEXT NOT NULL DEFAULT 'outdoor'"),
        ("events", "preferences_json", "TEXT DEFAULT '{}'"),
        ("scenarios", "setting", "TEXT NOT NULL DEFAULT 'outdoor'"),
        ("budget_items", "deposit_required_paise", "INTEGER NOT NULL DEFAULT 0"),
        ("budget_items", "superseded_by_id", "TEXT"),
        ("vendor_commitments", "deposit_required_paise", "INTEGER NOT NULL DEFAULT 0"),
        ("vendor_commitments", "needs_reconfirmation", "INTEGER NOT NULL DEFAULT 0"),
        ("vendor_commitments", "idempotency_key", "TEXT"),
        ("vendor_commitments", "request_fingerprint", "TEXT"),
        ("tasks", "reverification_reason", "TEXT"),
        ("scenarios", "event_date", "TEXT"),
        ("payments", "idempotency_key", "TEXT"),
        ("budget_items", "is_tax_inclusive", "INTEGER NOT NULL DEFAULT 0"),
        ("budget_items", "obligation_id", "TEXT"),
    ]
    columns_by_table = {
        table: {row["name"] for row in conn.execute(f"PRAGMA table_info({table});")}
        for table in {table for table, _, _ in migrations}
    }
    for table, col, col_def in migrations:
        if col not in columns_by_table[table]:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def};")
            columns_by_table[table].add(col)

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_event_idempotency_unique ON payments(event_id, idempotency_key);"
    )

    # Index the event-scoped reads used for every dashboard refresh and export.
    indexes = {
        "scenarios_event_status": ("scenarios", "event_id, status"),
        "items_scenario": ("budget_items", "scenario_id"),
        "vendors_event": ("vendor_commitments", "event_id"),
        "tasks_event_due": ("tasks", "event_id, due_date"),
        "runbook_event": ("runbook_cues", "event_id"),
        "themes_event": ("themes", "event_id"),
        "payments_event_date": ("payments", "event_id, paid_at DESC"),
        "incidents_event_date": ("incidents", "event_id, created_at DESC"),
        "logs_event_id": ("audit_logs", "event_id, id DESC"),
    }
    for name, (table, columns) in indexes.items():
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name} ON {table} ({columns});")

    # Backfill scenarios.event_date from events.event_date where null
    conn.execute("""
            UPDATE scenarios 
            SET event_date = (SELECT event_date FROM events WHERE events.id = scenarios.event_id)
            WHERE event_date IS NULL;
        """)

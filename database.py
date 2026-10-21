"""
Planqira SQLite Persistence Engine (planqira.db)
ACID-compliant relational storage with schema migrations,
foreign keys, payment ledgers, incident logging, and audit trail.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional
import uuid

from engine import compute_line_item_paise

DB_FILE = "planqira.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def is_postgres_configured() -> bool:
    return bool(DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")))


def get_db_path() -> str:
    """Returns the database file path, allowing dynamic test isolation and Vercel serverless /tmp write access."""
    if os.getenv("PLANQIRA_DB_PATH"):
        return os.getenv("PLANQIRA_DB_PATH")
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp/planqira.db"
    return DB_FILE


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
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
        ("tasks", "reverification_reason", "TEXT"),
    ]
    for table, col, col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def};")
        except sqlite3.OperationalError:
            pass  # Column already exists


def seed_demo_events(conn: sqlite3.Connection) -> None:
    """Seeds 3 realistic events idempotently on clean database initialization."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Royal Rajputana Heritage Wedding
    w_id = "evt-royal-heritage-wedding"
    conn.execute("""
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (w_id, "Royal Rajputana Heritage Wedding", "wedding", "Jaipur", "2026-11-25", "16:00", 6.0, "Asia/Kolkata", "outdoor", 250, 120000000, "INR", 1000, 1, json.dumps({"dietary": "Strict Vegetarian + Jain", "style": "Regal Rajputana"}), now_str))

    sc_w_id = "sc-wedding-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (sc_w_id, w_id, 1, "Baseline Master Plan", 250, 120000000, "outdoor", "ACTIVE", now_str))

    wedding_items = [
        ("item-w-venue", sc_w_id, "Venue & Space", "Heritage Haveli Grand Lawn", "FIXED", 30000000, 1, 1800, "APPROVED", 10000000, 10000000, "2026-10-30", None, "Includes 2 rehearsal buffer hours"),
        ("item-w-catering", sc_w_id, "Catering", "Royal Rajasthani Banquet (Pure Veg + Jain)", "PER_CAPITA", 140000, 1, 500, "QUOTED", 5000000, 0, "2026-11-10", None, "Live Dal Baati + Kulfi counter"),
        ("item-w-tables", sc_w_id, "Seating & Tables", "Banqueting Tables with Velvet Runners", "STEP_TIERED", 150000, 8, 1800, "ESTIMATED", 0, 0, None, None, "1 table per 8 guests"),
        ("item-w-buffet", sc_w_id, "Dining Logistics", "Dual-Sided Buffet Service Lines", "STEP_TIERED", 600000, 75, 1800, "ESTIMATED", 0, 0, None, None, "1 station per 75 guests"),
        ("item-w-decor", sc_w_id, "Decor & Florals", "Floral Mandap & Brass Lanterns", "FIXED", 18000000, 1, 1800, "APPROVED", 5000000, 5000000, "2026-11-01", None, "Locally sourced marigolds"),
        ("item-w-audio", sc_w_id, "Entertainment", "Shehnai & Live Folk Ensemble", "FIXED", 8000000, 1, 1800, "QUOTED", 2000000, 0, "2026-11-12", None, "Traditional afternoon entrance"),
        ("item-w-photo", sc_w_id, "Photography", "Candid Cinema & Drone Highlights", "FIXED", 12000000, 1, 1800, "APPROVED", 4000000, 4000000, "2026-11-05", None, "Dual shooter package"),
        ("item-w-favors", sc_w_id, "Guest Favors", "Handcrafted Mithai & Scented Ittar Box", "PER_CAPITA", 25000, 1, 1200, "ESTIMATED", 0, 0, None, None, "Return tokens for family"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_items)

    wedding_commitments = [
        ("com-w-caterer", w_id, "Catering", "Shahi Dastarkhwan Kitchens", "QUOTED", 36750000, 5000000, 0, "2026-11-05", "Are kitchen gas cylinder and live counter diesel generator charges billed separately?", "Hi Shahi Caterers, reviewing your ₹1,400/plate quote for 250 guests. Could you confirm if tasting sessions and waitstaff cutlery are all-inclusive?", "WhatsApp quote: ₹1,400 per plate + 5% GST for 250 pax", 0, 0, "idem-w-cat"),
        ("com-w-venue", w_id, "Venue & Space", "Raj Mandir Haveli Estates", "APPROVED", 35400000, 10000000, 10000000, "2026-10-30", "What is the overtime rate per 30 minutes after 11 PM?", "Deposit paid ₹1,00,000 via NEFT. Rehearsal buffer granted.", "Contract signed: ₹3,00,000 base + 18% GST", 1, 0, "idem-w-ven"),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_commitments)

    # Initial payment record for venue
    conn.execute("""
        INSERT INTO payments (id, event_id, commitment_id, budget_item_id, amount_paise, payment_method, reference_note, paid_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, ("pay-w-venue-1", w_id, "com-w-venue", "item-w-venue", 10000000, "NEFT", "Initial booking token payment", now_str))

    wedding_tasks = [
        ("task-w-1", w_id, "T-30 Days", "Finalize Pure Veg & Jain Tasting Session", "Catering Lead", "CRITICAL", "DONE", 1, "2026-10-25", None),
        ("task-w-2", w_id, "T-14 Days", "Confirm Banquet Floorplan & Stage Dimensions", "Family Lead", "HIGH", "PENDING", 0, "2026-11-11", None),
        ("task-w-3", w_id, "T-7 Days", "Freeze Final Guest Roster & Seating Clusters", "Logistics Head", "CRITICAL", "PENDING", 1, "2026-11-18", None),
        ("task-w-4", w_id, "T-1 Day", "Full Soundcheck & Generator Diesel Verification", "Audio Lead", "HIGH", "PENDING", 0, "2026-11-24", None),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_tasks)

    conn.execute("INSERT INTO task_dependencies (parent_task_id, child_task_id) VALUES (?, ?);", ("task-w-1", "task-w-3"))

    wedding_runbook = [
        ("rb-w-1", w_id, "15:00 - 16:30", "Doors Open / Welcome Drink Reception", "Catering bar active, musicians in position", "Host & Hospitality", "PENDING"),
        ("rb-w-2", w_id, "16:30 - 18:00", "Baraat Arrival & Floral Vow Exchange", "Audio spotlight on Mandap, quiet generator backup", "Coordinator & MC", "PENDING"),
        ("rb-w-3", w_id, "18:00 - 21:00", "Royal Banquet Dinner Service", "Open 4 buffet stations, replenish hot courses", "Catering Captain", "PENDING"),
    ]
    conn.executemany("""
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, wedding_runbook)

    wedding_themes = [
        ("th-w-1", w_id, "Rajputana Marigold Splendor", "Regal palace grandeur with brass urlis and velvet draping", json.dumps(["#9a3412", "#78350f", "#fef3c7", "#292524"]), "Fresh rosewater aroma and live shehnai notes", "Grand floral phoolon ki chaadar entry with cold pyrotechnics", "Locally grown marigolds instead of imported cut roses", 1),
        ("th-w-2", w_id, "Pastel Botanical Conservatory", "Ethereal day-lit celebration with soft eucalyptus and sheer drapes", json.dumps(["#365314", "#dcfce7", "#fafaf9", "#78716c"]), "Crisp lavender fragrance with acoustic string ensemble", "Golden hour sunset vows framed by botanical floral ring", "Potted herbs as table runners that double as guest favors", 0),
        ("th-w-3", w_id, "Midnight Starlight Pavilion", "Modern dramatic evening under a sparkling crystal canopy", json.dumps(["#1e1b4b", "#fde047", "#f4f4f5", "#475569"]), "Warm amber up-lighting and synchronized cello melodies", "First dance on low-lying cold dry-ice cloud layer", "Fairy light curtains against dark black fabric drops", 0),
    ]
    conn.executemany("""
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_themes)

    conn.execute("""
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (w_id, now_str, "INITIALIZE_EVENT", "Created baseline event with 8 line items and 10% contingency reserve", None, "Plan A (250 guests)"))

    # 2. Neo-Tokyo Cyberpunk 21st Birthday
    b_id = "evt-21st-birthday"
    conn.execute("""
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (b_id, "Neo-Tokyo Cyberpunk 21st Birthday", "birthday", "Bengaluru", "2026-12-05", "19:00", 5.0, "Asia/Kolkata", "indoor", 75, 35000000, "INR", 1000, 1, json.dumps({"dietary": "Asian Street Food", "style": "Neon Cyber-Noir"}), now_str))

    sc_b_id = "sc-birthday-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (sc_b_id, b_id, 1, "Birthday Master Plan", 75, 35000000, "indoor", "ACTIVE", now_str))

    birthday_items = [
        ("item-b-venue", sc_b_id, "Venue & Space", "Indiranagar Rooftop Glasshouse", "FIXED", 12000000, 1, 1800, "APPROVED", 5000000, 5000000, "2026-11-15", None, "Includes bar license"),
        ("item-b-catering", sc_b_id, "Catering", "Pan-Asian Sliders & Molecular Mocktail Bar", "PER_CAPITA", 120000, 1, 500, "QUOTED", 2000000, 0, "2026-11-20", None, "Bao buns + sushi rolls"),
        ("item-b-neon", sc_b_id, "Decor & Lighting", "Custom UV Neon Tubes & LED Tunnel Entrance", "FIXED", 4500000, 1, 1800, "APPROVED", 2000000, 2000000, "2026-11-18", None, "Rental with install"),
        ("item-b-dj", sc_b_id, "Entertainment", "Synthwave DJ & Live Saxophone Accompaniment", "FIXED", 3500000, 1, 1800, "QUOTED", 1000000, 0, "2026-11-25", None, "4-hour dance set"),
        ("item-b-cake", sc_b_id, "Cake & Dessert", "Holographic Geometric Tier Cake", "FIXED", 1500000, 1, 500, "ESTIMATED", 0, 0, None, None, "Dark chocolate + hazelnut praline"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_items)

    birthday_commitments = [
        ("com-b-venue", b_id, "Venue & Space", "Glasshouse Rooftop Indiranagar", "APPROVED", 14160000, 5000000, 5000000, "2026-11-15", "Does noise curfew at 11 PM require shifting to indoor lounge?", "Confirmed ₹1,20,000 base + 18% GST.", "Rooftop agreement signed", 1, 0, "idem-b-ven"),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_commitments)

    birthday_tasks = [
        ("task-b-1", b_id, "T-14 Days", "Confirm Mocktail Menu & Bar Stock Checklist", "Beverage Coordinator", "HIGH", "PENDING", 1, "2026-11-21", None),
        ("task-b-2", b_id, "T-7 Days", "Custom Neon Entrance Signs Installation Test", "Lighting Lead", "MEDIUM", "PENDING", 0, "2026-11-28", None),
        ("task-b-3", b_id, "T-1 Day", "Soundcheck & Playlist Alignment with DJ", "Host", "HIGH", "PENDING", 0, "2026-12-04", None),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_tasks)

    birthday_runbook = [
        ("rb-b-1", b_id, "19:00 - 20:30", "Guest Entry & Neon Photobooth Cocktails", "Bartenders live, ambient chillwave playlist", "Host & Greeter", "PENDING"),
        ("rb-b-2", b_id, "20:30 - 21:30", "Cyberpunk Cake Reveal & Toast", "Dim overheads, UV strobes focused on stage", "MC", "PENDING"),
        ("rb-b-3", b_id, "21:30 - 00:00", "High-Energy Synth DJ Set", "Bass boost active, late-night bao sliders replenish", "DJ & Floor Manager", "PENDING"),
    ]
    conn.executemany("""
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, birthday_runbook)

    birthday_themes = [
        ("th-b-1", b_id, "Neon Cyber-Noir", "Dark aesthetic pierced by vibrant magenta and cyan accents", json.dumps(["#1c1917", "#06b6d4", "#ec4899", "#a855f7"]), "Ozone haze aroma with deep 808 sub-bass rhythms", "Laser light show synchronized to the birthday countdown", "DIY UV string art photo backdrop instead of acrylic signs", 1),
        ("th-b-2", b_id, "Retro 80s Arcade Synthwave", "Warm nostalgia with palm tree silhouettes and neon grids", json.dumps(["#2e1065", "#ea580c", "#e11d48", "#14b8a6"]), "Cotton candy sweetness scent with vintage Chiptune riffs", "Playable vintage arcade cabinet tournament for guests", "Projector grid mapping instead of custom printed backdrops", 0),
        ("th-b-3", b_id, "Minimalist Industrial Chrome", "Sleek monochromatic elegance with silver accents", json.dumps(["#27272a", "#71717a", "#e4e4e7", "#ffffff"]), "Crisp bergamot scent and smooth deep house grooves", "Signature silver mirror photo installation with ring lights", "Polished aluminum riser tables without floral draping", 0),
    ]
    conn.executemany("""
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_themes)

    conn.execute("""
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (b_id, now_str, "INITIALIZE_EVENT", "Created baseline event with 5 line items and 10% contingency reserve", None, "Plan A (75 guests)"))

    # 3. Community Eco-Fest
    e_id = "evt-community-ecofest"
    conn.execute("""
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (e_id, "Sunlit Monsoon Community Harvest Festival", "community", "Pune", "2026-11-15", "10:00", 8.0, "Asia/Kolkata", "outdoor", 400, 80000000, "INR", 1000, 1, json.dumps({"dietary": "Organic Millet Feast", "style": "Eco Terracotta"}), now_str))

    sc_e_id = "sc-ecofest-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (sc_e_id, e_id, 1, "Community Master Plan", 400, 80000000, "outdoor", "ACTIVE", now_str))

    eco_items = [
        ("item-e-venue", sc_e_id, "Venue & Space", "Model Botanical Gardens Open Amphitheatre", "FIXED", 15000000, 1, 0, "APPROVED", 15000000, 15000000, "2026-10-20", None, "Municipal civic permit paid"),
        ("item-e-catering", sc_e_id, "Catering", "Organic Farm-to-Table Millet Feast", "PER_CAPITA", 60000, 1, 500, "QUOTED", 5000000, 0, "2026-11-01", None, "Locally harvested ingredients"),
        ("item-e-waste", sc_e_id, "Eco Logistics", "Zero-Waste Compostable Tableware & Sorting Hub", "STEP_TIERED", 250000, 100, 1800, "APPROVED", 1000000, 1000000, "2026-10-28", None, "1 waste hub per 100 attendees"),
        ("item-e-sound", sc_e_id, "Entertainment", "Solar-Powered Acoustic Soundstage", "FIXED", 8500000, 1, 1800, "APPROVED", 3000000, 3000000, "2026-11-02", None, "Battery storage included"),
        ("item-e-workshops", sc_e_id, "Activities", "Pottery & Seed Bomb Community Workshops", "STEP_TIERED", 150000, 50, 1800, "ESTIMATED", 0, 0, None, None, "1 facilitator per 50 participants"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_items)

    eco_commitments = [
        ("com-e-catering", e_id, "Catering", "Kisan Organic Co-op", "QUOTED", 25200000, 5000000, 0, "2026-11-01", "Will fresh banana leaf platters require additional washing water stations?", "Reviewing quote for 400 community members.", "Quote: ₹600/plate for 400 attendees", 0, 0, "idem-e-cat"),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_commitments)

    eco_tasks = [
        ("task-e-1", e_id, "T-14 Days", "Confirm Composting Partner & Waste Pickup Route", "Sustainability Officer", "CRITICAL", "PENDING", 0, "2026-11-01", None),
        ("task-e-2", e_id, "T-7 Days", "Lock Final Community RSVPs for Meal Preparation", "RSVP Lead", "CRITICAL", "PENDING", 1, "2026-11-08", None),
        ("task-e-3", e_id, "T-1 Day", "Solar Inverter Full Load Test & Shade Canopies", "Stage Tech Lead", "HIGH", "PENDING", 0, "2026-11-14", None),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_tasks)

    eco_runbook = [
        ("rb-e-1", e_id, "10:00 - 12:00", "Solar Soundcheck & Artisan Stall Setup", "Power batteries synced, shade awnings deployed", "Operations Director", "PENDING"),
        ("rb-e-2", e_id, "12:00 - 15:00", "Organic Millet Community Lunch Service", "Open 4 serving lines with volunteer marshals", "Catering Coordinator", "PENDING"),
        ("rb-e-3", e_id, "15:00 - 18:00", "Acoustic Folk Performance & Seed Bomb Distribution", "Acoustic microphones live, distribution tables open", "MC & Volunteer Captain", "PENDING"),
    ]
    conn.executemany("""
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, eco_runbook)

    eco_themes = [
        ("th-e-1", e_id, "Sunlit Monsoon Canopy", "Earthy terracotta hues and lush banana leaf greens", json.dumps(["#365314", "#9a3412", "#fef3c7", "#44403c"]), "Damp petrichor scent with soothing acoustic bamboo flutes", "Mass collective seed-bomb throwing ceremony at sunset", "Repurposed jute sacks for rustic display signage", 1),
        ("th-e-2", e_id, "Golden Harvest Fields", "Warm wheat and amber celebratory atmosphere", json.dumps(["#d97706", "#b45309", "#78350f", "#fef3c7"]), "Freshly toasted grain scent with joyful brass dhol accents", "Community harvest grain mandala created collectively", "Dried wild grasses as stage decor instead of fresh cut flowers", 0),
        ("th-e-3", e_id, "Earth & Sky Open Air", "Vibrant ultramarine blues with crisp cotton white drapes", json.dumps(["#1e3a8a", "#0284c7", "#f8fafc", "#15803d"]), "Fresh morning breeze aroma with live sarod melodies", "Unfurling of the giant community painted canvas banner", "Upcycled fabric banners created by school volunteers", 0),
    ]
    conn.executemany("""
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_themes)

    conn.execute("""
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (e_id, now_str, "INITIALIZE_EVENT", "Created baseline event with 5 line items and 10% contingency reserve", None, "Plan A (400 guests)"))


def create_event(event_data: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Creates a brand new celebration event with foundational budget, tasks, runbook, and themes."""
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    event_id = f"evt-{uuid.uuid4().hex[:10]}"
    scenario_id = f"sc-{event_id}-v1"

    title = event_data["title"].strip()
    event_type = event_data["event_type"]
    city = event_data["city"].strip()
    event_date = event_data["event_date"]
    start_time = event_data.get("start_time", "15:00")
    duration_hours = float(event_data.get("duration_hours", 5.0))
    timezone = event_data.get("timezone", "Asia/Kolkata")
    setting = event_data.get("setting", "outdoor")
    guests = int(event_data["guest_count"])
    target_budget_paise = int(event_data["target_budget_paise"])
    currency = event_data.get("currency", "INR")
    contingency_bps = int(event_data.get("contingency_bps", 1000))
    prefs = event_data.get("preferences", {})

    with get_connection(target_path) as conn:
        conn.execute("""
            INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
        """, (event_id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guests, target_budget_paise, currency, contingency_bps, json.dumps(prefs), now_str))

        conn.execute("""
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
            VALUES (?, ?, 1, 'Initial Blueprint', ?, ?, ?, 'ACTIVE', ?);
        """, (scenario_id, event_id, guests, target_budget_paise, setting, now_str))

        # Personalize catering, tasks, and decor from user preferences
        dietary_pref = str(prefs.get("dietary", "")).lower()
        style_pref = str(prefs.get("style", "")).lower()

        catering_title = "Main Celebration Dining Service"
        catering_notes = "Per-guest dining and beverage service"
        tasting_task_title = "Review Catering Menu & Finalize Food Tasting"

        if "jain" in dietary_pref or "pure veg" in dietary_pref or "vegetarian" in dietary_pref:
            catering_title = "Pure Vegetarian & Jain Celebration Banquet"
            catering_notes = "Strict Pure Veg & Jain culinary service with root-vegetable restrictions observed"
            tasting_task_title = "Finalize Pure Veg & Jain Tasting Session"
        elif "vegan" in dietary_pref:
            catering_title = "Plant-Based Organic Vegan Banquet"
            catering_notes = "100% dairy-free, plant-based artisanal catering"
            tasting_task_title = "Finalize Vegan Tasting & Ingredient Verification"
        elif "halal" in dietary_pref:
            catering_title = "Halal Certified Royal Feast Banquet"
            catering_notes = "Certified Halal preparation with traditional accompaniments"
            tasting_task_title = "Finalize Halal Menu Tasting & Certification Review"
        elif "asian" in dietary_pref or "pan-asian" in dietary_pref:
            catering_title = "Pan-Asian Sliders & Dim Sum Live Stations"
            catering_notes = "Interactive live wok and dim sum dining counters"
            tasting_task_title = "Pan-Asian Tasting & Live Station Setup Review"

        # Generate foundational budget line items based on event type
        allocatable = target_budget_paise - (target_budget_paise * contingency_bps + 5000) // 10000
        venue_budget = (allocatable * 30) // 100
        catering_unit = max(25000, ((allocatable * 40) // 100) // max(1, guests))
        decor_budget = (allocatable * 15) // 100
        sound_budget = (allocatable * 15) // 100

        items = [
            (f"item-{uuid.uuid4().hex[:10]}", scenario_id, "Venue & Space", f"{title} Main Space", "FIXED", venue_budget, 1, 1800, "ESTIMATED", 0, 0, None, None, f"Initial space allocation for {setting} setting"),
            (f"item-{uuid.uuid4().hex[:10]}", scenario_id, "Catering", catering_title, "PER_CAPITA", catering_unit, 1, 500, "ESTIMATED", 0, 0, None, None, catering_notes),
            (f"item-{uuid.uuid4().hex[:10]}", scenario_id, "Seating & Tables", "Guest Dining Tables & Chairs", "STEP_TIERED", 150000, 8, 1800, "ESTIMATED", 0, 0, None, None, "1 table cluster per 8 guests"),
            (f"item-{uuid.uuid4().hex[:10]}", scenario_id, "Decor & Styling", "Atmosphere & Floral Installation", "FIXED", decor_budget, 1, 1800, "ESTIMATED", 0, 0, None, None, f"{prefs.get('style', 'Theme-specific')} styling"),
            (f"item-{uuid.uuid4().hex[:10]}", scenario_id, "Entertainment", "Audio System & Musical Performance", "FIXED", sound_budget, 1, 1800, "ESTIMATED", 0, 0, None, None, "Sound and stage presentation"),
        ]
        conn.executemany("""
            INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, items)

        # Generate date-aware preparation tasks with lead time compression
        try:
            evt_dt = datetime.strptime(event_date, "%Y-%m-%d")
            today_dt = datetime.now(timezone.utc).replace(tzinfo=None)
            days_until = (evt_dt - today_dt).days
        except Exception:
            days_until = 30

        if days_until > 30:
            tasks = [
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-30 Days", "Lock Venue & Sign Base Contract", "Lead Organizer", "CRITICAL", "PENDING", 0, (evt_dt - timedelta(days=30)).strftime("%Y-%m-%d"), None),
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-21 Days", tasting_task_title, "Host", "HIGH", "PENDING", 1, (evt_dt - timedelta(days=21)).strftime("%Y-%m-%d"), None),
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-7 Days", "Freeze Guest Headcount & Seating Chart", "Coordinator", "CRITICAL", "PENDING", 1, (evt_dt - timedelta(days=7)).strftime("%Y-%m-%d"), None),
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-1 Day", "On-site Technical Soundcheck & Rehearsal", "Floor Lead", "HIGH", "PENDING", 0, (evt_dt - timedelta(days=1)).strftime("%Y-%m-%d"), None),
            ]
        else:
            # Compressed rapid schedule for short-notice celebrations
            tasks = [
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-5 Days (Rapid)", "Secure Available Venue & Immediate Token", "Lead Organizer", "CRITICAL", "PENDING", 0, (evt_dt - timedelta(days=max(1, min(5, days_until)))).strftime("%Y-%m-%d"), None),
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-3 Days (Rapid)", f"Lock Headcount & {tasting_task_title}", "Host", "CRITICAL", "PENDING", 1, (evt_dt - timedelta(days=max(1, min(3, days_until)))).strftime("%Y-%m-%d"), None),
                (f"task-{uuid.uuid4().hex[:10]}", event_id, "T-1 Day", "Confirm Vendor Arrival Windows & Power Setup", "Coordinator", "HIGH", "PENDING", 0, (evt_dt - timedelta(days=1)).strftime("%Y-%m-%d"), None),
            ]
        conn.executemany("""
            INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, tasks)

        # Generate minute-by-minute runbook cues respecting duration and midnight crossings
        try:
            start_hour, start_min = map(int, start_time.split(":"))
        except Exception:
            start_hour, start_min = 15, 0

        t1_start = f"{start_hour:02d}:{start_min:02d}"
        t1_end_h = (start_hour + int(duration_hours * 0.3)) % 24
        t1_end = f"{t1_end_h:02d}:{start_min:02d}"

        t2_end_h = (start_hour + int(duration_hours * 0.7)) % 24
        t2_end = f"{t2_end_h:02d}:{start_min:02d}"

        t3_end_h = (start_hour + int(duration_hours)) % 24
        t3_end = f"{t3_end_h:02d}:{start_min:02d}"

        runbook = [
            (f"rb-{uuid.uuid4().hex[:10]}", event_id, f"{t1_start} - {t1_end}", "Guest Arrival & Welcome Hospitality", "Crew positions active, audio check confirmed", "Host & Hospitality Lead", "PENDING"),
            (f"rb-{uuid.uuid4().hex[:10]}", event_id, f"{t1_end} - {t2_end}", "Main Celebration Moments & Keynote Ceremony", "Spotlights engaged, catering service lines live", "Coordinator & MC", "PENDING"),
            (f"rb-{uuid.uuid4().hex[:10]}", event_id, f"{t2_end} - {t3_end}", "Dinner Banquet & Social Dancing", "Dessert replenish, late transport staging", "Catering Captain & Floor Lead", "PENDING"),
        ]
        conn.executemany("""
            INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, runbook)

        # Generate 3 curated themes
        themes = [
            (f"th-{uuid.uuid4().hex[:10]}", event_id, f"{title} Signature Warmth", "Timeless warmth with natural terracotta and brass accents", json.dumps(["#9a3412", "#c2410c", "#fef3c7", "#292524"]), "Subtle sandalwood scent with acoustic instrumentals", "Dramatic golden-hour welcome entrance moment", "Locally sourced fabric banners instead of custom printed plastics", 1),
            (f"th-{uuid.uuid4().hex[:10]}", event_id, "Botanical Olive Serenity", "Organic foliage and crisp clean minimalist linens", json.dumps(["#365314", "#4d7c0f", "#f5f5f4", "#78716c"]), "Fresh eucalyptus notes with ambient lo-fi melodies", "Collective toast under illuminated botanical canopy", "Potted herbs and ferns that double as guest take-home gifts", 0),
            (f"th-{uuid.uuid4().hex[:10]}", event_id, "Evening Starlight Elegance", "Dramatic deep charcoal tones and warm ambient candlelight", json.dumps(["#1c1917", "#d97706", "#f5f5f4", "#44403c"]), "Warm amber glow with smooth acoustic jazz", "Surprise coordinated sparkler farewell sequence", "Fairy light cascades against neutral wall drapes", 0),
        ]
        conn.executemany("""
            INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, themes)

        # Audit log
        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "CREATE_EVENT", f"Created event '{title}' for {guests} guests with {setting} setting", None, f"v1 ({currency} {target_budget_paise/100:,.2f})"))

        conn.commit()
        return {"success": True, "event_id": event_id}


def get_event_by_id(event_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        evt_row = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt_row:
            return None
        event = dict(evt_row)
        if "preferences_json" in event and event["preferences_json"]:
            try:
                event["preferences"] = json.loads(event["preferences_json"])
            except Exception:
                event["preferences"] = {}

        sc_row = conn.execute("SELECT * FROM scenarios WHERE event_id = ? AND status = 'ACTIVE';", (event_id,)).fetchone()
        scenario = dict(sc_row) if sc_row else None
        scenario_id = scenario["id"] if scenario else None

        items = []
        if scenario_id:
            i_rows = conn.execute("SELECT * FROM budget_items WHERE scenario_id = ?;", (scenario_id,)).fetchall()
            items = [dict(r) for r in i_rows]

        v_rows = conn.execute("SELECT * FROM vendor_commitments WHERE event_id = ?;", (event_id,)).fetchall()
        vendors = [dict(r) for r in v_rows]

        t_rows = conn.execute("SELECT * FROM tasks WHERE event_id = ? ORDER BY due_date ASC;", (event_id,)).fetchall()
        tasks = [dict(r) for r in t_rows]

        dep_rows = conn.execute("SELECT * FROM task_dependencies;").fetchall()
        dependencies = [(r["parent_task_id"], r["child_task_id"]) for r in dep_rows]

        rb_rows = conn.execute("SELECT * FROM runbook_cues WHERE event_id = ?;", (event_id,)).fetchall()
        runbook = [dict(r) for r in rb_rows]

        th_rows = conn.execute("SELECT * FROM themes WHERE event_id = ?;", (event_id,)).fetchall()
        themes = []
        for r in th_rows:
            d = dict(r)
            d["palette_hex"] = json.loads(d["palette_hex"]) if isinstance(d["palette_hex"], str) else d["palette_hex"]
            themes.append(d)

        pay_rows = conn.execute("SELECT * FROM payments WHERE event_id = ? ORDER BY paid_at DESC;", (event_id,)).fetchall()
        payments = [dict(r) for r in pay_rows]

        inc_rows = conn.execute("SELECT * FROM incidents WHERE event_id = ? ORDER BY created_at DESC;", (event_id,)).fetchall()
        incidents = [dict(r) for r in inc_rows]

        log_rows = conn.execute("SELECT * FROM audit_logs WHERE event_id = ? ORDER BY id DESC LIMIT 30;", (event_id,)).fetchall()
        logs = [dict(r) for r in log_rows]

        sc_history_rows = conn.execute("SELECT * FROM scenarios WHERE event_id = ? ORDER BY version ASC;", (event_id,)).fetchall()
        scenarios_history = [dict(r) for r in sc_history_rows]

        return {
            "event": event,
            "active_scenario": scenario,
            "scenarios_history": scenarios_history,
            "budget_items": items,
            "vendors": vendors,
            "tasks": tasks,
            "dependencies": dependencies,
            "runbook": runbook,
            "themes": themes,
            "payments": payments,
            "incidents": incidents,
            "audit_logs": logs,
        }


def list_events(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY created_at DESC;").fetchall()
        return [dict(r) for r in rows]


def commit_scenario_version(
    event_id: str,
    new_guests: int,
    new_budget_items: Optional[List[Dict[str, Any]]] = None,
    note: str = "Scenario proposal",
    base_version: Optional[int] = None,
    new_setting: Optional[str] = None,
    new_date: Optional[str] = None,
    invalidated_task_ids: Optional[List[str]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transactionally creates a new immutable scenario version, verifies baseline version,
    persists affected tasks as NEEDS_REVIEW, and writes an audit log.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        evt = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        old_version = evt["active_scenario_version"]
        if base_version is not None and base_version != old_version:
            raise ValueError(f"Stale proposal rejected: Base version v{base_version} does not match current active version v{old_version}.")

        new_version = old_version + 1
        new_sc_id = f"sc-{event_id}-v{new_version}"
        setting = new_setting or evt["setting"]

        # Determine budget items: use provided or scale from active scenario
        items_to_insert = new_budget_items
        if items_to_insert is None or len(items_to_insert) == 0:
            active_sc = conn.execute("SELECT id FROM scenarios WHERE event_id = ? AND status = 'ACTIVE';", (event_id,)).fetchone()
            if active_sc:
                prev_rows = conn.execute("SELECT * FROM budget_items WHERE scenario_id = ?;", (active_sc["id"],)).fetchall()
                items_to_insert = [dict(r) for r in prev_rows]
            else:
                items_to_insert = []

        # Archive old active scenario
        conn.execute("UPDATE scenarios SET status = 'ARCHIVED' WHERE event_id = ? AND status = 'ACTIVE';", (event_id,))

        # Create new scenario
        conn.execute("""
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """, (new_sc_id, event_id, new_version, f"Scenario v{new_version} ({note})", new_guests, evt["target_budget_paise"], setting, now_str))

        # Insert new budget items with unique IDs, preserving approvals
        for idx, it in enumerate(items_to_insert):
            item_id = f"item-{event_id}-v{new_version}-{idx+1}-{uuid.uuid4().hex[:6]}"
            conn.execute("""
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                item_id,
                new_sc_id,
                it["category"],
                it["name"],
                it["pricing_model"],
                it["unit_cost_paise"],
                it.get("step_capacity", 1),
                it.get("tax_rate_bps", 0),
                it.get("approval_state", "ESTIMATED"),
                it.get("deposit_required_paise", 0),
                0,  # Cash paid is derived from the payments ledger
                it.get("deposit_due_date"),
                it.get("superseded_by_id"),
                it.get("notes"),
            ))

        # Persist affected tasks as needing review (including completed tasks whose preconditions shifted)
        if invalidated_task_ids:
            for tid in invalidated_task_ids:
                t_row = conn.execute("SELECT status FROM tasks WHERE id = ? AND event_id = ?;", (tid, event_id)).fetchone()
                prev_st = t_row["status"] if t_row else "UNKNOWN"
                conn.execute("""
                    UPDATE tasks SET status = 'NEEDS_REVIEW', reverification_reason = ? WHERE id = ? AND event_id = ?;
                """, (f"Invalidated by Scenario v{new_version} update ({note}) - previously {prev_st}", tid, event_id))

        # Flag affected vendor commitments for reconfirmation if headcount shifted
        if new_guests != evt["guest_count"]:
            conn.execute("""
                UPDATE vendor_commitments SET needs_reconfirmation = 1 WHERE event_id = ?;
            """, (event_id,))

        # Update event atomically checking base version
        cur = conn.execute("""
            UPDATE events SET guest_count = ?, setting = ?, active_scenario_version = ? 
            WHERE id = ? AND active_scenario_version = ?;
        """, (new_guests, setting, new_version, event_id, old_version))
        if cur.rowcount == 0:
            raise ValueError(f"Stale proposal rejected: Base version v{old_version} was modified concurrently.")

        if new_date:
            conn.execute("UPDATE events SET event_date = ? WHERE id = ?;", (new_date, event_id))

        # Record audit log
        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "COMMIT_SCENARIO", f"Committed scenario v{new_version}: {note}", f"v{old_version}", f"v{new_version} ({new_guests} guests)"))

        conn.commit()
        return {"success": True, "new_version": new_version, "scenario_id": new_sc_id}


def revert_scenario_version(
    event_id: str,
    target_version: int,
    reason: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely reverts an event by creating a new forward version from target_version items.
    Never deletes or alters payment records or historical audit logs.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        evt = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        target_sc = conn.execute("SELECT * FROM scenarios WHERE event_id = ? AND version = ?;", (event_id, target_version)).fetchone()
        if not target_sc:
            raise ValueError(f"Target scenario version v{target_version} not found for event {event_id}")

        old_version = evt["active_scenario_version"]
        new_version = old_version + 1
        new_sc_id = f"sc-{event_id}-v{new_version}"

        # Fetch items from target scenario
        target_items = conn.execute("SELECT * FROM budget_items WHERE scenario_id = ?;", (target_sc["id"],)).fetchall()

        # Archive currently active scenario
        conn.execute("UPDATE scenarios SET status = 'ARCHIVED' WHERE event_id = ? AND status = 'ACTIVE';", (event_id,))

        # Insert new active scenario representing the reverted state
        conn.execute("""
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """, (new_sc_id, event_id, new_version, f"Revert to v{target_version}: {reason}", target_sc["guest_count"], target_sc["target_budget_paise"], target_sc["setting"], now_str))

        # Re-insert items without copying stale historical paid balances
        # Actual cash allocations are computed dynamically from the immutable payments ledger
        for idx, it in enumerate(target_items):
            item_id = f"item-{event_id}-v{new_version}-{idx+1}-{uuid.uuid4().hex[:6]}"
            conn.execute("""
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                item_id,
                new_sc_id,
                it["category"],
                it["name"],
                it["pricing_model"],
                it["unit_cost_paise"],
                it["step_capacity"],
                it["tax_rate_bps"],
                it["approval_state"],
                it["deposit_required_paise"],
                0,  # Cash paid is derived from payments table, preventing financial drift
                it["deposit_due_date"],
                it["notes"],
            ))

        conn.execute("""
            UPDATE events SET guest_count = ?, setting = ?, active_scenario_version = ? WHERE id = ?;
        """, (target_sc["guest_count"], target_sc["setting"], new_version, event_id))

        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "REVERT_SCENARIO", f"Reverted event state to match v{target_version}: {reason}", f"v{old_version}", f"v{new_version}"))

        conn.commit()
        return {"success": True, "new_version": new_version, "scenario_id": new_sc_id}


def record_payment(
    event_id: str,
    amount_paise: int,
    payment_method: str,
    reference_note: str,
    commitment_id: Optional[str] = None,
    budget_item_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Records an actual payment transaction in the ledger, updating commitment and item paid balances."""
    if amount_paise <= 0:
        raise ValueError(f"Payment amount must be strictly positive, got {amount_paise}")

    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payment_id = f"pay-{uuid.uuid4().hex[:10]}"

    with get_connection(target_path) as conn:
        # Cross-event tenant validation
        evt = conn.execute("SELECT id FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        if commitment_id:
            comm = conn.execute("SELECT id FROM vendor_commitments WHERE id = ? AND event_id = ?;", (commitment_id, event_id)).fetchone()
            if not comm:
                raise ValueError(f"Commitment '{commitment_id}' not found for event '{event_id}'")

        if budget_item_id:
            b_item = conn.execute("""
                SELECT b.id FROM budget_items b 
                JOIN scenarios s ON b.scenario_id = s.id 
                WHERE b.id = ? AND s.event_id = ?;
            """, (budget_item_id, event_id)).fetchone()
            if not b_item:
                raise ValueError(f"Budget item '{budget_item_id}' not found for event '{event_id}'")

        conn.execute("""
            INSERT INTO payments (id, event_id, commitment_id, budget_item_id, amount_paise, payment_method, reference_note, paid_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (payment_id, event_id, commitment_id, budget_item_id, amount_paise, payment_method, reference_note, now_str))

        if commitment_id:
            conn.execute("""
                UPDATE vendor_commitments SET paid_amount_paise = paid_amount_paise + ? WHERE id = ? AND event_id = ?;
            """, (amount_paise, commitment_id, event_id))

        if budget_item_id:
            conn.execute("""
                UPDATE budget_items SET paid_amount_paise = paid_amount_paise + ? WHERE id = ?;
            """, (amount_paise, budget_item_id))

        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "RECORD_PAYMENT", f"Recorded payment of ₹{amount_paise/100:,.2f} via {payment_method} ({reference_note})", None, f"Payment {payment_id}"))

        conn.commit()
        return {"success": True, "payment_id": payment_id, "amount_paise": amount_paise}


def approve_vendor_quote_in_db(
    event_id: str,
    vendor_name: str,
    category: str,
    items: List[Dict[str, Any]],
    advance_deposit_paise: int = 0,
    deposit_due_date: Optional[str] = None,
    notes: Optional[str] = None,
    supersedes_item_id: Optional[str] = None,
    supersedes_item_ids: Optional[List[str]] = None,
    idempotency_key: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approves a vendor quote into the active scenario ledger in one atomic transaction.
    1. Recomputes exact line items and tiered math with taxes.
    2. Enforces idempotency against retried approvals.
    3. Prevents double-counting by superseding matching estimated items.
    4. Records deposit obligation strictly on commitment level to prevent multiplication.
    """
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(target_path) as conn:
        data = get_event_by_id(event_id, target_path)
        if not data:
            raise ValueError(f"Event {event_id} not found")

        # Idempotency check
        if idempotency_key:
            existing = conn.execute("SELECT * FROM vendor_commitments WHERE event_id = ? AND idempotency_key = ?;", (event_id, idempotency_key)).fetchone()
            if existing:
                return {"success": True, "commitment_id": existing["id"], "already_approved": True, "message": "Quote already approved with this key."}

        scenario_id = data["active_scenario"]["id"]
        guests = data["event"]["guest_count"]
        total_quote_paise = 0
        new_item_ids = []

        # Mark superseded estimated items to eliminate double-counting
        if supersedes_item_ids:
            for s_id in supersedes_item_ids:
                conn.execute("UPDATE budget_items SET approval_state = 'REPLACED' WHERE id = ?;", (s_id,))
        elif supersedes_item_id:
            conn.execute("UPDATE budget_items SET approval_state = 'REPLACED' WHERE id = ?;", (supersedes_item_id,))
        else:
            # Auto-supersede estimated items in the same category
            conn.execute("""
                UPDATE budget_items SET approval_state = 'REPLACED'
                WHERE scenario_id = ? AND category = ? AND approval_state = 'ESTIMATED';
            """, (scenario_id, category))

        for it in items:
            unit = max(0, int(it.get("unit_cost_paise", 0)))
            model = it.get("pricing_model", "FIXED")
            cap = max(1, int(it.get("step_capacity", 1)))
            tax_rate = max(0, min(10000, int(it.get("tax_rate_bps", 0))))

            calc = compute_line_item_paise(model, unit, guests, cap, tax_rate)
            total_quote_paise += calc["total_paise"]

            item_id = f"item-quote-{uuid.uuid4().hex[:10]}"
            new_item_ids.append(item_id)
            # Item deposit obligation is 0 to avoid multiplication across multi-item quotes;
            # the authoritative deposit obligation is held on the vendor_commitments record.
            conn.execute("""
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', 0, 0, ?, ?);
            """, (
                item_id,
                scenario_id,
                category,
                it["name"],
                model,
                unit,
                cap,
                tax_rate,
                deposit_due_date,
                notes,
            ))

        com_id = f"com-{uuid.uuid4().hex[:10]}"
        conn.execute("""
            INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
            VALUES (?, ?, ?, ?, 'APPROVED', ?, ?, 0, ?, ?, ?, ?, 1, 0, ?);
        """, (
            com_id,
            event_id,
            category,
            vendor_name,
            total_quote_paise,
            advance_deposit_paise,
            deposit_due_date,
            "Are kitchen fuel cylinders and generator diesel included?",
            f"Hi {vendor_name}, quote approved.",
            notes or "Extracted & approved via Planqira",
            idempotency_key,
        ))

        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (
            event_id,
            now_str,
            "APPROVE_VENDOR_QUOTE",
            f"Approved quote from {vendor_name} ({category}) with deposit requirement of ₹{advance_deposit_paise/100:,.2f}",
            "QUOTED",
            f"APPROVED (₹{total_quote_paise/100:,.2f})"
        ))

        conn.commit()
        return {
            "success": True,
            "commitment_id": com_id,
            "total_quote_paise": total_quote_paise,
            "item_ids": new_item_ids,
            "message": f"Approved quote from {vendor_name} and recorded in ledger without premature payment mark.",
        }


def create_incident(
    event_id: str,
    severity: str,
    title: str,
    description: str,
    resolution: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Records an operational event-day incident with resolution tracking."""
    target_path = db_path or get_db_path()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    inc_id = f"inc-{uuid.uuid4().hex[:10]}"

    with get_connection(target_path) as conn:
        conn.execute("""
            INSERT INTO incidents (id, event_id, severity, title, description, resolution, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (inc_id, event_id, severity, title, description, resolution, "RESOLVED" if resolution else "OPEN", now_str))

        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "LOG_INCIDENT", f"Logged {severity} incident: {title}", None, inc_id))

        conn.commit()
        return {"success": True, "incident_id": inc_id}


def list_incidents(event_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        rows = conn.execute("SELECT * FROM incidents WHERE event_id = ? ORDER BY created_at DESC;", (event_id,)).fetchall()
        return [dict(r) for r in rows]


def update_task_status(task_id: str, status: str, event_id: Optional[str] = None, db_path: Optional[str] = None) -> bool:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        if event_id:
            cur = conn.execute("UPDATE tasks SET status = ? WHERE id = ? AND event_id = ?;", (status, task_id, event_id))
        else:
            cur = conn.execute("UPDATE tasks SET status = ? WHERE id = ?;", (status, task_id))
        conn.commit()
        return cur.rowcount > 0


def update_runbook_status(cue_id: str, status: str, event_id: Optional[str] = None, db_path: Optional[str] = None) -> bool:
    target_path = db_path or get_db_path()
    with get_connection(target_path) as conn:
        if event_id:
            cur = conn.execute("UPDATE runbook_cues SET status = ? WHERE id = ? AND event_id = ?;", (status, cue_id, event_id))
        else:
            cur = conn.execute("UPDATE runbook_cues SET status = ? WHERE id = ?;", (status, cue_id))
        conn.commit()
        return cur.rowcount > 0

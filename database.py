"""
Planqira SQLite Persistence Engine (planqira.db)
ACID-compliant relational storage with schema versioning,
foreign keys, audit logging, and idempotent demo data seeding.
"""

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional

DB_FILE = "planqira.db"


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DB_FILE) -> None:
    """Initializes tables idempotently and seeds demo events if empty."""
    with get_connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            event_type TEXT NOT NULL,
            city TEXT NOT NULL,
            event_date TEXT NOT NULL,
            guest_count INTEGER NOT NULL,
            target_budget_paise INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            contingency_bps INTEGER NOT NULL DEFAULT 1000,
            active_scenario_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            guest_count INTEGER NOT NULL,
            target_budget_paise INTEGER NOT NULL,
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
            paid_amount_paise INTEGER NOT NULL DEFAULT 0,
            deposit_due_date TEXT,
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
            paid_amount_paise INTEGER NOT NULL DEFAULT 0,
            deposit_due_date TEXT,
            hidden_fee_question TEXT,
            negotiation_script TEXT,
            raw_quote_text TEXT,
            is_reviewed INTEGER NOT NULL DEFAULT 0,
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

        # Check if events already exist
        cursor = conn.execute("SELECT COUNT(*) as count FROM events;")
        count = cursor.fetchone()["count"]
        if count == 0:
            seed_demo_events(conn)


def seed_demo_events(conn: sqlite3.Connection) -> None:
    """Seeds 3 realistic events idempotently on clean database initialization."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Royal Heritage Wedding
    w_id = "evt-royal-heritage-wedding"
    conn.execute("""
        INSERT INTO events (id, title, event_type, city, event_date, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (w_id, "Royal Rajputana Heritage Wedding", "wedding", "Jaipur", "2026-11-25", 250, 120000000, "INR", 1000, 1, now_str))

    sc_w_id = "sc-wedding-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (sc_w_id, w_id, 1, "Baseline Master Plan", 250, 120000000, "ACTIVE", now_str))

    wedding_items = [
        ("item-w-venue", sc_w_id, "Venue & Space", "Heritage Haveli Grand Lawn", "FIXED", 30000000, 1, 1800, "APPROVED", 10000000, "2026-10-30", "Includes 2 rehearsal buffer hours"),
        ("item-w-catering", sc_w_id, "Catering", "Royal Rajasthani Banquet (Pure Veg + Jain)", "PER_CAPITA", 140000, 1, 500, "QUOTED", 0, "2026-11-10", "Live Dal Baati + Kulfi counter"),
        ("item-w-tables", sc_w_id, "Seating & Tables", "Banqueting Tables with Velvet Runners", "STEP_TIERED", 150000, 8, 1800, "ESTIMATED", 0, None, "1 table per 8 guests"),
        ("item-w-buffet", sc_w_id, "Dining Logistics", "Dual-Sided Buffet Service Lines", "STEP_TIERED", 600000, 75, 1800, "ESTIMATED", 0, None, "1 station per 75 guests"),
        ("item-w-decor", sc_w_id, "Decor & Florals", "Floral Mandap & Brass Lanterns", "FIXED", 18000000, 1, 1800, "APPROVED", 5000000, "2026-11-01", "Locally sourced marigolds"),
        ("item-w-audio", sc_w_id, "Entertainment", "Shehnai & Live Folk Ensemble", "FIXED", 8000000, 1, 1800, "QUOTED", 0, "2026-11-12", "Traditional afternoon entrance"),
        ("item-w-photo", sc_w_id, "Photography", "Candid Cinema & Drone Highlights", "FIXED", 12000000, 1, 1800, "APPROVED", 4000000, "2026-11-05", "Dual shooter package"),
        ("item-w-favors", sc_w_id, "Guest Favors", "Handcrafted Mithai & Scented Ittar Box", "PER_CAPITA", 25000, 1, 1200, "ESTIMATED", 0, None, "Return tokens for family"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, paid_amount_paise, deposit_due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_items)

    wedding_commitments = [
        ("com-w-caterer", w_id, "Catering", "Shahi Dastarkhwan Kitchens", "QUOTED", 36750000, 0, "2026-11-05", "Are kitchen gas cylinder and live counter diesel generator charges billed separately?", "Hi Shahi Caterers, reviewing your ₹1,400/plate quote for 250 guests. Could you confirm if tasting sessions and waitstaff cutlery are all-inclusive?", "WhatsApp quote: ₹1,400 per plate + 5% GST for 250 pax", 0),
        ("com-w-venue", w_id, "Venue", "Raj Mandir Haveli Estates", "APPROVED", 35400000, 10000000, "2026-10-30", "What is the overtime rate per 30 minutes after 11 PM?", "Deposit paid ₹1,00,000 via NEFT. Rehearsal buffer granted.", "Contract signed: ₹3,00,000 base + 18% GST", 1),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_commitments)

    wedding_tasks = [
        ("task-w-1", w_id, "T-30 Days", "Finalize Pure Veg & Jain Tasting Session", "Catering Lead", "CRITICAL", "DONE", 1, "2026-10-25"),
        ("task-w-2", w_id, "T-14 Days", "Confirm Banquet Floorplan & Stage Dimensions", "Family Lead", "HIGH", "PENDING", 0, "2026-11-11"),
        ("task-w-3", w_id, "T-7 Days", "Freeze Final Guest Roster & Seating Clusters", "Logistics Head", "CRITICAL", "PENDING", 1, "2026-11-18"),
        ("task-w-4", w_id, "T-1 Day", "Full Soundcheck & Generator Diesel Verification", "Audio Lead", "HIGH", "PENDING", 0, "2026-11-24"),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wedding_tasks)

    # Task dependencies: task-w-3 depends on task-w-1
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
        ("th-w-1", w_id, "Rajputana Marigold Splendor", "Regal palace grandeur with brass urlis and velvet draping", json.dumps(["#D4AF37", "#800020", "#FAF0E6", "#2D112C"]), "Fresh rosewater aroma and live shehnai notes", "Grand floral phoolon ki chaadar entry with cold pyrotechnics", "Locally grown marigolds instead of imported cut roses", 1),
        ("th-w-2", w_id, "Pastel Botanical Conservatory", "Ethereal day-lit celebration with soft eucalyptus and sheer drapes", json.dumps(["#A3B18A", "#E8D7D8", "#FCFAF6", "#C5A880"]), "Crisp lavender fragrance with acoustic string ensemble", "Golden hour sunset vows framed by botanical floral ring", "Potted herbs as table runners that double as guest favors", 0),
        ("th-w-3", w_id, "Midnight Starlight Pavilion", "Modern dramatic evening under a sparkling crystal canopy", json.dumps(["#0B132B", "#F59E0B", "#E0E1DD", "#3B1E3E"]), "Warm amber up-lighting and synchronized cello melodies", "First dance on low-lying cold dry-ice cloud layer", "Fairy light curtains against dark black fabric drops", 0),
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
        INSERT INTO events (id, title, event_type, city, event_date, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (b_id, "Neo-Tokyo Cyberpunk 21st Birthday", "birthday", "Bengaluru", "2026-12-05", 75, 35000000, "INR", 1000, 1, now_str))

    sc_b_id = "sc-birthday-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
    """, (sc_b_id, b_id, 1, "Birthday Master Plan", 75, 35000000, now_str))

    birthday_items = [
        ("item-b-venue", sc_b_id, "Venue & Space", "Indiranagar Rooftop Glasshouse", "FIXED", 12000000, 1, 1800, "APPROVED", 5000000, "2026-11-15", "Includes bar license"),
        ("item-b-catering", sc_b_id, "Catering", "Pan-Asian Sliders & Molecular Mocktail Bar", "PER_CAPITA", 120000, 1, 500, "QUOTED", 0, "2026-11-20", "Bao buns + sushi rolls"),
        ("item-b-neon", sc_b_id, "Decor & Lighting", "Custom UV Neon Tubes & LED Tunnel Entrance", "FIXED", 4500000, 1, 1800, "APPROVED", 2000000, "2026-11-18", "Rental with install"),
        ("item-b-dj", sc_b_id, "Entertainment", "Synthwave DJ & Live Saxophone Accompaniment", "FIXED", 3500000, 1, 1800, "QUOTED", 0, "2026-11-25", "4-hour dance set"),
        ("item-b-cake", sc_b_id, "Cake & Dessert", "Holographic Geometric Tier Cake", "FIXED", 1500000, 1, 500, "ESTIMATED", 0, None, "Dark chocolate + hazelnut praline"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, paid_amount_paise, deposit_due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_items)

    birthday_commitments = [
        ("com-b-venue", b_id, "Venue", "Glasshouse Rooftop Indiranagar", "APPROVED", 14160000, 5000000, "2026-11-15", "Does noise curfew at 11 PM require shifting to indoor lounge?", "Confirmed ₹1,20,000 base + 18% GST.", "Rooftop agreement signed", 1),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, birthday_commitments)

    birthday_tasks = [
        ("task-b-1", b_id, "T-14 Days", "Confirm Mocktail Menu & Bar Stock Checklist", "Beverage Coordinator", "HIGH", "PENDING", 1, "2026-11-21"),
        ("task-b-2", b_id, "T-7 Days", "Custom Neon Entrance Signs Installation Test", "Lighting Lead", "MEDIUM", "PENDING", 0, "2026-11-28"),
        ("task-b-3", b_id, "T-1 Day", "Soundcheck & Playlist Alignment with DJ", "Host", "HIGH", "PENDING", 0, "2026-12-04"),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
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
        ("th-b-1", b_id, "Neon Cyber-Noir", "Dark aesthetic pierced by vibrant magenta and cyan lasers", json.dumps(["#0A0A12", "#00F0FF", "#FF007F", "#7928CA"]), "Ozone haze aroma with deep 808 sub-bass rhythms", "Laser light show synchronized to the birthday countdown", "DIY UV string art photo backdrop instead of acrylic signs", 1),
        ("th-b-2", b_id, "Retro 80s Arcade Synthwave", "Warm nostalgia with palm tree silhouettes and neon grids", json.dumps(["#1A0B2E", "#FF7700", "#FF0055", "#00FFCC"]), "Cotton candy sweetness scent with vintage Chiptune riffs", "Playable vintage arcade cabinet tournament for guests", "Projector grid mapping instead of custom printed backdrops", 0),
        ("th-b-3", b_id, "Minimalist Industrial Chrome", "Sleek monochromatic elegance with silver accents", json.dumps(["#18181B", "#71717A", "#E4E4E7", "#FFFFFF"]), "Crisp bergamot scent and smooth deep house grooves", "Signature silver mirror photo installation with ring lights", "Polished aluminum riser tables without floral draping", 0),
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
        INSERT INTO events (id, title, event_type, city, event_date, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (e_id, "Sunlit Monsoon Community Harvest Festival", "community", "Pune", "2026-11-15", 400, 80000000, "INR", 1000, 1, now_str))

    sc_e_id = "sc-ecofest-v1"
    conn.execute("""
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
    """, (sc_e_id, e_id, 1, "Community Master Plan", 400, 80000000, now_str))

    eco_items = [
        ("item-e-venue", sc_e_id, "Venue & Space", "Model Botanical Gardens Open Amphitheatre", "FIXED", 15000000, 1, 0, "APPROVED", 15000000, "2026-10-20", "Municipal civic permit paid"),
        ("item-e-catering", sc_e_id, "Catering", "Organic Farm-to-Table Millet Feast", "PER_CAPITA", 60000, 1, 500, "QUOTED", 0, "2026-11-01", "Locally harvested ingredients"),
        ("item-e-waste", sc_e_id, "Eco Logistics", "Zero-Waste Compostable Tableware & Sorting Hub", "STEP_TIERED", 250000, 100, 1800, "APPROVED", 1000000, "2026-10-28", "1 waste hub per 100 attendees"),
        ("item-e-sound", sc_e_id, "Entertainment", "Solar-Powered Acoustic Soundstage", "FIXED", 8500000, 1, 1800, "APPROVED", 3000000, "2026-11-02", "Battery storage included"),
        ("item-e-workshops", sc_e_id, "Activities", "Pottery & Seed Bomb Community Workshops", "STEP_TIERED", 150000, 50, 1800, "ESTIMATED", 0, None, "1 facilitator per 50 participants"),
    ]
    conn.executemany("""
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, paid_amount_paise, deposit_due_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_items)

    eco_commitments = [
        ("com-e-catering", e_id, "Catering", "Kisan Organic Co-op", "QUOTED", 25200000, 0, "2026-11-01", "Will fresh banana leaf platters require additional washing water stations?", "Reviewing quote for 400 community members.", "Quote: ₹600/plate for 400 attendees", 0),
    ]
    conn.executemany("""
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_commitments)

    eco_tasks = [
        ("task-e-1", e_id, "T-14 Days", "Confirm Composting Partner & Waste Pickup Route", "Sustainability Officer", "CRITICAL", "PENDING", 0, "2026-11-01"),
        ("task-e-2", e_id, "T-7 Days", "Lock Final Community RSVPs for Meal Preparation", "RSVP Lead", "CRITICAL", "PENDING", 1, "2026-11-08"),
        ("task-e-3", e_id, "T-1 Day", "Solar Inverter Full Load Test & Shade Canopies", "Stage Tech Lead", "HIGH", "PENDING", 0, "2026-11-14"),
    ]
    conn.executemany("""
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
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
        ("th-e-1", e_id, "Sunlit Monsoon Canopy", "Earthy terracotta hues and lush banana leaf greens", json.dumps(["#2D5A27", "#C89D7C", "#F4F1EA", "#5C4033"]), "Damp petrichor scent with soothing acoustic bamboo flutes", "Mass collective seed-bomb throwing ceremony at sunset", "Repurposed jute sacks for rustic display signage", 1),
        ("th-e-2", e_id, "Golden Harvest Fields", "Warm wheat and amber celebratory atmosphere", json.dumps(["#D97706", "#FBBF24", "#78350F", "#FEF3C7"]), "Freshly toasted grain scent with joyful brass dhol accents", "Community harvest grain mandala created collectively", "Dried wild grasses as stage decor instead of fresh cut flowers", 0),
        ("th-e-3", e_id, "Earth & Sky Open Air", "Vibrant ultramarine blues with crisp cotton white drapes", json.dumps(["#1E3A8A", "#60A5FA", "#F8FAFC", "#047857"]), "Fresh morning breeze aroma with live sarod melodies", "Unfurling of the giant community painted canvas banner", "Upcycled fabric banners created by school volunteers", 0),
    ]
    conn.executemany("""
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, eco_themes)

    conn.execute("""
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (e_id, now_str, "INITIALIZE_EVENT", "Created baseline event with 5 line items and 10% contingency reserve", None, "Plan A (400 guests)"))


def get_event_by_id(event_id: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        evt_row = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt_row:
            return None
        event = dict(evt_row)

        sc_row = conn.execute("SELECT * FROM scenarios WHERE event_id = ? AND status = 'ACTIVE';", (event_id,)).fetchone()
        scenario = dict(sc_row) if sc_row else None
        scenario_id = scenario["id"] if scenario else None

        items = []
        if scenario_id:
            i_rows = conn.execute("SELECT * FROM budget_items WHERE scenario_id = ?;", (scenario_id,)).fetchall()
            items = [dict(r) for r in i_rows]

        v_rows = conn.execute("SELECT * FROM vendor_commitments WHERE event_id = ?;", (event_id,)).fetchall()
        vendors = [dict(r) for r in v_rows]

        t_rows = conn.execute("SELECT * FROM tasks WHERE event_id = ?;", (event_id,)).fetchall()
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

        log_rows = conn.execute("SELECT * FROM audit_logs WHERE event_id = ? ORDER BY id DESC LIMIT 20;", (event_id,)).fetchall()
        logs = [dict(r) for r in log_rows]

        return {
            "event": event,
            "active_scenario": scenario,
            "budget_items": items,
            "vendors": vendors,
            "tasks": tasks,
            "dependencies": dependencies,
            "runbook": runbook,
            "themes": themes,
            "audit_logs": logs,
        }


def list_events(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY created_at DESC;").fetchall()
        return [dict(r) for r in rows]


def commit_scenario_version(
    event_id: str,
    new_guests: int,
    new_budget_items: List[Dict[str, Any]],
    note: str,
    db_path: str = DB_FILE,
) -> Dict[str, Any]:
    """Transactionally creates a new immutable scenario version and writes an audit log."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection(db_path) as conn:
        evt = conn.execute("SELECT * FROM events WHERE id = ?;", (event_id,)).fetchone()
        if not evt:
            raise ValueError(f"Event {event_id} not found")

        old_version = evt["active_scenario_version"]
        new_version = old_version + 1
        new_sc_id = f"sc-{event_id}-v{new_version}"

        # Archive old active scenario
        conn.execute("UPDATE scenarios SET status = 'ARCHIVED' WHERE event_id = ? AND status = 'ACTIVE';", (event_id,))

        # Create new scenario
        conn.execute("""
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
        """, (new_sc_id, event_id, new_version, f"Scenario v{new_version} ({note})", new_guests, evt["target_budget_paise"], now_str))

        # Insert new budget items
        for idx, it in enumerate(new_budget_items):
            item_id = f"item-{event_id}-v{new_version}-{idx+1}"
            conn.execute("""
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, paid_amount_paise, deposit_due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                it.get("paid_amount_paise", 0),
                it.get("deposit_due_date"),
                it.get("notes"),
            ))

        # Update event's guest count and active version
        conn.execute("""
            UPDATE events SET guest_count = ?, active_scenario_version = ? WHERE id = ?;
        """, (new_guests, new_version, event_id))

        # Record audit log
        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (event_id, now_str, "COMMIT_SCENARIO", f"Promoted scenario v{new_version}: {note}", f"v{old_version}", f"v{new_version} ({new_guests} guests)"))

        conn.commit()

        return {"success": True, "new_version": new_version, "scenario_id": new_sc_id}

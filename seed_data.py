"""Fictional sample events used only when a database is empty."""

import json
import sqlite3
import time


def seed_demo_events(conn: sqlite3.Connection) -> None:
    """Seeds 3 realistic events idempotently on clean database initialization."""
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Royal Rajputana Heritage Wedding
    w_id = "evt-royal-heritage-wedding"
    conn.execute(
        """
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            w_id,
            "Royal Rajputana Heritage Wedding",
            "wedding",
            "Jaipur",
            "2026-11-25",
            "16:00",
            6.0,
            "Asia/Kolkata",
            "outdoor",
            250,
            120000000,
            "INR",
            1000,
            1,
            json.dumps({"dietary": "Strict Vegetarian + Jain", "style": "Regal Rajputana"}),
            now_str,
        ),
    )

    sc_w_id = "sc-wedding-v1"
    conn.execute(
        """
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            sc_w_id,
            w_id,
            1,
            "Baseline Master Plan",
            250,
            120000000,
            "outdoor",
            "2026-11-25",
            "ACTIVE",
            now_str,
        ),
    )

    wedding_items = [
        (
            "item-w-venue",
            sc_w_id,
            "Venue & Space",
            "Heritage Haveli Grand Lawn",
            "FIXED",
            30000000,
            1,
            1800,
            "APPROVED",
            10000000,
            10000000,
            "2026-10-30",
            None,
            "Includes 2 rehearsal buffer hours",
        ),
        (
            "item-w-catering",
            sc_w_id,
            "Catering",
            "Royal Rajasthani Banquet (Pure Veg + Jain)",
            "PER_CAPITA",
            140000,
            1,
            500,
            "QUOTED",
            5000000,
            0,
            "2026-11-10",
            None,
            "Live Dal Baati + Kulfi counter",
        ),
        (
            "item-w-tables",
            sc_w_id,
            "Seating & Tables",
            "Banqueting Tables with Velvet Runners",
            "STEP_TIERED",
            150000,
            8,
            1800,
            "ESTIMATED",
            0,
            0,
            None,
            None,
            "1 table per 8 guests",
        ),
        (
            "item-w-buffet",
            sc_w_id,
            "Dining Logistics",
            "Dual-Sided Buffet Service Lines",
            "STEP_TIERED",
            600000,
            75,
            1800,
            "ESTIMATED",
            0,
            0,
            None,
            None,
            "1 station per 75 guests",
        ),
        (
            "item-w-decor",
            sc_w_id,
            "Decor & Florals",
            "Floral Mandap & Brass Lanterns",
            "FIXED",
            18000000,
            1,
            1800,
            "APPROVED",
            5000000,
            5000000,
            "2026-11-01",
            None,
            "Locally sourced marigolds",
        ),
        (
            "item-w-audio",
            sc_w_id,
            "Entertainment",
            "Shehnai & Live Folk Ensemble",
            "FIXED",
            8000000,
            1,
            1800,
            "QUOTED",
            2000000,
            0,
            "2026-11-12",
            None,
            "Traditional afternoon entrance",
        ),
        (
            "item-w-photo",
            sc_w_id,
            "Photography",
            "Candid Cinema & Drone Highlights",
            "FIXED",
            12000000,
            1,
            1800,
            "APPROVED",
            4000000,
            4000000,
            "2026-11-05",
            None,
            "Dual shooter package",
        ),
        (
            "item-w-favors",
            sc_w_id,
            "Guest Favors",
            "Handcrafted Mithai & Scented Ittar Box",
            "PER_CAPITA",
            25000,
            1,
            1200,
            "ESTIMATED",
            0,
            0,
            None,
            None,
            "Return tokens for family",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        wedding_items,
    )

    wedding_commitments = [
        (
            "com-w-caterer",
            w_id,
            "Catering",
            "Shahi Dastarkhwan Kitchens",
            "QUOTED",
            36750000,
            5000000,
            0,
            "2026-11-05",
            "Are kitchen gas cylinder and live counter diesel generator charges billed separately?",
            "Hi Shahi Caterers, reviewing your ₹1,400/plate quote for 250 guests. Could you confirm if tasting sessions and waitstaff cutlery are all-inclusive?",
            "WhatsApp quote: ₹1,400 per plate + 5% GST for 250 pax",
            0,
            0,
            "idem-w-cat",
        ),
        (
            "com-w-venue",
            w_id,
            "Venue & Space",
            "Raj Mandir Haveli Estates",
            "APPROVED",
            35400000,
            10000000,
            10000000,
            "2026-10-30",
            "What is the overtime rate per 30 minutes after 11 PM?",
            "Deposit paid ₹1,00,000 via NEFT. Rehearsal buffer granted.",
            "Contract signed: ₹3,00,000 base + 18% GST",
            1,
            0,
            "idem-w-ven",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        wedding_commitments,
    )

    # Initial payment record for venue
    conn.execute(
        """
        INSERT INTO payments (id, event_id, commitment_id, budget_item_id, amount_paise, payment_method, reference_note, paid_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            "pay-w-venue-1",
            w_id,
            "com-w-venue",
            "item-w-venue",
            10000000,
            "NEFT",
            "Initial booking token payment",
            now_str,
        ),
    )

    wedding_tasks = [
        (
            "task-w-1",
            w_id,
            "T-30 Days",
            "Finalize Pure Veg & Jain Tasting Session",
            "Catering Lead",
            "CRITICAL",
            "DONE",
            1,
            "2026-10-25",
            None,
        ),
        (
            "task-w-2",
            w_id,
            "T-14 Days",
            "Confirm Banquet Floorplan & Stage Dimensions",
            "Family Lead",
            "HIGH",
            "PENDING",
            0,
            "2026-11-11",
            None,
        ),
        (
            "task-w-3",
            w_id,
            "T-7 Days",
            "Freeze Final Guest Roster & Seating Clusters",
            "Logistics Head",
            "CRITICAL",
            "PENDING",
            1,
            "2026-11-18",
            None,
        ),
        (
            "task-w-4",
            w_id,
            "T-1 Day",
            "Full Soundcheck & Generator Diesel Verification",
            "Audio Lead",
            "HIGH",
            "PENDING",
            0,
            "2026-11-24",
            None,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        wedding_tasks,
    )

    conn.execute(
        "INSERT INTO task_dependencies (parent_task_id, child_task_id) VALUES (?, ?);",
        ("task-w-1", "task-w-3"),
    )

    wedding_runbook = [
        (
            "rb-w-1",
            w_id,
            "15:00 - 16:30",
            "Doors Open / Welcome Drink Reception",
            "Catering bar active, musicians in position",
            "Host & Hospitality",
            "PENDING",
        ),
        (
            "rb-w-2",
            w_id,
            "16:30 - 18:00",
            "Baraat Arrival & Floral Vow Exchange",
            "Audio spotlight on Mandap, quiet generator backup",
            "Coordinator & MC",
            "PENDING",
        ),
        (
            "rb-w-3",
            w_id,
            "18:00 - 21:00",
            "Royal Banquet Dinner Service",
            "Open 4 buffet stations, replenish hot courses",
            "Catering Captain",
            "PENDING",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """,
        wedding_runbook,
    )

    wedding_themes = [
        (
            "th-w-1",
            w_id,
            "Rajputana Marigold Splendor",
            "Regal palace grandeur with brass urlis and velvet draping",
            json.dumps(["#9a3412", "#78350f", "#fef3c7", "#292524"]),
            "Fresh rosewater aroma and live shehnai notes",
            "Grand floral phoolon ki chaadar entry with cold pyrotechnics",
            "Locally grown marigolds instead of imported cut roses",
            1,
        ),
        (
            "th-w-2",
            w_id,
            "Pastel Botanical Conservatory",
            "Ethereal day-lit celebration with soft eucalyptus and sheer drapes",
            json.dumps(["#365314", "#dcfce7", "#fafaf9", "#78716c"]),
            "Crisp lavender fragrance with acoustic string ensemble",
            "Golden hour sunset vows framed by botanical floral ring",
            "Potted herbs as table runners that double as guest favors",
            0,
        ),
        (
            "th-w-3",
            w_id,
            "Midnight Starlight Pavilion",
            "Modern dramatic evening under a sparkling crystal canopy",
            json.dumps(["#1e1b4b", "#fde047", "#f4f4f5", "#475569"]),
            "Warm amber up-lighting and synchronized cello melodies",
            "First dance on low-lying cold dry-ice cloud layer",
            "Fairy light curtains against dark black fabric drops",
            0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        wedding_themes,
    )

    conn.execute(
        """
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """,
        (
            w_id,
            now_str,
            "INITIALIZE_EVENT",
            "Created baseline event with 8 line items and 10% contingency reserve",
            None,
            "Plan A (250 guests)",
        ),
    )

    # 2. Neo-Tokyo Cyberpunk 21st Birthday
    b_id = "evt-21st-birthday"
    conn.execute(
        """
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            b_id,
            "Neo-Tokyo Cyberpunk 21st Birthday",
            "birthday",
            "Bengaluru",
            "2026-12-05",
            "19:00",
            5.0,
            "Asia/Kolkata",
            "indoor",
            75,
            35000000,
            "INR",
            1000,
            1,
            json.dumps({"dietary": "Asian Street Food", "style": "Neon Cyber-Noir"}),
            now_str,
        ),
    )

    sc_b_id = "sc-birthday-v1"
    conn.execute(
        """
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            sc_b_id,
            b_id,
            1,
            "Birthday Master Plan",
            75,
            35000000,
            "indoor",
            "2026-12-05",
            "ACTIVE",
            now_str,
        ),
    )

    birthday_items = [
        (
            "item-b-venue",
            sc_b_id,
            "Venue & Space",
            "Indiranagar Rooftop Glasshouse",
            "FIXED",
            12000000,
            1,
            1800,
            "APPROVED",
            5000000,
            5000000,
            "2026-11-15",
            None,
            "Includes bar license",
        ),
        (
            "item-b-catering",
            sc_b_id,
            "Catering",
            "Pan-Asian Sliders & Molecular Mocktail Bar",
            "PER_CAPITA",
            120000,
            1,
            500,
            "QUOTED",
            2000000,
            0,
            "2026-11-20",
            None,
            "Bao buns + sushi rolls",
        ),
        (
            "item-b-neon",
            sc_b_id,
            "Decor & Lighting",
            "Custom UV Neon Tubes & LED Tunnel Entrance",
            "FIXED",
            4500000,
            1,
            1800,
            "APPROVED",
            2000000,
            2000000,
            "2026-11-18",
            None,
            "Rental with install",
        ),
        (
            "item-b-dj",
            sc_b_id,
            "Entertainment",
            "Synthwave DJ & Live Saxophone Accompaniment",
            "FIXED",
            3500000,
            1,
            1800,
            "QUOTED",
            1000000,
            0,
            "2026-11-25",
            None,
            "4-hour dance set",
        ),
        (
            "item-b-cake",
            sc_b_id,
            "Cake & Dessert",
            "Holographic Geometric Tier Cake",
            "FIXED",
            1500000,
            1,
            500,
            "ESTIMATED",
            0,
            0,
            None,
            None,
            "Dark chocolate + hazelnut praline",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        birthday_items,
    )

    birthday_commitments = [
        (
            "com-b-venue",
            b_id,
            "Venue & Space",
            "Glasshouse Rooftop Indiranagar",
            "APPROVED",
            14160000,
            5000000,
            5000000,
            "2026-11-15",
            "Does noise curfew at 11 PM require shifting to indoor lounge?",
            "Confirmed ₹1,20,000 base + 18% GST.",
            "Rooftop agreement signed",
            1,
            0,
            "idem-b-ven",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        birthday_commitments,
    )

    birthday_tasks = [
        (
            "task-b-1",
            b_id,
            "T-14 Days",
            "Confirm Mocktail Menu & Bar Stock Checklist",
            "Beverage Coordinator",
            "HIGH",
            "PENDING",
            1,
            "2026-11-21",
            None,
        ),
        (
            "task-b-2",
            b_id,
            "T-7 Days",
            "Custom Neon Entrance Signs Installation Test",
            "Lighting Lead",
            "MEDIUM",
            "PENDING",
            0,
            "2026-11-28",
            None,
        ),
        (
            "task-b-3",
            b_id,
            "T-1 Day",
            "Soundcheck & Playlist Alignment with DJ",
            "Host",
            "HIGH",
            "PENDING",
            0,
            "2026-12-04",
            None,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        birthday_tasks,
    )

    birthday_runbook = [
        (
            "rb-b-1",
            b_id,
            "19:00 - 20:30",
            "Guest Entry & Neon Photobooth Cocktails",
            "Bartenders live, ambient chillwave playlist",
            "Host & Greeter",
            "PENDING",
        ),
        (
            "rb-b-2",
            b_id,
            "20:30 - 21:30",
            "Cyberpunk Cake Reveal & Toast",
            "Dim overheads, UV strobes focused on stage",
            "MC",
            "PENDING",
        ),
        (
            "rb-b-3",
            b_id,
            "21:30 - 00:00",
            "High-Energy Synth DJ Set",
            "Bass boost active, late-night bao sliders replenish",
            "DJ & Floor Manager",
            "PENDING",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """,
        birthday_runbook,
    )

    birthday_themes = [
        (
            "th-b-1",
            b_id,
            "Neon Cyber-Noir",
            "Dark aesthetic pierced by vibrant magenta and cyan accents",
            json.dumps(["#1c1917", "#06b6d4", "#ec4899", "#a855f7"]),
            "Ozone haze aroma with deep 808 sub-bass rhythms",
            "Laser light show synchronized to the birthday countdown",
            "DIY UV string art photo backdrop instead of acrylic signs",
            1,
        ),
        (
            "th-b-2",
            b_id,
            "Retro 80s Arcade Synthwave",
            "Warm nostalgia with palm tree silhouettes and neon grids",
            json.dumps(["#2e1065", "#ea580c", "#e11d48", "#14b8a6"]),
            "Cotton candy sweetness scent with vintage Chiptune riffs",
            "Playable vintage arcade cabinet tournament for guests",
            "Projector grid mapping instead of custom printed backdrops",
            0,
        ),
        (
            "th-b-3",
            b_id,
            "Minimalist Industrial Chrome",
            "Sleek monochromatic elegance with silver accents",
            json.dumps(["#27272a", "#71717a", "#e4e4e7", "#ffffff"]),
            "Crisp bergamot scent and smooth deep house grooves",
            "Signature silver mirror photo installation with ring lights",
            "Polished aluminum riser tables without floral draping",
            0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        birthday_themes,
    )

    conn.execute(
        """
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """,
        (
            b_id,
            now_str,
            "INITIALIZE_EVENT",
            "Created baseline event with 5 line items and 10% contingency reserve",
            None,
            "Plan A (75 guests)",
        ),
    )

    # 3. Community Eco-Fest
    e_id = "evt-community-ecofest"
    conn.execute(
        """
        INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            e_id,
            "Sunlit Monsoon Community Harvest Festival",
            "community",
            "Pune",
            "2026-11-15",
            "10:00",
            8.0,
            "Asia/Kolkata",
            "outdoor",
            400,
            80000000,
            "INR",
            1000,
            1,
            json.dumps({"dietary": "Organic Millet Feast", "style": "Eco Terracotta"}),
            now_str,
        ),
    )

    sc_e_id = "sc-ecofest-v1"
    conn.execute(
        """
        INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        (
            sc_e_id,
            e_id,
            1,
            "Community Master Plan",
            400,
            80000000,
            "outdoor",
            "2026-11-15",
            "ACTIVE",
            now_str,
        ),
    )

    eco_items = [
        (
            "item-e-venue",
            sc_e_id,
            "Venue & Space",
            "Model Botanical Gardens Open Amphitheatre",
            "FIXED",
            15000000,
            1,
            0,
            "APPROVED",
            15000000,
            15000000,
            "2026-10-20",
            None,
            "Municipal civic permit paid",
        ),
        (
            "item-e-catering",
            sc_e_id,
            "Catering",
            "Organic Farm-to-Table Millet Feast",
            "PER_CAPITA",
            60000,
            1,
            500,
            "QUOTED",
            5000000,
            0,
            "2026-11-01",
            None,
            "Locally harvested ingredients",
        ),
        (
            "item-e-waste",
            sc_e_id,
            "Eco Logistics",
            "Zero-Waste Compostable Tableware & Sorting Hub",
            "STEP_TIERED",
            250000,
            100,
            1800,
            "APPROVED",
            1000000,
            1000000,
            "2026-10-28",
            None,
            "1 waste hub per 100 attendees",
        ),
        (
            "item-e-sound",
            sc_e_id,
            "Entertainment",
            "Solar-Powered Acoustic Soundstage",
            "FIXED",
            8500000,
            1,
            1800,
            "APPROVED",
            3000000,
            3000000,
            "2026-11-02",
            None,
            "Battery storage included",
        ),
        (
            "item-e-workshops",
            sc_e_id,
            "Activities",
            "Pottery & Seed Bomb Community Workshops",
            "STEP_TIERED",
            150000,
            50,
            1800,
            "ESTIMATED",
            0,
            0,
            None,
            None,
            "1 facilitator per 50 participants",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        eco_items,
    )

    eco_commitments = [
        (
            "com-e-catering",
            e_id,
            "Catering",
            "Kisan Organic Co-op",
            "QUOTED",
            25200000,
            5000000,
            0,
            "2026-11-01",
            "Will fresh banana leaf platters require additional washing water stations?",
            "Reviewing quote for 400 community members.",
            "Quote: ₹600/plate for 400 attendees",
            0,
            0,
            "idem-e-cat",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, deposit_required_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed, needs_reconfirmation, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        eco_commitments,
    )

    eco_tasks = [
        (
            "task-e-1",
            e_id,
            "T-14 Days",
            "Confirm Composting Partner & Waste Pickup Route",
            "Sustainability Officer",
            "CRITICAL",
            "PENDING",
            0,
            "2026-11-01",
            None,
        ),
        (
            "task-e-2",
            e_id,
            "T-7 Days",
            "Lock Final Community RSVPs for Meal Preparation",
            "RSVP Lead",
            "CRITICAL",
            "PENDING",
            1,
            "2026-11-08",
            None,
        ),
        (
            "task-e-3",
            e_id,
            "T-1 Day",
            "Solar Inverter Full Load Test & Shade Canopies",
            "Stage Tech Lead",
            "HIGH",
            "PENDING",
            0,
            "2026-11-14",
            None,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        eco_tasks,
    )

    eco_runbook = [
        (
            "rb-e-1",
            e_id,
            "10:00 - 12:00",
            "Solar Soundcheck & Artisan Stall Setup",
            "Power batteries synced, shade awnings deployed",
            "Operations Director",
            "PENDING",
        ),
        (
            "rb-e-2",
            e_id,
            "12:00 - 15:00",
            "Organic Millet Community Lunch Service",
            "Open 4 serving lines with volunteer marshals",
            "Catering Coordinator",
            "PENDING",
        ),
        (
            "rb-e-3",
            e_id,
            "15:00 - 18:00",
            "Acoustic Folk Performance & Seed Bomb Distribution",
            "Acoustic microphones live, distribution tables open",
            "MC & Volunteer Captain",
            "PENDING",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """,
        eco_runbook,
    )

    eco_themes = [
        (
            "th-e-1",
            e_id,
            "Sunlit Monsoon Canopy",
            "Earthy terracotta hues and lush banana leaf greens",
            json.dumps(["#365314", "#9a3412", "#fef3c7", "#44403c"]),
            "Damp petrichor scent with soothing acoustic bamboo flutes",
            "Mass collective seed-bomb throwing ceremony at sunset",
            "Repurposed jute sacks for rustic display signage",
            1,
        ),
        (
            "th-e-2",
            e_id,
            "Golden Harvest Fields",
            "Warm wheat and amber celebratory atmosphere",
            json.dumps(["#d97706", "#b45309", "#78350f", "#fef3c7"]),
            "Freshly toasted grain scent with joyful brass dhol accents",
            "Community harvest grain mandala created collectively",
            "Dried wild grasses as stage decor instead of fresh cut flowers",
            0,
        ),
        (
            "th-e-3",
            e_id,
            "Earth & Sky Open Air",
            "Vibrant ultramarine blues with crisp cotton white drapes",
            json.dumps(["#1e3a8a", "#0284c7", "#f8fafc", "#15803d"]),
            "Fresh morning breeze aroma with live sarod melodies",
            "Unfurling of the giant community painted canvas banner",
            "Upcycled fabric banners created by school volunteers",
            0,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """,
        eco_themes,
    )

    conn.execute(
        """
        INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?);
    """,
        (
            e_id,
            now_str,
            "INITIALIZE_EVENT",
            "Created baseline event with 5 line items and 10% contingency reserve",
            None,
            "Plan A (400 guests)",
        ),
    )

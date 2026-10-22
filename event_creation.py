"""Create an event and its initial budget, checklist, schedule, and themes atomically."""

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from database_setup import get_connection, get_db_path


def create_event(event_data: dict[str, Any], db_path: str | None = None) -> dict[str, Any]:
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
    if datetime.strptime(event_date, "%Y-%m-%d").date() < datetime.now(ZoneInfo(timezone)).date():
        raise ValueError("Choose today or a future event date in the event's timezone.")
    setting = event_data.get("setting", "outdoor")
    guests = int(event_data["guest_count"])
    target_budget_paise = int(event_data["target_budget_paise"])
    currency = event_data.get("currency", "INR")
    contingency_bps = int(event_data.get("contingency_bps", 1000))
    prefs = event_data.get("preferences") or {}

    with get_connection(target_path) as conn:
        conn.execute(
            """
            INSERT INTO events (id, title, event_type, city, event_date, start_time, duration_hours, timezone, setting, guest_count, target_budget_paise, currency, contingency_bps, active_scenario_version, preferences_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
        """,
            (
                event_id,
                title,
                event_type,
                city,
                event_date,
                start_time,
                duration_hours,
                timezone,
                setting,
                guests,
                target_budget_paise,
                currency,
                contingency_bps,
                json.dumps(prefs),
                now_str,
            ),
        )

        conn.execute(
            """
            INSERT INTO scenarios (id, event_id, version, name, guest_count, target_budget_paise, setting, event_date, status, created_at)
            VALUES (?, ?, 1, 'Initial Blueprint', ?, ?, ?, ?, 'ACTIVE', ?);
        """,
            (scenario_id, event_id, guests, target_budget_paise, setting, event_date, now_str),
        )

        # Personalize catering, tasks, and decor from user preferences
        dietary_pref = str(prefs.get("dietary", "")).lower()

        catering_title = "Main Celebration Dining Service"
        catering_notes = "Per-guest dining and beverage service"
        tasting_task_title = "Review Catering Menu & Finalize Food Tasting"

        if "jain" in dietary_pref or "pure veg" in dietary_pref or "vegetarian" in dietary_pref:
            catering_title = "Pure Vegetarian & Jain Celebration Banquet"
            catering_notes = (
                "Strict Pure Veg & Jain culinary service with root-vegetable restrictions observed"
            )
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
            (
                f"item-{uuid.uuid4().hex[:10]}",
                scenario_id,
                "Venue & Space",
                f"{title} Main Space",
                "FIXED",
                venue_budget,
                1,
                1800,
                "ESTIMATED",
                0,
                0,
                None,
                None,
                f"Initial space allocation for {setting} setting",
            ),
            (
                f"item-{uuid.uuid4().hex[:10]}",
                scenario_id,
                "Catering",
                catering_title,
                "PER_CAPITA",
                catering_unit,
                1,
                500,
                "ESTIMATED",
                0,
                0,
                None,
                None,
                catering_notes,
            ),
            (
                f"item-{uuid.uuid4().hex[:10]}",
                scenario_id,
                "Seating & Tables",
                "Guest Dining Tables & Chairs",
                "STEP_TIERED",
                150000,
                8,
                1800,
                "ESTIMATED",
                0,
                0,
                None,
                None,
                "1 table cluster per 8 guests",
            ),
            (
                f"item-{uuid.uuid4().hex[:10]}",
                scenario_id,
                "Decor & Styling",
                "Atmosphere & Floral Installation",
                "FIXED",
                decor_budget,
                1,
                1800,
                "ESTIMATED",
                0,
                0,
                None,
                None,
                f"{prefs.get('style', 'Theme-specific')} styling",
            ),
            (
                f"item-{uuid.uuid4().hex[:10]}",
                scenario_id,
                "Entertainment",
                "Audio System & Musical Performance",
                "FIXED",
                sound_budget,
                1,
                1800,
                "ESTIMATED",
                0,
                0,
                None,
                None,
                "Sound and stage presentation",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, deposit_required_paise, paid_amount_paise, deposit_due_date, superseded_by_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            items,
        )

        # Generate date-aware preparation tasks with lead time compression
        evt_dt = datetime.strptime(event_date, "%Y-%m-%d")
        today = datetime.now(ZoneInfo(timezone)).date()
        days_until = (evt_dt.date() - today).days

        if days_until > 30:
            tasks = [
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-30 Days",
                    "Lock Venue & Sign Base Contract",
                    "Lead Organizer",
                    "CRITICAL",
                    "PENDING",
                    0,
                    (evt_dt - timedelta(days=30)).strftime("%Y-%m-%d"),
                    None,
                ),
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-21 Days",
                    tasting_task_title,
                    "Host",
                    "HIGH",
                    "PENDING",
                    1,
                    (evt_dt - timedelta(days=21)).strftime("%Y-%m-%d"),
                    None,
                ),
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-7 Days",
                    "Freeze Guest Headcount & Seating Chart",
                    "Coordinator",
                    "CRITICAL",
                    "PENDING",
                    1,
                    (evt_dt - timedelta(days=7)).strftime("%Y-%m-%d"),
                    None,
                ),
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-1 Day",
                    "On-site Technical Soundcheck & Rehearsal",
                    "Floor Lead",
                    "HIGH",
                    "PENDING",
                    0,
                    (evt_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
                    None,
                ),
            ]
        else:
            # Compressed rapid schedule for short-notice celebrations
            tasks = [
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-5 Days (Rapid)",
                    "Secure Available Venue & Immediate Token",
                    "Lead Organizer",
                    "CRITICAL",
                    "PENDING",
                    0,
                    (evt_dt - timedelta(days=max(1, min(5, days_until)))).strftime("%Y-%m-%d"),
                    None,
                ),
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-3 Days (Rapid)",
                    f"Lock Headcount & {tasting_task_title}",
                    "Host",
                    "CRITICAL",
                    "PENDING",
                    1,
                    (evt_dt - timedelta(days=max(1, min(3, days_until)))).strftime("%Y-%m-%d"),
                    None,
                ),
                (
                    f"task-{uuid.uuid4().hex[:10]}",
                    event_id,
                    "T-1 Day",
                    "Confirm Vendor Arrival Windows & Power Setup",
                    "Coordinator",
                    "HIGH",
                    "PENDING",
                    0,
                    (evt_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
                    None,
                ),
            ]
        # Short-notice preparation cannot be scheduled before today.
        tasks = [
            tuple(
                max(row[8], today.isoformat()) if i == 8 else value for i, value in enumerate(row)
            )
            for row in tasks
        ]
        conn.executemany(
            """
            INSERT INTO tasks (id, event_id, timeframe, title, owner, priority, status, depends_on_guests, due_date, reverification_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            tasks,
        )

        # Generate minute-by-minute runbook cues respecting duration and midnight crossings
        try:
            start_hour, start_min = map(int, start_time.split(":"))
        except (ValueError, TypeError):
            start_hour, start_min = 15, 0

        duration_minutes = round(duration_hours * 60)

        def cue_time(offset):
            day, minute = divmod(start_hour * 60 + start_min + offset, 1440)
            hour, minute = divmod(minute, 60)
            return f"{hour:02d}:{minute:02d}" + (f" (+{day}d)" if day else "")

        t1_start = cue_time(0)
        t1_end = cue_time(round(duration_minutes * 0.3))
        t2_end = cue_time(round(duration_minutes * 0.7))
        t3_end = cue_time(duration_minutes)

        runbook = [
            (
                f"rb-{uuid.uuid4().hex[:10]}",
                event_id,
                f"{t1_start} - {t1_end}",
                "Guest Arrival & Welcome Hospitality",
                "Crew positions active, audio check confirmed",
                "Host & Hospitality Lead",
                "PENDING",
            ),
            (
                f"rb-{uuid.uuid4().hex[:10]}",
                event_id,
                f"{t1_end} - {t2_end}",
                "Main Celebration Moments & Keynote Ceremony",
                "Spotlights engaged, catering service lines live",
                "Coordinator & MC",
                "PENDING",
            ),
            (
                f"rb-{uuid.uuid4().hex[:10]}",
                event_id,
                f"{t2_end} - {t3_end}",
                "Dinner Banquet & Social Dancing",
                "Dessert replenish, late transport staging",
                "Catering Captain & Floor Lead",
                "PENDING",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO runbook_cues (id, event_id, time_slot, front_of_house, back_of_house, lead_role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
            runbook,
        )

        # Generate 3 curated themes
        themes = [
            (
                f"th-{uuid.uuid4().hex[:10]}",
                event_id,
                f"{title} Signature Warmth",
                "Timeless warmth with natural terracotta and brass accents",
                json.dumps(["#9a3412", "#c2410c", "#fef3c7", "#292524"]),
                "Subtle sandalwood scent with acoustic instrumentals",
                "Dramatic golden-hour welcome entrance moment",
                "Locally sourced fabric banners instead of custom printed plastics",
                1,
            ),
            (
                f"th-{uuid.uuid4().hex[:10]}",
                event_id,
                "Botanical Olive Serenity",
                "Organic foliage and crisp clean minimalist linens",
                json.dumps(["#365314", "#4d7c0f", "#f5f5f4", "#78716c"]),
                "Fresh eucalyptus notes with ambient lo-fi melodies",
                "Collective toast under illuminated botanical canopy",
                "Potted herbs and ferns that double as guest take-home gifts",
                0,
            ),
            (
                f"th-{uuid.uuid4().hex[:10]}",
                event_id,
                "Evening Starlight Elegance",
                "Dramatic deep charcoal tones and warm ambient candlelight",
                json.dumps(["#1c1917", "#d97706", "#f5f5f4", "#44403c"]),
                "Warm amber glow with smooth acoustic jazz",
                "Surprise coordinated sparkler farewell sequence",
                "Fairy light cascades against neutral wall drapes",
                0,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO themes (id, event_id, name, tagline, palette_hex, sensory_hook, signature_moment, diy_swap, is_selected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            themes,
        )

        # Audit log
        conn.execute(
            """
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                event_id,
                now_str,
                "CREATE_EVENT",
                f"Created event '{title}' for {guests} guests with {setting} setting",
                None,
                f"v1 ({currency} {target_budget_paise / 100:,.2f})",
            ),
        )

        conn.commit()
        return {"success": True, "event_id": event_id}

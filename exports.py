"""CSV and calendar download routes, including spreadsheet and calendar escaping."""

import csv
import io
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Response

from database import get_event_by_id
from engine import evaluate_event_solvency

router = APIRouter()


def _sanitize_csv_cell(val: Any) -> str:
    """Neutralizes CSV formula injection attacks by prefixing dangerous triggers with single quote."""
    s = str(val or "")
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


@router.get("/api/events/{event_id}/export.csv")
def export_csv(event_id: str):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    items = data["budget_items"]
    solvency = evaluate_event_solvency(
        target_budget_paise=evt["target_budget_paise"],
        contingency_bps=evt["contingency_bps"],
        line_items=items,
        guest_count=evt["guest_count"],
        payments=data["payments"],
        vendor_commitments=data["vendors"],
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["PLANQIRA EVENT FINANCIAL LEDGER"])
    writer.writerow(["Event Title", _sanitize_csv_cell(evt["title"])])
    writer.writerow(["Event Date", evt["event_date"]])
    writer.writerow(["Guest Headcount", evt["guest_count"]])
    writer.writerow(["Setting", evt["setting"]])
    writer.writerow(["Target Budget", f"{evt['currency']} {evt['target_budget_paise'] / 100:,.2f}"])
    writer.writerow(
        ["10% Contingency Reserve", f"{evt['currency']} {solvency['contingency_paise'] / 100:,.2f}"]
    )
    writer.writerow(
        [
            "Total Projected Spend",
            f"{evt['currency']} {solvency['total_projected_paise'] / 100:,.2f}",
        ]
    )
    writer.writerow(
        ["Total Paid Cash", f"{evt['currency']} {solvency['total_paid_paise'] / 100:,.2f}"]
    )
    writer.writerow(
        ["Total Outstanding", f"{evt['currency']} {solvency['total_outstanding_paise'] / 100:,.2f}"]
    )
    writer.writerow(
        ["Variance (Surplus/Deficit)", f"{evt['currency']} {solvency['variance_paise'] / 100:,.2f}"]
    )
    writer.writerow(["Solvency Status", solvency["solvency_status"]])
    writer.writerow([])

    writer.writerow(
        [
            "Category",
            "Item Name",
            "Pricing Formula",
            "Unit Cost",
            "Quantity",
            "Subtotal",
            "Tax Rate",
            "Tax Amount",
            "Total Cost",
            "Approval State",
            "Payment Status",
            "Deposit Required",
            "Paid Amount",
            "Notes",
        ]
    )

    for it in solvency["items"]:
        writer.writerow(
            [
                _sanitize_csv_cell(it["category"]),
                _sanitize_csv_cell(it["name"]),
                it["pricing_model"],
                f"{it['unit_cost_paise'] / 100:.2f}",
                it["quantity"],
                f"{it['subtotal_paise'] / 100:.2f}",
                f"{it['tax_rate_bps'] / 100:.2f}%",
                f"{it['tax_paise'] / 100:.2f}",
                f"{it['total_paise'] / 100:.2f}",
                it["approval_state"],
                it["calculated_payment_status"],
                f"{it.get('deposit_required_paise', 0) / 100:.2f}",
                f"{it['paid_amount_paise'] / 100:.2f}",
                _sanitize_csv_cell(it.get("notes") or ""),
            ]
        )

    csv_data = output.getvalue()
    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", evt["title"].lower()).strip("-")
    filename = f"planqira-ledger-{clean_slug}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _escape_ics_text(text: str) -> str:
    """Escapes commas, semicolons, and newlines per RFC-5545 specification."""
    if not text:
        return ""
    t = text.replace("\\", "\\\\")
    t = t.replace(",", "\\,")
    t = t.replace(";", "\\;")
    t = t.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return t


def _fold_ics_line(line: str) -> str:
    """Folds lines at 75 octets per RFC-5545 section 3.1."""
    chunks = []
    current = []
    byte_count = 0
    for character in line:
        width = len(character.encode("utf-8"))
        if byte_count + width > 75:
            chunks.append("".join(current))
            current = [" "]  # Continuation marker counts toward the 75-octet limit.
            byte_count = 1
        current.append(character)
        byte_count += width
    chunks.append("".join(current))
    return "\r\n".join(chunks)


@router.get("/api/events/{event_id}/export.ics")
def export_ics(event_id: str):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    tasks = data["tasks"]
    runbook = data["runbook"]

    clean_title = _escape_ics_text(evt["title"])
    now_stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    raw_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Planqira//Precision Operations Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Planqira - {clean_title}",
    ]

    # Convert tasks to VEVENT with RFC-5545 non-inclusive exclusive DTEND
    for t in tasks:
        try:
            task_dt = datetime.strptime(t["due_date"], "%Y-%m-%d")
            start_date_str = task_dt.strftime("%Y%m%d")
            # All-day end date must be exclusive next day per RFC-5545 3.6.1
            end_date_str = (task_dt + timedelta(days=1)).strftime("%Y%m%d")
        except (ValueError, TypeError, ZoneInfoNotFoundError):
            start_date_str = t["due_date"].replace("-", "")
            end_date_str = start_date_str

        uid = f"task-{t['id']}@planqira.local"
        summary = _escape_ics_text(f"[{t['timeframe']}] {t['title']}")
        desc = _escape_ics_text(
            f"Owner: {t['owner']} | Priority: {t['priority']} | Status: {t['status']}"
        )
        raw_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{start_date_str}",
                f"DTEND;VALUE=DATE:{end_date_str}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"STATUS:{'CONFIRMED' if t['status'] == 'DONE' else 'TENTATIVE'}",
                "END:VEVENT",
            ]
        )

    # Convert runbook cues respecting event start time, duration, and midnight crossings
    evt_date_str = evt["event_date"]  # YYYY-MM-DD
    start_time_str = evt.get("start_time", "15:00")
    duration = float(evt.get("duration_hours", 5.0))

    try:
        base_dt = datetime.strptime(f"{evt_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = base_dt + timedelta(hours=duration)
        event_zone = ZoneInfo(evt.get("timezone", "Asia/Kolkata"))
        main_start = base_dt.replace(tzinfo=event_zone).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        main_end = end_dt.replace(tzinfo=event_zone).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

        # Main celebration master event
        raw_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:event-main-{evt['id']}@planqira.local",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{main_start}",
                f"DTEND:{main_end}",
                f"SUMMARY:{clean_title} (Main Event)",
                f"LOCATION:{_escape_ics_text(evt['city'])} ({evt['setting']})",
                f"DESCRIPTION:{clean_title} celebration for {evt['guest_count']} guests.",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        pass

    try:
        e_dt = datetime.strptime(evt_date_str, "%Y-%m-%d")
        dt_start_date = e_dt.strftime("%Y%m%d")
        dt_end_date = (e_dt + timedelta(days=1)).strftime("%Y%m%d")
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        dt_start_date = evt_date_str.replace("-", "")
        dt_end_date = dt_start_date

    for rb in runbook:
        uid = f"runbook-{rb['id']}@planqira.local"
        summary = _escape_ics_text(f"[Runbook] {rb['time_slot']} - {rb['lead_role']}")
        desc = _escape_ics_text(f"Guest: {rb['front_of_house']} | Crew: {rb['back_of_house']}")
        timing_lines = [f"DTSTART;VALUE=DATE:{dt_start_date}", f"DTEND;VALUE=DATE:{dt_end_date}"]
        clock_times = re.findall(r"(\d{2}):(\d{2})(?: \(\+(\d+)d\))?", rb["time_slot"])
        if len(clock_times) == 2:
            zone = ZoneInfo(evt.get("timezone", "Asia/Kolkata"))
            start_clock, end_clock = clock_times

            def cue_datetime(clock, zone=zone):
                hour, minute, day = clock
                return datetime.strptime(evt_date_str, "%Y-%m-%d").replace(
                    hour=int(hour), minute=int(minute), tzinfo=zone
                ) + timedelta(days=int(day or 0))

            cue_start, cue_end = cue_datetime(start_clock), cue_datetime(end_clock)
            if cue_end <= cue_start:
                cue_end += timedelta(days=1)
            timing_lines = [
                f"DTSTART:{cue_start.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{cue_end.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            ]
        raw_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_stamp}",
                *timing_lines,
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                f"STATUS:{'CONFIRMED' if rb['status'] == 'COMPLETED' else 'TENTATIVE'}",
                "END:VEVENT",
            ]
        )

    raw_lines.append("END:VCALENDAR")
    # Apply RFC-5545 line folding at 75 octets
    folded_lines = [_fold_ics_line(line) for line in raw_lines]
    ics_data = "\r\n".join(folded_lines)
    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", evt["title"].lower()).strip("-")
    filename = f"planqira-schedule-{clean_slug}.ics"

    return Response(
        content=ics_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

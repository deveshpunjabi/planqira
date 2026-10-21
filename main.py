"""
Planqira — Event Decision, Commitment & Operations Platform
FastAPI operational control plane with strict Pydantic validation,
transactional scenario commits, payment recording, and RFC-compliant exporters.
"""

from contextlib import asynccontextmanager
import csv
from datetime import datetime, timedelta
import io
import os
import re
import time
from typing import Any, Dict, List, Literal, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_service import get_active_model, parse_vendor_quote_text
from database import (
    approve_vendor_quote_in_db,
    commit_scenario_version,
    create_event,
    create_incident,
    get_event_by_id,
    init_db,
    list_events,
    list_incidents,
    record_payment,
    revert_scenario_version,
    update_runbook_status,
    update_task_status,
)
from engine import (
    DependencyDAG,
    evaluate_event_solvency,
    simulate_scenario_impact,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database idempotently on startup
    init_db()
    yield


app = FastAPI(
    title="Planqira — Event Decision & Operations Platform",
    description="Deterministic Financial Solver, Decision Impact DAG & SQLite ACID Engine",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# REQUEST & RESPONSE SCHEMAS (Strict Pydantic Validation)
# =====================================================================

class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    event_type: str = Field(..., min_length=2, max_length=50)
    city: str = Field(..., min_length=2, max_length=80)
    event_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_time: str = Field("15:00", pattern=r"^\d{2}:\d{2}$")
    duration_hours: float = Field(5.0, ge=1.0, le=72.0)
    timezone: str = Field("Asia/Kolkata", min_length=2, max_length=60)
    setting: Literal["indoor", "outdoor", "hybrid"] = "outdoor"
    guest_count: int = Field(..., ge=1, le=10000)
    target_budget_paise: int = Field(..., gt=0)
    currency: str = Field("INR", min_length=3, max_length=3)
    contingency_bps: int = Field(1000, ge=0, le=5000)  # Default 10%
    preferences: Optional[Dict[str, Any]] = None


class SimulateRequest(BaseModel):
    new_guests: int = Field(..., ge=1, le=10000, description="Target simulated guest headcount")
    new_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    new_setting: Optional[Literal["indoor", "outdoor", "hybrid"]] = None
    base_version: Optional[int] = Field(None, ge=1)


class CommitScenarioRequest(BaseModel):
    new_guests: int = Field(..., ge=1, le=10000)
    new_budget_items: List[Dict[str, Any]]
    note: str = Field(..., min_length=3, max_length=200)
    base_version: int = Field(..., ge=1, description="Active version this proposal was simulated against")
    new_setting: Optional[Literal["indoor", "outdoor", "hybrid"]] = None
    new_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    invalidated_task_ids: Optional[List[str]] = None


class RevertScenarioRequest(BaseModel):
    target_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=200)


class QuoteParseRequest(BaseModel):
    raw_quote_text: str = Field(..., min_length=5, max_length=4000)


class ApproveQuoteRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=120)
    category: str = Field(..., min_length=1, max_length=60)
    items: List[Dict[str, Any]]
    advance_deposit_paise: int = Field(0, ge=0)
    deposit_due_date: Optional[str] = None
    notes: Optional[str] = None
    supersedes_item_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class RecordPaymentRequest(BaseModel):
    amount_paise: int = Field(..., gt=0)
    payment_method: str = Field("BANK_TRANSFER", max_length=50)
    reference_note: str = Field(..., min_length=2, max_length=200)
    commitment_id: Optional[str] = None
    budget_item_id: Optional[str] = None


class CreateIncidentRequest(BaseModel):
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=5, max_length=500)
    resolution: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    status: Literal["PENDING", "DONE", "NEEDS_REVIEW"]


class UpdateRunbookRequest(BaseModel):
    status: Literal["PENDING", "ACTIVE", "COMPLETED", "DELAYED"]


# =====================================================================
# REST ENDPOINTS
# =====================================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Planqira — Event Decision & Operations Platform",
        "version": "2.1.0",
        "model": get_active_model(),
        "has_server_key": bool(os.getenv("GEMINI_API_KEY")),
        "persistence": "SQLite ACID (planqira.db)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/events")
def get_events():
    return {"events": list_events()}


@app.post("/api/events")
def post_create_event(req: CreateEventRequest):
    try:
        result = create_event(req.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events/{event_id}")
def get_event(event_id: str):
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
    )

    return {
        "event": evt,
        "active_scenario": data["active_scenario"],
        "scenarios_history": data["scenarios_history"],
        "solvency": solvency,
        "vendors": data["vendors"],
        "tasks": data["tasks"],
        "dependencies": data["dependencies"],
        "runbook": data["runbook"],
        "themes": data["themes"],
        "payments": data["payments"],
        "incidents": data["incidents"],
        "audit_logs": data["audit_logs"],
    }


@app.post("/api/events/{event_id}/simulate")
def simulate_scenario(event_id: str, req: SimulateRequest):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    items = data["budget_items"]
    tasks = data["tasks"]
    deps = data["dependencies"]

    # Construct real dependency DAG
    dag = DependencyDAG()
    for t in tasks:
        parent_ids = [parent for parent, child in deps if child == t["id"]]
        trigger_params = []
        if t["depends_on_guests"]:
            trigger_params.append("guests")
        if "outdoor" in t["title"].lower() or "weather" in t["title"].lower():
            trigger_params.append("setting")
        if "date" in t["title"].lower() or "schedule" in t["title"].lower():
            trigger_params.append("date")

        dag.add_node(
            node_id=t["id"],
            node_type="TASK",
            title=t["title"],
            depends_on_ids=parent_ids,
            trigger_params=trigger_params,
            status=t["status"],
        )

    # Run side-by-side simulation
    sim_result = simulate_scenario_impact(
        baseline_guests=evt["guest_count"],
        new_guests=req.new_guests,
        target_budget_paise=evt["target_budget_paise"],
        contingency_bps=evt["contingency_bps"],
        line_items=items,
        dag=dag,
        baseline_date=evt["event_date"],
        new_date=req.new_date,
        baseline_setting=evt["setting"],
        new_setting=req.new_setting,
    )

    return sim_result


@app.post("/api/events/{event_id}/commit-scenario")
def commit_scenario(event_id: str, req: CommitScenarioRequest):
    try:
        result = commit_scenario_version(
            event_id=event_id,
            new_guests=req.new_guests,
            new_budget_items=req.new_budget_items,
            note=req.note,
            base_version=req.base_version,
            new_setting=req.new_setting,
            new_date=req.new_date,
            invalidated_task_ids=req.invalidated_task_ids,
        )
        return result
    except ValueError as e:
        # Check if stale proposal
        if "Stale proposal" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/{event_id}/revert-scenario")
def revert_scenario(event_id: str, req: RevertScenarioRequest):
    try:
        result = revert_scenario_version(
            event_id=event_id,
            target_version=req.target_version,
            reason=req.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/{event_id}/parse-quote")
def parse_quote(event_id: str, req: QuoteParseRequest):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    guests = data["event"]["guest_count"]
    parsed = parse_vendor_quote_text(req.raw_quote_text, guests)
    return parsed


@app.post("/api/events/{event_id}/approve-quote")
def approve_quote(event_id: str, req: ApproveQuoteRequest):
    try:
        result = approve_vendor_quote_in_db(
            event_id=event_id,
            vendor_name=req.vendor_name,
            category=req.category,
            items=req.items,
            advance_deposit_paise=req.advance_deposit_paise,
            deposit_due_date=req.deposit_due_date,
            notes=req.notes,
            supersedes_item_id=req.supersedes_item_id,
            idempotency_key=req.idempotency_key,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/{event_id}/record-payment")
def post_record_payment(event_id: str, req: RecordPaymentRequest):
    try:
        result = record_payment(
            event_id=event_id,
            amount_paise=req.amount_paise,
            payment_method=req.payment_method,
            reference_note=req.reference_note,
            commitment_id=req.commitment_id,
            budget_item_id=req.budget_item_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events/{event_id}/incidents")
def get_incidents(event_id: str):
    return {"incidents": list_incidents(event_id)}


@app.post("/api/events/{event_id}/incidents")
def post_incident(event_id: str, req: CreateIncidentRequest):
    try:
        result = create_incident(
            event_id=event_id,
            severity=req.severity,
            title=req.title,
            description=req.description,
            resolution=req.resolution,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/events/{event_id}/tasks/{task_id}")
def patch_task(event_id: str, task_id: str, req: UpdateTaskRequest):
    updated = update_task_status(task_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "status": req.status}


@app.patch("/api/events/{event_id}/runbook/{cue_id}")
def patch_runbook(event_id: str, cue_id: str, req: UpdateRunbookRequest):
    updated = update_runbook_status(cue_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Runbook cue not found")
    return {"success": True, "cue_id": cue_id, "status": req.status}


# =====================================================================
# VERIFIED FILE EXPORTERS (Protected against Formula Injection)
# =====================================================================

def _sanitize_csv_cell(val: Any) -> str:
    """Neutralizes CSV formula injection attacks by prefixing dangerous triggers with single quote."""
    s = str(val or "")
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


@app.get("/api/events/{event_id}/export.csv")
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
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["PLANQIRA EVENT FINANCIAL LEDGER"])
    writer.writerow(["Event Title", _sanitize_csv_cell(evt["title"])])
    writer.writerow(["Event Date", evt["event_date"]])
    writer.writerow(["Guest Headcount", evt["guest_count"]])
    writer.writerow(["Setting", evt["setting"]])
    writer.writerow(["Target Budget", f"{evt['currency']} {evt['target_budget_paise']/100:,.2f}"])
    writer.writerow(["10% Contingency Reserve", f"{evt['currency']} {solvency['contingency_paise']/100:,.2f}"])
    writer.writerow(["Total Projected Spend", f"{evt['currency']} {solvency['total_projected_paise']/100:,.2f}"])
    writer.writerow(["Total Paid Cash", f"{evt['currency']} {solvency['total_paid_paise']/100:,.2f}"])
    writer.writerow(["Total Outstanding", f"{evt['currency']} {solvency['total_outstanding_paise']/100:,.2f}"])
    writer.writerow(["Variance (Surplus/Deficit)", f"{evt['currency']} {solvency['variance_paise']/100:,.2f}"])
    writer.writerow(["Solvency Status", solvency["solvency_status"]])
    writer.writerow([])

    writer.writerow([
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
    ])

    for it in solvency["items"]:
        writer.writerow([
            _sanitize_csv_cell(it["category"]),
            _sanitize_csv_cell(it["name"]),
            it["pricing_model"],
            f"{it['unit_cost_paise']/100:.2f}",
            it["quantity"],
            f"{it['subtotal_paise']/100:.2f}",
            f"{it['tax_rate_bps']/100:.2f}%",
            f"{it['tax_paise']/100:.2f}",
            f"{it['total_paise']/100:.2f}",
            it["approval_state"],
            it["calculated_payment_status"],
            f"{it.get('deposit_required_paise', 0)/100:.2f}",
            f"{it['paid_amount_paise']/100:.2f}",
            _sanitize_csv_cell(it.get("notes") or ""),
        ])

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


@app.get("/api/events/{event_id}/export.ics")
def export_ics(event_id: str):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    tasks = data["tasks"]
    runbook = data["runbook"]

    clean_title = _escape_ics_text(evt["title"])
    now_stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Planqira//Precision Operations Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Planqira - {clean_title}",
    ]

    # Convert tasks to VEVENT
    for t in tasks:
        due_str = t["due_date"].replace("-", "")
        uid = f"task-{t['id']}@planqira.local"
        summary = _escape_ics_text(f"[{t['timeframe']}] {t['title']}")
        desc = _escape_ics_text(f"Owner: {t['owner']} | Priority: {t['priority']} | Status: {t['status']}")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{due_str}",
            f"DTEND;VALUE=DATE:{due_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"STATUS:{'CONFIRMED' if t['status'] == 'DONE' else 'TENTATIVE'}",
            "END:VEVENT",
        ])

    # Convert runbook cues respecting event start time, duration, and midnight crossings
    evt_date_str = evt["event_date"]  # YYYY-MM-DD
    start_time_str = evt.get("start_time", "15:00")
    duration = float(evt.get("duration_hours", 5.0))

    try:
        base_dt = datetime.strptime(f"{evt_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = base_dt + timedelta(hours=duration)
        main_start = base_dt.strftime("%Y%m%dT%H%M00")
        main_end = end_dt.strftime("%Y%m%dT%H%M00")

        # Main celebration master event
        lines.extend([
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
        ])
    except Exception:
        pass

    for rb in runbook:
        uid = f"runbook-{rb['id']}@planqira.local"
        summary = _escape_ics_text(f"[Runbook] {rb['time_slot']} - {rb['lead_role']}")
        desc = _escape_ics_text(f"Guest: {rb['front_of_house']} | Crew: {rb['back_of_house']}")
        dt_date = evt_date_str.replace("-", "")
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{dt_date}",
            f"DTEND;VALUE=DATE:{dt_date}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"STATUS:{'CONFIRMED' if rb['status'] == 'COMPLETED' else 'TENTATIVE'}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_data = "\r\n".join(lines)
    clean_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", evt["title"].lower()).strip("-")
    filename = f"planqira-schedule-{clean_slug}.ics"

    return Response(
        content=ics_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Mount static assets & web pages
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/homepage.html")


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("static/dashboard.html")


@app.get("/app")
def serve_app_alias():
    return FileResponse("static/dashboard.html")


@app.get("/index.html")
def serve_index_alias():
    return FileResponse("static/homepage.html")

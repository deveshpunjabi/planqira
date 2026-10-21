"""
Planqira — Autonomous Event Decision, Commitment & Operations Engine
FastAPI application with REST endpoints, CSV/ICS exports,
and static file serving.
"""

import csv
import io
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_service import parse_vendor_quote_text
from database import (
    commit_scenario_version,
    get_event_by_id,
    init_db,
    list_events,
    get_connection,
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
    version="2.0.0",
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

class SimulateRequest(BaseModel):
    new_guests: int = Field(..., ge=1, le=10000, description="Target simulated guest headcount")


class CommitScenarioRequest(BaseModel):
    new_guests: int = Field(..., ge=1, le=10000)
    new_budget_items: List[Dict[str, Any]]
    note: str = Field(..., max_length=200)


class QuoteParseRequest(BaseModel):
    raw_quote_text: str = Field(..., min_length=5, max_length=3000)


class ApproveQuoteRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    items: List[Dict[str, Any]]
    advance_deposit_paise: int = Field(0, ge=0)
    deposit_due_date: Optional[str] = None
    notes: Optional[str] = None


# =====================================================================
# REST ENDPOINTS
# =====================================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Planqira — Event Decision & Operations Platform",
        "version": "2.0.0",
        "has_server_key": bool(os.getenv("GEMINI_API_KEY")),
        "persistence": "SQLite ACID (planqira.db)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/events")
def get_events():
    return {"events": list_events()}


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
        "solvency": solvency,
        "vendors": data["vendors"],
        "tasks": data["tasks"],
        "dependencies": data["dependencies"],
        "runbook": data["runbook"],
        "themes": data["themes"],
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
        trigger_params = ["guests"] if t["depends_on_guests"] else []
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
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    scenario_id = data["active_scenario"]["id"]
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_connection() as conn:
        total_quote_paise = 0
        for it in req.items:
            unit = it.get("unit_cost_paise", 0)
            model = it.get("pricing_model", "FIXED")
            qty = data["event"]["guest_count"] if model == "PER_CAPITA" else 1
            total_quote_paise += unit * qty

            item_id = f"item-quote-{int(time.time()*1000)}"
            conn.execute("""
                INSERT INTO budget_items (id, scenario_id, category, name, pricing_model, unit_cost_paise, step_capacity, tax_rate_bps, approval_state, paid_amount_paise, deposit_due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?);
            """, (
                item_id,
                scenario_id,
                req.category,
                it["name"],
                model,
                unit,
                it.get("step_capacity", 1),
                it.get("tax_rate_bps", 0),
                req.advance_deposit_paise,
                req.deposit_due_date,
                req.notes,
            ))

        # Add vendor commitment record
        com_id = f"com-{int(time.time()*1000)}"
        conn.execute("""
            INSERT INTO vendor_commitments (id, event_id, category, vendor_name, approval_state, total_quote_paise, paid_amount_paise, deposit_due_date, hidden_fee_question, negotiation_script, raw_quote_text, is_reviewed)
            VALUES (?, ?, ?, ?, 'APPROVED', ?, ?, ?, ?, ?, ?, 1);
        """, (
            com_id,
            event_id,
            req.category,
            req.vendor_name,
            total_quote_paise,
            req.advance_deposit_paise,
            req.deposit_due_date,
            "Are kitchen fuel cylinders and generator diesel included?",
            f"Hi {req.vendor_name}, quote approved.",
            "Extracted & approved via Planqira",
        ))

        # Record audit log
        conn.execute("""
            INSERT INTO audit_logs (event_id, timestamp, action_type, description, previous_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (
            event_id,
            now_str,
            "APPROVE_VENDOR_QUOTE",
            f"Approved quote from {req.vendor_name} ({req.category})",
            "QUOTED",
            f"APPROVED (₹{total_quote_paise/100:,.2f})"
        ))

        conn.commit()

    return {"success": True, "message": f"Approved quote from {req.vendor_name} and recorded in ledger."}


# =====================================================================
# VERIFIED FILE EXPORTS
# =====================================================================

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

    # Metadata headers
    writer.writerow(["PLANQIRA EVENT FINANCIAL LEDGER"])
    writer.writerow(["Event Title", evt["title"]])
    writer.writerow(["Event Date", evt["event_date"]])
    writer.writerow(["Guest Headcount", evt["guest_count"]])
    writer.writerow(["Target Budget", f"{evt['currency']} {evt['target_budget_paise']/100:,.2f}"])
    writer.writerow(["10% Contingency Reserve", f"{evt['currency']} {solvency['contingency_paise']/100:,.2f}"])
    writer.writerow(["Total Projected Spend", f"{evt['currency']} {solvency['total_projected_paise']/100:,.2f}"])
    writer.writerow(["Variance (Surplus/Deficit)", f"{evt['currency']} {solvency['variance_paise']/100:,.2f}"])
    writer.writerow(["Solvency Status", solvency["solvency_status"]])
    writer.writerow([])

    # Table header
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
        "Paid Amount",
        "Notes",
    ])

    for it in solvency["items"]:
        writer.writerow([
            it["category"],
            it["name"],
            it["pricing_model"],
            f"{it['unit_cost_paise']/100:.2f}",
            it["quantity"],
            f"{it['subtotal_paise']/100:.2f}",
            f"{it['tax_rate_bps']/100:.2f}%",
            f"{it['tax_paise']/100:.2f}",
            f"{it['total_paise']/100:.2f}",
            it["approval_state"],
            it["calculated_payment_status"],
            f"{it['paid_amount_paise']/100:.2f}",
            it.get("notes") or "",
        ])

    csv_data = output.getvalue()
    filename = f"planqira-ledger-{evt['title'].lower().replace(' ', '-')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/events/{event_id}/export.ics")
def export_ics(event_id: str):
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    tasks = data["tasks"]
    runbook = data["runbook"]

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Planqira//Event Operations Engine//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Planqira - {evt['title']}",
    ]

    # Convert tasks to VEVENT
    for t in tasks:
        due = t["due_date"].replace("-", "")
        uid = f"task-{t['id']}@planqira.local"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}",
            f"DTSTART;VALUE=DATE:{due}",
            f"DTEND;VALUE=DATE:{due}",
            f"SUMMARY:[{t['timeframe']}] {t['title']}",
            f"DESCRIPTION:Owner: {t['owner']} | Priority: {t['priority']} | Status: {t['status']}",
            f"STATUS:{'CONFIRMED' if t['status'] == 'DONE' else 'TENTATIVE'}",
            "END:VEVENT",
        ])

    # Convert runbook cues on event date
    evt_date_str = evt["event_date"].replace("-", "")
    for rb in runbook:
        uid = f"runbook-{rb['id']}@planqira.local"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}",
            f"DTSTART;VALUE=DATE:{evt_date_str}",
            f"DTEND;VALUE=DATE:{evt_date_str}",
            f"SUMMARY:[Runbook] {rb['time_slot']} - {rb['lead_role']}",
            f"DESCRIPTION:Guest: {rb['front_of_house']} | Crew: {rb['back_of_house']}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_data = "\r\n".join(lines)
    filename = f"planqira-schedule-{evt['title'].lower().replace(' ', '-')}.ics"

    return Response(
        content=ics_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Mount static files & root page
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

"""
Planqira — Event Decision, Commitment & Operations Platform
FastAPI operational control plane with strict Pydantic validation,
transactional scenario commits, payment recording, and RFC-compliant exporters.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
    build_task_dag,
    evaluate_event_solvency,
    simulate_scenario_impact,
)
from exports import router as export_router
from schemas import (
    ApproveQuoteRequest,
    CommitScenarioRequest,
    CreateEventRequest,
    CreateIncidentRequest,
    QuoteParseRequest,
    RecordPaymentRequest,
    RevertScenarioRequest,
    SimulateRequest,
    UpdateRunbookRequest,
    UpdateTaskRequest,
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
    allow_origins=[
        origin.strip()
        for origin in os.getenv("PLANQIRA_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/events"):
        response.headers["Cache-Control"] = "no-store"
    return response


# =====================================================================
# REST ENDPOINTS
# =====================================================================


def _mutation_error(error: ValueError) -> HTTPException:
    """Keep conflict responses consistent across mutation endpoints."""
    message = str(error)
    conflict = "Stale proposal" in message or "Idempotency conflict" in message
    return HTTPException(status_code=409 if conflict else 400, detail=message)


@app.exception_handler(Exception)
async def unexpected_error(request, error):
    logging.getLogger(__name__).error("Unhandled request error", exc_info=error)
    return JSONResponse(
        status_code=500, content={"detail": "Unable to complete this request. Please try again."}
    )


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
    except ValueError as e:
        raise _mutation_error(e) from e


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
        payments=data["payments"],
        vendor_commitments=data["vendors"],
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

    dag = build_task_dag(tasks, deps)

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
        # Server-owned authoritative scenario calculation (P0 fix: prevent client cost forgery)
        result = commit_scenario_version(
            event_id=event_id,
            new_guests=req.new_guests,
            note=req.note,
            base_version=req.base_version,
            new_setting=req.new_setting,
            new_date=req.new_date,
            invalidated_task_ids=req.invalidated_task_ids,
        )
        return result
    except ValueError as e:
        raise _mutation_error(e) from e


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
        raise _mutation_error(e) from e


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
            items=[item.model_dump() for item in req.items],
            advance_deposit_paise=req.advance_deposit_paise,
            deposit_due_date=req.deposit_due_date,
            notes=req.notes,
            supersedes_item_id=req.supersedes_item_id,
            supersedes_item_ids=req.supersedes_item_ids,
            idempotency_key=req.idempotency_key,
        )
        return result
    except ValueError as e:
        raise _mutation_error(e) from e


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
            idempotency_key=req.idempotency_key,
        )
        return result
    except ValueError as e:
        raise _mutation_error(e) from e


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
        raise _mutation_error(e) from e


@app.patch("/api/events/{event_id}/tasks/{task_id}")
def patch_task(event_id: str, task_id: str, req: UpdateTaskRequest):
    updated = update_task_status(task_id, req.status, event_id=event_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "status": req.status}


@app.patch("/api/events/{event_id}/runbook/{cue_id}")
def patch_runbook(event_id: str, cue_id: str, req: UpdateRunbookRequest):
    updated = update_runbook_status(cue_id, req.status, event_id=event_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Runbook cue not found")
    return {"success": True, "cue_id": cue_id, "status": req.status}


# =====================================================================
# VERIFIED FILE EXPORTERS (Protected against Formula Injection)
# =====================================================================

app.include_router(export_router)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount static assets & web pages with absolute path resilience
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "homepage.html"))


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/app")
def serve_app_alias():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/index.html")
def serve_index_alias():
    return FileResponse(os.path.join(STATIC_DIR, "homepage.html"))

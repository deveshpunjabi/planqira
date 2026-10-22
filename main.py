"""
Planqira — Event Decision, Commitment & Operations Platform
FastAPI operational control plane with strict Pydantic validation,
transactional scenario commits, payment recording, and RFC-compliant exporters.
Hardened with enterprise security headers, rate limiting, and response compression.
"""

import logging
import os
import re
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

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

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("planqira")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database idempotently on startup
    init_db()
    yield


app = FastAPI(
    title="Planqira — Event Decision & Operations Platform",
    description="Deterministic Financial Solver, Decision Impact DAG & SQLite ACID Engine with Enterprise Security Hardening",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =====================================================================
# SECURITY & PERFORMANCE MIDDLEWARE
# =====================================================================

# 1. Payload Size Limiter Middleware (DoS protection, max 2MB)
MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024  # 2MB


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={"detail": "Payload Too Large: maximum allowed request body is 2MB."},
                    )
            except ValueError:
                pass
        return await call_next(request)


# 2. Sliding Window In-Memory Rate Limiter (Brute-force / Flood mitigation)
class SlidingWindowRateLimiter:
    """Thread-safe, sliding-window in-memory rate limiter with RFC-6585 compliance."""

    def __init__(self, default_limit: int = 200, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, client_id: str, limit: int | None = None) -> tuple[bool, int, int]:
        max_limit = limit or self.default_limit
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            calls = self._history[client_id]
            calls = [t for t in calls if t > cutoff]
            if len(calls) >= max_limit:
                reset_after = max(1, int(self.window_seconds - (now - calls[0])))
                self._history[client_id] = calls
                return False, 0, reset_after
            calls.append(now)
            self._history[client_id] = calls
            remaining = max(0, max_limit - len(calls))
            return True, remaining, self.window_seconds


rate_limiter = SlidingWindowRateLimiter(default_limit=200, window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Whitelist static assets, landing pages, health checks, and API docs from rate limiting
        if (
            path.startswith("/static/")
            or path in ("/", "/dashboard", "/app", "/index.html", "/api/health", "/docs", "/redoc", "/openapi.json")
        ):
            return await call_next(request)

        # Bypass rate limiting in automated testing environments or local testclients
        client_host = request.client.host if request.client else "testclient"
        if os.getenv("PLANQIRA_TESTING") == "1" or client_host in ("testclient", "localhost"):
            return await call_next(request)

        # Stricter ceiling for heavy simulation and cognitive quote extraction routes
        effective_limit = 60 if ("parse-quote" in path or "simulate" in path) else 200
        allowed, remaining, reset_time = rate_limiter.check(client_host, limit=effective_limit)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too Many Requests: operational rate limit exceeded. Please retry later."},
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(effective_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + reset_time)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(effective_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# 3. Comprehensive Security Headers Middleware (OWASP / Mozilla Observatory Compliant)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Fine-grained cache control policies
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        elif request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400, immutable"

        return response


# Register middlewares in optimal order (outer layer executed first on request)
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# GZip Compression for efficient wire transfers (over 500 bytes)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS Policy Configuration
configured_origins = [
    origin.strip()
    for origin in os.getenv("PLANQIRA_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
default_safe_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]
origins = configured_origins if configured_origins else (["*"] if os.getenv("VERCEL") else default_safe_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With", "Idempotency-Key", "X-API-Key"],
    max_age=600,
)


# =====================================================================
# AUTHENTICATION & ACCESS VERIFICATION
# =====================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_access(api_key: str | None = Security(api_key_header)) -> bool:
    """
    Optional enterprise API authentication layer.
    If PLANQIRA_API_KEY is configured in the environment, mutation endpoints require
    a matching X-API-Key header. If unconfigured, the application runs in permissive demo mode.
    """
    expected_key = os.getenv("PLANQIRA_API_KEY", "").strip()
    if not expected_key:
        return True
    if not api_key or api_key.strip() != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: valid X-API-Key header required for operational mutations.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True


def _validate_id(identifier: str, field_name: str = "identifier") -> None:
    """Validates alphanumeric route parameters to prevent directory traversal or SQL anomalies."""
    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", identifier):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format: must be 1-64 alphanumeric or hyphen/underscore characters.",
        )


def _mutation_error(error: ValueError) -> HTTPException:
    """Keep conflict responses consistent across mutation endpoints."""
    message = str(error)
    conflict = "Stale proposal" in message or "Idempotency conflict" in message
    return HTTPException(status_code=409 if conflict else 400, detail=message)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    logger.error("Unhandled request error on %s %s", request.method, request.url.path, exc_info=error)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Unable to complete this request. Please try again."},
    )


# =====================================================================
# REST ENDPOINTS
# =====================================================================


@app.get("/api/health")
def health():
    """Health check endpoint providing platform diagnostics and operational readiness."""
    return {
        "status": "ok",
        "app": "Planqira — Event Decision & Operations Platform",
        "version": "2.1.0",
        "model": get_active_model(),
        "has_server_key": bool(os.getenv("GEMINI_API_KEY")),
        "persistence": "SQLite ACID (planqira.db)",
        "security": {
            "csp_enabled": True,
            "hsts_enabled": True,
            "rate_limiter_active": True,
            "auth_mode": "ENFORCED" if bool(os.getenv("PLANQIRA_API_KEY")) else "OPEN_DEMO",
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/api/events")
def get_events():
    """Returns the list of all registered celebration events."""
    return {"events": list_events()}


@app.post("/api/events")
def post_create_event(req: CreateEventRequest, _authorized: bool = Depends(verify_api_access)):
    """Creates a new celebration event with initial financial blueprint, timeline, runbook, and themes."""
    try:
        result = create_event(req.model_dump())
        return result
    except ValueError as e:
        raise _mutation_error(e) from e


@app.get("/api/events/{event_id}")
def get_event(event_id: str):
    """Retrieves authoritative event details, active scenario, solvency ledger, and operational status."""
    _validate_id(event_id, "event_id")
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
    """Calculates side-by-side what-if impact on budget, contingency reserve, and task DAGs."""
    _validate_id(event_id, "event_id")
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    evt = data["event"]
    items = data["budget_items"]
    tasks = data["tasks"]
    deps = data["dependencies"]

    dag = build_task_dag(tasks, deps)

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
def commit_scenario(
    event_id: str, req: CommitScenarioRequest, _authorized: bool = Depends(verify_api_access)
):
    """Atomically commits a simulated scenario proposal with server-owned authoritative calculation."""
    _validate_id(event_id, "event_id")
    try:
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
def revert_scenario(
    event_id: str, req: RevertScenarioRequest, _authorized: bool = Depends(verify_api_access)
):
    """Restores a previous historical scenario revision cleanly and non-destructively."""
    _validate_id(event_id, "event_id")
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
    """Extracts structured line items and hidden fee questions from raw vendor quotes."""
    _validate_id(event_id, "event_id")
    data = get_event_by_id(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")

    guests = data["event"]["guest_count"]
    parsed = parse_vendor_quote_text(req.raw_quote_text, guests)
    return parsed


@app.post("/api/events/{event_id}/approve-quote")
def approve_quote(
    event_id: str, req: ApproveQuoteRequest, _authorized: bool = Depends(verify_api_access)
):
    """Approves a parsed vendor quote, binds commitment contracts, and replaces superseded items."""
    _validate_id(event_id, "event_id")
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
def post_record_payment(
    event_id: str, req: RecordPaymentRequest, _authorized: bool = Depends(verify_api_access)
):
    """Records an actual cash payment in the double-entry immutable ledger with idempotency deduplication."""
    _validate_id(event_id, "event_id")
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
    """Retrieves operational incidents for the event day."""
    _validate_id(event_id, "event_id")
    return {"incidents": list_incidents(event_id)}


@app.post("/api/events/{event_id}/incidents")
def post_incident(
    event_id: str, req: CreateIncidentRequest, _authorized: bool = Depends(verify_api_access)
):
    """Logs an operational incident on event day with severity rating and resolution action."""
    _validate_id(event_id, "event_id")
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
def patch_task(
    event_id: str,
    task_id: str,
    req: UpdateTaskRequest,
    _authorized: bool = Depends(verify_api_access),
):
    """Updates preparation task status within the topological DAG."""
    _validate_id(event_id, "event_id")
    _validate_id(task_id, "task_id")
    updated = update_task_status(task_id, req.status, event_id=event_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "status": req.status}


@app.patch("/api/events/{event_id}/runbook/{cue_id}")
def patch_runbook(
    event_id: str,
    cue_id: str,
    req: UpdateRunbookRequest,
    _authorized: bool = Depends(verify_api_access),
):
    """Updates minute-by-minute execution status for a runbook cue."""
    _validate_id(event_id, "event_id")
    _validate_id(cue_id, "cue_id")
    updated = update_runbook_status(cue_id, req.status, event_id=event_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Runbook cue not found")
    return {"success": True, "cue_id": cue_id, "status": req.status}


# =====================================================================
# VERIFIED FILE EXPORTERS & STATIC ASSETS
# =====================================================================

app.include_router(export_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

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

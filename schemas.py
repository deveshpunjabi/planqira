"""Validated API input contracts; no database or web application dependencies."""

import re
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class SanitizedModel(BaseModel):
    """Base model enforcing null-byte protection and basic XSS script tag stripping on inputs."""

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def sanitize_input(cls, v: Any) -> Any:
        if isinstance(v, str):
            if "\x00" in v:
                raise ValueError("Null bytes are strictly prohibited in request inputs.")
            # Neutralize script tags for defense-in-depth against stored XSS
            cleaned = re.sub(
                r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", v, flags=re.IGNORECASE | re.DOTALL
            )
            return cleaned.strip()
        return v


class CalendarRequest(SanitizedModel):
    @field_validator("event_date", "new_date", "deposit_due_date", check_fields=False)
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("start_time", check_fields=False)
    @classmethod
    def valid_time(cls, value):
        datetime.strptime(value, "%H:%M")
        return value

    @field_validator("timezone", check_fields=False)
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Choose a valid IANA timezone, for example Asia/Kolkata") from None
        return value


class CreateEventRequest(CalendarRequest):
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
    currency: Literal["INR"] = "INR"
    contingency_bps: int = Field(1000, ge=0, le=5000)  # Default 10%
    preferences: dict[str, Any] | None = None


class SimulateRequest(CalendarRequest):
    new_guests: int = Field(..., ge=1, le=10000, description="Target simulated guest headcount")
    new_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    new_setting: Literal["indoor", "outdoor", "hybrid"] | None = None
    base_version: int | None = Field(None, ge=1)


class CommitScenarioRequest(CalendarRequest):
    new_guests: int = Field(..., ge=1, le=10000)
    new_budget_items: list[dict[str, Any]] | None = None
    note: str = Field(..., min_length=3, max_length=200)
    base_version: int = Field(
        ..., ge=1, description="Active version this proposal was simulated against"
    )
    new_setting: Literal["indoor", "outdoor", "hybrid"] | None = None
    new_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    invalidated_task_ids: list[str] | None = None


class RevertScenarioRequest(SanitizedModel):
    target_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=3, max_length=200)


class QuoteParseRequest(SanitizedModel):
    raw_quote_text: str = Field(..., min_length=5, max_length=4000)


class QuoteItem(SanitizedModel):
    name: str = Field(min_length=1, max_length=200)
    pricing_model: Literal["FIXED", "PER_CAPITA", "STEP_TIERED"]
    unit_cost_paise: int = Field(ge=0, strict=True)
    step_capacity: int = Field(1, ge=1, strict=True)
    tax_rate_bps: int = Field(0, ge=0, le=10000, strict=True)
    is_tax_inclusive: bool = False
    notes: str | None = Field(None, max_length=4000)


class ApproveQuoteRequest(CalendarRequest):
    vendor_name: str = Field(..., min_length=1, max_length=120)
    category: str = Field(..., min_length=1, max_length=60)
    items: list[QuoteItem] = Field(min_length=1, max_length=100)
    advance_deposit_paise: int = Field(0, ge=0)
    deposit_due_date: str | None = None
    notes: str | None = None
    supersedes_item_id: str | None = None
    supersedes_item_ids: list[str] | None = None
    idempotency_key: str | None = None


class RecordPaymentRequest(SanitizedModel):
    amount_paise: int = Field(..., gt=0)
    payment_method: str = Field("BANK_TRANSFER", max_length=50)
    reference_note: str = Field(..., min_length=2, max_length=200)
    commitment_id: str | None = None
    budget_item_id: str | None = None
    idempotency_key: str | None = None


class CreateIncidentRequest(SanitizedModel):
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=5, max_length=500)
    resolution: str | None = None


class UpdateTaskRequest(SanitizedModel):
    status: Literal["PENDING", "DONE", "NEEDS_REVIEW"]


class UpdateRunbookRequest(SanitizedModel):
    status: Literal["PENDING", "ACTIVE", "COMPLETED", "DELAYED"]

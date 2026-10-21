"""
Planqira AI Cognitive Services
Integrates with Gemini 2.5 Flash via google-genai SDK for:
1. Event Blueprint & Personalized Creative Concept Generation
2. Unstructured Vendor Quote Parsing (WhatsApp/Email -> Structured Line Items + GST)
3. Deficit Cure & Counter-Negotiation Advisory
Features a transparent offline heuristic fallback that explicitly discloses simulated state.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Check if google-genai is available
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False


# Default to Google DeepMind's Gemma 4 (gemma-4-26b-a4b-it / gemma-4-31b-it) or Gemini model
DEFAULT_MODEL = os.getenv("AI_MODEL", os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it"))


def get_active_model() -> str:
    """Returns the configured model identifier."""
    return os.getenv("AI_MODEL", os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it"))


class ExtractedLineItem(BaseModel):
    name: str
    pricing_model: str = Field(description="Must be 'FIXED', 'PER_CAPITA', or 'STEP_TIERED'")
    unit_cost_paise: int
    step_capacity: int = 1
    tax_rate_bps: int = Field(0, description="1800 for 18% GST")


class ParsedQuoteResult(BaseModel):
    vendor_name: str
    category: str
    extracted_items: List[ExtractedLineItem]
    advance_deposit_paise: int
    deposit_due_date: Optional[str] = None
    flagged_clauses: List[str]
    suggested_negotiation_reply: str


def parse_vendor_quote_text(raw_quote_text: str, current_guest_count: int = 150) -> Dict[str, Any]:
    """
    Parses messy vendor communication (WhatsApp message / email).
    Uses Gemini 2.5 Flash structured output if key is configured,
    otherwise runs transparent heuristic extraction disclosing simulated state.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    active_model = get_active_model()

    if api_key and HAS_GENAI_LIB:
        try:
            client = genai.Client(api_key=api_key)
            system_prompt = (
                "You are an expert event auditor. Parse this raw vendor message into structured line items. "
                "Tag items as FIXED (setup fee, DJ, lighting), PER_CAPITA (food plate, favors), or STEP_TIERED. "
                "Convert all rupee amounts to integer paise (1 Rupee = 100 Paise). "
                "Extract GST % as basis points (e.g., 18% = 1800, 5% = 500). "
                "Flag any surprise clauses like corkage, generator diesel, overtime penalties."
            )
            response = client.models.generate_content(
                model=active_model,
                contents=f"Current Event Guests: {current_guest_count}\nVendor Message:\n{raw_quote_text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=ParsedQuoteResult,
                    temperature=0.2,
                ),
            )
            result = json.loads(response.text)
            return {
                "success": True,
                "is_simulated": False,
                "model": active_model,
                "data": result,
                "review_status": "PENDING_REVIEW",
            }
        except Exception as e:
            # Fall back to heuristic parser gracefully
            pass

    # Heuristic Parser (Discloses simulated offline status)
    return heuristic_quote_parser(raw_quote_text, current_guest_count)


def heuristic_quote_parser(raw_text: str, current_guest_count: int) -> Dict[str, Any]:
    """Deterministic regex heuristic parser for offline demonstration."""
    text_lower = raw_text.lower()

    vendor_name = "Extracted Vendor Partner"
    category = "General"
    extracted_items = []
    flagged_clauses = []
    advance_paise = 0

    if "cater" in text_lower or "plate" in text_lower or "pax" in text_lower or "food" in text_lower:
        category = "Catering"
        vendor_name = "Shahi Dastarkhwan Caterers"
        # Search for per plate rate like 850 or 1200
        plate_match = re.search(r"(?:rs\.?|₹|\b)?\s*(\d{3,4})\s*(?:per\s*plate|/plate|per\s*pax|/pax)", text_lower)
        plate_rate = int(plate_match.group(1)) if plate_match else 850
        extracted_items.append({
            "name": f"Master Banquet Buffet ({plate_rate}/plate)",
            "pricing_model": "PER_CAPITA",
            "unit_cost_paise": plate_rate * 100,
            "step_capacity": 1,
            "tax_rate_bps": 500 if "5%" in text_lower else 1800,
        })
        if "stall" in text_lower or "counter" in text_lower or "chaat" in text_lower:
            extracted_items.append({
                "name": "Live Chaat & Dessert Counter Setup",
                "pricing_model": "FIXED",
                "unit_cost_paise": 1800000,
                "step_capacity": 1,
                "tax_rate_bps": 1800,
            })
        flagged_clauses.append("Kitchen fuel cylinders and ice bins are excluded from base quote.")
        advance_paise = 2500000

    elif "decor" in text_lower or "flower" in text_lower or "stage" in text_lower or "light" in text_lower:
        category = "Decor"
        vendor_name = "Vibrant Flora & Lighting Studio"
        extracted_items.append({
            "name": "Stage Backdrop & Overhead Ambient Truss",
            "pricing_model": "FIXED",
            "unit_cost_paise": 4500000,
            "step_capacity": 1,
            "tax_rate_bps": 1800,
        })
        flagged_clauses.append("Overtime teardown fee of ₹4,000/hour applies after 1:00 AM.")
        advance_paise = 1500000

    elif "sound" in text_lower or "dj" in text_lower or "mic" in text_lower or "music" in text_lower:
        category = "Entertainment"
        vendor_name = "Pulse AV & Sound Rigging"
        extracted_items.append({
            "name": "Line Array Sound System + Wireless Mics",
            "pricing_model": "FIXED",
            "unit_cost_paise": 2800000,
            "step_capacity": 1,
            "tax_rate_bps": 1800,
        })
        flagged_clauses.append("Municipal sound curfew strictly enforced at 10:00 PM.")
        advance_paise = 1000000
    else:
        extracted_items.append({
            "name": "Service Deliverable Base Package",
            "pricing_model": "FIXED",
            "unit_cost_paise": 2000000,
            "step_capacity": 1,
            "tax_rate_bps": 1800,
        })

    suggested_reply = (
        f"Hi {vendor_name}, thanks for the quote. We are planning for {current_guest_count} guests. "
        "Could you confirm if generator fuel and breakdown labor are bundled, and whether the 18% GST invoice can be issued upon final milestone completion?"
    )

    return {
        "success": True,
        "is_simulated": True,
        "notice": "Simulated Heuristic Extraction (Offline Demo Mode)",
        "data": {
            "vendor_name": vendor_name,
            "category": category,
            "extracted_items": extracted_items,
            "advance_deposit_paise": advance_paise,
            "deposit_due_date": "2026-11-05",
            "flagged_clauses": flagged_clauses,
            "suggested_negotiation_reply": suggested_reply,
        },
        "review_status": "PENDING_REVIEW",
    }

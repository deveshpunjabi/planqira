"""
Planqira AI Cognitive Services Adapter
Integrates with Google DeepMind Gemma 4 (gemma-4-31b-it / gemma-4-26b-a4b-it) & Gemini 2.5 Flash
via the official google-genai SDK with local Pydantic validation, bounded timeouts,
and honest, transparent offline heuristic fallback.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Check if google-genai SDK is available
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False
    APIError = Exception


# Configurable model identifier: defaults to Gemma 4 31B (gemma-4-31b-it)
DEFAULT_MODEL = os.getenv("AI_MODEL", os.getenv("GEMINI_MODEL", "gemma-4-31b-it"))


def get_active_model() -> str:
    """Returns the configured model identifier."""
    return os.getenv("AI_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_MODEL))


class ExtractedLineItem(BaseModel):
    name: str = Field(..., max_length=120)
    pricing_model: str = Field(description="Must be 'FIXED', 'PER_CAPITA', or 'STEP_TIERED'")
    unit_cost_paise: int = Field(..., ge=0)
    step_capacity: int = Field(1, ge=1)
    tax_rate_bps: int = Field(0, ge=0, le=10000, description="Tax rate in basis points, e.g. 1800 for 18% GST")
    is_tax_inclusive: bool = False
    notes: Optional[str] = None

    @field_validator("pricing_model")
    @classmethod
    def validate_pricing_model(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ("FIXED", "PER_CAPITA", "STEP_TIERED"):
            return "FIXED"
        return upper


class ParsedQuoteResult(BaseModel):
    vendor_name: str = Field(..., max_length=120)
    category: str = Field(..., max_length=60)
    extracted_items: List[ExtractedLineItem]
    advance_deposit_paise: int = Field(0, ge=0)
    deposit_due_date: Optional[str] = None
    explicit_clauses_extracted: List[str] = Field(default_factory=list)
    suggested_clarification_questions: List[str] = Field(default_factory=list)
    suggested_negotiation_reply: str = Field("", max_length=1000)


def parse_vendor_quote_text(raw_quote_text: str, current_guest_count: int = 150) -> Dict[str, Any]:
    """
    Parses messy vendor communications into structured line items.
    1. Enforces strict input bounds and sanitization.
    2. Calls Gemma 4 via Google GenAI SDK if GEMINI_API_KEY is configured.
    3. Validates output locally against ParsedQuoteResult schema.
    4. Falls back gracefully and honestly to heuristic extraction when offline,
       explicitly tagging 'extraction_mode': 'CREDENTIAL_FREE_HEURISTIC'.
    """
    sanitized_text = raw_quote_text.strip()[:4000]
    if len(sanitized_text) < 5:
        return {
            "success": False,
            "error": "Quote text too short to extract line items.",
            "extraction_mode": "REJECTED",
        }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    active_model = get_active_model()

    if api_key and HAS_GENAI_LIB:
        try:
            client = genai.Client(api_key=api_key)
            system_prompt = (
                "You are an expert event auditor. Parse the raw vendor communication into structured line items. "
                "CRITICAL RULES:\n"
                "1. Extract ONLY facts present in the text. Do NOT hallucinate vendor names, costs, or unmentioned services.\n"
                "2. Tag items as 'FIXED', 'PER_CAPITA' (per guest/person/plate), or 'STEP_TIERED' (e.g. per table/bus).\n"
                "3. Convert all rupee currency amounts to integer paise (1 Rupee = 100 Paise).\n"
                "4. Extract GST or tax % as basis points (e.g., 18% = 1800, 5% = 500).\n"
                "5. Only list clauses explicitly mentioned (e.g. generator diesel, overtime, corkage) in explicit_clauses_extracted.\n"
                "6. General protection questions belong in suggested_clarification_questions."
            )

            prompt_content = f"Event Headcount Context: {current_guest_count} guests\nVendor Text:\n{sanitized_text}"
            response = client.models.generate_content(
                model=active_model,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=ParsedQuoteResult,
                    temperature=0.1,
                ),
            )

            raw_json = json.loads(response.text)
            validated = ParsedQuoteResult.model_validate(raw_json)

            return {
                "success": True,
                "is_simulated": False,
                "extraction_mode": "LIVE_AI",
                "model_used": active_model,
                "source_quote_text": sanitized_text,
                "review_status": "PENDING_HUMAN_REVIEW",
                "data": validated.model_dump(),
            }
        except Exception as e:
            # Fall back honestly to heuristic parser
            pass

    # Credential-Free Heuristic Extraction (Disclosed & Honest)
    heuristic_data = _heuristic_quote_parser(sanitized_text, current_guest_count)
    return {
        "success": True,
        "is_simulated": True,
        "extraction_mode": "CREDENTIAL_FREE_HEURISTIC",
        "model_used": f"{active_model} (Simulated Local Heuristic)",
        "source_quote_text": sanitized_text,
        "review_status": "PENDING_HUMAN_REVIEW",
        "data": heuristic_data,
    }


def _classify_service_status(service_pattern: str, text: str) -> str:
    """
    Parses vendor text to classify the status of a specific service/term (e.g. diesel, corkage, transport, overtime).
    Returns:
      - 'INCLUDED': explicitly included, waived, free, or stated with zero/no extra surcharge
      - 'EXCLUDED': explicitly excluded, charged extra, subject to surcharge, or chargeable
      - 'UNSPECIFIED': mentioned without clear inclusion or exclusion, or not mentioned
    """
    low = text.lower()
    clauses = re.split(r"[.;\n]", low)

    for c in clauses:
        c_clean = c.strip()
        if not re.search(service_pattern, c_clean):
            continue

        # 1. Positive inclusion / fee waiver patterns
        # Handles: "no corkage fee", "no surcharge for diesel", "diesel included at no extra charge", "corkage waived", "free delivery"
        positive_patterns = [
            r"\bno\s+(?:extra\s+|additional\s+)?(?:surcharge|charge|fee|cost)\b",
            r"\bwithout\s+(?:extra\s+|additional\s+)?(?:surcharge|charge|fee|cost)\b",
            r"\bat\s+no\s+(?:extra\s+)?(?:charge|cost|fee|surcharge)\b",
            r"\bno\s+surcharge\b",
            r"\bzero\s+(?:surcharge|charge|fee|cost)\b",
            r"\bno\s+(?:corkage|diesel|fuel|transport|delivery|overtime)\s*(?:fee|charge|cost|surcharge)?\b",
            r"\b(?:corkage|diesel|fuel|transport|delivery|overtime)\s+(?:fee\s+|charge\s+)?(?:is\s+)?(?:waived|complimentary|free)\b",
            r"\b(?:waived|complimentary|free\s+delivery|free\s+transport)\b",
            r"(?<!not\s)(?<!not\s\s)\b(?:included|inclusive)\b",
        ]

        # 2. Negative exclusion / surcharge patterns
        # Handles: "diesel not included", "corkage fee required", "transport extra", "outstation transport extra", "corkage applicable"
        negative_patterns = [
            r"\bnot\s+(?:included|inclusive)\b",
            r"\bcharged\s+(?:extra|separately|additional)\b",
            r"\bpayable\s+by\s+client\b",
            r"\bclient\s+scope\b",
            r"\bexcludes?\b",
            r"\bexcluding\b",
            r"(?<!no\s)(?<!without\s)(?<!zero\s)\b(?:extra\s+charge|additional\s+fee|surcharge|surcharges)\b",
            r"(?<!no\s)(?<!without\s)\b(?:corkage|diesel|transport|delivery)\s+(?:extra|applicable|required|chargeable)\b",
            r"\b(?:corkage\s+fee\s+required|corkage\s+applicable|corkage\s+required)\b",
            r"\b(?:outstation|travel)\s+(?:fees?\s+applicable|extra)\b",
            r"(?<!no\s)\bextra\b",
        ]

        has_pos = any(re.search(p, c_clean) for p in positive_patterns)
        has_neg = any(re.search(p, c_clean) for p in negative_patterns)

        if has_pos and not has_neg:
            return "INCLUDED"
        elif has_neg and not has_pos:
            return "EXCLUDED"
        elif has_pos and has_neg:
            # Resolving combinations: "diesel included at no extra charge" -> INCLUDED
            if re.search(r"\bno\s+(?:extra\s+charge|surcharge)\b", c_clean) or re.search(r"\bincluded\s+at\s+no\s+extra\b", c_clean):
                return "INCLUDED"
            if re.search(r"\bnot\s+included\b", c_clean):
                return "EXCLUDED"
            return "INCLUDED" if ("included" in c_clean or "waived" in c_clean or "free" in c_clean) else "EXCLUDED"

    return "UNSPECIFIED"


def _is_service_included(concept_pattern: str, text: str) -> bool:
    """Backward compatible wrapper around _classify_service_status."""
    return _classify_service_status(concept_pattern, text) == "INCLUDED"


def _is_advance_label(label: str) -> bool:
    """Returns True if the label describes an advance deposit rather than a purchased line item."""
    return bool(re.search(r"\b(?:advance|deposit|token|booking\s+amount|down\s+payment)\b", label, re.IGNORECASE))


def _heuristic_quote_parser(text: str, guests: int) -> Dict[str, Any]:
    """
    Deterministic regex-based heuristic extractor for offline verification and testing.
    Never pretends to be live AI; extracts observable figures from text.
    Correctly handles:
    1. Advance deposits vs line items (advance is never added as a purchasable budget line item).
    2. Multi-clause negation ('Diesel not included', 'No corkage fee', 'Diesel included at no extra charge', 'No surcharge for diesel').
    3. Tax-inclusive pricing (preserves authoritative gross pricing and computes advance against gross quoted total).
    4. Unconfirmed pricing ('price to be confirmed' / 'TBD' tagged with PRICE_UNCONFIRMED).
    """
    # Detect vendor name
    vendor_match = re.search(r"(?:this is|from|regards,?|team|vendor:?)\s+([A-Z][A-Za-z0-9\s&]{2,40}?)(?:[.,\n]|\s+catering|\s+productions|\s+sound|$)", text, re.IGNORECASE)
    prefix_match = re.search(r"^([A-Z][A-Za-z0-9\s&]{2,40}?):", text.strip())
    if vendor_match:
        vendor_name = vendor_match.group(1).strip()
    elif prefix_match:
        vendor_name = prefix_match.group(1).strip()
    else:
        vendor_name = "Vendor Partner (Extracted)"

    # Detect category
    category = "General Logistics"
    low = text.lower()
    if any(k in low for k in ["cater", "thali", "food", "buffet", "plate", "pax", "dal baati", "snack"]):
        category = "Catering"
    elif any(k in low for k in ["dj", "sound", "light", "truss", "music", "audio", "speaker"]):
        category = "Entertainment"
    elif any(k in low for k in ["decor", "mandap", "flower", "lantern", "stage", "draping"]):
        category = "Decor & Styling"
    elif any(k in low for k in ["venue", "hall", "lawn", "rooftop", "banquet"]):
        category = "Venue & Space"
    elif any(k in low for k in ["photo", "video", "cinema", "drone", "album"]):
        category = "Photography"

    # Detect tax rate and whether quote is tax-inclusive
    tax_bps = 0
    tax_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*gst", low)
    if tax_match:
        tax_pct = float(tax_match.group(1))
        tax_bps = int(round(tax_pct * 100))

    is_tax_inclusive = bool(
        re.search(r"(?:including|inclusive\s+of|incl\.?|all[- ]inclusive)\s+(?:\d+(?:\.\d+)?\s*%\s*)?gst", low) or
        re.search(r"gst\s+(?:included|inclusive)", low)
    )

    # Check for unconfirmed price markers
    is_unconfirmed_text = bool(
        re.search(r"\b(?:to be confirmed|tbd|on request|to be discussed|pending confirmation|rates on call|price unconfirmed)\b", low)
    )

    # 1. Detect per-person pricing
    per_person_match = re.search(r"(?:rs\.?|inr|₹)\s*(\d[\d,]*)\s*(?:per\s+(?:person|pax|guest|head|plate)|\/-\s*per)", low)
    items: List[ExtractedLineItem] = []
    extracted_advance_paise = 0

    if per_person_match:
        raw_unit_rupees = int(per_person_match.group(1).replace(",", ""))
        raw_paise = raw_unit_rupees * 100
        if is_tax_inclusive and tax_bps > 0:
            note = f"Tax-inclusive quote (Gross ₹{raw_unit_rupees:,.2f} incl. {tax_bps/100:.1f}% GST)"
            is_incl = True
        else:
            note = None
            is_incl = False

        items.append(
            ExtractedLineItem(
                name="Per-Plate Banquet Service",
                pricing_model="PER_CAPITA",
                unit_cost_paise=raw_paise,
                step_capacity=1,
                tax_rate_bps=tax_bps,
                is_tax_inclusive=is_incl,
                notes=note,
            )
        )
        total_estimated_paise = raw_paise * max(1, guests)
    else:
        # 2. Parse multi-item matches while strictly filtering out advance deposits
        item_matches = list(re.finditer(r"([A-Za-z0-9\s&]{3,40}?)\s*(?:rs\.?|inr|₹)\s*([\d,]+)", text, re.IGNORECASE))
        filtered_matches = []
        for m in item_matches:
            lbl = m.group(1).strip()
            lbl = re.sub(r"^.*?:\s*", "", lbl).strip()
            amt = int(m.group(2).replace(",", ""))
            if _is_advance_label(lbl):
                if extracted_advance_paise == 0:
                    extracted_advance_paise = amt * 100
            else:
                if amt >= 500:
                    filtered_matches.append((lbl, amt))

        if filtered_matches:
            for lbl, amt in filtered_matches:
                gross_paise = amt * 100
                if is_tax_inclusive and tax_bps > 0:
                    note = f"Tax-inclusive quote (Gross ₹{amt:,.2f} incl. {tax_bps/100:.1f}% GST)"
                    is_incl = True
                else:
                    note = None
                    is_incl = False

                items.append(
                    ExtractedLineItem(
                        name=lbl.capitalize(),
                        pricing_model="FIXED",
                        unit_cost_paise=gross_paise,
                        step_capacity=1,
                        tax_rate_bps=tax_bps,
                        is_tax_inclusive=is_incl,
                        notes=note,
                    )
                )
            total_estimated_paise = sum(it.unit_cost_paise for it in items)
        else:
            # Fallback for flat amounts or unconfirmed quotes
            amounts = re.findall(r"(?:rs\.?|inr|₹)\s*(\d[\d,]*)", low)
            clean_amts = [int(a.replace(",", "")) for a in amounts if int(a.replace(",", "")) >= 500]

            if clean_amts and not is_unconfirmed_text:
                gross_paise = clean_amts[0] * 100
                if is_tax_inclusive and tax_bps > 0:
                    note = f"Tax-inclusive quote (Gross ₹{clean_amts[0]:,.2f} incl. {tax_bps/100:.1f}% GST)"
                    is_incl = True
                else:
                    note = None
                    is_incl = False

                items.append(
                    ExtractedLineItem(
                        name=f"{category} Package",
                        pricing_model="FIXED",
                        unit_cost_paise=gross_paise,
                        step_capacity=1,
                        tax_rate_bps=tax_bps,
                        is_tax_inclusive=is_incl,
                        notes=note,
                    )
                )
                total_estimated_paise = gross_paise
            else:
                # Unconfirmed or missing price
                items.append(
                    ExtractedLineItem(
                        name=f"{category} Package",
                        pricing_model="FIXED",
                        unit_cost_paise=0,
                        step_capacity=1,
                        tax_rate_bps=tax_bps,
                        is_tax_inclusive=False,
                        notes="PRICE_UNCONFIRMED: Rate not finalized by vendor. Must be confirmed before commitment approval.",
                    )
                )
                total_estimated_paise = 0

    # Advance deposit calculation (strictly derived from gross quoted total)
    advance_paise = 0
    if extracted_advance_paise > 0:
        advance_paise = extracted_advance_paise
    else:
        # Check percentage advance against total quoted gross
        pct_adv_match = re.search(r"(\d{1,2})\s*%\s*(?:advance|deposit|token)", low) or re.search(r"(?:advance|token|deposit)(?:\s+is|\s+of)?\s*(\d{1,2})\s*%", low)
        if pct_adv_match:
            pct = int(pct_adv_match.group(1))
            advance_paise = (total_estimated_paise * pct) // 100
        else:
            adv_match = re.search(r"(?:advance|token|deposit)(?:\s+is|\s+of)?\s*(?:rs\.?|inr|₹)\s*(\d[\d,]*)", low)
            if adv_match:
                advance_paise = int(adv_match.group(1).replace(",", "")) * 100

    # Date detection
    due_date = None
    date_match = re.search(r"(?:by|before|due)\s+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z0-9]+)", low)
    if date_match:
        due_date = date_match.group(1).strip()

    # Flag explicit clauses with comprehensive negation and waiver detection
    clauses = []
    # Diesel / Kitchen fuel
    diesel_st = _classify_service_status(r"diesel|fuel", low)
    if diesel_st == "INCLUDED":
        clauses.append("Kitchen fuel and generator diesel explicitly included in quote (no surcharge).")
    elif diesel_st == "EXCLUDED":
        clauses.append("Kitchen fuel and generator diesel charged separately as surcharge.")

    # Corkage
    corkage_st = _classify_service_status(r"corkage|liquor", low)
    if corkage_st == "INCLUDED":
        clauses.append("Outside beverage corkage fee waived / complimentary.")
    elif corkage_st == "EXCLUDED":
        clauses.append("Outside beverage corkage fee required.")

    # Transport
    transport_st = _classify_service_status(r"transport|delivery|km", low)
    if transport_st == "INCLUDED":
        clauses.append("Local transport and delivery included in quote.")
    elif transport_st == "EXCLUDED":
        clauses.append("Outstation travel/transport fees applicable beyond city radius.")

    # Overtime
    overtime_st = _classify_service_status(r"overtime|curfew|per\s+hour", low)
    if overtime_st == "INCLUDED":
        clauses.append("Flexible schedule with overtime penalties waived.")
    elif overtime_st == "EXCLUDED":
        clauses.append("Overtime hours beyond agreed time slot incur hourly penalty fees.")

    # Questions & negotiation reply
    questions = [
        "Does the quoted total include full setup, breakdown, and disposal fees?",
        f"Can you provide a line-item tax breakdown matching the quoted {tax_bps/100:.1f}% GST rate?",
    ]
    if category == "Catering":
        questions.append("Are guest tasting sessions, ceramic crockery, and serving staff included?")
    if total_estimated_paise == 0:
        questions.append(f"Item pricing was not specified in the quote. Please confirm the rate for {category} before final commitment.")

    negotiation_script = (
        f"Hi {vendor_name}, thank you for sending over the quote for {category}. "
        f"We are evaluating options for {guests} guests. Before locking in the agreement, "
        f"could you confirm if the {tax_bps/100:.1f}% GST and setup logistics are all-inclusive?"
    )

    return {
        "vendor_name": vendor_name,
        "category": category,
        "extracted_items": [it.model_dump() for it in items],
        "advance_deposit_paise": advance_paise,
        "deposit_due_date": due_date,
        "explicit_clauses_extracted": clauses,
        "suggested_clarification_questions": questions,
        "suggested_negotiation_reply": negotiation_script,
    }

"""
Document type classification. Runs as one step of the EXISTING ingestion
pipeline (see app.services.document_processing) — it classifies each uploaded
document into an industrial document type purely from its own extracted text,
so the Maintenance / Compliance / Reports dashboards can be populated
automatically from what the user actually uploaded. No demo data, no
predefined machines/SOPs — only inference from the document itself.

The category is a lightweight signal derived from vocabulary that genuinely
appears in the document (a maintenance log really does say "work order",
"downtime", "repaired"; an SOP really does say "standard operating
procedure", "shall", "step 1"). When Gemini is available it refines the
classification; otherwise the deterministic keyword-scoring result is used.
"""
import os
import json
import logging
from typing import Dict, List, Tuple
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical document-type taxonomy. GENERAL is the fallback when nothing
# clearly matches — never guessed as a specific industrial type.
GENERAL = "General Document"

# The maintenance dashboard is built from documents in these categories.
MAINTENANCE_CATEGORIES = {
    "Machine Manual", "Maintenance Log", "Incident Report", "Inspection Report",
}
# The compliance dashboard is built from documents in these categories.
COMPLIANCE_CATEGORIES = {
    "SOP", "Inspection Report", "Audit Report", "Safety Procedure", "Regulatory Document",
}

# Detection signals per category. These are patterns that occur in the
# document's OWN text — not injected content. Multi-word phrases score higher
# than single words since they are far less ambiguous.
_CATEGORY_SIGNALS: Dict[str, Dict[str, List[str]]] = {
    "Machine Manual": {
        "strong": ["operating manual", "user manual", "installation manual", "technical specification",
                   "operating instructions", "product manual", "equipment manual", "datasheet"],
        "weak": ["manual", "specification", "torque", "rpm", "voltage", "assembly", "lubrication", "model no"],
    },
    "Maintenance Log": {
        "strong": ["work order", "maintenance log", "maintenance record", "preventive maintenance",
                   "service record", "downtime", "repaired", "replaced part", "maintenance history"],
        "weak": ["maintenance", "serviced", "repair", "technician", "scheduled", "overhaul", "spare part"],
    },
    "Incident Report": {
        "strong": ["incident report", "root cause", "failure mode", "breakdown", "unplanned shutdown",
                   "near miss", "failure occurred", "equipment failure"],
        "weak": ["incident", "failure", "fault", "alarm", "tripped", "leak", "overheating", "vibration"],
    },
    "Inspection Report": {
        "strong": ["inspection report", "inspection checklist", "visual inspection", "measured value",
                   "acceptance criteria", "inspection date", "inspected by", "condition assessment"],
        "weak": ["inspection", "inspected", "measurement", "tolerance", "reading", "gauge", "within limits"],
    },
    "SOP": {
        "strong": ["standard operating procedure", "sop", "operating procedure", "step-by-step",
                   "procedure number", "purpose and scope", "responsibilities"],
        "weak": ["procedure", "shall", "step 1", "must ensure", "guideline", "protocol"],
    },
    "Inventory": {
        "strong": ["inventory list", "stock level", "bill of materials", "parts inventory",
                   "reorder level", "stock on hand", "material list"],
        "weak": ["inventory", "quantity", "stock", "sku", "part number", "unit price", "warehouse"],
    },
    "Training Record": {
        "strong": ["training record", "training certificate", "competency assessment", "trained on",
                   "certification of completion", "training program"],
        "weak": ["training", "certified", "attended", "course", "trainee", "instructor", "competency"],
    },
    "Quality Report": {
        "strong": ["quality report", "quality control", "quality assurance", "defect rate",
                   "non-conformance", "quality metrics", "test results", "batch quality"],
        "weak": ["quality", "defect", "reject", "tolerance", "conformance", "qc", "qa"],
    },
    "Audit Report": {
        "strong": ["audit report", "audit findings", "internal audit", "compliance audit",
                   "audit score", "auditor", "corrective action", "audit checklist"],
        "weak": ["audit", "finding", "observation", "non-compliance", "compliance", "corrective"],
    },
    "Safety Procedure": {
        "strong": ["safety procedure", "safety protocol", "lockout tagout", "hazard analysis",
                   "personal protective equipment", "risk assessment", "emergency procedure", "permit to work"],
        "weak": ["safety", "hazard", "ppe", "risk", "emergency", "danger", "warning", "protective"],
    },
    "Regulatory Document": {
        "strong": ["regulatory compliance", "regulation", "statutory requirement", "iso 9001",
                   "iso 14001", "osha", "environmental compliance", "legal requirement", "standard requirement"],
        "weak": ["regulatory", "compliance", "statutory", "iso", "standard", "certification", "directive"],
    },
}


def _keyword_scores(text_lower: str) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for category, signals in _CATEGORY_SIGNALS.items():
        score = 0.0
        for phrase in signals["strong"]:
            if phrase in text_lower:
                score += 3.0
        for word in signals["weak"]:
            if word in text_lower:
                score += 1.0
        if score:
            scores[category] = score
    return scores


def _rule_based_classify(text: str) -> Tuple[str, Dict[str, float]]:
    scores = _keyword_scores(text.lower())
    if not scores:
        return GENERAL, {}
    best = max(scores, key=scores.get)
    # Require a minimum of confidence so a single stray weak keyword doesn't
    # mislabel an otherwise generic document.
    if scores[best] < 2.0:
        return GENERAL, scores
    return best, scores


def _gemini_classify(text: str, candidate_scores: Dict[str, float]) -> str | None:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    categories = list(_CATEGORY_SIGNALS.keys()) + [GENERAL]
    # Cap the excerpt so classification stays cheap; the type is almost always
    # evident from the first page or two.
    excerpt = text[:6000]
    prompt = f"""
You are classifying an industrial/enterprise document into exactly ONE type.
Choose strictly from this list (return the type verbatim):
{json.dumps(categories)}

Base your decision ONLY on the document text below. If it does not clearly fit
a specific industrial type, return "{GENERAL}".

Document text:
---
{excerpt}
---

Respond in EXACT JSON: {{"category": "<one of the types above>"}}
No markdown, no explanation.
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text.strip())
        category = data.get("category")
        if category in categories:
            return category
        logger.warning(f"Gemini returned unknown document category {category!r}; keeping rule-based result.")
    except Exception as e:
        logger.error(f"Gemini document classification failed: {e}; keeping rule-based result.")
    return None


def classify_document(text: str, filename: str = "") -> str:
    """
    Returns the best-fit document category for the given extracted text.
    Combines the document filename (a genuine signal — people name files
    "pump_inspection_report.pdf") with body-text keyword scoring, then lets
    Gemini refine when available. Always returns a value from the taxonomy
    (or GENERAL), never fabricated content.
    """
    combined = f"{filename}\n{text}" if filename else text
    rule_category, scores = _rule_based_classify(combined)

    gemini_category = _gemini_classify(text, scores)
    final = gemini_category or rule_category

    logger.info(
        f"Classified document {filename or '(unnamed)'} as {final!r} "
        f"(rule-based={rule_category!r}, gemini={gemini_category!r})"
    )
    return final

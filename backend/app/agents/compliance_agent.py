import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service, format_chunks_as_context, extractive_answer, not_found_message

logger = logging.getLogger(__name__)


class ComplianceAgent:
    def __init__(self):
        self.active = gemini_service.active

    def evaluate_compliance(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates inspection/audit content against SOP/procedure text found in the
        user's own uploaded documents. Never fabricates findings — if no relevant
        content was retrieved, or Gemini is unavailable, falls back to a grounded,
        non-fabricated report built from the retrieved chunks only.
        """
        logger.info("ComplianceAgent running evaluation for query: %r (%d context chunk(s))", query, len(context_chunks))

        if not context_chunks:
            logger.info("ComplianceAgent: no context chunks retrieved, returning not-found report.")
            return self._not_found_report(query)

        context_str = format_chunks_as_context(context_chunks)

        prompt = f"""
You are a senior compliance auditor briefing a plant/business owner on exactly what they
need to know. Your task is to analyze the provided inspection/audit content against any
procedure or standard limits found in the SAME context. Use ONLY the context below — never
introduce facts, parameters, or limits that are not present in it, but be thorough: surface
every relevant parameter, figure, and deviation the context actually contains, not just the
first one you find.

Retrieved Document Context:
---
{context_str}
---

User Query/Focus: {query}

Please perform the following audit strictly from the context above:
1. Identify all inspected parameters actually mentioned in the context (e.g. measurements, thresholds).
2. For each parameter, check any official limits specified in the text.
3. Compare the inspected value against that limit.
4. Flag any non-compliant values.
5. Compute a general Compliance Score (0 to 100%) based only on what is present.
6. Formulate corrective actions grounded in the context.
7. Include confidence and explainability metrics.
8. Write "summary" as a complete briefing a busy owner could act on directly — not a one-line
   restatement of the question.

If the context does not contain enough information to audit compliance, set "compliance_score" to 0,
leave "checklist" and "corrective_actions" empty, and explain this in "summary".

Return your response in EXACT JSON format with these keys:
- "compliance_score": (int)
- "summary": (string summarizing the compliance audit)
- "checklist": list of objects, each containing:
  - "parameter": (string)
  - "sop_limit": (string)
  - "inspected_value": (string)
  - "status": ("COMPLIANT" or "NON_COMPLIANT")
  - "deviation": (string detail of discrepancy or "None")
- "corrective_actions": list of strings for remediation
- "confidence_score": (float, e.g. 0.89)
- "reasoning_steps": list of strings of logical audit steps taken
- "evidence_base": list of strings detailing document standards matched

Do not wrap in markdown or add explanations outside the JSON block.
"""

        try:
            if not self.active:
                logger.info("ComplianceAgent: Gemini unavailable, building extractive summary report.")
                return self._extractive_report(query, context_chunks)

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"ComplianceAgent evaluation failed: {e}. Falling back to extractive summary.")
            return self._extractive_report(query, context_chunks)

    def _not_found_report(self, query: str) -> Dict[str, Any]:
        return {
            "compliance_score": 0,
            "summary": not_found_message(query),
            "checklist": [],
            "corrective_actions": [],
            "confidence_score": 0.0,
            "reasoning_steps": ["No matching content was retrieved from the uploaded documents."],
            "evidence_base": []
        }

    def _extractive_report(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Non-fabricated fallback used when Gemini is unavailable — builds a concise
        extractive summary from the retrieved chunks (never a raw excerpt dump,
        and never hardcoded/demo content).
        """
        summary, citations = extractive_answer(query, context_chunks)
        if not citations:
            return self._not_found_report(query)
        return {
            "compliance_score": 0,
            "summary": f"AI reasoning is currently unavailable. Summary from your uploaded documents: {summary}",
            "checklist": [],
            "corrective_actions": [],
            "confidence_score": 0.3,
            "reasoning_steps": [
                "Retrieved matching content from uploaded documents.",
                "Gemini reasoning unavailable — returning an extractive summary instead of a structured audit."
            ],
            "evidence_base": sorted({c["document_name"] for c in citations})
        }


compliance_agent = ComplianceAgent()

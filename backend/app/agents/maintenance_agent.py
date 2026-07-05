import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service, format_chunks_as_context

logger = logging.getLogger(__name__)


class MaintenanceAgent:
    def __init__(self):
        self.active = gemini_service.active

    def generate_rca(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes failure logs, manuals, and records retrieved from the user's own
        uploaded documents to build an RCA. Never fabricates a report — if no relevant
        content was retrieved, or Gemini is unavailable, falls back to a grounded,
        non-fabricated report built from the retrieved chunks only.
        """
        logger.info("MaintenanceAgent generating RCA for query: %r (%d context chunk(s))", query, len(context_chunks))

        if not context_chunks:
            logger.info("MaintenanceAgent: no context chunks retrieved, returning not-found report.")
            return self._not_found_rca()

        context_str = format_chunks_as_context(context_chunks)

        prompt = f"""
You are a reliability engineer building a formal Root Cause Analysis (RCA) report for a failure
described in the context below. Use ONLY the context — never introduce equipment, dates, or facts
that are not present in it.

Retrieved Document Context:
---
{context_str}
---

User Query/Asset under investigation: {query}

Please formulate an RCA with the following sections, grounded strictly in the context above:
1. Equipment details and status under investigation.
2. Failure mode identification.
3. Chronological timeline of the failure (containing structured objects with time, event, status, and detail).
4. Underlying root cause (using 5-Whys methodology if applicable).
5. Specific maintenance actions performed or proposed.
6. Long-term preventive maintenance recommendations.
7. Lessons learned.
8. Confidence and explainability metrics.

If the context does not contain enough information for a section, use an empty list/string for it
rather than inventing details, and reflect the gap honestly in "root_cause".

Return your response in EXACT JSON format with these keys:
- "equipment_id": (string, e.g. "P-102", or "" if not present in context)
- "failure_mode": (string)
- "chronology": list of strings outlining events
- "timeline": list of objects, each containing:
  - "time": (string, e.g. "2026-05-08")
  - "event": (string, e.g. "Inspection")
  - "status": (string, one of: "normal", "warning", "ignored", "failure", "repair")
  - "detail": (string)
- "root_cause": (string)
- "maintenance_actions_taken": list of strings of actions performed
- "preventive_recommendations": list of strings for preventing recurrence
- "lessons_learned": list of strings
- "confidence_score": (float between 0.00 and 1.00)
- "reasoning_steps": list of strings detailing reasoning logic
- "evidence_base": list of strings detailing supporting documents and observations

Do not wrap in markdown or add explanations outside the JSON block.
"""

        try:
            if not self.active:
                logger.info("MaintenanceAgent: Gemini unavailable, building grounded fallback RCA.")
                return self._grounded_fallback_rca(context_chunks)

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"MaintenanceAgent RCA generation failed: {e}. Falling back to grounded chunk-based RCA.")
            return self._grounded_fallback_rca(context_chunks)

    def _not_found_rca(self) -> Dict[str, Any]:
        return {
            "equipment_id": "",
            "failure_mode": "No relevant information was found in the uploaded documents.",
            "chronology": [],
            "timeline": [],
            "root_cause": "No relevant information was found in the uploaded documents.",
            "maintenance_actions_taken": [],
            "preventive_recommendations": [],
            "lessons_learned": [],
            "confidence_score": 0.0,
            "reasoning_steps": ["No matching content was retrieved from the uploaded documents."],
            "evidence_base": []
        }

    def _grounded_fallback_rca(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Non-fabricated fallback used when Gemini is unavailable but relevant chunks
        were retrieved — surfaces the raw excerpts instead of a hardcoded demo RCA.
        """
        filenames = sorted({c.get("metadata", {}).get("filename", "Unknown Document") for c in context_chunks})
        excerpt = "\n\n".join(
            f"[{c.get('metadata', {}).get('filename', 'Unknown Document')}] {(c.get('page_content') or '').strip()[:1500]}"
            for c in context_chunks[:3]
        )
        return {
            "equipment_id": "",
            "failure_mode": "AI reasoning unavailable — see retrieved excerpts below.",
            "chronology": [],
            "timeline": [],
            "root_cause": f"AI reasoning is currently unavailable. Showing relevant excerpts retrieved from your uploaded documents instead:\n\n{excerpt}",
            "maintenance_actions_taken": [],
            "preventive_recommendations": [],
            "lessons_learned": [],
            "confidence_score": 0.3,
            "reasoning_steps": [
                "Retrieved matching content from uploaded documents.",
                "Gemini reasoning unavailable — returning raw excerpts instead of a structured RCA."
            ],
            "evidence_base": filenames
        }


maintenance_agent = MaintenanceAgent()

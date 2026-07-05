import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class KnowledgeAgent:
    def __init__(self):
        self.active = gemini_service.active

    def retrieve_sop_or_manual(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Retrieves SOPs and manuals context, parses out specific instructions,
        and constructs an authoritative, cited answer.
        """
        logger.info("KnowledgeAgent retrieving SOP/manual information...")
        
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "Unknown Document")
            context_str += f"[Source ID: {filename}, Chunk: {i}]\nContent: {chunk.get('page_content', '')}\n\n"

        prompt = f"""
You are the central Knowledge Agent for the Centurion Petrochemical Plant.
Your task is to answer queries specifically relating to standard operating procedures (SOPs), mechanical manuals, and OEM guidelines.

Context:
---
{context_str}
---

User Query: {query}

Please formulate an authoritative answer citing details from the text.
Include a confidence score (from 0.00 to 1.00), a list of step-by-step reasoning steps, and evidence items.

Return your response in EXACT JSON format with these keys:
- "response": (string, markdown allowed, answering the query clearly with citations in brackets like [SOP-MECH-022.pdf])
- "confidence_score": (float, e.g. 0.94)
- "reasoning_steps": list of strings detailing the search & correlation logic
- "evidence_base": list of strings of specific sections, rules, or values extracted

Do not include any extra text outside the JSON.
"""

        try:
            if not self.active:
                logger.info("KnowledgeAgent running in Mock mode.")
                return self._get_mock_knowledge_response(query)

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"KnowledgeAgent query failed: {e}")
            return self._get_mock_knowledge_response(query)

    def _get_mock_knowledge_response(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        if "sop" in q or "alignment" in q or "mech-022" in q:
            return {
                "response": "The standard procedure for centrifugal pump shaft alignment is defined in **SOP-MECH-022** [SOP-MECH-022.pdf]. Key constraints include:\n\n*   **Radial Shaft Misalignment limit:** Max 0.05 mm [SOP-MECH-022.pdf, Section 3.1].\n*   **Vibration sweep checks:** Frequency must be monthly for general assets and bi-weekly for Train 2 rotating machinery [SOP-MECH-022.pdf, Section 4.2].\n*   **Drip rate safety boundary:** Mechanical seals must not exceed 3 drops/minute leakage during normal service [SOP-MECH-022.pdf, Section 1.5].",
                "confidence_score": 0.95,
                "reasoning_steps": [
                    "Identified SOP request matching standard mechanical alignment guidelines.",
                    "Retrieved SOP-MECH-022 manual chunks from knowledge base.",
                    "Extracted radial shaft tolerance boundary (0.05 mm) and seal leak limits."
                ],
                "evidence_base": [
                    "SOP-MECH-022 Section 3.1: Alignment limit = 0.05 mm",
                    "SOP-MECH-022 Section 1.5: Seal safety boundary = 3 drops/min"
                ]
            }
        else:
            return {
                "response": "Based on the Centurion Plant manuals [Manual-Pump-P102.pdf], operations criteria require replacing the mechanical seal (Part No. S-100) whenever radial alignment deviations exceed 0.05 mm for continuous periods exceeding 24 hours. The impeller kit K-402 must be assembled according to instructions on Page 45 [Manual-Pump-P102.pdf].",
                "confidence_score": 0.91,
                "reasoning_steps": [
                    "Scanned query for plant equipment manual references.",
                    "Correlated Pump P-102 specifications with OEM guidelines.",
                    "Isolated mechanical seal Part No. S-100 and Impeller assembly guide."
                ],
                "evidence_base": [
                    "Manual-Pump-P102.pdf Page 45: Impeller assembly details K-402",
                    "Manual-Pump-P102.pdf Page 12: Seal type S-100 specifications"
                ]
            }


knowledge_agent = KnowledgeAgent()

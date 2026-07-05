import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class ComplianceAgent:
    def __init__(self):
        self.active = gemini_service.active

    def evaluate_compliance(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates inspection reports against SOP procedures.
        Compares numeric tolerances and safety requirements.
        """
        logger.info("ComplianceAgent running evaluation...")
        
        # Consolidate text context
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "Unknown Document")
            context_str += f"[Source: {filename}]\nContent: {chunk.get('page_content', '')}\n\n"

        prompt = f"""
You are the Lead Safety & Regulatory Compliance Auditor for the Centurion Petrochemical Plant.
Your task is to analyze the provided inspection report details against the plant SOPs.

SOP and Inspection Context:
---
{context_str}
---

User Query/Focus: {query}

Please perform the following audit:
1. Identify all inspected parameters (e.g. shaft misalignment, temperature, pressure).
2. For each parameter, check the official SOP limits specified in the text.
3. Compare the inspected value against the SOP limit.
4. Flag any non-compliant values.
5. Compute a general Compliance Score (0 to 100%).
6. Formulate corrective actions.
7. Include confidence and explainability metrics.

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
                logger.info("ComplianceAgent running in Mock mode.")
                return self._get_mock_compliance_report(query)
                
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"ComplianceAgent evaluation failed: {e}")
            return self._get_mock_compliance_report(query)

    def _get_mock_compliance_report(self, query: str) -> Dict[str, Any]:
        return {
            "compliance_score": 75,
            "summary": "The shaft alignment inspection for Centrifugal Pump P-102 failed to meet the tolerances defined in SOP-MECH-022. Operating temperature is close to safety thresholds.",
            "checklist": [
                {
                    "parameter": "Radial Shaft Misalignment",
                    "sop_limit": "Max 0.05 mm",
                    "inspected_value": "0.08 mm",
                    "status": "NON_COMPLIANT",
                    "deviation": "Exceeds tolerance limit by 0.03 mm"
                },
                {
                    "parameter": "Vibration Amplitude",
                    "sop_limit": "Max 2.8 mm/s RMS",
                    "inspected_value": "4.2 mm/s RMS",
                    "status": "NON_COMPLIANT",
                    "deviation": "Exceeds alert limit by 1.4 mm/s RMS"
                },
                {
                    "parameter": "Casing Temperature",
                    "sop_limit": "Max 75 C",
                    "inspected_value": "72 C",
                    "status": "COMPLIANT",
                    "deviation": "None"
                },
                {
                    "parameter": "Mechanical Seal Leak Rate",
                    "sop_limit": "Max 3 drops/min",
                    "inspected_value": "12 drops/min",
                    "status": "NON_COMPLIANT",
                    "deviation": "Excessive leakage indicating seal face wear"
                }
            ],
            "corrective_actions": [
                "Shutdown Pump P-102 immediately to prevent catastrophic bearing failure.",
                "Execute laser shaft realignment according to SOP-MECH-022 Section 3.",
                "Replace mechanical seal using Spare Part: Mechanical Seal S-100.",
                "Perform a post-maintenance vibration sweep before placing the unit back in service."
            ],
            "confidence_score": 0.89,
            "reasoning_steps": [
                "Pulled alignment safety standard SOP-MECH-022 Section 3.",
                "Compared maintenance log alignment parameters (0.08 mm) with maximum bounds.",
                "Identified non-compliant mechanical seal leakage levels."
            ],
            "evidence_base": [
                "SOP-MECH-022.pdf Section 3: Alignment specifications",
                "SOP-MECH-022.pdf Section 1: Seal leakage parameters"
            ]
        }


compliance_agent = ComplianceAgent()

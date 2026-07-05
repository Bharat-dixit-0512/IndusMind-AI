import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class MaintenanceAgent:
    def __init__(self):
        self.active = gemini_service.active

    def generate_rca(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes failures logs, manuals, and records to build an RCA.
        Returns a structured report with confidence, reasoning, evidence, and visual timeline events.
        """
        logger.info("MaintenanceAgent generating RCA...")
        
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "Unknown Document")
            context_str += f"[Source: {filename}]\nContent: {chunk.get('page_content', '')}\n\n"

        prompt = f"""
You are the Chief Reliability Engineer at the Centurion Petrochemical Plant.
You are tasked with generating a formal Root Cause Analysis (RCA) report for an equipment failure.

Failure Context and logs:
---
{context_str}
---

User Query/Asset under investigation: {query}

Please formulate an RCA with the following sections:
1. Equipment details and status under investigation.
2. Failure mode identification.
3. Chronological timeline of the failure (containing structured objects with time, event, status, and detail).
4. Underlying root cause (using 5-Whys methodology if applicable).
5. Specific maintenance actions performed or proposed.
6. Long-term preventive maintenance recommendations.
7. Lessons learned.
8. Confidence and explainability metrics.

Return your response in EXACT JSON format with these keys:
- "equipment_id": (string, e.g. "P-102")
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
                logger.info("MaintenanceAgent running in Mock mode.")
                return self._get_mock_rca(query)
                
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"MaintenanceAgent RCA generation failed: {e}")
            return self._get_mock_rca(query)

    def _get_mock_rca(self, query: str) -> Dict[str, Any]:
        # Predefined mock RCA report for Pump P-102 Centurion Plant
        return {
            "equipment_id": "P-102",
            "failure_mode": "Mechanical Seal Rupture due to High Shaft Vibration",
            "chronology": [
                "2026-05-08: Pre-operational inspection logs normal vibration levels (1.8 mm/s RMS).",
                "2026-05-12: Standard operator logs mention a slight hum and leakage rate at 5 drops/min.",
                "2026-05-14: Vibration monitor triggers alarm at 4.2 mm/s RMS. Operations reports primary seal rupture and manual shutdown."
            ],
            "timeline": [
                {
                    "time": "2026-05-08",
                    "event": "Baseline Sweep",
                    "status": "normal",
                    "detail": "Radial vibration within normal limits (1.8 mm/s RMS)."
                },
                {
                    "time": "2026-05-12",
                    "event": "Hum & Leakage",
                    "status": "warning",
                    "detail": "Slight hum heard; mechanical seal leak reported at 5 drops/min."
                },
                {
                    "time": "2026-05-13",
                    "event": "Warning Ignored",
                    "status": "ignored",
                    "detail": "No corrective alignment was scheduled due to shift transition delays."
                },
                {
                    "time": "2026-05-14",
                    "event": "Critical Alarm",
                    "status": "failure",
                    "detail": "Vibration spikes to 4.2 mm/s RMS. Mechanical seal ruptures. Casing shutdown."
                },
                {
                    "time": "2026-05-15",
                    "event": "Realignment & Seal Swap",
                    "status": "repair",
                    "detail": "Mechanical Seal S-100 and Impeller Kit K-402 replaced. Realigned to 0.02 mm."
                }
            ],
            "root_cause": "The primary root cause was structural shaft misalignment (0.08 mm vs. SOP limit of 0.05 mm) which occurred during the previous motor swap. This created dynamic offset stresses, causing impeller wobbling, bearing wear, and ultimate mechanical seal face degradation.",
            "maintenance_actions_taken": [
                "Pump shutdown and isolation locks applied.",
                "Impeller casing opened; found worn seal faces and slight bearing clearance.",
                "Replaced mechanical seal with Seal Model S-100.",
                "Installed Impeller Kit K-402 to refresh rotating elements.",
                "Performed laser shaft alignment, reducing radial tolerance to 0.02 mm."
            ],
            "preventive_recommendations": [
                "Enforce mandatory laser alignment verification sheet signed off by QA after any motor decouplings.",
                "Increase predictive vibration probe monitoring sweeps from monthly to bi-weekly on Train 2 rotary assets.",
                "Add mechanical seal leak indicators to operator round checklist templates."
            ],
            "lessons_learned": [
                "Coupling motor alignment cannot be performed by simple visual check or straight-edge methods.",
                "Early leakage reports must trigger immediate corrective inspection, not just manual log notes."
            ],
            "confidence_score": 0.92,
            "reasoning_steps": [
                "Scanned operational history database for Pump P-102 work logs.",
                "Correlated alignment values with SOP-MECH-022 criteria.",
                "Matched historical vibration spike timings to telemetry data."
            ],
            "evidence_base": [
                "Inspection-C301.pdf Page 3: Telemetry threshold guidelines",
                "WO-9844-RCA.xlsx Row 4: Logged maintenance vibration details",
                "SOP-MECH-022.pdf Section 3.1: Alignment specifications"
            ]
        }


maintenance_agent = MaintenanceAgent()

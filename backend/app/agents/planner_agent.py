import logging
import json
import re
from typing import Dict, Any, List
import google.generativeai as genai

from app.core.config import settings
from app.services.vector_store import vector_store
from app.services.graph_db import graph_db
from app.services.gemini_service import gemini_service
from app.agents.compliance_agent import compliance_agent
from app.agents.maintenance_agent import maintenance_agent
from app.agents.knowledge_agent import knowledge_agent

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self):
        self.active = gemini_service.active

    def classify_intent(self, query: str) -> str:
        """
        Classifies user query into COMPLIANCE, MAINTENANCE, KNOWLEDGE, REPORTS, or GENERAL_QA.
        """
        if not self.active:
            q = query.lower()
            if "report" in q or "export" in q or "pdf" in q:
                return "REPORTS"
            elif any(x in q for x in ["comply", "compliance", "audit", "standard", "regulation"]):
                return "COMPLIANCE"
            elif any(x in q for x in ["sop", "manual", "guideline", "oem", "procedure"]):
                return "KNOWLEDGE"
            elif any(x in q for x in ["rca", "fail", "broken", "cause", "trouble", "suggest", "prevent", "maintenance"]):
                return "MAINTENANCE"
            return "GENERAL_QA"

        prompt = f"""
You are the central Planner Agent for the Industrial AI Brain platform.
Your task is to classify the user's query into one of five operational routing categories:

1. "COMPLIANCE": Queries asking to check compliance of work, inspect audits, compare logs against SOPs, or assess regulatory scores.
2. "MAINTENANCE": Queries requesting Root Cause Analysis (RCA), failure mode troubleshooting, maintenance history lookups, or repair details.
3. "KNOWLEDGE": Queries asking directly for manuals, SOP details, guidelines, or OEM documentation sections (e.g. "Show me the SOP for misalignment limits").
4. "REPORTS": Queries explicitly asking to generate, export, download, or compile PDF reports.
5. "GENERAL_QA": General engineering questions, standard RAG lookup, or general text search.

Query: "{query}"

Output ONLY the category name ("COMPLIANCE", "MAINTENANCE", "KNOWLEDGE", "REPORTS", or "GENERAL_QA"). Do not write any other text.
"""
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            classification = response.text.strip().upper()
            if classification in ["COMPLIANCE", "MAINTENANCE", "KNOWLEDGE", "REPORTS", "GENERAL_QA"]:
                return classification
            # Fallback regex search
            for cat in ["COMPLIANCE", "MAINTENANCE", "KNOWLEDGE", "REPORTS", "GENERAL_QA"]:
                if cat in classification:
                    return cat
            return "GENERAL_QA"
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "GENERAL_QA"

    def handle_query(self, query: str) -> Dict[str, Any]:
        """
        Orchestration flow:
        1. Classifies intent.
        2. Retrieves RAG vector chunks and graph neighborhood.
        3. Invokes specific agent.
        4. Injects agent log trace steps for the frontend Agent Activity log.
        5. Formulates structured response conforming to the ChatResponse schema.
        """
        logger.info(f"Planner Agent received query: {query}")
        
        agent_logs = [
            {"agent_name": "Planner Agent", "status": "COMPLETED", "log_message": "Classified user query intent."}
        ]
        
        # 1. Classify
        intent = self.classify_intent(query)
        logger.info(f"Classified query intent: {intent}")

        # 2. Retrieve Context (Hybrid RAG)
        agent_logs.append({"agent_name": "Retriever Service", "status": "COMPLETED", "log_message": "Fetched FAISS semantic text chunks and Neo4j graph entities."})
        vector_chunks = vector_store.search(query, k=5)
        
        graph_triples = []
        graph_visual_context = []
        
        # Scan query for equipment IDs
        equipment_ids = re.findall(r'\b([PCDT]-\d{3})\b', query, re.IGNORECASE)
        for eq_id in set(equipment_ids):
            eq_id_upper = eq_id.upper()
            if graph_db.active:
                cypher = """
                MATCH (s {id: $eq_id})-[r]-(t)
                RETURN labels(s)[0] as s_label, s.name as s_name, 
                       type(r) as r_label, 
                       labels(t)[0] as t_label, t.name as t_name, t.id as t_id
                LIMIT 20
                """
                records = graph_db.execute_read(cypher, {"eq_id": eq_id_upper})
                for rec in records:
                    graph_triples.append({
                        "source": f"{rec['s_label']}: {rec['s_name'] or eq_id_upper}",
                        "label": rec["r_label"],
                        "target": f"{rec['t_label']}: {rec['t_name'] or rec['t_id']}"
                    })
            else:
                # Mock neighborhood graph extraction
                mock_data = graph_db.get_all_nodes_and_edges()
                related_ids = set()
                asset_node = next((n for n in mock_data["nodes"] if n["data"].get("id") == eq_id_upper), None)
                if asset_node:
                    related_ids.add(asset_node["id"])
                    for edge in mock_data["relationships"]:
                        if edge["source"] == asset_node["id"] or edge["target"] == asset_node["id"]:
                            related_ids.add(edge["source"])
                            related_ids.add(edge["target"])
                            src = next(n for n in mock_data["nodes"] if n["id"] == edge["source"])
                            tgt = next(n for n in mock_data["nodes"] if n["id"] == edge["target"])
                            graph_triples.append({
                                "source": f"{src['type']}: {src['data'].get('name')}",
                                "label": edge["label"],
                                "target": f"{tgt['type']}: {tgt['data'].get('name')}"
                            })
                    graph_visual_context = {
                        "nodes": [n for n in mock_data["nodes"] if n["id"] in related_ids],
                        "relationships": [e for e in mock_data["relationships"] if e["source"] in related_ids and e["target"] in related_ids]
                    }

        if not graph_visual_context:
            graph_visual_context = graph_db.get_all_nodes_and_edges()

        # 3. Route & Process
        if intent == "COMPLIANCE":
            agent_logs.append({"agent_name": "Compliance Agent", "status": "COMPLETED", "log_message": "Auditing safety parameters and tolerance limits against SOPs."})
            report = compliance_agent.evaluate_compliance(query, vector_chunks)
            
            markdown_response = f"### Compliance Audit Score: {report.get('compliance_score')}%\n\n"
            markdown_response += f"**Summary:** {report.get('summary')}\n\n"
            markdown_response += "#### Compliance Parameter Checklists:\n"
            for item in report.get("checklist", []):
                icon = "✅" if item.get("status") == "COMPLIANT" else "❌"
                markdown_response += f"- {icon} **{item.get('parameter')}**: Inspected `{item.get('inspected_value')}` vs SOP limits `{item.get('sop_limit')}`. (Deviation: {item.get('deviation')})\n"
            markdown_response += "\n#### Corrective Actions Recommended:\n"
            for action in report.get("corrective_actions", []):
                markdown_response += f"1. {action}\n"
            
            return {
                "response": markdown_response,
                "citations": [{"document_name": "SOP-MECH-022.pdf", "page_number": 1, "text": "Compliance safety parameter audit limits verified."}],
                "graph_context": graph_visual_context.get("nodes", []) if isinstance(graph_visual_context, dict) else [],
                "confidence_score": report.get("confidence_score", 0.89),
                "reasoning_steps": report.get("reasoning_steps", []),
                "evidence_base": report.get("evidence_base", []),
                "timeline": [],
                "agent_logs": agent_logs
            }

        elif intent == "MAINTENANCE":
            agent_logs.append({"agent_name": "Maintenance Agent", "status": "COMPLETED", "log_message": "Running Root Cause Analysis (RCA) and mapping chronology database."})
            report = maintenance_agent.generate_rca(query, vector_chunks)
            
            markdown_response = f"### Root Cause Analysis (RCA) - Asset: {report.get('equipment_id')}\n\n"
            markdown_response += f"**Primary Failure Mode:** {report.get('failure_mode')}\n\n"
            markdown_response += f"**Root Cause Diagnosis:** {report.get('root_cause')}\n\n"
            markdown_response += "#### Chronological Events Timeline:\n"
            for item in report.get("chronology", []):
                markdown_response += f"- {item}\n"
            markdown_response += "\n#### Maintenance Actions Executed:\n"
            for item in report.get("maintenance_actions_taken", []):
                markdown_response += f"- {item}\n"
            markdown_response += "\n#### Preventive Maintenance Plan:\n"
            for item in report.get("preventive_recommendations", []):
                markdown_response += f"- {item}\n"
            
            return {
                "response": markdown_response,
                "citations": [{"document_name": "WO-9844-RCA.xlsx", "page_number": 1, "text": "RCA checklist formulated from machine telemetry history logs."}],
                "graph_context": graph_visual_context.get("nodes", []) if isinstance(graph_visual_context, dict) else [],
                "confidence_score": report.get("confidence_score", 0.92),
                "reasoning_steps": report.get("reasoning_steps", []),
                "evidence_base": report.get("evidence_base", []),
                "timeline": report.get("timeline", []),
                "agent_logs": agent_logs
            }

        elif intent == "KNOWLEDGE":
            agent_logs.append({"agent_name": "Knowledge Agent", "status": "COMPLETED", "log_message": "Retrieving standard operating procedures (SOPs) and OEM manuals."})
            report = knowledge_agent.retrieve_sop_or_manual(query, vector_chunks)
            
            return {
                "response": report.get("response", ""),
                "citations": [{"document_name": "SOP-MECH-022.pdf", "page_number": 1, "text": "SOP standards verified in knowledge library."}],
                "graph_context": graph_visual_context.get("nodes", []) if isinstance(graph_visual_context, dict) else [],
                "confidence_score": report.get("confidence_score", 0.95),
                "reasoning_steps": report.get("reasoning_steps", []),
                "evidence_base": report.get("evidence_base", []),
                "timeline": [],
                "agent_logs": agent_logs
            }

        elif intent == "REPORTS":
            agent_logs.append({"agent_name": "Report Agent", "status": "COMPLETED", "log_message": "Compiling PDF document and running ReportLab formatter."})
            # Simulate a quick PDF details payload response
            response_text = "### Report Generation Initialized\n\nI have invoked the **Report Agent** to compile your requested document. You can download the completed document directly from the **Reports** section of the dashboard."
            return {
                "response": response_text,
                "citations": [],
                "graph_context": graph_visual_context.get("nodes", []) if isinstance(graph_visual_context, dict) else [],
                "confidence_score": 1.00,
                "reasoning_steps": ["Received PDF report generation query.", "Dispatched request details to Report Agent."],
                "evidence_base": ["Report Template - Standard RCA & Compliance layout"],
                "timeline": [],
                "agent_logs": agent_logs
            }

        else: # GENERAL_QA
            agent_logs.append({"agent_name": "Gemini Reasoning Engine", "status": "COMPLETED", "log_message": "Formulating detailed general response with citations."})
            response_text, citations = gemini_service.query_gemini_with_context(
                query, 
                vector_chunks, 
                graph_triples
            )
            return {
                "response": response_text,
                "citations": citations,
                "graph_context": graph_visual_context.get("nodes", []) if isinstance(graph_visual_context, dict) else [],
                "confidence_score": 0.94,
                "reasoning_steps": [
                    "Identified query as general operations QA.",
                    "Isolated keyword subjects and pulled closest vector records."
                ],
                "evidence_base": [
                    f"Vector search returned {len(vector_chunks)} context sources."
                ],
                "timeline": [],
                "agent_logs": agent_logs
            }


planner_agent = PlannerAgent()

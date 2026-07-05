import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from app.core.config import settings
from app.services.graph_db import graph_db

logger = logging.getLogger(__name__)

# Predefined lists of known entities for dictionary matching
KNOWN_ENGINEERS = ["elena rostova", "marcus vance", "john doe", "sarah connor"]
KNOWN_LOCATIONS = ["train 2", "centurion plant", "compressor deck", "pump house"]
KNOWN_PARTS = ["impeller kit k-402", "mechanical seal s-100", "journal bearing j-50", "rotor shaft rs-10"]


def rule_based_extract(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extracts structured entities deterministically using regular expressions
    and vocabulary matching.
    """
    text_lower = text.lower()
    entities = {
        "Machine": [],
        "SOP": [],
        "Engineer": [],
        "Location": [],
        "SparePart": []
    }
    
    # 1. Matches Asset IDs like P-102, C-301, T-502
    machine_matches = re.findall(r'\b([PCDT]-\d{3})\b', text, re.IGNORECASE)
    for m in set(machine_matches):
        m_upper = m.upper()
        # Determine machine type
        m_type = "Pump" if m_upper.startswith("P") else ("Compressor" if m_upper.startswith("C") else "Turbine")
        entities["Machine"].append({
            "id": m_upper,
            "name": f"{m_type} {m_upper}",
            "type": m_type,
            "status": "OPERATIONAL"
        })
        
    # 2. Matches SOP codes like SOP-MECH-022, SOP-ELEC-101
    sop_matches = re.findall(r'\b(SOP-[A-Z]+-\d{3})\b', text, re.IGNORECASE)
    for s in set(sop_matches):
        entities["SOP"].append({
            "id": s.upper(),
            "title": f"Standard Procedure {s.upper()}",
            "code": s.upper()
        })
        
    # 3. Dictionary matching for Engineers
    for eng in KNOWN_ENGINEERS:
        if eng in text_lower:
            # Capitalize name nicely
            name = " ".join([w.capitalize() for w in eng.split()])
            initials = "".join([w[0].upper() for w in eng.split()])
            entities["Engineer"].append({
                "id": f"ENG-{initials}",
                "name": name,
                "specialization": "Maintenance Specialist"
            })
            
    # 4. Dictionary matching for Locations
    for loc in KNOWN_LOCATIONS:
        if loc in text_lower:
            loc_id = "LOC-" + loc.upper().replace(" ", "_")
            entities["Location"].append({
                "id": loc_id,
                "name": loc.title()
            })
            
    # 5. Dictionary matching for Spare Parts
    for part in KNOWN_PARTS:
        if part in text_lower:
            # Extract code (e.g. k-402)
            code_match = re.search(r'([ksj]-\d{3})', part, re.IGNORECASE)
            part_id = "PART-" + (code_match.group(1).upper() if code_match else part.upper().replace(" ", "_"))
            entities["SparePart"].append({
                "id": part_id,
                "name": part.title(),
                "part_number": code_match.group(1).upper() if code_match else "UNKNOWN"
            })
            
    return entities


def extract_semantic_relations_with_gemini(
    text: str, 
    extracted_entities: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Uses Gemini 2.5 Flash to extract semantic relationships and complex entities
    (e.g., Failures, MaintenanceRecords) that connect our rule-based entities.
    """
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("Gemini API key not configured. Skipping semantic relationship extraction.")
        return []
        
    # Format entities to guide Gemini
    entity_summary = json.dumps(extracted_entities, indent=2)
    
    prompt = f"""
You are an expert industrial knowledge graph building agent.
We have already extracted these basic entities from an industrial report:
{entity_summary}

Here is the document text:
---
{text}
---

Your task is to identify:
1. Complex entities:
   - "Failure" (symptom, root_cause, severity)
   - "MaintenanceRecord" (id/work_order, date, action_taken, cost, duration)
   - "InspectionReport" (id, date, score)
2. Relationships (edges) connecting ANY of the entities:
   - Engineer PERFORMED MaintenanceRecord
   - MaintenanceRecord ON_MACHINE Machine
   - InspectionReport INSPECTED Machine
   - InspectionReport RECORDED Failure
   - Failure OCCURRED_ON Machine
   - Machine LOCATED_AT Location
   - Machine USES_PART SparePart
   - MaintenanceRecord REPLACED SparePart
   - MaintenanceRecord FOLLOWED_SOP SOP

Provide your response in EXACT JSON format containing two arrays: "nodes" (for newly discovered complex entities, each must have a unique ID like "FAIL-P-102-1" or "WO-9912") and "relationships" (specifying source_id, target_id, relation_type, and attributes).

Format:
{{
  "nodes": [
    {{
      "type": "Failure",
      "properties": {{
        "id": "FAIL-P-102-2",
        "symptom": "cavitation and flow drop",
        "root_cause": "clogged suction strainer",
        "severity": "MEDIUM"
      }}
    }}
  ],
  "relationships": [
    {{
      "source_id": "ENG-ER",
      "target_id": "WO-9844",
      "relation_type": "PERFORMED",
      "properties": {{}}
    }}
  ]
}}
Do not write markdown formatting (like ```json) or explanation outside the JSON string.
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        data = json.loads(response.text.strip())
        return data
    except Exception as e:
        logger.error(f"Gemini relationship extraction failed: {e}")
        return {"nodes": [], "relationships": []}


def extract_and_sync_entities(filename: str, text: str) -> None:
    """
    Main pipeline: runs rule-based parser, queries Gemini for relationships,
    and updates the active Neo4j graph database.
    """
    logger.info(f"Running hybrid entity extraction on {filename}")
    
    # 1. Rule-based extraction
    rules_entities = rule_based_extract(text)
    
    # 2. Sync rule-based entities to Neo4j
    for label, node_list in rules_entities.items():
        for node in node_list:
            cypher = f"MERGE (n:{label} {{id: $id}}) SET n += $properties"
            graph_db.execute_write(cypher, {"id": node["id"], "properties": node})
            
    # 3. Semantic extraction via Gemini
    semantic_data = extract_semantic_relations_with_gemini(text, rules_entities)
    
    # 4. Sync semantic nodes
    for node in semantic_data.get("nodes", []):
        lbl = node.get("type")
        props = node.get("properties", {})
        if lbl and props.get("id"):
            cypher = f"MERGE (n:{lbl} {{id: $id}}) SET n += $properties"
            graph_db.execute_write(cypher, {"id": props["id"], "properties": props})
            
    # 5. Sync relationships
    for rel in semantic_data.get("relationships", []):
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_type = rel.get("relation_type")
        props = rel.get("properties", {})
        
        if source_id and target_id and rel_type:
            # We don't know the labels of source and target, so match generally by id property
            cypher = f"""
            MATCH (s {{id: $source_id}})
            MATCH (t {{id: $target_id}})
            MERGE (s)-[r:{rel_type}]->(t)
            SET r += $properties
            """
            graph_db.execute_write(cypher, {
                "source_id": source_id,
                "target_id": target_id,
                "properties": props
            })
            
    logger.info("Hybrid entity extraction completed and synced to Graph Database.")

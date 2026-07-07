import os
import re
import json
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from app.core.config import settings
from app.services.graph_db import graph_db

logger = logging.getLogger(__name__)

# Neo4j label/relationship-type safety validation, and all Cypher
# construction for node/relationship upserts, now lives centrally in
# app.services.graph_db (see upsert_node/upsert_relationship) — this module
# only ever hands it plain extracted data.

# Dictionary-matching vocabularies for Engineer/Location/SparePart entities. These are
# intentionally empty by default so entity extraction only ever reflects names/terms
# that are actually present in documents a user uploads — never a predefined demo set.
#
# To try the extractor against the optional Centurion Plant sample dataset, import
# CENTURION_KNOWN_ENGINEERS / CENTURION_KNOWN_LOCATIONS / CENTURION_KNOWN_PARTS from
# app.services.seed_data and assign them here manually; they are not wired in by default.
KNOWN_ENGINEERS: List[str] = []
KNOWN_LOCATIONS: List[str] = []
KNOWN_PARTS: List[str] = []

# General-purpose technology/skill lexicon used for dictionary matching across any
# uploaded document (resumes, tickets, reports, etc.) — this is a generic real-world
# vocabulary, not data tied to any specific demo company or plant.
KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "swift",
    "react", "react.js", "next.js", "vue", "angular", "node.js", "express.js", "django", "flask",
    "fastapi", "spring", "spring boot", ".net",
    "html", "css", "tailwind",
    "sql", "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform", "ci/cd", "jenkins",
    "git", "github", "gitlab", "linux", "unix",
    "machine learning", "deep learning", "nlp", "data science", "pandas", "numpy", "tensorflow", "pytorch",
    "rest api", "graphql", "websockets", "microservices",
    "agile", "scrum", "devops",
]

# Common patterns for organization-name suffixes (used to bias the capitalized-phrase
# heuristic toward genuine organizations rather than arbitrary Title Case text).
_ORG_SUFFIXES = (
    "University", "Institute", "College", "School", "Inc", "Inc.", "LLC", "Ltd", "Ltd.",
    "Pvt", "Corp", "Corporation", "Technologies", "Systems", "Solutions", "Company", "Co.",
    "Labs", "Group", "Foundation",
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Word-connector is [ \t]+ (not \s+) so matches never span across line breaks —
# otherwise unrelated preceding text (e.g. a section heading) gets swept in.
_ORG_RE = re.compile(
    r"\b([A-Z][\w&.]*(?:[ \t]+[A-Z][\w&.]*){0,4}[ \t]+(?:" + "|".join(re.escape(s) for s in _ORG_SUFFIXES) + r")\.?)\b"
)
# Matches common date formats: "May 2025", "May 2025 - July 2025", "2026-05-14", "05/14/2026"
_DATE_RE = re.compile(
    r"\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{2,4})\b",
    re.IGNORECASE,
)


def rule_based_extract(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extracts structured entities deterministically using regular expressions
    and vocabulary matching — never fabricated, only whatever literally appears
    in the given document text.
    """
    text_lower = text.lower()
    entities = {
        "Machine": [],
        "SOP": [],
        "Engineer": [],
        "Location": [],
        "SparePart": [],
        "Organization": [],
        "Skill": [],
        "Date": [],
        "Contact": [],
    }

    # 1. Matches Asset IDs like P-102, C-301, T-502 (industrial equipment tagging convention)
    machine_matches = re.findall(r'\b([PCDT]-\d{3})\b', text, re.IGNORECASE)
    for m in set(machine_matches):
        m_upper = m.upper()
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

    # 3. Dictionary matching for Engineers (opt-in vocabulary, empty by default)
    for eng in KNOWN_ENGINEERS:
        if eng in text_lower:
            name = " ".join([w.capitalize() for w in eng.split()])
            initials = "".join([w[0].upper() for w in eng.split()])
            entities["Engineer"].append({
                "id": f"ENG-{initials}",
                "name": name,
                "specialization": "Maintenance Specialist"
            })

    # 4. Dictionary matching for Locations (opt-in vocabulary, empty by default)
    for loc in KNOWN_LOCATIONS:
        if loc in text_lower:
            loc_id = "LOC-" + loc.upper().replace(" ", "_")
            entities["Location"].append({
                "id": loc_id,
                "name": loc.title()
            })

    # 5. Dictionary matching for Spare Parts (opt-in vocabulary, empty by default)
    for part in KNOWN_PARTS:
        if part in text_lower:
            code_match = re.search(r'([ksj]-\d{3})', part, re.IGNORECASE)
            part_id = "PART-" + (code_match.group(1).upper() if code_match else part.upper().replace(" ", "_"))
            entities["SparePart"].append({
                "id": part_id,
                "name": part.title(),
                "part_number": code_match.group(1).upper() if code_match else "UNKNOWN"
            })

    # 6. Generic organization-name detection (companies, universities, institutions)
    for org in set(m.strip() for m in _ORG_RE.findall(text)):
        entities["Organization"].append({
            "id": "ORG-" + re.sub(r"\W+", "_", org.upper()).strip("_"),
            "name": org,
        })

    # 7. Generic skill/technology dictionary matching
    for skill in KNOWN_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            entities["Skill"].append({
                "id": "SKILL-" + re.sub(r"\W+", "_", skill.upper()).strip("_"),
                "name": skill.title(),
            })

    # 8. Generic date mentions (useful for timelines, tenure ranges, deadlines, etc.)
    for date_str in set(m.strip() for m in _DATE_RE.findall(text)):
        entities["Date"].append({
            "id": "DATE-" + re.sub(r"\W+", "_", date_str.upper()).strip("_"),
            "value": date_str,
        })

    # 9. Contact emails (useful anchor entities for Person nodes)
    for email in set(_EMAIL_RE.findall(text)):
        entities["Contact"].append({
            "id": "CONTACT-" + re.sub(r"\W+", "_", email.upper()),
            "email": email,
        })

    return entities


def extract_semantic_relations_with_gemini(
    text: str,
    extracted_entities: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Uses Gemini to extract semantic entities and relationships that connect our
    rule-based entities — covering people, organizations, skills, projects,
    technologies, and dates found in ANY kind of uploaded document (resumes,
    tickets, reports, manuals, etc.), not just industrial equipment records.
    """
    empty_result = {"nodes": [], "relationships": []}

    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("Gemini API key not configured. Skipping semantic relationship extraction.")
        return empty_result

    # Format entities to guide Gemini
    entity_summary = json.dumps(extracted_entities, indent=2)

    prompt = f"""
You are an expert knowledge graph extraction agent. Extract entities and relationships
strictly and only from the document text provided below — never invent entities that
are not present in it. The document could be anything: a resume, an event ticket, a
maintenance report, a contract, or a technical manual — infer the right entities from
its actual content, not from any assumed domain.

We have already extracted these basic entities from the document:
{entity_summary}

Here is the document text:
---
{text}
---

Your task is to identify, wherever actually present in the text:
1. Entities:
   - "Person" (name, role/title if stated)
   - "Organization" (name, and role such as employer, university, or event host)
   - "Skill" (name, e.g. a technology, programming language, or competency)
   - "Project" (name, description, technologies used)
   - "Event" (name, date, location)
   - Any domain-specific complex entities actually described in the text (e.g. "Failure",
     "MaintenanceRecord", "InspectionReport" for industrial/maintenance documents)
2. Relationships (edges) connecting ANY of the entities, for example:
   - Person WORKED_AT Organization
   - Person HAS_SKILL Skill
   - Person WORKED_ON Project
   - Project USES_TECHNOLOGY Skill
   - Person ATTENDED Event
   - Person STUDIED_AT Organization
   - (or industrial relations like MaintenanceRecord ON_MACHINE Machine, when relevant)

Provide your response in EXACT JSON format containing two arrays: "nodes" (for newly
discovered entities, each with a unique ID such as "PERSON-JOHN-DOE" or "ORG-ACME-INC")
and "relationships" (specifying source_id, target_id, relation_type, and attributes).

Format:
{{
  "nodes": [
    {{
      "type": "Person",
      "properties": {{
        "id": "PERSON-JANE-DOE",
        "name": "Jane Doe",
        "role": "Software Engineer Intern"
      }}
    }}
  ],
  "relationships": [
    {{
      "source_id": "PERSON-JANE-DOE",
      "target_id": "ORG-ACME-INC",
      "relation_type": "WORKED_AT",
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
        if not isinstance(data, dict):
            logger.warning("Gemini semantic extraction returned an unexpected shape; ignoring.")
            return empty_result
        data.setdefault("nodes", [])
        data.setdefault("relationships", [])
        return data
    except Exception as e:
        logger.error(f"Gemini relationship extraction failed: {e}")
        return empty_result


def extract_and_sync_entities(filename: str, text: str, user_id: str, document_id: str) -> None:
    """
    Main pipeline: runs rule-based parser, queries Gemini for relationships,
    and updates the active Neo4j graph database.

    Every node id is scoped to `user_id` only (never `document_id`), so the
    SAME entity mentioned across several of one user's documents becomes
    exactly ONE node/edge referenced by several documents — never one
    duplicate per document — while entities still never cross user
    boundaries (one user's graph data can never be matched into another
    user's retrieval/answers). Each node/relationship keeps a `document_ids`
    array of every document that currently references it (see
    graph_db.upsert_node/upsert_relationship); deleting a document removes
    its ID from that array and only deletes the node/relationship outright
    once no uploaded document references it anymore (see
    graph_db.remove_document_entities) — so a shared entity is never wiped
    out just because ONE of the documents mentioning it was deleted.

    A `Document` node is also created for this upload, with a `MENTIONS`
    relationship to every entity extracted from it — turning the graph into
    a real document-provenance graph (you can query "which documents mention
    X"), not just a flat bag of entities.
    """
    logger.info(f"Running hybrid entity extraction on {filename} (user_id={user_id}, document_id={document_id})")

    def scoped(raw_id: str) -> str:
        return f"{raw_id}::{user_id}"

    doc_node_id = graph_db.upsert_document(document_id, filename, user_id)

    # 1. Rule-based extraction
    rules_entities = rule_based_extract(text)
    rule_count = sum(len(v) for v in rules_entities.values())
    logger.info(f"Rule-based extraction found {rule_count} entities in {filename}: "
                f"{ {k: len(v) for k, v in rules_entities.items()} }")

    # 2. Sync rule-based entities to Neo4j, scoped per-user; merged across
    # this user's documents (see scoped() above)
    for label, node_list in rules_entities.items():
        for node in node_list:
            node_id = scoped(node["id"])
            props = {**node, "id": node_id, "user_id": user_id}
            graph_db.upsert_node(label, node_id, props, document_id)
            graph_db.link_mention(doc_node_id, node_id)

    # 3. Semantic extraction via Gemini (works with the original, unscoped ids
    # it generates itself; everything is scoped uniformly at sync time below)
    semantic_data = extract_semantic_relations_with_gemini(text, rules_entities)
    logger.info(f"Semantic extraction found {len(semantic_data.get('nodes', []))} node(s) and "
                f"{len(semantic_data.get('relationships', []))} relationship(s) in {filename}")

    # 4. Sync semantic nodes, scoped per-user; merged across this user's
    # documents
    for node in semantic_data.get("nodes", []):
        label = node.get("type") or "Entity"
        props = node.get("properties", {})
        raw_id = props.get("id")
        if raw_id:
            node_id = scoped(raw_id)
            scoped_props = {**props, "id": node_id, "user_id": user_id}
            graph_db.upsert_node(label, node_id, scoped_props, document_id)
            graph_db.link_mention(doc_node_id, node_id)

    # 5. Sync relationships, scoped per-user (same scoping applies uniformly
    # whether source/target came from rule-based extraction or Gemini);
    # merged across documents that independently assert the same edge
    for rel in semantic_data.get("relationships", []):
        source_id = rel.get("source_id")
        target_id = rel.get("target_id")
        rel_type = rel.get("relation_type") or "RELATED_TO"
        props = rel.get("properties", {})

        if source_id and target_id:
            graph_db.upsert_relationship(scoped(source_id), scoped(target_id), rel_type, props, document_id)

    logger.info("Hybrid entity extraction completed and synced to Graph Database.")

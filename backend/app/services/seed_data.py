"""
Optional demo/sample dataset for the Centurion Petrochemical Plant.

Nothing in this module is imported or used automatically by the runtime.
It exists purely so a sample knowledge graph can be loaded on demand, e.g.
via `POST /api/v1/graph/reseed` (see app.services.graph_db.load_centurion_mock_graph).

The application's real behavior — RAG answers, entity extraction, and the
knowledge graph — is driven entirely by whatever documents a user actually
uploads. This file must never be imported by default from a code path that
runs automatically.
"""

CENTURION_MOCK_NODES = [
    # Locations
    {"id": "n1",  "type": "Location",         "data": {"id": "LOC-T2",        "name": "Train 2 Processing Area",        "label": "Location: Train 2"}},
    {"id": "n11", "type": "Location",         "data": {"id": "LOC-UTIL",      "name": "Train 2 Utility Bay",            "label": "Location: Utility Bay"}},
    # Machines
    {"id": "n2",  "type": "Machine",          "data": {"id": "P-102",         "name": "Centrifugal Pump P-102",         "type": "Pump",       "status": "OPERATIONAL", "label": "Machine: Pump P-102"}},
    {"id": "n3",  "type": "Machine",          "data": {"id": "C-301",         "name": "Reciprocating Compressor C-301", "type": "Compressor", "status": "WARNING",     "label": "Machine: Compressor C-301"}},
    # Engineers
    {"id": "n4",  "type": "Engineer",         "data": {"id": "ENG-ER",        "name": "Elena Rostova",  "specialization": "Rotary Equipment",    "label": "Engineer: Elena Rostova"}},
    {"id": "n5",  "type": "Engineer",         "data": {"id": "ENG-MV",        "name": "Marcus Vance",   "specialization": "Vibration Specialist", "label": "Engineer: Marcus Vance"}},
    {"id": "n12", "type": "Engineer",         "data": {"id": "OPR-AM",        "name": "Ahmad Malik",    "specialization": "Operator - Train 2",   "label": "Operator: Ahmad Malik"}},
    # Spare Parts
    {"id": "n6",  "type": "SparePart",        "data": {"id": "PART-IMP402",   "name": "Impeller Kit K-402",    "part_number": "IMP-402",   "stock": 4, "label": "SparePart: Impeller Kit"}},
    {"id": "n13", "type": "SparePart",        "data": {"id": "PART-SEAL-S100","name": "Mechanical Seal S-100", "part_number": "SEAL-S100", "stock": 7, "label": "SparePart: Seal S-100"}},
    # Failure
    {"id": "n7",  "type": "Failure",          "data": {"id": "FAIL-P102-1",   "symptom": "High vibration and seal leakage", "root_cause": "Misaligned shaft and worn impeller bearings", "severity": "CRITICAL", "label": "Failure: Vibrations/Leak"}},
    # Maintenance Records
    {"id": "n8",  "type": "MaintenanceRecord","data": {"id": "WO-9844",        "date": "2026-05-14", "action_taken": "Shaft realigned, Impeller Kit K-402 and Seal S-100 replaced", "label": "Maintenance: WO-9844"}},
    # SOPs
    {"id": "n9",  "type": "SOP",              "data": {"id": "SOP-MECH-022",  "title": "Standard Shaft Alignment Protocol", "code": "SOP-MECH-022", "label": "SOP: Shaft Alignment"}},
    # Inspection Reports
    {"id": "n10", "type": "InspectionReport", "data": {"id": "INSP-P102-JUN2026","date": "2026-06-28", "checklist_version": "v1.2", "score": 75, "label": "Inspection: INSP-P102-JUN2026"}},
    {"id": "n14", "type": "InspectionReport", "data": {"id": "INSP-C301-JUN2026","date": "2026-06-30", "checklist_version": "v1.1", "score": 68, "label": "Inspection: INSP-C301-JUN2026"}},
]

CENTURION_MOCK_EDGES = [
    # Spatial / location hierarchy
    {"id": "e1",  "source": "n2",  "target": "n1",  "label": "LOCATED_AT"},
    {"id": "e2",  "source": "n3",  "target": "n1",  "label": "LOCATED_AT"},
    {"id": "e15", "source": "n11", "target": "n1",  "label": "PART_OF"},
    {"id": "e16", "source": "n13", "target": "n11", "label": "STORED_IN"},
    # Maintenance work order chains
    {"id": "e3",  "source": "n8",  "target": "n2",  "label": "ON_MACHINE"},
    {"id": "e4",  "source": "n4",  "target": "n8",  "label": "PERFORMED"},
    {"id": "e5",  "source": "n8",  "target": "n6",  "label": "REPLACED_WITH"},
    {"id": "e17", "source": "n8",  "target": "n13", "label": "REPLACED_WITH"},
    {"id": "e10", "source": "n8",  "target": "n9",  "label": "FOLLOWED_SOP"},
    # Failure linkages
    {"id": "e6",  "source": "n7",  "target": "n2",  "label": "OCCURRED_ON"},
    {"id": "e7",  "source": "n8",  "target": "n7",  "label": "RESOLVED"},
    # Engineer responsibilities
    {"id": "e8",  "source": "n4",  "target": "n2",  "label": "RESPONSIBLE_FOR"},
    {"id": "e9",  "source": "n5",  "target": "n3",  "label": "RESPONSIBLE_FOR"},
    # Inspection → Machine / Failure / SOP
    {"id": "e11", "source": "n10", "target": "n2",  "label": "INSPECTED_ON"},
    {"id": "e12", "source": "n10", "target": "n7",  "label": "LOGGED_INCIDENT"},
    {"id": "e13", "source": "n10", "target": "n9",  "label": "COMPARED_TO"},
    {"id": "e18", "source": "n10", "target": "n9",  "label": "FOLLOWED_SOP"},
    {"id": "e19", "source": "n14", "target": "n3",  "label": "INSPECTED_ON"},
    # Operator conducted inspections
    {"id": "e20", "source": "n12", "target": "n10", "label": "CONDUCTED_BY"},
    {"id": "e21", "source": "n12", "target": "n14", "label": "CONDUCTED_BY"},
]

# Optional demo vocabulary for app.services.entity_extractor's rule-based dictionary
# matching. NOT imported by entity_extractor.py by default — real deployments should
# only extract entities that are actually present in uploaded documents. Wire these
# in manually (see the comment in entity_extractor.py) if you want the sample dataset
# to also drive dictionary-based entity matching.
CENTURION_KNOWN_ENGINEERS = ["elena rostova", "marcus vance", "john doe", "sarah connor"]
CENTURION_KNOWN_LOCATIONS = ["train 2", "centurion plant", "compressor deck", "pump house"]
CENTURION_KNOWN_PARTS = ["impeller kit k-402", "mechanical seal s-100", "journal bearing j-50", "rotor shaft rs-10"]

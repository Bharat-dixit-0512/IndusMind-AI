from fastapi import APIRouter, Depends, status
from app.services.graph_db import graph_db
from app.api.deps import get_current_user, RoleChecker
from app.models.user import User, UserRole

router = APIRouter()
require_admin = RoleChecker([UserRole.ADMIN])


@router.get("/")
def get_graph_data(
    current_user: User = Depends(get_current_user)
):
    """
    Returns nodes and relationships formatted for React Flow frontend rendering,
    restricted to entities extracted from this user's own documents (plus any
    ownerless legacy/demo-seeded nodes) — never another user's entities.
    """
    return graph_db.get_owned_graph(str(current_user.id))


@router.get("/patterns")
def get_recurring_patterns(
    current_user: User = Depends(get_current_user)
):
    """
    Surfaces entities that recur across two or more of this user's own
    documents (e.g. the same machine mentioned in a work order AND an
    inspection report) — a minimal "lessons learned" / cross-document pattern
    intelligence feature built on the Document→MENTIONS→Entity provenance
    graph populated at ingestion time.
    """
    patterns = graph_db.find_recurring_entities(str(current_user.id))
    return {"patterns": patterns}


@router.post("/reseed", status_code=status.HTTP_200_OK)
def reseed_graph_database(
    current_user: User = Depends(require_admin)
):
    """
    Resets and re-seeds the graph with the optional Centurion Petrochemical
    Plant demo dataset. ADMIN-only: this repopulates a shared, ownerless demo
    layer visible to every user, so it must not be triggerable by any random
    authenticated account.
    """
    graph_db.load_centurion_mock_graph()
    return {"detail": "Mock graph database successfully seeded"}

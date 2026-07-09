from fastapi import APIRouter, Depends
from app.services.graph_db import graph_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/")
def get_graph_data(
    current_user: User = Depends(get_current_user)
):
    """
    Returns nodes and relationships formatted for React Flow frontend rendering,
    restricted to entities extracted from this user's own uploaded documents —
    never another user's entities, and never ownerless demo/seed data (the
    graph reflects only currently-uploaded documents).
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

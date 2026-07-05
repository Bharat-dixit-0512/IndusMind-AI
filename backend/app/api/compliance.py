from fastapi import APIRouter, Depends
from app.agents.compliance_agent import compliance_agent
from app.services.vector_store import vector_store
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/check")
def run_compliance_check(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an immediate compliance check against SOPs for a specific query/asset.
    """
    # Retrieve relevant vector chunks
    chunks = vector_store.search(query, k=5)
    report = compliance_agent.evaluate_compliance(query, chunks)
    return report

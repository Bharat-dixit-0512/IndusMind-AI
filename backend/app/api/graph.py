from fastapi import APIRouter, Depends, status
from app.services.graph_db import graph_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/")
def get_graph_data(
    current_user: User = Depends(get_current_user)
):
    """
    Returns the complete list of nodes and relationships formatted
    for React Flow frontend rendering.
    """
    return graph_db.get_all_nodes_and_edges()


@router.post("/reseed", status_code=status.HTTP_200_OK)
def reseed_graph_database(
    current_user: User = Depends(get_current_user)
):
    """
    Resets and re-seeds the graph with the Centurion Petrochemical Plant baseline data.
    """
    graph_db.load_centurion_mock_graph()
    return {"detail": "Mock graph database successfully seeded"}

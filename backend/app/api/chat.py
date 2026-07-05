from fastapi import APIRouter, Depends
from app.schemas.chat import ChatQuery, ChatResponse
from app.agents.planner_agent import planner_agent
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def ask_chat_agent(
    query: ChatQuery,
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint for unified AI Chat.
    Intercepted by the central Planner Agent to orchestrate and format response
    with citations, confidence score, reasoning steps, timeline, and agent logs.
    """
    result = planner_agent.handle_query(query.message)
    return ChatResponse(
        response=result.get("response", ""),
        citations=result.get("citations", []),
        graph_context=result.get("graph_context", []),
        confidence_score=result.get("confidence_score", 0.90),
        reasoning_steps=result.get("reasoning_steps", []),
        evidence_base=result.get("evidence_base", []),
        timeline=result.get("timeline", []),
        agent_logs=result.get("agent_logs", []),
    )

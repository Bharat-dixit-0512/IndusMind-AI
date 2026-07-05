from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatQuery(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


class Citation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    text: str


class TimelineEvent(BaseModel):
    time: str
    event: str
    status: str  # "normal", "warning", "ignored", "failure", "repair"
    detail: str


class AgentLogStep(BaseModel):
    agent_name: str
    status: str  # "COMPLETED", "IN_PROGRESS", "SKIPPED"
    log_message: str


class ChatResponse(BaseModel):
    response: str
    citations: List[Citation]
    graph_context: Optional[List[dict]] = []
    
    # Explainability & Agentic enhancements
    confidence_score: float = 0.90
    reasoning_steps: List[str] = []
    evidence_base: List[str] = []
    timeline: Optional[List[TimelineEvent]] = []
    agent_logs: Optional[List[AgentLogStep]] = []

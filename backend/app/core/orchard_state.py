from typing import List, Dict, TypedDict, Any

from langchain_core.messages import BaseMessage

class OrchardState(TypedDict):
    """
    Represents the state of our LangGraph agent.
    """
    messages: List[BaseMessage] # The conversation history
    user_query: str | None
    image_urls: List[str] | None
    intent: str | None
    session_id: str | None
    
    orchard_profile: Dict[str, Any] | None
    is_profile_fetched: bool

    # 新增：证据矩阵和置信度结果（使用Dict避免序列化问题）
    evidence_matrix: Dict[str, Any] | None
    confidence_result: Dict[str, Any] | None

    # ... (rest of the state)

    realtime_weather: Dict[str, Any] | None
    historical_cases_retrieved: List[Dict[str, Any]] | None
    
    initial_diagnosis_suggestion: str | None
    intermediate_reasoning: str | None
    working_diagnosis: str | None # The current best guess for the diagnosis
    decision: str | None # "clarify" or "report"

    clarification_needed: bool
    clarification_count: int | None # Track number of clarifications
    clarification_question: str | None
    
    # LLM评判相关字段
    need_clarification: bool | None
    clarification_focus: str | None
    
    final_diagnosis_report: Dict[str, Any] | None
    final_report: Dict[str, Any] | None  # For dynamic engine final output
    confidence_score: float | None
    
    workflow_step: str
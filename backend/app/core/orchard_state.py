from typing import List, Dict, TypedDict, Any, Optional

from langchain_core.messages import BaseMessage

class OrchardState(TypedDict):
    """
    LangGraph Agent 的共享状态对象。
    在工作流各节点之间传递，积累诊断证据。
    """
    # ── 对话基础 ──────────────────────────────────────────────
    messages: List[BaseMessage]
    user_query: Optional[str]
    image_urls: Optional[List[str]]
    session_id: Optional[str]

    # ── 意图 ──────────────────────────────────────────────────
    intent: Optional[str]   # "Complex Diagnostic" / "Simple Q&A" / "Direct Tool-Use"

    # ── 果园档案 ──────────────────────────────────────────────
    orchard_profile: Optional[Dict[str, Any]]
    is_profile_fetched: bool

    # ── 感知层输出（视觉模型） ──────────────────────────────
    # vision_result 由 run_image_diagnosis 节点写入
    # 结构: {
    #   "top_k": [{"rank","class_en","class_zh","coarse_class","probability"}, ...],
    #   "top1_class": str, "top1_class_zh": str, "top1_coarse": str,
    #   "top1_prob": float,   # 视觉置信度 0~1
    #   "energy_score": float, "is_ood": bool,
    #   "fuzzy_disease_key": str | None,   # 对应模糊推理的疾病名（中文）
    #   "available": bool,                 # 本地模型是否成功推理
    #   "description": str,                # 多模态 LLM 描述（降级路径）
    # }
    vision_result: Optional[Dict[str, Any]]

    # ── 推理层输出（模糊推理引擎） ──────────────────────────
    # environmental_risk 由 parallel_context_acquisition 节点写入
    # 结构: {"炭疽病": {"risk_score": 72.5, "risk_level": "高风险", ...}, ...}
    environmental_risk: Optional[Dict[str, Any]]

    # ── 气象数据 & 历史病例 ───────────────────────────────────
    realtime_weather: Optional[Dict[str, Any]]
    historical_cases_retrieved: Optional[List[Dict[str, Any]]]

    # ── 证据矩阵 & 置信度（决策层核心） ─────────────────────
    evidence_matrix: Optional[Dict[str, Any]]
    confidence_result: Optional[Dict[str, Any]]

    # ── 置信度路由控制 ────────────────────────────────────────
    # fast_path: True 表示走快通路（高置信度直接确诊）
    fast_path: Optional[bool]
    # LLM 评判结果
    need_clarification: Optional[bool]
    clarification_focus: Optional[str]
    # 追问控制
    clarification_needed: bool
    clarification_count: Optional[int]
    clarification_question: Optional[str]

    # ── 中间诊断状态 ──────────────────────────────────────────
    initial_diagnosis_suggestion: Optional[str]
    intermediate_reasoning: Optional[str]
    working_diagnosis: Optional[str]
    decision: Optional[str]   # "clarify" / "report"
    confidence_score: Optional[float]

    # ── 最终输出 ──────────────────────────────────────────────
    treatment_knowledge: Optional[str]
    final_diagnosis_report: Optional[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]

    # ── 流程追踪 ──────────────────────────────────────────────
    workflow_step: str

"""
LangGraph 工作流状态图
======================
论文 5.4.2 工作流拓扑结构

优化后的拓扑（相比原版）：
  1. 入口路由保持不变（支持多轮追问）
  2. 意图识别：规则前置，LLM 兜底（-1 次 LLM 调用）
  3. 图像诊断节点：本地 CitrusHVT，降级 LLM（-10s 平均）
  4. parallel_context_acquisition：ThreadPoolExecutor 并发
     天气 API + 历史检索 + 模糊推理同时执行（-50% 等待时间）
  5. 置信度计算：快通路门控
     高置信 + 无OOD + 环境不冲突 → 跳过 LLM 评判（-3s）
  6. 快通路条件边：Fast-path 直接跳过智能追问
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.orchard_state import OrchardState

# ── 节点导入 ──────────────────────────────────────────────────
from app.agents.graph.intent_recognition_node import intent_recognition_node
from app.agents.graph.rag_qa_node import rag_qa_node
from app.agents.graph.direct_tool_call_node import direct_tool_call_node
from app.agents.graph.calculate_confidence_node import calculate_confidence_node
from app.agents.graph.smart_questioning_node import smart_questioning_node
from app.agents.graph.build_evidence_matrix_node import build_evidence_matrix_node
from app.agents.graph.process_user_response_node import process_user_response_node
from app.agents.tools.fetch_orchard_profile import fetch_orchard_profile
from app.agents.tools.run_image_diagnosis import run_image_diagnosis
from app.agents.tools.parallel_context_acquisition import parallel_context_acquisition
from app.agents.tools.retrieve_treatment_knowledge import retrieve_treatment_knowledge
from app.agents.graph.reasoning_nodes import generate_final_report
from app.agents.dynamic_engine.executor import dynamic_engine_executor


# ================================================================
# 路由函数
# ================================================================

def route_entry(state: OrchardState) -> str:
    """入口路由：判断是否为追问回答"""
    if state.get("clarification_needed"):
        return "process_user_response"
    return "intent_recognition"


def route_by_intent(state: OrchardState) -> str:
    """意图路由"""
    # 检查是否是用户对追问的回答
    if state.get("clarification_needed") and state.get("messages"):
        last = state.get("messages", [])[-1]
        if hasattr(last, "__class__") and last.__class__.__name__ == "HumanMessage":
            return "process_user_response"

    intent = state.get("intent", "Complex Diagnostic")
    if intent == "Complex Diagnostic":
        return "fetch_orchard_profile"
    elif intent == "Simple Q&A":
        return "rag_qa_node"
    elif intent == "Direct Tool-Use":
        return "direct_tool_call_node"
    else:
        return "fetch_orchard_profile"


def route_after_confidence(state: OrchardState) -> str:
    """
    置信度节点后的路由：
      fast_path=True  → 直接跳到 retrieve_treatment_knowledge（跳过追问）
      high confidence  → retrieve_treatment_knowledge
      low confidence   → smart_questioning（但不超过 3 次）
    """
    fast_path = state.get("fast_path", False)
    if fast_path:
        print("[Router] Fast-path → retrieve_treatment_knowledge")
        return "retrieve_treatment_knowledge"

    confidence_result = state.get("confidence_result") or {}
    confidence_score = confidence_result.get("confidence_score", 0.0)
    need_clarification = state.get("need_clarification")
    if need_clarification is None:
        need_clarification = state.get("clarification_needed", False)
    clarification_count = state.get("clarification_count") or 0

    print(f"[Router] confidence={confidence_score:.2f}, need_clarify={need_clarification}, "
          f"count={clarification_count}")

    if clarification_count >= 3:
        print("[Router] 追问上限，强制报告")
        return "retrieve_treatment_knowledge"

    if confidence_score >= 0.90:
        return "retrieve_treatment_knowledge"
    elif confidence_score >= 0.70 and not need_clarification:
        return "retrieve_treatment_knowledge"
    else:
        return "smart_questioning"


def route_after_smart_questioning(state: OrchardState) -> str:
    """追问节点后的路由"""
    if state.get("clarification_needed"):
        return END
    return "retrieve_treatment_knowledge"


# ================================================================
# 构建状态图
# ================================================================

workflow = StateGraph(OrchardState)

# ── 注册节点 ───────────────────────────────────────────────────
workflow.add_node("intent_recognition", intent_recognition_node)
workflow.add_node("fetch_orchard_profile", fetch_orchard_profile)
workflow.add_node("run_image_diagnosis", run_image_diagnosis)
workflow.add_node("parallel_context_acquisition", parallel_context_acquisition)
workflow.add_node("build_evidence_matrix", build_evidence_matrix_node)
workflow.add_node("calculate_confidence", calculate_confidence_node)
workflow.add_node("smart_questioning", smart_questioning_node)
workflow.add_node("retrieve_treatment_knowledge", retrieve_treatment_knowledge)
workflow.add_node("generate_final_report", generate_final_report)
workflow.add_node("process_user_response", process_user_response_node)
workflow.add_node("rag_qa_node", rag_qa_node)
workflow.add_node("direct_tool_call_node", direct_tool_call_node)
workflow.add_node("dynamic_engine", dynamic_engine_executor)

# ── 入口条件路由 ──────────────────────────────────────────────
workflow.set_conditional_entry_point(
    route_entry,
    {
        "process_user_response": "process_user_response",
        "intent_recognition": "intent_recognition",
    },
)

# ── 意图路由 ──────────────────────────────────────────────────
workflow.add_conditional_edges(
    "intent_recognition",
    route_by_intent,
    {
        "fetch_orchard_profile": "fetch_orchard_profile",
        "rag_qa_node": "rag_qa_node",
        "direct_tool_call_node": "direct_tool_call_node",
        "dynamic_engine": "dynamic_engine",
        "process_user_response": "process_user_response",
    },
)

# ── 主诊断路径 ────────────────────────────────────────────────
# fetch_orchard_profile → run_image_diagnosis → parallel_context_acquisition
# (注：图像诊断先执行，并行节点中再补充天气/历史/模糊推理)
workflow.add_edge("fetch_orchard_profile", "run_image_diagnosis")
workflow.add_edge("run_image_diagnosis", "parallel_context_acquisition")
workflow.add_edge("parallel_context_acquisition", "build_evidence_matrix")
workflow.add_edge("build_evidence_matrix", "calculate_confidence")

# ── 置信度后的快慢双回路 ──────────────────────────────────────
workflow.add_conditional_edges(
    "calculate_confidence",
    route_after_confidence,
    {
        "smart_questioning": "smart_questioning",
        "retrieve_treatment_knowledge": "retrieve_treatment_knowledge",
    },
)

# ── 追问节点 ──────────────────────────────────────────────────
workflow.add_conditional_edges(
    "smart_questioning",
    route_after_smart_questioning,
    {
        "retrieve_treatment_knowledge": "retrieve_treatment_knowledge",
        END: END,
    },
)

# ── 追问回答处理 ──────────────────────────────────────────────
workflow.add_edge("process_user_response", "parallel_context_acquisition")

# ── 报告生成路径 ──────────────────────────────────────────────
workflow.add_edge("retrieve_treatment_knowledge", "generate_final_report")
workflow.add_edge("generate_final_report", END)

# ── 其它分支终止 ──────────────────────────────────────────────
workflow.add_edge("dynamic_engine", END)
workflow.add_edge("rag_qa_node", END)
workflow.add_edge("direct_tool_call_node", END)

# ── 编译 ──────────────────────────────────────────────────────
# LangGraph 0.2+：get_state / astream 需要 checkpointer，否则报 No checkpointer set
_checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=_checkpointer)
app = graph

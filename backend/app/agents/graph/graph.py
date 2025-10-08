from langgraph.graph import StateGraph, END
from app.core.orchard_state import OrchardState

# Import all our nodes
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

def route_entry(state: OrchardState):
    """根据是否存在追问，决定流程入口"""
    if state.get("clarification_needed"):
        return "process_user_response"
    return "intent_recognition"

def route_by_intent(state: OrchardState):
    # 首先检查是否是用户对澄清问题的回答
    if state.get("clarification_needed") and state.get("messages"):
        last_message = state.get("messages", [])[-1]
        if hasattr(last_message, 'content') and hasattr(last_message, '__class__'):
            # 检查是否是用户消息（HumanMessage）
            if last_message.__class__.__name__ == 'HumanMessage':
                print("DEBUG: 检测到用户回答澄清问题，路由到 process_user_response")
                return "process_user_response"
    
    intent = state.get("intent", "Complex Diagnostic")
    if intent == "Complex Diagnostic":
        return "fetch_orchard_profile"
    elif intent == "Simple Q&A":
        return "rag_qa_node"  # 将在阶段二实现
    elif intent == "Direct Tool-Use":
        return "direct_tool_call_node"  # 将在阶段二实现
    else:
        # 默认路由到复杂诊断
        return "fetch_orchard_profile"

def should_continue(state: OrchardState):
    """基于LLM评判结果的继续逻辑"""
    print(f"DEBUG: should_continue called with decision: {state.get('decision')}")
    print(f"DEBUG: 当前状态键: {list(state.keys())}")
    
    # 检查是否有置信度结果
    confidence_result_data = state.get("confidence_result")
    if not confidence_result_data:
        print("DEBUG: No confidence result, routing to retrieve_treatment_knowledge")
        return "retrieve_treatment_knowledge"
    
    # 基于LLM评判结果决定是否需要追问
    confidence_score = confidence_result_data.get("confidence_score", 0.0)
    
    # 优先使用LLM评判的need_clarification，如果没有则使用clarification_needed
    need_clarification = state.get("need_clarification")
    if need_clarification is None:
        need_clarification = state.get("clarification_needed", False)
    
    clarification_count = state.get("clarification_count", 0)
    clarification_focus = state.get("clarification_focus", "")
    
    print(f"DEBUG: 置信度: {confidence_score:.2f}, 需要澄清: {need_clarification}, 追问次数: {clarification_count}")
    print(f"DEBUG: 澄清重点: {clarification_focus}")
    print(f"DEBUG: need_clarification来源: {'LLM评判' if state.get('need_clarification') is not None else 'clarification_needed'}")
    
    # 检查追问次数限制
    if clarification_count >= 3:
        print("DEBUG: 追问次数已达上限，停止追问并生成报告")
        return "retrieve_treatment_knowledge"
    
    # 基于置信度和LLM建议决定
    if confidence_score >= 0.9:
        print("DEBUG: 高置信度，直接生成报告")
        return "retrieve_treatment_knowledge"
    elif confidence_score >= 0.7 and not need_clarification:
        print("DEBUG: 中等置信度且LLM认为无需澄清，生成报告")
        return "retrieve_treatment_knowledge"
    else:
        print("DEBUG: 需要澄清，路由到智能追问")
        return "smart_questioning"

def after_smart_questioning(state: OrchardState):
    """智能追问后的决策"""
    if state.get("clarification_needed"):
        # 如果需要澄清，图的执行会暂停，等待下一个输入
        # langgraph会自动处理这种情况，我们不需要显式地返回END
        return END
    else:
        # 如果不需要澄清（例如，追问次数达到上限），则继续生成报告
        return "retrieve_treatment_knowledge"

# Define the graph workflow
workflow = StateGraph(OrchardState)

# 节点函数已从独立模块导入

# Add nodes to the graph
workflow.add_node("intent_recognition", intent_recognition_node)
workflow.add_node("fetch_orchard_profile", fetch_orchard_profile)
workflow.add_node("run_image_diagnosis", run_image_diagnosis)
workflow.add_node("parallel_context_acquisition", parallel_context_acquisition)
workflow.add_node("retrieve_treatment_knowledge", retrieve_treatment_knowledge)
workflow.add_node("generate_final_report", generate_final_report)
workflow.add_node("dynamic_engine", dynamic_engine_executor)
workflow.add_node("rag_qa_node", rag_qa_node)
workflow.add_node("direct_tool_call_node", direct_tool_call_node)
workflow.add_node("calculate_confidence", calculate_confidence_node)
workflow.add_node("smart_questioning", smart_questioning_node)
workflow.add_node("build_evidence_matrix", build_evidence_matrix_node)
workflow.add_node("process_user_response", process_user_response_node)


# Set the conditional entry point
workflow.set_conditional_entry_point(
    route_entry,
    {
        "process_user_response": "process_user_response",
        "intent_recognition": "intent_recognition",
    }
)

# Define the edges
workflow.add_edge("process_user_response", "parallel_context_acquisition")

workflow.add_conditional_edges(
    "intent_recognition",
    route_by_intent,
    {
        "fetch_orchard_profile": "fetch_orchard_profile",
        "rag_qa_node": "rag_qa_node",
        "direct_tool_call_node": "direct_tool_call_node",
        "dynamic_engine": "dynamic_engine",
        "process_user_response": "process_user_response",
    }
)

# Diagnosis branch - a clear, looped flow
workflow.add_edge("fetch_orchard_profile", "run_image_diagnosis")
workflow.add_edge("run_image_diagnosis", "parallel_context_acquisition")
workflow.add_edge("parallel_context_acquisition", "build_evidence_matrix")
workflow.add_edge("build_evidence_matrix", "calculate_confidence")
workflow.add_conditional_edges(
    "calculate_confidence",
    should_continue,
    {
        "smart_questioning": "smart_questioning",
        "retrieve_treatment_knowledge": "retrieve_treatment_knowledge",
    },
)

# After smart questioning, the graph will pause for user input.
# The next invocation with the user's response will be routed by the entry point.
workflow.add_conditional_edges(
    "smart_questioning",
    after_smart_questioning,
    {
        "retrieve_treatment_knowledge": "retrieve_treatment_knowledge",
        END: END
    }
)

workflow.add_edge("retrieve_treatment_knowledge", "generate_final_report")
workflow.add_edge("generate_final_report", END)

# Dynamic engine branch
workflow.add_edge("dynamic_engine", END)

# RAG QA branch
workflow.add_edge("rag_qa_node", END)

# Direct tool call branch
workflow.add_edge("direct_tool_call_node", END)

# Compile the graph into a runnable app
# Note: For LangGraph API, persistence is handled automatically by the platform
graph = workflow.compile()
app = graph
"""
意图识别节点 — 规则前置 + LLM 兜底
=====================================
优化策略：
1. 先用轻量级关键词规则判断（0 LLM 调用，< 1ms）
2. 仅在规则无法判断时才调用 LLM（约 1-2s）
3. 有图片附件时直接归为 Complex Diagnostic

论文 5.4.4.1：意图识别节点
"""

import re
from app.core.orchard_state import OrchardState

# ── 规则关键词表 ────────────────────────────────────────────
_DIAGNOSTIC_KEYWORDS = re.compile(
    r"叶片|叶子|果实|枝条|枝干|根部|症状|病斑|黄化|褪绿|斑点|腐烂|枯萎|流胶|"
    r"什么病|怎么了|发黄|变黑|变白|卷曲|畸形|穿孔|病害|虫害|感染|蔓延|扩散|"
    r"帮我诊断|帮忙看看|这是什么|是不是病|怎么防治|严重吗|有问题",
    re.IGNORECASE,
)

_SIMPLE_QA_KEYWORDS = re.compile(
    r"^(什么是|介绍一下|柑橘|橙子|橘子|柚子)\s*(病|虫|知识|种植|养护)|"
    r"(怎么种|施肥|浇水|修剪|何时|一般在|发生规律|生长周期).*(?<!病)(?<!虫)$|"
    r"^(是什么|概念|定义|原理)",
    re.IGNORECASE,
)

_TOOL_KEYWORDS = re.compile(
    r"天气|气温|下雨|湿度|温度|预报|果园档案|历史案例|我的果园|上次的|档案信息",
    re.IGNORECASE,
)


def _rule_based_intent(user_query: str, has_images: bool) -> str | None:
    """
    基于规则的快速意图识别。
    返回意图字符串，或 None（无法判断，需 LLM）。
    """
    if not user_query:
        return "Complex Diagnostic" if has_images else None

    # 有图片 → 必定是诊断
    if has_images:
        return "Complex Diagnostic"

    # 诊断关键词优先级最高
    if _DIAGNOSTIC_KEYWORDS.search(user_query):
        return "Complex Diagnostic"

    # 工具调用
    if _TOOL_KEYWORDS.search(user_query):
        return "Direct Tool-Use"

    # 简单知识问答
    if _SIMPLE_QA_KEYWORDS.search(user_query):
        return "Simple Q&A"

    return None


def intent_recognition_node(state: OrchardState) -> OrchardState:
    """意图识别节点：规则优先，LLM 兜底"""
    print("---INTENT RECOGNITION (RULE-FIRST)---")

    user_query = state.get("user_query", "") or ""
    has_images = bool(state.get("image_urls"))

    # ── Step 1: 规则判断（无 LLM 开销） ──────────────────
    intent = _rule_based_intent(user_query, has_images)

    if intent:
        print(f"--> [规则] Intent: {intent}")
        state["intent"] = intent
        state["workflow_step"] = f"Intent (rule): {intent}"
        return state

    # ── Step 2: LLM 兜底（仅对模糊 query） ─────────────
    print("--> [LLM] 规则无法判断，调用 LLM 识别意图...")
    try:
        from app.services.llm_service import llm
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "将用户输入分类为以下三类之一，仅输出类别名称，不要其他内容：\n"
             "- Complex Diagnostic：用户在描述症状、寻求病因诊断、或有图片需要分析\n"
             "- Simple Q&A：简单知识性问答，无需诊断推理\n"
             "- Direct Tool-Use：需要查询天气/果园档案/历史案例等工具"),
            ("user", "{query}"),
        ])
        chain = prompt | llm | StrOutputParser()
        raw = chain.invoke({"query": user_query}).strip()

        if "Complex" in raw:
            intent = "Complex Diagnostic"
        elif "Simple" in raw:
            intent = "Simple Q&A"
        elif "Direct" in raw or "Tool" in raw:
            intent = "Direct Tool-Use"
        else:
            intent = "Complex Diagnostic"

    except Exception as e:
        print(f"LLM intent error: {e}, 默认 Complex Diagnostic")
        intent = "Complex Diagnostic"

    print(f"--> [LLM] Intent: {intent}")
    state["intent"] = intent
    state["workflow_step"] = f"Intent (llm): {intent}"
    return state

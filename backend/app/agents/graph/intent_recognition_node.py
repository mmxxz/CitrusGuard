from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def intent_recognition_node(state: OrchardState) -> OrchardState:
    """
    First node in the graph. Determines the user's intent.
    """
    print("---DETERMINING USER INTENT---")
    
    user_query = state.get("user_query", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at routing user queries. Classify the user's intent into one of THREE labels:

        1. Complex Diagnostic: 用户在描述症状/图片、寻求病因判断或诊断。需要综合分析多种证据（视觉、症状、环境、历史）进行复杂诊断。
           - 包含症状描述："叶片发黄"、"果实有斑点"、"枝条枯萎"
           - 包含图片上传或视觉描述
           - 寻求诊断："这是什么病"、"为什么会出现这种情况"
           - 需要多轮交互澄清的复杂问题

        2. Simple Q&A: 简单的知识问答，可以直接从知识库获取答案。
           - 询问病害基本信息："柑橘黄龙病是什么"
           - 询问一般性知识："柑橘需要多少水"
           - 询问概念解释："什么是有机农业"
           - 不需要复杂推理的纯知识性问题

        3. Direct Tool-Use: 直接使用特定工具获取信息。
           - 询问天气："今天天气怎么样"、"未来一周降雨情况"
           - 询问历史案例："类似情况的历史案例"
           - 询问果园档案："我的果园信息"
           - 明确需要特定工具功能的问题

        输出严格为其中一个标签：Complex Diagnostic 或 Simple Q&A 或 Direct Tool-Use。
        """),
        ("user", "{query}")
    ])
    
    parser = StrOutputParser()
    chain = prompt | llm | parser
    
    try:
        intent = chain.invoke({"query": user_query})
        # 标准化意图标签
        if "Complex Diagnostic" in intent:
            intent = "Complex Diagnostic"
        elif "Simple Q&A" in intent:
            intent = "Simple Q&A"
        elif "Direct Tool-Use" in intent:
            intent = "Direct Tool-Use"
        else:
            # 如果LLM返回了意外的格式，尝试解析
            intent = intent.strip()
    except Exception as e:
        print(f"LLM API error in intent_recognition_node: {e}")
        # Default to Complex Diagnostic (最安全的默认选择)
        intent = "Complex Diagnostic"
        
    print(f"--> User Intent: {intent}")
    state["intent"] = intent
    state["workflow_step"] = f"Intent classified as: {intent}"
    return state

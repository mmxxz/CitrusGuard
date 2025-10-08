from app.core.orchard_state import OrchardState
from app.services.vector_store_service import search_with_treatment_focus

def retrieve_treatment_knowledge(state: OrchardState) -> OrchardState:
    """
    Tool node to retrieve treatment knowledge from the vector store.
    Supports re-retrieval based on flags for multi-turn conversations.
    """
    print("---RETRIEVING TREATMENT KNOWLEDGE FROM VECTOR STORE---")
    
    # Check if we need to re-retrieve treatment knowledge
    need_retrieval = not state.get("treatment_knowledge") or state.get("need_reretrieve_treatment_knowledge", False)
    
    if not need_retrieval:
        print("使用缓存的治疗方案知识")
        return state
    
    diagnosis = state.get("working_diagnosis", "Unknown")
    # 当走 treatment 意图时，可能没有经过诊断链路，working_diagnosis 为空
    if not diagnosis or diagnosis == "Unknown":
        # 从用户查询中提取疾病关键词：去掉空格与防治类词
        q = (state.get("user_query", "") or "")
        q_compact = q.replace(" ", "")
        for kw in ["防治", "治疗", "治理", "用药", "药剂"]:
            q_compact = q_compact.replace(kw, "")
        diagnosis = q_compact or q
    
    # 使用混合检索并提取防治摘要
    results = search_with_treatment_focus(diagnosis, k=8)
    if results:
        top = results[0]
        knowledge = f"{top.get('name','未知条目')} 防治摘要:\n{top.get('treatment_summary','无')}"
    else:
        knowledge = "未在知识库中找到相关防治知识。"
    
    state["treatment_knowledge"] = knowledge
    state["workflow_step"] = "Retrieved treatment knowledge"
    
    # Clear the flag after retrieval
    if "need_reretrieve_treatment_knowledge" in state:
        del state["need_reretrieve_treatment_knowledge"]
    
    return state

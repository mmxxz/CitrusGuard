from app.core.orchard_state import OrchardState
from app.services.vector_store_service import search_similar_documents

def retrieve_historical_cases(state: OrchardState) -> OrchardState:
    """
    Tool node to retrieve historical cases from a vector DB.
    For now, it uses the same knowledge base as treatment knowledge.
    Supports multi-turn conversations by using updated evidence matrix.
    """
    print("---RETRIEVING HISTORICAL CASES FROM VECTOR STORE---")

    # Build query from user input and updated evidence matrix
    query_parts = []
    
    # Add original user query
    user_query = state.get("user_query", "")
    if user_query:
        query_parts.append(user_query)
    
    # Add evidence from updated matrix for better retrieval
    evidence_matrix_data = state.get("evidence_matrix", {})
    if evidence_matrix_data:
        evidence_parts = []
        
        # Extract visual evidence
        visual = evidence_matrix_data.get("visual", {})
        if visual.get("leaf_color"):
            evidence_parts.append(f"叶片颜色: {visual['leaf_color']}")
        if visual.get("leaf_spots"):
            evidence_parts.append(f"叶片斑点: {', '.join(visual['leaf_spots'])}")
        if visual.get("fruit_condition"):
            evidence_parts.append(f"果实状况: {visual['fruit_condition']}")
        
        # Extract symptom evidence
        symptom = evidence_matrix_data.get("symptom", {})
        if symptom.get("primary_symptoms"):
            evidence_parts.append(f"主要症状: {', '.join(symptom['primary_symptoms'])}")
        if symptom.get("secondary_symptoms"):
            evidence_parts.append(f"次要症状: {', '.join(symptom['secondary_symptoms'])}")
        
        if evidence_parts:
            query_parts.append(" ".join(evidence_parts))
    
    # Combine all query parts
    combined_query = " ".join(query_parts) if query_parts else user_query
    print(f"DEBUG: 历史病例检索查询: {combined_query}")

    try:
        # In a real app, you might have a separate collection for historical cases.
        # For now, we search the main knowledge base (sync).
        documents = search_similar_documents(combined_query, k=5)

        # 处理检索到的文档，确保有正确的格式
        retrieved_cases = []
        for i, doc in enumerate(documents):
            case = {
                "case_id": f"case_{i+1}",
                "diagnosis": doc.metadata.get("name", "未知病害"),
                "category": doc.metadata.get("category", "未知类别"),
                "treatment": doc.metadata.get("treatment_summary", "无治疗方案"),
                "effectiveness": "good",  # 默认值
                "similarity_score": 0.8 - i * 0.05,  # 递减的相似度分数
                "description": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            }
            retrieved_cases.append(case)

        state["historical_cases_retrieved"] = retrieved_cases
        state["workflow_step"] = "Retrieved similar historical cases"
        print(f"DEBUG: 检索到 {len(retrieved_cases)} 个历史病例")

    except Exception as e:
        print(f"Vector store error: {e}, using mock data")
        # 模拟历史案例数据
        state["historical_cases_retrieved"] = [
            {
                "case_id": "case_123",
                "diagnosis": "柑橘黄龙病",
                "category": "病毒病",
                "treatment": "及时清除病树，防治木虱",
                "effectiveness": "good",
                "similarity_score": 0.8
            },
            {
                "case_id": "case_456",
                "diagnosis": "柑橘缺铁症",
                "category": "营养缺乏",
                "treatment": "叶面喷施硫酸亚铁",
                "effectiveness": "excellent",
                "similarity_score": 0.7
            }
        ]
        state["workflow_step"] = "Retrieved mock historical cases"

    return state

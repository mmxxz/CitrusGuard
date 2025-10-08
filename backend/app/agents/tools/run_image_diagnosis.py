from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate

def run_image_diagnosis(state: OrchardState) -> OrchardState:
    """Tool node to perform initial image diagnosis (placeholder)."""
    print("---RUNNING IMAGE DIAGNOSIS (SIMULATED)---")
    
    user_query = state.get("user_query", "No description provided.")
    image_urls = state.get("image_urls", [])

    try:
        # In a real scenario, you would use a vision model.
        # Here, we simulate it by sending the description to Kimi.
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一位专业的农业诊断专家。基于用户对症状的描述，提供一个简短的初步假设。你的回答应该是一个简短的短语。"),
            ("user", "症状: {query}\n图片URL (仅供参考，不进行分析): {urls}")
        ])
        
        chain = prompt | llm
        response = chain.invoke({"query": user_query, "urls": image_urls})
        
        suggestion = response.content
    except Exception as e:
        print(f"LLM API error: {e}")
        # Use mock response when API is rate limited or unavailable
        suggestion = "基于症状描述，初步怀疑可能是柑橘黄龙病或营养缺乏问题，需要进一步检查确认。"
    
    state["initial_diagnosis_suggestion"] = suggestion
    state["workflow_step"] = "Image analysis complete"
    return state

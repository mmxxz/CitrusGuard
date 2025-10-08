from app.core.orchard_state import OrchardState
from app.schemas.evidence import EvidenceMatrix
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import logging

logger = logging.getLogger(__name__)

def process_user_response_node(state: OrchardState) -> OrchardState:
    """
    处理用户对澄清问题的回答，并更新证据矩阵
    """
    print("---PROCESSING USER RESPONSE---")
    
    try:
        # 1. 获取必要信息
        last_question = state.get("clarification_question", "")
        user_response = ""
        messages = state.get("messages", [])
        if messages:
            # 获取最后一条用户消息
            for msg in reversed(messages):
                if hasattr(msg, 'content') and hasattr(msg, '__class__'):
                    # 检查是否是用户消息（HumanMessage）
                    if msg.__class__.__name__ == 'HumanMessage':
                        user_response = msg.content
                        break

        if not last_question or not user_response:
            logger.warning("缺少上一轮问题或用户回答，跳过处理")
            return state
            
        # 2. 获取当前的证据矩阵
        evidence_matrix_data = state.get("evidence_matrix", {})
        evidence_matrix = EvidenceMatrix(**evidence_matrix_data)
        
        # 3. 使用LLM解析用户回答并更新证据矩阵
        updated_evidence = parse_response_and_update_evidence(
            last_question, user_response, evidence_matrix.model_dump()
        )
        
        if updated_evidence:
            state["evidence_matrix"] = updated_evidence
            state["workflow_step"] = "Evidence matrix updated with user response"
            
            # 清除所有可能影响重新计算的缓存数据
            if "confidence_result" in state:
                del state["confidence_result"]
            if "historical_cases_retrieved" in state:
                del state["historical_cases_retrieved"]
            if "treatment_knowledge_retrieved" in state:
                del state["treatment_knowledge_retrieved"]
            
            # 标记需要重新检索历史病例
            state["need_reretrieve_historical_cases"] = True
            state["need_reretrieve_treatment_knowledge"] = True
            
            logger.info("证据矩阵已根据用户回答更新，所有缓存数据已清除")
            print(f"DEBUG: 证据矩阵已更新，新证据矩阵: {updated_evidence}")
        else:
            logger.warning("未能从用户回答中提取有效信息")
            state["workflow_step"] = "User response processed, no new evidence extracted"

    except Exception as e:
        logger.error(f"处理用户回答时出错: {e}")
        state["workflow_step"] = "Error processing user response"
        
    return state

def parse_response_and_update_evidence(question: str, response: str, current_evidence: dict) -> dict:
    """
    使用LLM解析用户回答，并返回更新后的证据矩阵字典
    """
    parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能农业助手，负责解析用户对澄清问题的回答。
        你的任务是根据用户的回答，更新一个结构化的JSON证据对象。
        请只更新与问题直接相关的字段。如果用户的回答无法提供有效信息，则返回原始的JSON对象。
        
        这是当前的证据对象结构：
        {{"visual": {{"leaf_color": [], "leaf_spots": [], "fruit_condition": []}}, 
          "symptom": {{"primary_symptoms": [], "secondary_symptoms": []}}, 
          "environmental": {{"temperature": null, "humidity": null, "soil_ph": null}}, 
          "historical": {{"similar_cases": []}}}}
          
        请返回一个与上述结构完全相同的、更新后的JSON对象。"""),
        ("user", """我们向用户提出了以下问题：
        "{question}"
        
        用户回答：
        "{response}"
        
        这是当前需要更新的证据对象：
        {current_evidence}
        
        请根据用户的回答，返回更新后的证据对象。""")
    ])
    
    chain = prompt | llm | parser
    
    try:
        updated_evidence = chain.invoke({
            "question": question,
            "response": response,
            "current_evidence": current_evidence
        })
        return updated_evidence
    except Exception as e:
        logger.error(f"LLM解析用户回答失败: {e}")
        return current_evidence # 出错时返回原始证据

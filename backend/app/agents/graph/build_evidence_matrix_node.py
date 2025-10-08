from app.core.orchard_state import OrchardState
from app.schemas.evidence import (
    EvidenceMatrix, VisualEvidence, SymptomEvidence,
    EnvironmentalEvidence, HistoricalEvidence
)
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import logging

logger = logging.getLogger(__name__)

def build_evidence_matrix_node(state: OrchardState) -> OrchardState:
    """
    构建证据矩阵节点
    将state中的原始数据解析并组装成结构化的EvidenceMatrix对象
    """
    print("---BUILDING EVIDENCE MATRIX---")
    
    try:
        # 1. 初始化空的证据模型
        visual = VisualEvidence()
        symptom = SymptomEvidence()
        environmental = EnvironmentalEvidence()
        historical = HistoricalEvidence()
        
        # 2. 解析症状和视觉证据 (使用LLM)
        user_query = state.get("user_query", "")
        image_analysis = state.get("initial_diagnosis_suggestion", "")
        
        # 创建一个组合的文本描述
        combined_description = f"用户描述: {user_query}\n初步图像分析: {image_analysis}"
        
        if combined_description.strip():
            parsed_symptoms = parse_symptoms_with_llm(combined_description)
            if parsed_symptoms:
                symptom.primary_symptoms = parsed_symptoms.get("primary_symptoms", [])
                symptom.secondary_symptoms = parsed_symptoms.get("secondary_symptoms", [])
                
                # 处理视觉证据 - 将列表转换为字符串
                leaf_colors = parsed_symptoms.get("leaf_color", [])
                if leaf_colors:
                    visual.leaf_color = ", ".join(leaf_colors) if isinstance(leaf_colors, list) else str(leaf_colors)
                
                visual.leaf_spots = parsed_symptoms.get("leaf_spots", [])
                
                fruit_conditions = parsed_symptoms.get("fruit_condition", [])
                if fruit_conditions:
                    visual.fruit_condition = ", ".join(fruit_conditions) if isinstance(fruit_conditions, list) else str(fruit_conditions)

        # 3. 填充环境证据
        weather_data = state.get("realtime_weather", {})
        if weather_data and weather_data.get("current"):
            environmental.temperature = weather_data["current"].get("temperature")
            environmental.humidity = weather_data["current"].get("humidity")
        
        orchard_profile = state.get("orchard_profile", {})
        if orchard_profile:
            # 假设值，应从果园档案获取
            # 在实际应用中，您可能需要从orchard_profile中获取更详细的土壤信息
            environmental.soil_ph = orchard_profile.get("soil_ph", 7.0) 
            
        # 4. 填充历史证据
        historical_cases = state.get("historical_cases_retrieved", [])
        if historical_cases:
            historical.similar_cases = [
                {"disease_name": case.get("diagnosis"), "category": case.get("category")}
                for case in historical_cases
            ]
            
        # 5. 组装并存储证据矩阵
        evidence_matrix = EvidenceMatrix(
            visual=visual,
            symptom=symptom,
            environmental=environmental,
            historical=historical
        )
        
        state["evidence_matrix"] = evidence_matrix.model_dump()
        state["workflow_step"] = "Evidence matrix built"
        
        logger.info("证据矩阵构建完成")
        
    except Exception as e:
        logger.error(f"构建证据矩阵时出错: {e}")
        # 即使出错，也创建一个空的矩阵以保证流程继续
        state["evidence_matrix"] = EvidenceMatrix().model_dump()
        state["workflow_step"] = "Error building evidence matrix"
        
    return state

def parse_symptoms_with_llm(description: str) -> dict:
    """使用LLM从文本中解析结构化的症状和视觉证据"""
    
    parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个农业信息提取专家。
        你的任务是从用户提供的文本中提取结构化的症状和视觉信息。
        请以JSON格式返回，包含以下键 (如果信息不存在，则返回空列表[]):
        - \"primary_symptoms\": List[str] 主要症状的关键描述
        - \"secondary_symptoms\": List[str] 次要症状或补充描述
        - \"leaf_color\": List[str] 描述叶片颜色的词语 (例如: \"发黄\", \"暗绿\")
        - \"leaf_spots\": List[str] 描述叶片斑点的词语 (例如: \"圆形病斑\", \"褐色斑点\")
        - \"fruit_condition\": List[str] 描述果实状况的词语 (例如: \"畸形\", \"腐烂\")
        """),
        ("user", "请从以下文本中提取信息:\n\n{description}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        return chain.invoke({"description": description})
    except Exception as e:
        logger.error(f"LLM解析症状失败: {e}")
        return {}

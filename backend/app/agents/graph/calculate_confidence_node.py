from app.core.orchard_state import OrchardState
from app.schemas.evidence import EvidenceMatrix, EvidenceGap, ConfidenceResult, EvidenceType
from app.schemas.disease_profile import DiseaseProfile
from app.crud.disease_profile import get_disease_profile_crud
from app.core.database import SessionLocal
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Dict, Any, Tuple
import json

def calculate_confidence_node(state: OrchardState) -> OrchardState:
    """
    置信度计算节点 - 非LLM逻辑
    基于证据矩阵和病害档案进行量化置信度计算
    """
    print("---CALCULATE CONFIDENCE NODE---")
    
    try:
        # 1. 获取证据矩阵
        evidence_matrix_data = state.get("evidence_matrix")
        print(f"DEBUG: 获取到的证据矩阵数据: {evidence_matrix_data}")
        
        if not evidence_matrix_data:
            print("警告: 没有找到证据矩阵，使用默认值")
            evidence_matrix = EvidenceMatrix()
        else:
            # 从Dict转换为EvidenceMatrix对象
            evidence_matrix = EvidenceMatrix(**evidence_matrix_data)
            print(f"DEBUG: 证据矩阵对象创建成功: {evidence_matrix}")
        
        # 2. 获取候选病害档案
        db = SessionLocal()
        try:
            disease_crud = get_disease_profile_crud(db)
            candidate_diseases = disease_crud.get_candidates_for_evidence(evidence_matrix, limit=10)
        finally:
            db.close()
        
        if not candidate_diseases:
            print("警告: 没有找到候选病害档案")
            state["confidence_result"] = ConfidenceResult(
                disease_candidates=[],
                confidence_score=0.0,
                reasoning="没有找到候选病害档案"
            )
            return state
        
        # 3. 使用大模型进行置信度评判
        confidence_result, llm_metadata = llm_based_confidence_evaluation(evidence_matrix, candidate_diseases, state)
        
        state["confidence_result"] = confidence_result.model_dump()
        state["workflow_step"] = "LLM-based confidence calculated"
        
        # 更新澄清信息到状态
        state["need_clarification"] = llm_metadata.get("need_clarification", False)
        state["clarification_focus"] = llm_metadata.get("clarification_focus", "")
        
        print(f"LLM置信度评判完成: {confidence_result.confidence_score:.2f}, 最高分候选: {confidence_result.top_candidate['disease_name'] if confidence_result.top_candidate else 'None'}")
        print(f"DEBUG: 澄清信息 - need_clarification: {state.get('need_clarification')}, focus: {state.get('clarification_focus')}")
        
    except Exception as e:
        print(f"置信度计算节点错误: {e}")
        state["confidence_result"] = ConfidenceResult(
            confidence_score=0.0,
            reasoning=f"置信度计算失败: {str(e)}"
        ).model_dump()
        state["workflow_step"] = "Confidence calculation error"
    
    return state

def calculate_disease_match_score(disease: DiseaseProfile, evidence_matrix: EvidenceMatrix) -> float:
    """计算单个病害与证据矩阵的匹配度"""
    total_score = 0.0
    weight_sum = 0.0
    
    # 视觉证据匹配 (权重: 0.3)
    visual_score = calculate_visual_match_score(disease, evidence_matrix.visual)
    total_score += visual_score * 0.3
    weight_sum += 0.3
    
    # 症状证据匹配 (权重: 0.4)
    symptom_score = calculate_symptom_match_score(disease, evidence_matrix.symptom)
    total_score += symptom_score * 0.4
    weight_sum += 0.4
    
    # 环境证据匹配 (权重: 0.2)
    env_score = calculate_environmental_match_score(disease, evidence_matrix.environmental)
    total_score += env_score * 0.2
    weight_sum += 0.2
    
    # 历史证据匹配 (权重: 0.1)
    hist_score = calculate_historical_match_score(disease, evidence_matrix.historical)
    total_score += hist_score * 0.1
    weight_sum += 0.1
    
    return total_score / weight_sum if weight_sum > 0 else 0.0

def calculate_visual_match_score(disease: DiseaseProfile, visual_evidence) -> float:
    """计算视觉证据匹配度"""
    if not disease.visual_symptoms_checklist:
        return 0.0
    
    visual_checklist = disease.visual_symptoms_checklist
    matches = 0
    total_checks = 0
    
    # 检查叶片颜色变化 - 改进匹配逻辑
    if visual_evidence.leaf_color and visual_checklist.get("leaf_color_changes"):
        total_checks += 1
        evidence_color = visual_evidence.leaf_color.lower()
        for color_desc in visual_checklist["leaf_color_changes"]:
            color_desc_lower = color_desc.lower()
            # 检查关键词匹配
            color_keywords = ["黄化", "黄", "褪绿", "黄绿", "斑驳"]
            if any(keyword in evidence_color and keyword in color_desc_lower for keyword in color_keywords):
                matches += 1
                break
    
    # 检查叶片斑点 - 改进匹配逻辑
    if visual_evidence.leaf_spots and visual_checklist.get("leaf_spots_patterns"):
        total_checks += 1
        evidence_spots = " ".join(visual_evidence.leaf_spots).lower()
        for spot_desc in visual_checklist["leaf_spots_patterns"]:
            spot_desc_lower = spot_desc.lower()
            # 检查关键词匹配
            spot_keywords = ["斑点", "病斑", "斑", "黄褐", "褐色"]
            if any(keyword in evidence_spots and keyword in spot_desc_lower for keyword in spot_keywords):
                matches += 1
                break
    
    # 检查果实状况 - 改进匹配逻辑
    if visual_evidence.fruit_condition and visual_checklist.get("fruit_conditions"):
        total_checks += 1
        evidence_fruit = visual_evidence.fruit_condition.lower()
        for fruit_desc in visual_checklist["fruit_conditions"]:
            fruit_desc_lower = fruit_desc.lower()
            # 检查关键词匹配
            fruit_keywords = ["果", "果实", "橙红", "青绿", "红鼻子"]
            if any(keyword in evidence_fruit and keyword in fruit_desc_lower for keyword in fruit_keywords):
                matches += 1
                break
    
    return matches / total_checks if total_checks > 0 else 0.0

def calculate_symptom_match_score(disease: DiseaseProfile, symptom_evidence) -> float:
    """计算症状证据匹配度"""
    if not disease.key_diagnostic_features:
        return 0.0
    
    matches = 0
    total_features = len(disease.key_diagnostic_features)
    
    for feature in disease.key_diagnostic_features:
        feature_lower = feature.lower()
        
        # 检查主要症状 - 改进匹配逻辑
        if symptom_evidence.primary_symptoms:
            for symptom in symptom_evidence.primary_symptoms:
                symptom_lower = symptom.lower()
                # 检查关键词匹配
                symptom_keywords = ["黄化", "黄", "褪绿", "斑点", "病斑", "斑驳"]
                if any(keyword in symptom_lower and keyword in feature_lower for keyword in symptom_keywords):
                    matches += 1
                    break
            else:
                # 如果没有匹配到主要症状，检查次要症状
                if symptom_evidence.secondary_symptoms:
                    for symptom in symptom_evidence.secondary_symptoms:
                        symptom_lower = symptom.lower()
                        if any(keyword in symptom_lower and keyword in feature_lower for keyword in symptom_keywords):
                            matches += 0.5  # 次要症状权重较低
                            break
    
    return matches / total_features if total_features > 0 else 0.0

def calculate_environmental_match_score(disease: DiseaseProfile, env_evidence) -> float:
    """计算环境证据匹配度"""
    if not disease.environmental_triggers_checklist:
        return 0.0
    
    env_checklist = disease.environmental_triggers_checklist
    matches = 0
    total_checks = 0
    
    # 检查温度范围
    if env_evidence.temperature and env_checklist.get("temperature_range"):
        total_checks += 1
        temp_range = env_checklist["temperature_range"]
        if temp_range.get("min", 0) <= env_evidence.temperature <= temp_range.get("max", 100):
            matches += 1
    
    # 检查湿度范围
    if env_evidence.humidity and env_checklist.get("humidity_range"):
        total_checks += 1
        humidity_range = env_checklist["humidity_range"]
        if humidity_range.get("min", 0) <= env_evidence.humidity <= humidity_range.get("max", 100):
            matches += 1
    
    # 检查土壤pH
    if env_evidence.soil_ph and env_checklist.get("soil_ph_range"):
        total_checks += 1
        ph_range = env_checklist["soil_ph_range"]
        if ph_range.get("min", 0) <= env_evidence.soil_ph <= ph_range.get("max", 14):
            matches += 1
    
    return matches / total_checks if total_checks > 0 else 0.0

def calculate_historical_match_score(disease: DiseaseProfile, hist_evidence) -> float:
    """计算历史证据匹配度"""
    if not hist_evidence.similar_cases:
        return 0.0
    
    matches = 0
    total_cases = len(hist_evidence.similar_cases)
    
    for case in hist_evidence.similar_cases:
        if case.get("disease_name") == disease.disease_name:
            matches += 1
        elif case.get("category") == disease.category:
            matches += 0.5  # 同类别权重较低
    
    return matches / total_cases if total_cases > 0 else 0.0

def identify_evidence_gaps(evidence_matrix: EvidenceMatrix, top_candidate: Dict, candidate_diseases: List) -> List[EvidenceGap]:
    """识别证据缺口"""
    gaps = []
    
    if not top_candidate:
        return gaps
    
    # 获取最高分候选的病害档案
    top_disease = next((d for d in candidate_diseases if d.disease_id == top_candidate["disease_id"]), None)
    if not top_disease:
        return gaps
    
    # 检查视觉证据缺口
    if top_disease.visual_symptoms_checklist:
        visual_checklist = top_disease.visual_symptoms_checklist
        if visual_checklist.get("leaf_color_changes") and not evidence_matrix.visual.leaf_color:
            gaps.append(EvidenceGap(
                evidence_type=EvidenceType.VISUAL.value,
                field_name="leaf_color",
                description="缺少叶片颜色信息",
                importance=0.8,
                suggested_question="请描述叶片的颜色变化情况"
            ))
    
    # 检查症状证据缺口
    if top_disease.key_diagnostic_features:
        if not evidence_matrix.symptom.primary_symptoms:
            gaps.append(EvidenceGap(
                evidence_type=EvidenceType.SYMPTOM.value,
                field_name="primary_symptoms",
                description="缺少主要症状描述",
                importance=0.9,
                suggested_question="请详细描述观察到的主要症状"
            ))
    
    # 检查环境证据缺口
    if top_disease.environmental_triggers_checklist:
        env_checklist = top_disease.environmental_triggers_checklist
        if env_checklist.get("temperature_range") and not evidence_matrix.environmental.temperature:
            gaps.append(EvidenceGap(
                evidence_type=EvidenceType.ENVIRONMENTAL.value,
                field_name="temperature",
                description="缺少温度信息",
                importance=0.6,
                suggested_question="请提供当前环境温度信息"
            ))
    
    return gaps

def identify_differentiation_points(candidate_diseases: List[Dict]) -> List[str]:
    """识别差异化诊断点"""
    if len(candidate_diseases) < 2:
        return []
    
    differentiation_points = []
    
    # 比较前两个候选的关键特征
    top1 = candidate_diseases[0]
    top2 = candidate_diseases[1]
    
    if top1["category"] != top2["category"]:
        differentiation_points.append(f"病害类别不同: {top1['category']} vs {top2['category']}")
    
    if abs(top1["match_score"] - top2["match_score"]) < 0.1:
        differentiation_points.append("匹配度非常接近，需要更多证据进行区分")
    
    return differentiation_points

def calculate_overall_confidence(disease_scores: List[Dict], evidence_matrix: EvidenceMatrix) -> float:
    """计算总体置信度"""
    if not disease_scores:
        return 0.0
    
    # 基于最高分和分数差距
    top_score = disease_scores[0]["match_score"]
    second_score = disease_scores[1]["match_score"] if len(disease_scores) > 1 else 0.0
    
    # 基础置信度
    base_confidence = top_score
    
    # 分数差距奖励
    score_gap = top_score - second_score
    gap_bonus = min(score_gap * 0.5, 0.2)  # 最多0.2的奖励
    
    # 证据完整性奖励
    completeness_bonus = evidence_matrix.completeness_score * 0.1
    
    # 最终置信度
    final_confidence = base_confidence + gap_bonus + completeness_bonus
    
    return min(final_confidence, 1.0)  # 确保不超过1.0

def generate_reasoning_text(disease_scores: List[Dict], evidence_gaps: List[EvidenceGap], confidence: float) -> str:
    """生成推理文本"""
    reasoning_parts = []
    
    if disease_scores:
        top_disease = disease_scores[0]
        reasoning_parts.append(f"最高匹配病害: {top_disease['disease_name']} (匹配度: {top_disease['match_score']:.2f})")
        
        if len(disease_scores) > 1:
            second_disease = disease_scores[1]
            reasoning_parts.append(f"次高匹配病害: {second_disease['disease_name']} (匹配度: {second_disease['match_score']:.2f})")
    
    if evidence_gaps:
        gap_descriptions = [gap.description for gap in evidence_gaps[:3]]  # 最多显示3个缺口
        reasoning_parts.append(f"关键证据缺口: {', '.join(gap_descriptions)}")
    
    reasoning_parts.append(f"总体置信度: {confidence:.2f}")
    
    return " | ".join(reasoning_parts)

def llm_based_confidence_evaluation(evidence_matrix: EvidenceMatrix, candidate_diseases: List[DiseaseProfile], state: OrchardState) -> Tuple[ConfidenceResult, Dict]:
    """
    基于大模型的置信度评判系统
    使用LLM根据证据矩阵和病害档案进行智能置信度评判
    """
    print("---LLM-BASED CONFIDENCE EVALUATION---")
    
    # 构建病害档案信息
    disease_profiles = []
    for disease in candidate_diseases:
        profile = {
            "disease_id": disease.disease_id,
            "disease_name": disease.disease_name,
            "category": disease.category,
            "severity_level": disease.severity_level.value,
            "description": disease.description,
            "key_diagnostic_features": disease.key_diagnostic_features,
            "visual_symptoms_checklist": disease.visual_symptoms_checklist,
            "environmental_triggers_checklist": disease.environmental_triggers_checklist
        }
        disease_profiles.append(profile)
    
    # 构建证据信息
    evidence_info = {
        "visual": {
            "leaf_color": evidence_matrix.visual.leaf_color,
            "leaf_spots": evidence_matrix.visual.leaf_spots,
            "fruit_condition": evidence_matrix.visual.fruit_condition,
            "leaf_texture": evidence_matrix.visual.leaf_texture,
            "stem_condition": evidence_matrix.visual.stem_condition,
            "root_condition": evidence_matrix.visual.root_condition,
            "overall_health": evidence_matrix.visual.overall_health
        },
        "symptom": {
            "primary_symptoms": evidence_matrix.symptom.primary_symptoms,
            "secondary_symptoms": evidence_matrix.symptom.secondary_symptoms,
            "symptom_severity": evidence_matrix.symptom.symptom_severity,
            "symptom_duration": evidence_matrix.symptom.symptom_duration,
            "affected_areas": evidence_matrix.symptom.affected_areas,
            "progression_pattern": evidence_matrix.symptom.progression_pattern
        },
        "environmental": {
            "temperature": evidence_matrix.environmental.temperature,
            "humidity": evidence_matrix.environmental.humidity,
            "rainfall": evidence_matrix.environmental.rainfall,
            "soil_ph": evidence_matrix.environmental.soil_ph,
            "soil_moisture": evidence_matrix.environmental.soil_moisture,
            "wind_speed": evidence_matrix.environmental.wind_speed,
            "sunlight_exposure": evidence_matrix.environmental.sunlight_exposure,
            "recent_weather_events": evidence_matrix.environmental.recent_weather_events
        },
        "historical": {
            "similar_cases": evidence_matrix.historical.similar_cases,
            "previous_treatments": evidence_matrix.historical.previous_treatments,
            "seasonal_patterns": evidence_matrix.historical.seasonal_patterns,
            "outbreak_history": evidence_matrix.historical.outbreak_history,
            "treatment_success_rate": evidence_matrix.historical.treatment_success_rate
        }
    }
    
    # 获取对话历史上下文
    messages = state.get("messages", [])
    conversation_context = []
    for msg in messages[-5:]:  # 只取最近5条消息作为上下文
        if hasattr(msg, 'content'):
            if msg.__class__.__name__ == 'HumanMessage':
                conversation_context.append(f"用户: {msg.content}")
            elif msg.__class__.__name__ == 'AIMessage':
                conversation_context.append(f"AI: {msg.content}")
    
    # 构建LLM提示
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的柑橘病害诊断专家，具有丰富的植物病理学知识和诊断经验。

你的任务是根据提供的证据信息和候选病害档案，进行智能的置信度评判。

评判标准：
1. 症状匹配度：主要症状和次要症状与病害档案的匹配程度
2. 视觉证据：叶片、果实、枝干等外观特征与病害特征的匹配度
3. 环境条件：温度、湿度、土壤等环境因素是否有利于该病害发生
4. 历史案例：相似历史病例的支持程度
5. 证据完整性：现有证据的充分性和可靠性

置信度评判规则：
- 0.9-1.0：高度确信，症状典型，证据充分，可以确定诊断
- 0.7-0.9：较确信，症状较典型，证据较充分，需要少量补充信息
- 0.5-0.7：中等确信，症状部分匹配，需要更多证据支持
- 0.3-0.5：低确信，症状不典型，证据不足，需要大量补充信息
- 0.0-0.3：极低确信，症状不匹配，无法确定诊断

请返回JSON格式的结果，包含：
- disease_candidates: 候选病害列表，按匹配度排序，每个候选包含disease_name, match_score, reasoning字段
- top_candidate: 最高分候选病害的完整信息（包含disease_name, match_score等字段）
- confidence_score: 总体置信度 (0.0-1.0)
- evidence_gaps: 证据缺口描述列表（字符串数组）
- differentiation_points: 差异化诊断点列表（字符串数组）
- reasoning: 详细的推理过程
- need_clarification: 是否需要进一步澄清（布尔值）
- clarification_focus: 澄清重点（字符串，多个问题用" | "分隔）

请确保返回的JSON格式正确，所有字段都必须存在。"""),
        ("user", """请根据以下信息进行置信度评判：

【对话上下文】
{conversation_context}

【证据信息】
{evidence_info}

【候选病害档案】
{disease_profiles}

请进行专业的置信度评判，并返回JSON格式的结果。""")
    ])
    
    parser = JsonOutputParser()
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "conversation_context": "\n".join(conversation_context),
            "evidence_info": json.dumps(evidence_info, ensure_ascii=False, indent=2),
            "disease_profiles": json.dumps(disease_profiles, ensure_ascii=False, indent=2)
        })
        
        print(f"DEBUG: LLM评判结果: {result}")
        
        # 处理LLM返回的数据格式
        disease_candidates = result.get("disease_candidates", [])
        
        # 处理top_candidate - 确保是字典格式
        top_candidate = result.get("top_candidate")
        if isinstance(top_candidate, str):
            # 如果是字符串，从disease_candidates中找到对应的候选
            top_candidate = next((c for c in disease_candidates if c.get("disease_name") == top_candidate), None)
        
        # 处理evidence_gaps - 转换为EvidenceGap对象
        evidence_gaps = []
        gaps_data = result.get("evidence_gaps", [])
        for i, gap_desc in enumerate(gaps_data):
            if isinstance(gap_desc, str):
                evidence_gaps.append(EvidenceGap(
                    evidence_type=EvidenceType.VISUAL.value,  # 使用枚举值
                    field_name=f"gap_{i}",
                    description=gap_desc,
                    importance=0.8 - i * 0.1,  # 递减的重要性
                    suggested_question=f"请提供关于{gap_desc}的更多信息"
                ))
            elif isinstance(gap_desc, dict):
                evidence_gaps.append(EvidenceGap(**gap_desc))
        
        # 处理differentiation_points - 确保是列表
        differentiation_points = result.get("differentiation_points", [])
        if isinstance(differentiation_points, str):
            differentiation_points = [differentiation_points]
        
        # 处理clarification_focus - 确保是字符串
        clarification_focus = result.get("clarification_focus", "")
        if isinstance(clarification_focus, list):
            clarification_focus = " | ".join(clarification_focus)
        
        # 构建置信度结果
        confidence_result = ConfidenceResult(
            disease_candidates=disease_candidates,
            top_candidate=top_candidate,
            confidence_score=result.get("confidence_score", 0.0),
            evidence_gaps=evidence_gaps,
            differentiation_points=differentiation_points,
            reasoning=result.get("reasoning", "LLM评判完成")
        )
        
        # 准备元数据
        llm_metadata = {
            "need_clarification": result.get("need_clarification", False),
            "clarification_focus": clarification_focus
        }
        
        return confidence_result, llm_metadata
        
    except Exception as e:
        print(f"LLM置信度评判错误: {e}")
        # 返回默认结果
        default_result = ConfidenceResult(
            disease_candidates=[],
            confidence_score=0.0,
            reasoning=f"LLM评判失败: {str(e)}"
        )
        default_metadata = {
            "need_clarification": False,
            "clarification_focus": ""
        }
        return default_result, default_metadata

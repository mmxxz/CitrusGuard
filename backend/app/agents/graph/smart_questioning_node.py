from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from app.schemas.evidence import ConfidenceResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Dict, Any
import json

# 导入数据库相关
from app.core.database import SessionLocal
from app.crud.disease_profile import get_disease_profile_crud

async def smart_questioning_node(state: OrchardState) -> OrchardState:
    """
    基于LLM评判结果的智能追问节点
    """
    print("---SMART QUESTIONING NODE (LLM-BASED)---")
    print(f"DEBUG: 进入smart_questioning_node，当前状态键: {list(state.keys())}")
    
    try:
        # 1. 检查是否应停止追问
        clarification_count = state.get("clarification_count", 0)
        if clarification_count >= 3: # 最多追问3次
            print("追问次数已达上限，停止追问并生成报告")
            state["clarification_needed"] = False
            state["decision"] = "report"
            return state

        # 2. 获取LLM评判结果
        confidence_result_data = state.get("confidence_result")
        if not confidence_result_data:
            state["clarification_question"] = {"question": "抱歉，内部数据出错，无法生成问题。", "options": []}
            state["clarification_needed"] = True
            return state

        confidence_result = ConfidenceResult(**confidence_result_data)
        
        # 3. 检查LLM是否建议需要澄清
        need_clarification = state.get("need_clarification", False)
        
        if not need_clarification and confidence_result.confidence_score >= 0.7:
            print("LLM认为无需澄清且置信度足够，直接生成报告")
            state["clarification_needed"] = False
            state["decision"] = "report"
            return state
        
        # 4. 生成差异化诊断问题
        question_obj = await generate_differentiating_question(confidence_result, state)
        
        # 5. 更新状态
        state["clarification_question"] = question_obj
        state["clarification_needed"] = True
        state["decision"] = "clarify"
        state["workflow_step"] = "Smart questioning generated"
        state["clarification_count"] = clarification_count + 1
        
        print(f"生成智能追问: {question_obj}")
        
    except Exception as e:
        print(f"❌ 智能追问节点错误: {e}")
        import traceback
        print("完整错误堆栈:")
        traceback.print_exc()
        state["clarification_question"] = {
            "question": "生成问题时遇到错误，请描述一下您观察到的最明显症状。",
            "options": ["叶片问题", "果实问题", "枝干问题", "根部问题"]
        }
        state["clarification_needed"] = True
        state["workflow_step"] = "Smart questioning error"
    
    return state

async def generate_differentiating_question(confidence_result: ConfidenceResult, state: OrchardState) -> Dict[str, Any]:
    """
    基于LLM澄清建议生成智能问题
    """
    # 1. 检查LLM是否提供了澄清重点
    clarification_focus = state.get("clarification_focus", "")
    if clarification_focus:
        print(f"DEBUG: 使用LLM澄清重点: {clarification_focus}")
        
        main_question = clarification_focus.split(" | ")[0]
            
        return {
            "question": main_question,
            "options": ["是", "否", "不确定", "需要更多信息"]
        }
    
    # 2. 基于证据缺口生成问题
    evidence_gaps = confidence_result.evidence_gaps
    if evidence_gaps:
        most_important_gap = max(evidence_gaps, key=lambda x: x.get('importance', 0))
        suggested_question = most_important_gap.get('suggested_question', '')
        
        if suggested_question:
            print(f"DEBUG: 基于证据缺口生成问题: {suggested_question}")
            return {
                "question": suggested_question,
                "options": ["是", "否", "不确定", "需要更多信息"]
            }
    
    # 3. 基于候选病害生成差异化问题
    candidates = confidence_result.disease_candidates
    if not candidates or len(candidates) < 2:
        return {
            "question": "为了更准确地诊断，请您再详细描述一下观察到的异常情况，比如病斑的形状、颜色，或者叶片卷曲的样子？",
            "options": ["补充完毕", "没有其他异常"]
        }
    
    top_candidate = candidates[0]
    second_candidate = candidates[1]

    # 4. 从数据库获取这两种病害的详细档案
    db = SessionLocal()
    try:
        disease_crud = get_disease_profile_crud(db)
        top_profile = disease_crud.get_by_name(top_candidate['disease_name'])
        second_profile = disease_crud.get_by_name(second_candidate['disease_name'])
    finally:
        db.close()

    if not top_profile or not second_profile:
        return {
            "question": "数据库信息不足，无法进行精确提问。请您再详细描述一下症状？",
            "options": ["补充完毕", "没有其他异常"]
        }

    context = {
        "current_evidence": state.get("evidence_matrix", {}),
        "top_candidate": {
            "name": top_profile.disease_name,
            "key_features": top_profile.key_diagnostic_features,
            "visual_checklist": top_profile.visual_symptoms_checklist
        },
        "second_candidate": {
            "name": second_profile.disease_name,
            "key_features": second_profile.key_diagnostic_features,
            "visual_checklist": second_profile.visual_symptoms_checklist
        }
    }
    
    return await ask_llm_for_differentiating_question(context)


async def ask_llm_for_differentiating_question(context: Dict[str, Any]) -> Dict[str, Any]:
    """调用LLM生成差异化问题和选项"""
    
    parser = JsonOutputParser()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位顶级的植物病理学专家和沟通专家。你的任务是根据现有信息，设计一个**最关键**的多项选择题，以区分两种最可能的植物病害。

**严格遵循以下指令:**
1.  **分析差异**: 仔细比对两种候选病害的“关键诊断特征”和“视觉特征”。找出它们之间最显著、最独特的区别。
2.  **聚焦一点**: 你的问题必须只针对**一个**最具决定性的区分点。例如，是病斑的形状（圆形 vs 不规则），还是叶片黄化的模式（均匀 vs 沿叶脉）。不要问宽泛的问题。
3.  **设计选项**: 提供2-4个清晰、简洁、互斥的选项。选项应该直接对应于不同病害的特征。其中一个选项可以是“以上都不是”或“不确定”。
4.  **用户友好**: 使用简单易懂的语言，避免专业术语。
5.  **JSON输出**: 必须严格按照以下JSON格式返回，不包含任何额外的解释或文字。
    ```json
    {{
      "question": "这里是你的问题",
      "options": ["选项A", "选项B", "选项C"]
    }}
    ```
"""),
        ("user", """**上下文信息:**

1.  **当前已掌握的证据:**
    ```json
    {current_evidence}
    ```

2.  **候选病害一 (最可能):**
    - **名称**: {top_candidate_name}
    - **关键特征**: {top_candidate_features}
    - **视觉特征**: {top_candidate_visual}

3.  **候选病害二 (次可能):**
    - **名称**: {second_candidate_name}
    - **关键特征**: {second_candidate_features}
    - **视觉特征**: {second_candidate_visual}

请根据以上信息，生成你的诊断问题。""")
    ])
    
    chain = prompt | llm | parser
    
    try:
        context_str = {
            "current_evidence": json.dumps(context["current_evidence"], ensure_ascii=False, indent=2),
            "top_candidate_name": context["top_candidate"]["name"],
            "top_candidate_features": ", ".join(context["top_candidate"]["key_features"]),
            "top_candidate_visual": json.dumps(context["top_candidate"]["visual_checklist"], ensure_ascii=False, indent=2),
            "second_candidate_name": context["second_candidate"]["name"],
            "second_candidate_features": ", ".join(context["second_candidate"]["key_features"]),
            "second_candidate_visual": json.dumps(context["second_candidate"]["visual_checklist"], ensure_ascii=False, indent=2)
        }
        
        question_obj = await chain.ainvoke(context_str)
        return question_obj
    except Exception as e:
        print(f"LLM生成差异化问题失败: {e}")
        return {
            "question": "为了进一步诊断，请问您观察到的叶片发黄，更接近以下哪种情况？",
            "options": [
                "整个叶片均匀变黄",
                "只有叶脉是绿的，叶肉变黄",
                "从叶尖或叶缘开始变黄",
                "不确定/其他情况"
            ]
        }

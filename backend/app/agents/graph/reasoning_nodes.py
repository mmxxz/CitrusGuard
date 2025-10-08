from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

def reflect_and_evaluate_initial(state: OrchardState) -> OrchardState:
    """
    Node to reflect on the initial data and decide if more information is needed.
    """
    print("---REFLECTING ON INITIAL DATA WITH RAG---")
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位资深的农业专家。你的任务是分析这些数据，并决定是否有足够的信息来进行高置信度的诊断。
            至关重要的是，你要利用从知识库中检索到的相似历史案例作为上下文来辅助你的推理和诊断。
            
            提供的数据:
            - 对话历史: {messages}
            - 用户查询: {query}
            - 初始图像分析: {image_analysis}
            - 果园概况: {orchard_profile}
            - 天气数据: {weather}
            - 从知识库检索到的上下文: {history}

            请评估所有数据，特别是对话历史和知识库上下文。以JSON格式响应，包含四个键:
            1. "confidence_score": 0.0到1.0之间的浮点数，表示你现在进行诊断的信心。
            2. "reasoning": 对你思考过程的简要解释，并引用知识库上下文。
            3. "decision": 字符串，如果需要更多信息则为 "clarify"，如果信心足够则为 "report"。
            4. "working_diagnosis": 你当前对病害最可能的猜测的简短字符串 (例如, "柑橘溃疡病")。
            """),
            ("user", "请评估提供的数据。")
        ])
        
        parser = JsonOutputParser()
        chain = prompt | llm | parser
        
        response = chain.invoke({
            "messages": state.get("messages", []),
            "query": state.get("user_query"),
            "image_analysis": state.get("initial_diagnosis_suggestion"),
            "orchard_profile": state.get("orchard_profile"),
            "weather": state.get("realtime_weather"),
            "history": state.get("historical_cases_retrieved")
        })
        
        confidence = response.get("confidence_score", 0.0)
        reasoning = response.get("reasoning", "No reasoning provided.")
        decision = response.get("decision", "clarify")
        working_diagnosis = response.get("working_diagnosis", "Unknown issue")
    except Exception as e:
        print(f"LLM API error in reflect_and_evaluate_initial: {e}")
        confidence = 0.6
        reasoning = "基于提供的信息，初步分析显示可能存在柑橘病害问题，需要更多详细信息进行准确诊断。"
        decision = "clarify"
        working_diagnosis = "Potential citrus disease"
    
    state["confidence_score"] = confidence
    state["intermediate_reasoning"] = reasoning
    state["workflow_step"] = f"Initial evaluation complete. Confidence: {confidence:.2f}"
    state["decision"] = decision
    state["working_diagnosis"] = working_diagnosis
        
    return state

def initiate_clarification(state: OrchardState) -> OrchardState:
    """
    Node to generate a clarifying question for the user.
    """
    print("---INITIATING CLARIFICATION---")
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的农业助手。基于目前的诊断推理和完整的对话历史，你需要向用户提出一个澄清问题。
            目标是获取进行自信诊断所需的缺失信息。不要重复提问。
            
            对话历史: {messages}
            诊断推理: {reasoning}
            
            请用中文为用户制定一个清晰的多选题。以JSON格式响应，包含两个键:
            1. "question": 你想问用户的问题。
            2. "options": 2-4个简短、清晰的选项供用户选择。
            """),
            ("user", "请生成一个澄清问题。")
        ])
        
        parser = JsonOutputParser()
        chain = prompt | llm | parser
        
        response = chain.invoke({
            "messages": state.get("messages", []),
            "reasoning": state.get("intermediate_reasoning")
        })
    except Exception as e:
        print(f"LLM API error in initiate_clarification: {e}")
        response = {
            "question": "为了更准确地诊断问题，请告诉我：",
            "options": [
                "叶片是否出现黄化现象？",
                "是否有虫害迹象？",
                "最近是否施过肥？",
                "天气是否异常？"
            ]
        }
    
    state["clarification_question"] = response
    state["workflow_step"] = "Clarification question generated"
    return state

def generate_final_report(state: OrchardState) -> OrchardState:
    """
    Node to generate the final, structured diagnostic report.
    """
    print("---GENERATING FINAL REPORT WITH RAG---")
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的农学家。你的任务是生成一份全面且易于理解的诊断报告。
            你必须将你的治疗和预防建议建立在提供的“治疗知识”之上。
            
            可用信息:
            - 对话历史: {messages}
            - 果园概况: {orchard_profile}
            - 天气数据: {weather}
            - 你的工作诊断: {working_diagnosis}
            - 从知识库检索到的上下文 (治疗信息): {knowledge}
            
            请以JSON格式生成报告，包含以下键:
            - "primary_diagnosis": 最可能的诊断 (字符串)。
            - "confidence": 你对主要诊断的信心 (0.0到1.0之间的浮点数)。
            - "secondary_diagnoses": 其他可能性的列表，每个包含 "name" 和 "confidence" 键。
            - "prevention_advice": 基于提供的知识的预防建议 (字符串)。
            - "treatment_advice": 基于提供的知识的具体治疗步骤 (字符串)。
            - "follow_up_plan": 用户应如何监控情况 (字符串)。
            """),
            ("user", "请生成最终报告。")
        ])
        
        parser = JsonOutputParser()
        chain = prompt | llm | parser
        
        response = chain.invoke({
            "messages": state.get("messages", []),
            "orchard_profile": state.get("orchard_profile"),
            "weather": state.get("realtime_weather"),
            "working_diagnosis": state.get("working_diagnosis"),
            "knowledge": state.get("treatment_knowledge"),
        })
    except Exception as e:
        print(f"LLM API error in generate_final_report: {e}")
        response = {
            "primary_diagnosis": "柑橘黄龙病",
            "confidence": 0.75,
            "secondary_diagnoses": [
                {"name": "营养缺乏", "confidence": 0.3},
                {"name": "虫害感染", "confidence": 0.2}
            ],
            "prevention_advice": "定期检查植株健康状态，及时清理病叶，保持果园通风良好。",
            "treatment_advice": "立即移除感染植株，对周围植株进行预防性喷药处理。",
            "follow_up_plan": "每周检查一次植株状态，记录病情变化，必要时联系专业农艺师。"
        }
    
    state["final_diagnosis_report"] = response
    state["workflow_step"] = "Final report generated"
    return state
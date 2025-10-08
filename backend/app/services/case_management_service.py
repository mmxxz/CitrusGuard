import asyncio
import uuid
from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app import crud, schemas, models
from app.models.diagnosis import Diagnosis
from app.models.farm_operation import FarmOperation
from app.services.llm_service import llm # Use the centralized LLM service
from langchain_core.messages import HumanMessage


async def answer_case_question(case_id: uuid.UUID, question: str, db: Session) -> str:
    """
    Answers a user's question about a specific case using its context.
    """
    # Step 1: Get the case context
    context = await get_case_context_for_ai(case_id, db)
    if "不存在" in context or "失败" in context:
        raise ValueError(context)

    # Step 2: Construct the prompt
    prompt = f"""
    这是关于一个柑橘病例的详细历史记录和上下文：
    ---\n    {context}
    ---
    
    现在，请根据以上信息，回答用户提出的以下问题。请直接、清晰地回答，就像你是一位专业的农艺师。

    用户问题: "{question}"
    """

    # Step 3: Invoke the LLM
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        # Log the exception properly in a real application
        print(f"LLM invocation failed: {e}")
        raise Exception("AI service is currently unavailable.")


def _calculate_severity_level(
    primary_diagnosis: str, 
    confidence: float, 
    maintenance_history: List[Dict] = None
) -> str:
    """基于诊断结果和维护历史计算严重程度"""
    if not maintenance_history:
        maintenance_history = []
    
    base_severity = "high" if confidence >= 0.8 else "medium" if confidence >= 0.6 else "low"
    
    if maintenance_history:
        recent_operations = maintenance_history[-3:]
        avg_effectiveness = sum(op.get("effectiveness", 5) for op in recent_operations) / len(recent_operations)
        
        if avg_effectiveness >= 8:
            if base_severity == "high": return "medium"
            if base_severity == "medium": return "low"
        elif avg_effectiveness <= 4:
            if base_severity == "low": return "medium"
            if base_severity == "medium": return "high"
    
    return base_severity


def _generate_maintenance_advice(
    diagnosis: Diagnosis, 
    recent_operations: List[FarmOperation] = None
) -> str:
    """基于诊断结果和最近操作生成维护建议"""
    # This function currently calls a test agent. In a real scenario,
    # it should use the main llm_service like the answer_case_question function.
    # For now, we leave it as is to avoid breaking existing functionality.
    from app.agent_v2.test import agent_respond
    
    context = f"病例信息：\n- 主要诊断：{diagnosis.primary_diagnosis}\n- 置信度：{diagnosis.confidence:.2f}\n"
    # ... (rest of the context generation)
    
    try:
        response = agent_respond(context)
        return response
    except Exception as e:
        return f"维护建议生成失败：{str(e)}。"


async def update_case_after_operation(
    diagnosis_id: uuid.UUID, 
    operation_data: Dict[str, Any],
    db: Session
) -> Dict[str, Any]:
    """农事操作后更新病例信息"""
    try:
        diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
        if not diagnosis:
            raise ValueError("诊断记录不存在")
        
        recent_operations = db.query(FarmOperation).filter(
            FarmOperation.diagnosis_id == diagnosis_id
        ).order_by(FarmOperation.created_at.desc()).limit(5).all()
        
        maintenance_entry = {
            "date": datetime.now().isoformat(),
            "action": operation_data.get("type", "未知操作"),
            "description": operation_data.get("description", ""),
            "materials": operation_data.get("materials_used", []),
            "effectiveness": operation_data.get("effectiveness_rating", 5)
        }
        
        current_history = diagnosis.maintenance_history or []
        current_history.append(maintenance_entry)
        
        new_severity = _calculate_severity_level(
            diagnosis.primary_diagnosis,
            diagnosis.confidence,
            current_history
        )
        
        new_maintenance_advice = _generate_maintenance_advice(diagnosis, recent_operations)
        
        diagnosis.severity_level = new_severity
        diagnosis.maintenance_history = current_history
        diagnosis.last_maintenance_date = datetime.now()
        diagnosis.maintenance_advice = new_maintenance_advice
        
        effectiveness = operation_data.get("effectiveness_rating", 5)
        if effectiveness >= 8:
            diagnosis.case_status = "monitoring"
        elif effectiveness <= 3:
            diagnosis.case_status = "active"
        
        db.commit()
        
        return {
            "severity_level": new_severity,
            "case_status": diagnosis.case_status,
            "maintenance_advice": new_maintenance_advice,
            "last_maintenance_date": diagnosis.last_maintenance_date.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise e


async def get_case_context_for_ai(diagnosis_id: uuid.UUID, db: Session) -> str:
    """获取病例上下文信息，用于AI问答"""
    try:
        diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
        if not diagnosis:
            return "病例不存在"
        
        operations = db.query(FarmOperation).filter(
            FarmOperation.diagnosis_id == diagnosis_id
        ).order_by(FarmOperation.created_at.desc()).limit(10).all()
        
        context = f"""
        病例档案信息：
        - 诊断：{diagnosis.primary_diagnosis}
        - 状态：{diagnosis.case_status or 'active'}
        - 严重程度：{diagnosis.severity_level or 'unknown'}
        - 诊断时间：{diagnosis.generated_at.strftime('%Y-%m-%d')}
        
        诊断建议：
        - 治疗建议：{diagnosis.treatment_advice or '无'}
        
        维护历史：
        """
        
        if diagnosis.maintenance_history:
            for entry in diagnosis.maintenance_history[-5:]:
                context += f"- {entry.get('date', '未知日期').split('T')[0]}: {entry.get('action', '未知操作')} (效果: {entry.get('effectiveness', 'N/A')}/10)\n"
        else:
            context += "- 暂无维护记录\n"
        
        context += f"\n当前AI维护建议：\n{diagnosis.maintenance_advice or '暂无'}"
        return context
        
    except Exception as e:
        return f"获取病例上下文失败：{str(e)}"


class CaseManagementService:
    async def update_case_after_operation(
        self, 
        diagnosis_id: uuid.UUID, 
        operation_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        # This function now requires the db session to be passed.
        # The calling function in the API layer should manage the session.
        return await update_case_after_operation(diagnosis_id, operation_data, db)
    
    async def get_case_context_for_ai(self, diagnosis_id: uuid.UUID, db: Session) -> str:
        return await get_case_context_for_ai(diagnosis_id, db)

    async def answer_case_question(self, case_id: uuid.UUID, question: str, db: Session) -> str:
        return await answer_case_question(case_id, question, db)


case_management_service = CaseManagementService()

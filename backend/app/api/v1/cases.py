from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.services.case_management_service import case_management_service
from app.schemas.diagnosis import CaseQuestion
from app import models

router = APIRouter()

@router.post("/cases/{case_id}/ask", response_model=dict)
async def ask_case_question(
    case_id: UUID,
    request: CaseQuestion,
    db: Session = Depends(get_db)
):
    """
    针对特定病例进行提问，获取AI的上下文回答。
    """
    try:
        answer = await case_management_service.answer_case_question(
            case_id=case_id, 
            question=request.question, 
            db=db
        )
        return {"answer": answer}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

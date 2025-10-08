import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas, crud, models
from app.schemas.diagnosis import CaseFile
from app.schemas.farm_operation import FarmOperation, FarmOperationCreate
from app.core.database import get_db
from app.services.auth_service import get_current_user
from app.crud import diagnosis as diagnosis_crud
from app.crud import farm_operation as farm_operation_crud
from app.services.case_management_service import case_management_service

router = APIRouter(
    prefix="/orchards",
    tags=["orchards"],
)

@router.post("/{orchard_id}/cases/{diagnosis_id}/operation", response_model=schemas.FarmOperation)
def create_farm_operation_for_case(
    orchard_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
    operation: schemas.FarmOperationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")
    
    # Ensure the diagnosis belongs to the user and orchard
    db_diag = diagnosis_crud.get_diagnosis_result(db, diagnosis_id)
    if db_diag is None:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    session = diagnosis_crud.get_diagnosis_session(db, db_diag.session_id)
    if session is None or session.orchard_id != orchard_id:
        raise HTTPException(status_code=403, detail="Diagnosis does not belong to this orchard")

    operation.diagnosis_id = diagnosis_id
    
    # 创建农事操作
    created_operation = farm_operation_crud.create_farm_operation(
        db=db, 
        orchard_id=orchard_id, 
        user_id=current_user.id, 
        operation=operation
    )
    
    # 异步更新病例信息
    try:
        operation_data = {
            "type": operation.type,
            "description": operation.description,
            "materials_used": operation.materials_used,
            "effectiveness_rating": getattr(operation, 'effectiveness_rating', 5)
        }
        # 注意：这里应该使用异步调用，但为了简化，我们使用同步方式
        # 在实际生产环境中，应该使用后台任务队列
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            case_update = loop.run_until_complete(
                case_management_service.update_case_after_operation(diagnosis_id, operation_data)
            )
        finally:
            loop.close()
    except Exception as e:
        # 病例更新失败不应该影响农事操作的创建
        print(f"Failed to update case after operation: {e}")
    
    return created_operation


@router.get("/{orchard_id}/cases/{diagnosis_id}/ai-context")
async def get_case_ai_context(
    orchard_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """获取病例的AI问答上下文"""
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")
    
    # 确保诊断属于用户和果园
    db_diag = diagnosis_crud.get_diagnosis_result(db, diagnosis_id)
    if db_diag is None:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    session = diagnosis_crud.get_diagnosis_session(db, db_diag.session_id)
    if session is None or session.orchard_id != orchard_id:
        raise HTTPException(status_code=403, detail="Diagnosis does not belong to this orchard")
    
    context = await case_management_service.get_case_context_for_ai(diagnosis_id)
    return {"context": context}


@router.post("/", response_model=schemas.Orchard)
def create_orchard(
    orchard: schemas.OrchardCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    return crud.orchard.create_user_orchard(db=db, orchard=orchard, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Orchard])
def read_orchards(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    orchards = crud.orchard.get_orchards_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return orchards

@router.get("/{orchard_id}", response_model=schemas.Orchard)
def read_orchard(
    orchard_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None:
        raise HTTPException(status_code=404, detail="Orchard not found")
    if db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_orchard

@router.put("/{orchard_id}", response_model=schemas.Orchard)
def update_orchard(
    orchard_id: uuid.UUID,
    orchard_in: schemas.OrchardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None:
        raise HTTPException(status_code=404, detail="Orchard not found")
    if db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.orchard.update_orchard(db=db, db_orchard=db_orchard, orchard_in=orchard_in)

@router.delete("/{orchard_id}", response_model=schemas.Orchard)
def delete_orchard(
    orchard_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None:
        raise HTTPException(status_code=404, detail="Orchard not found")
    if db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.orchard.delete_orchard(db=db, db_orchard=db_orchard)

@router.get("/{orchard_id}/health_overview", response_model=schemas.HealthOverview)
def read_health_overview(
    orchard_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")

    mock_weather_data = {
        "condition": "多云", "temperature": 26.5, "humidity": 78.0, "precipitation": 2.5, "wind_speed": 10.2
    }
    mock_briefing = "今日湿度较高，请注意防范炭疽病。建议检查果园排水系统。"

    overview_data = {
        "health_score": db_orchard.health_score if db_orchard.health_score is not None else 85.0,
        "has_new_alerts": db_orchard.has_new_alerts if db_orchard.has_new_alerts is not None else True,
        "current_weather": mock_weather_data,
        "ai_daily_briefing": mock_briefing,
    }
    return schemas.HealthOverview(**overview_data)

@router.get("/{orchard_id}/alerts", response_model=List[schemas.Alert])
def read_orchard_alerts(
    orchard_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")
    
    alerts = crud.alert.get_alerts_by_orchard(db, orchard_id=orchard_id, skip=skip, limit=limit)
    return alerts

@router.get("/{orchard_id}/cases", response_model=List[CaseFile])
def read_orchard_cases(
    orchard_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")
    
    cases = diagnosis_crud.get_cases_by_orchard(db, orchard_id=orchard_id, skip=skip, limit=limit)
    return cases

@router.get("/{orchard_id}/cases/{diagnosis_id}/detail", response_model=schemas.DiagnosisResult)
def get_case_detail(
    orchard_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """获取病例的详细信息"""
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")
    
    # 获取诊断结果
    db_diagnosis = diagnosis_crud.get_diagnosis_result(db, diagnosis_id)
    if db_diagnosis is None:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    # 验证诊断结果属于该果园
    session = diagnosis_crud.get_diagnosis_session(db, db_diagnosis.session_id)
    if session is None or session.orchard_id != orchard_id:
        raise HTTPException(status_code=403, detail="Diagnosis does not belong to this orchard")
    
    return db_diagnosis

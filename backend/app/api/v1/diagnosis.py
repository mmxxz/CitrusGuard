import uuid
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app import schemas, crud, models
from app.api.v1.orchards import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.services.agent_v2_service import agent_v2_service
from app.services.langgraph_service import langgraph_service
from app.services.websocket_service import manager


def _diagnosis_agent_backend() -> str:
    """来自环境变量 DIAGNOSIS_AGENT_BACKEND：agent_v2 | langgraph"""
    return (settings.DIAGNOSIS_AGENT_BACKEND or "agent_v2").strip().lower()

router = APIRouter(
    prefix="/orchards/{orchard_id}/diagnosis",
    tags=["diagnosis"],
)

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

@router.post("/start", response_model=schemas.DiagnosisSessionStartResponse)
async def start_diagnosis(
    orchard_id: uuid.UUID,
    initial_data: schemas.DiagnosisSessionStart,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_orchard = crud.orchard.get_orchard(db, orchard_id=orchard_id)
    if db_orchard is None or db_orchard.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Orchard not found")

    # 1. Create the session in the DB first to get a stable session_id
    db_session = crud.diagnosis.create_diagnosis_session(db, orchard_id=orchard_id, user_id=current_user.id)
    session_id = str(db_session.id)
    
    # 2. Store the user's first message
    crud.diagnosis.create_message(db, session_id=db_session.id, message=schemas.MessageBase(sender="user", content_text=initial_data.initial_description))

    # 3. 后台诊断任务：默认 agent_v2；设置 DIAGNOSIS_AGENT_BACKEND=langgraph 走 app/agents 状态图
    q = initial_data.initial_description or ""
    if _diagnosis_agent_backend() == "langgraph":
        await langgraph_service.start_new_session(
            session_id=session_id,
            orchard_id=orchard_id,
            initial_query=q,
            image_urls=initial_data.image_urls,
        )
    else:
        await agent_v2_service.start_new_session(
            session_id=session_id,
            orchard_id=orchard_id,
            initial_query=initial_data.initial_description,
            image_urls=initial_data.image_urls,
        )
    
    return schemas.DiagnosisSessionStartResponse(session_id=session_id)

@router.post("/{session_id}/continue")
async def continue_diagnosis(
    orchard_id: uuid.UUID,
    session_id: str,
    user_input: schemas.DiagnosisSessionContinue,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    crud.diagnosis.create_message(
        db,
        session_id=uuid.UUID(session_id),
        message=schemas.MessageBase(
            sender="user",
            content_text=user_input.user_input,
            content_image_urls=user_input.image_urls,
        ),
    )
    if _diagnosis_agent_backend() == "langgraph":
        await langgraph_service.continue_session(session_id, user_input.user_input)
    else:
        await agent_v2_service.continue_session(
            session_id,
            user_input.user_input,
            user_input.image_urls,
        )
    return {"status": "received"}

@router.get("/{session_id}/result", response_model=schemas.DiagnosisResult)
def get_diagnosis_result(
    orchard_id: uuid.UUID,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = crud.diagnosis.get_diagnosis_session(db, session_id=session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Diagnosis session not found")

    result = crud.diagnosis.get_diagnosis_result_by_session(db, session_id=session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not yet available for this session.")
    
    return result

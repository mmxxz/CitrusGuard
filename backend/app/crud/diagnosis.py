from sqlalchemy.orm import Session
import uuid

from app.models import diagnosis as models
from app.models import farm_operation
from app.schemas import diagnosis as schemas

# === DiagnosisSession CRUD ===

def create_diagnosis_session(db: Session, orchard_id: uuid.UUID, user_id: uuid.UUID, session_id_override: uuid.UUID | None = None):
    db_session = models.DiagnosisSession(
        id=session_id_override if session_id_override else uuid.uuid4(),
        orchard_id=orchard_id,
        user_id=user_id,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_diagnosis_session(db: Session, session_id: uuid.UUID):
    return db.query(models.DiagnosisSession).filter(models.DiagnosisSession.id == session_id).first()

def create_diagnosis_result(db: Session, session_id: uuid.UUID, result_data: schemas.DiagnosisResultCreate):
    db_diagnosis = models.Diagnosis(
        session_id=session_id,
        **result_data.model_dump()
    )
    db.add(db_diagnosis)
    
    # Update session status
    db_session = get_diagnosis_session(db, session_id)
    if db_session:
        db_session.status = "completed"
        db.add(db_session)

    db.commit()
    db.refresh(db_diagnosis)
    return db_diagnosis


def upsert_diagnosis_result(db: Session, session_id: uuid.UUID, result_data: schemas.DiagnosisResultCreate):
    """
    若该会话已有 diagnoses 行则更新（多轮后 agent 才输出正式报告时同步档案），否则新建。
    """
    row = get_diagnosis_result_by_session(db, session_id)
    if row is None:
        return create_diagnosis_result(db, session_id, result_data)
    payload = result_data.model_dump()
    for key, val in payload.items():
        if hasattr(row, key):
            setattr(row, key, val)
    db_session = get_diagnosis_session(db, session_id)
    if db_session:
        db_session.status = "completed"
        db.add(db_session)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def get_diagnosis_result_by_session(db: Session, session_id: uuid.UUID):
    return db.query(models.Diagnosis).filter(models.Diagnosis.session_id == session_id).first()

def get_diagnosis_result(db: Session, diagnosis_id: uuid.UUID):
    return db.query(models.Diagnosis).filter(models.Diagnosis.id == diagnosis_id).first()

# === DiagnosisMessage CRUD ===

def create_message(db: Session, session_id: uuid.UUID, message: schemas.MessageBase):
    db_message = models.DiagnosisMessage(
        session_id=session_id,
        sender=message.sender,
        content_text=message.content_text,
        content_image_urls=message.content_image_urls,
        message_type=message.message_type
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

# === Case Files CRUD ===

def get_cases_by_orchard(db: Session, orchard_id: uuid.UUID, skip: int = 0, limit: int = 100):
    """Get all diagnosis cases for a specific orchard"""
    # Get all completed diagnosis sessions for this orchard
    sessions = db.query(models.DiagnosisSession).filter(
        models.DiagnosisSession.orchard_id == orchard_id,
        models.DiagnosisSession.status == "completed"
    ).offset(skip).limit(limit).all()
    
    cases = []
    for session in sessions:
        # Get the diagnosis result for this session
        diagnosis = get_diagnosis_result_by_session(db, session.id)
        if diagnosis:
            # Get farm operations for this diagnosis to determine status and effectiveness
            farm_ops = db.query(farm_operation.FarmOperation).filter(
                farm_operation.FarmOperation.diagnosis_id == diagnosis.id
            ).all()
            
            # Determine status based on farm operations
            status = "resolved" if farm_ops else "active"
            
            # Calculate effectiveness from farm operations
            effectiveness = None
            if farm_ops:
                # Get the latest farm operation's effectiveness
                latest_op = max(farm_ops, key=lambda x: x.operation_date)
                effectiveness = latest_op.effectiveness_rating
            
            # Determine severity based on confidence
            if diagnosis.confidence >= 0.8:
                severity = "high"
            elif diagnosis.confidence >= 0.6:
                severity = "medium"
            else:
                severity = "low"
            
            case = {
                "id": diagnosis.id,
                "date": diagnosis.generated_at,
                "diagnosis": diagnosis.primary_diagnosis,
                "status": status,
                "severity": severity,
                "treatment": diagnosis.treatment_advice,
                "effectiveness": effectiveness
            }
            cases.append(case)
    
    return cases

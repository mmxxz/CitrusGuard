from sqlalchemy.orm import Session
import uuid

from app.models.orchard import Orchard
from app.schemas.orchard import OrchardCreate, OrchardUpdate

def get_orchard(db: Session, orchard_id: uuid.UUID):
    return db.query(Orchard).filter(Orchard.id == orchard_id).first()

def get_orchards_by_user(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(Orchard).filter(Orchard.user_id == user_id).offset(skip).limit(limit).all()

def create_user_orchard(db: Session, orchard: OrchardCreate, user_id: uuid.UUID):
    db_orchard = Orchard(**orchard.model_dump(), user_id=user_id)
    db.add(db_orchard)
    db.commit()
    db.refresh(db_orchard)
    return db_orchard

def update_orchard(db: Session, db_orchard: Orchard, orchard_in: OrchardUpdate):
    orchard_data = orchard_in.model_dump(exclude_unset=True)
    for key, value in orchard_data.items():
        setattr(db_orchard, key, value)
    db.add(db_orchard)
    db.commit()
    db.refresh(db_orchard)
    return db_orchard

def delete_orchard(db: Session, db_orchard: Orchard):
    # First delete all related diagnosis sessions and their data
    from app.models import diagnosis as diagnosis_models
    
    # Delete diagnosis results first (they reference diagnosis sessions)
    diagnosis_sessions = db.query(diagnosis_models.DiagnosisSession).filter(
        diagnosis_models.DiagnosisSession.orchard_id == db_orchard.id
    ).all()
    
    for session in diagnosis_sessions:
        # Delete diagnosis results for this session
        db.query(diagnosis_models.Diagnosis).filter(
            diagnosis_models.Diagnosis.session_id == session.id
        ).delete()
        
        # Delete diagnosis messages for this session
        db.query(diagnosis_models.DiagnosisMessage).filter(
            diagnosis_models.DiagnosisMessage.session_id == session.id
        ).delete()
    
    # Delete diagnosis sessions
    db.query(diagnosis_models.DiagnosisSession).filter(
        diagnosis_models.DiagnosisSession.orchard_id == db_orchard.id
    ).delete()
    
    # Now delete the orchard
    db.delete(db_orchard)
    db.commit()
    return db_orchard

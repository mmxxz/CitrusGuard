from sqlalchemy.orm import Session
import uuid

from app.models import farm_operation as models
from app.schemas import farm_operation as schemas

def create_farm_operation(db: Session, orchard_id: uuid.UUID, user_id: uuid.UUID, operation: schemas.FarmOperationCreate):
    db_operation = models.FarmOperation(
        **operation.model_dump(),
        orchard_id=orchard_id,
        user_id=user_id,
    )
    db.add(db_operation)
    db.commit()
    db.refresh(db_operation)
    return db_operation

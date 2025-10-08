from sqlalchemy.orm import Session
import uuid

from app.models.alert import Alert

def get_alerts_by_orchard(db: Session, orchard_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(Alert).filter(Alert.orchard_id == orchard_id).offset(skip).limit(limit).all()

# In a real application, creating an alert would be a more complex process,
# likely triggered by a background service that analyzes data.
# For now, we'll just have a simple function to get them.

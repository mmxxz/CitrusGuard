from typing import Dict, Optional
import uuid

_session_to_orchard: Dict[str, uuid.UUID] = {}
_current_session_id: Optional[str] = None

def register(session_id: str, orchard_id: uuid.UUID) -> None:
    _session_to_orchard[session_id] = orchard_id

def get_orchard_id(session_id: str) -> Optional[uuid.UUID]:
    return _session_to_orchard.get(session_id)

def set_current_session(session_id: str) -> None:
    global _current_session_id
    _current_session_id = session_id

def get_current_session() -> Optional[str]:
    return _current_session_id



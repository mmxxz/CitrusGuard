from typing import Dict

_session_turn: Dict[str, int] = {}

def next_turn(session_id: str) -> int:
    current = _session_turn.get(session_id, 0) + 1
    _session_turn[session_id] = current
    return current

def get_turn(session_id: str) -> int:
    return _session_turn.get(session_id, 0)



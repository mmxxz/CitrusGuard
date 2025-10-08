from app.core.orchard_state import OrchardState
from app.crud import orchard as orchard_crud
from app.core.database import SessionLocal

def fetch_orchard_profile(state: OrchardState) -> OrchardState:
    """Tool node to fetch orchard profile from the database."""
    if state.get("is_profile_fetched"):
        print("---SKIPPING ORCHARD PROFILE FETCH (CACHED)---")
        return state

    print("---FETCHING ORCHARD PROFILE---")
    db = SessionLocal()
    try:
        # Assuming the full orchard_profile with ID is passed in the initial state
        orchard_id = state.get("orchard_profile", {}).get("id")
        if not orchard_id:
            print("WARNING: Orchard ID not found in state, using default profile")
            # Use a default profile when no orchard ID is available
            profile = {
                "id": None, "name": "Unknown Orchard",
                "location_latitude": None, "location_longitude": None,
                "address_detail": "Unknown location",
                "main_variety": "Citrus", "avg_tree_age": None,
                "soil_type": "Unknown",
            }
            state["orchard_profile"] = profile
            state["is_profile_fetched"] = True
            state["workflow_step"] = "Using default orchard profile"
            return state
            
        # Convert string to UUID if needed
        import uuid
        try:
            if isinstance(orchard_id, str):
                orchard_id = uuid.UUID(orchard_id)
        except ValueError:
            print(f"WARNING: Invalid UUID format: {orchard_id}, using default profile")
            profile = {
                "id": None, "name": "Unknown Orchard",
                "location_latitude": None, "location_longitude": None,
                "address_detail": "Unknown location",
                "main_variety": "Citrus", "avg_tree_age": None,
                "soil_type": "Unknown",
            }
            state["orchard_profile"] = profile
            state["is_profile_fetched"] = True
            state["workflow_step"] = "Using default orchard profile (invalid UUID)"
            return state
            
        db_orchard = orchard_crud.get_orchard(db, orchard_id=orchard_id)
        if not db_orchard:
            print(f"WARNING: Orchard with ID {orchard_id} not found, using default profile")
            # Use a default profile when orchard is not found
            profile = {
                "id": orchard_id, "name": "Unknown Orchard",
                "location_latitude": None, "location_longitude": None,
                "address_detail": "Unknown location",
                "main_variety": "Citrus", "avg_tree_age": None,
                "soil_type": "Unknown",
            }
            state["orchard_profile"] = profile
            state["is_profile_fetched"] = True
            state["workflow_step"] = "Using default orchard profile (orchard not found)"
            return state

        profile = {
            "id": db_orchard.id, "name": db_orchard.name,
            "location_latitude": db_orchard.location_latitude,
            "location_longitude": db_orchard.location_longitude,
            "address_detail": db_orchard.address_detail,
            "main_variety": db_orchard.main_variety,
            "avg_tree_age": db_orchard.avg_tree_age,
            "soil_type": db_orchard.soil_type,
        }
        state["orchard_profile"] = profile
        state["is_profile_fetched"] = True # Set the cache flag
        state["workflow_step"] = "Fetched orchard profile"
        return state
    except Exception as e:
        print(f"ERROR: Failed to fetch orchard profile: {e}")
        # Use a default profile when any error occurs
        profile = {
            "id": state.get("orchard_profile", {}).get("id"), 
            "name": "Unknown Orchard",
            "location_latitude": None, "location_longitude": None,
            "address_detail": "Unknown location",
            "main_variety": "Citrus", "avg_tree_age": None,
            "soil_type": "Unknown",
        }
        state["orchard_profile"] = profile
        state["is_profile_fetched"] = True
        state["workflow_step"] = f"Using default orchard profile (error: {str(e)[:50]})"
        return state
    finally:
        db.close()

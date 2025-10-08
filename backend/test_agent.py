import asyncio
import uuid
from app.services.langgraph_service import langgraph_service
from app.core.database import SessionLocal
from app import crud, schemas

# A mock orchard ID and user ID for testing purposes.
MOCK_ORCHARD_ID = None
user_id = None

def setup_test_data():
    """Ensures at least one user and one orchard exist for testing."""
    global MOCK_ORCHARD_ID, user_id
    db = SessionLocal()
    try:
        user = crud.user.get_user_by_email(db, email="test@example.com")
        if not user:
            user_create = schemas.UserCreate(email="test@example.com", password="password", full_name="Test User")
            user = crud.user.create_user(db, user=user_create)
        user_id = user.id
        
        orchard = crud.orchard.get_orchards_by_user(db, user_id=user.id)
        if not orchard:
            orchard_create = schemas.OrchardCreate(name="Test Orchard")
            orchard = crud.orchard.create_user_orchard(db, orchard=orchard_create, user_id=user.id)
        else:
            orchard = orchard[0]
        MOCK_ORCHARD_ID = orchard.id
        print(f"--- Using Orchard ID for test: {MOCK_ORCHARD_ID} ---")
    finally:
        db.close()

async def test_diagnosis_flow():
    """Tests the 'safe core' diagnosis workflow."""
    print("\n--- SCENARIO 1: TESTING DIAGNOSIS FLOW ---")
    
    # 1. Start session with a diagnostic query
    print("\nStep 1: Starting session with a diagnostic query...")
    query = "My citrus leaves have yellow spots and some weird bumps."
    session_id = uuid.uuid4()
    
    # Manually create the session in the DB, just like the API would
    db = SessionLocal()
    crud.diagnosis.create_diagnosis_session(db, orchard_id=MOCK_ORCHARD_ID, user_id=user_id, session_id_override=session_id)
    db.close()

    initial_state = {
        "user_query": query, "image_urls": None, "orchard_profile": {"id": MOCK_ORCHARD_ID},
        "is_profile_fetched": False, "clarification_needed": True, "clarification_count": 0,
        "workflow_step": "Session started", "session_id": str(session_id)
    }
    await langgraph_service.run_graph(str(session_id), initial_state)
    print(f"✅ Session started with ID: {session_id}")

    # 2. Check the result of the first run (should be a clarification)
    print("\nStep 2: Checking for clarification question...")
    current_state = langgraph_service.conversation_states.get(str(session_id), {})
    print(f"DEBUG: Current state keys: {list(current_state.keys())}")
    print(f"DEBUG: workflow_step: {current_state.get('workflow_step')}")
    print(f"DEBUG: decision: {current_state.get('decision')}")
    print(f"DEBUG: confidence_score: {current_state.get('confidence_score')}")
    clarification = current_state.get("clarification_question")
    print(f"DEBUG: clarification_question: {clarification}")

    # Let's check if a final report was generated instead
    final_report = current_state.get("final_diagnosis_report")
    if final_report:
        print(f"DEBUG: Final report was generated instead: {final_report.get('primary_diagnosis')}")

    assert clarification and "question" in clarification, "Test Failed: No clarification question was generated."
    print(f"✅ Got clarification: {clarification['question']}")

    # 3. Continue session with an answer
    print("\nStep 3: Answering the clarification question...")
    answer = "It's happening on the older leaves."
    task = await langgraph_service.continue_session(str(session_id), answer)
    await task

    # 4. Check the final result (should be a diagnosis report)
    print("\nStep 4: Checking for final diagnosis report...")
    final_state = langgraph_service.conversation_states.get(str(session_id), {})
    report = final_state.get("final_diagnosis_report")
    assert report and "primary_diagnosis" in report, "Test Failed: No final report was generated."
    print(f"✅ Got final report. Primary Diagnosis: {report['primary_diagnosis']}")
    print("--- DIAGNOSIS FLOW TEST PASSED ---")


async def test_dynamic_engine_flow():
    """Tests the 'creative engine' general QA workflow."""
    print("\n--- SCENARIO 2: TESTING DYNAMIC ENGINE FLOW ---")
    
    # 1. Start session with a general query
    print("\nStep 1: Starting session with a general query...")
    query = "What should I be concerned about today?"
    session_id = uuid.uuid4()
    
    # Manually create the session in the DB
    db = SessionLocal()
    crud.diagnosis.create_diagnosis_session(db, orchard_id=MOCK_ORCHARD_ID, user_id=user_id, session_id_override=session_id)
    db.close()

    initial_state = {
        "user_query": query, "image_urls": None, "orchard_profile": {"id": MOCK_ORCHARD_ID},
        "is_profile_fetched": False, "clarification_needed": True, "clarification_count": 0,
        "workflow_step": "Session started", "session_id": str(session_id)
    }
    await langgraph_service.run_graph(str(session_id), initial_state)
    print(f"✅ Session started with ID: {session_id}")

    # Add a small delay to ensure async operations complete
    await asyncio.sleep(2)

    # 2. Check the final result (should be a briefing)
    print("\nStep 2: Checking for final briefing...")
    final_state = langgraph_service.conversation_states.get(str(session_id), {})
    print(f"DEBUG: Dynamic engine final state keys: {list(final_state.keys())}")
    print(f"DEBUG: final_report value: {final_state.get('final_report')}")
    report = final_state.get("final_report") # Note: dynamic engine uses a different key
    assert report and "briefing" in report, "Test Failed: No briefing was generated."
    print(f"✅ Got final briefing: {report['briefing'][:100]}...")
    print("--- DYNAMIC ENGINE FLOW TEST PASSED ---")


async def main():
    setup_test_data()
    if not MOCK_ORCHARD_ID:
        print("Setup failed. Aborting tests.")
        return
        
    try:
        await test_diagnosis_flow()
        await test_dynamic_engine_flow()
        print("\n\n🎉🎉🎉 ALL AGENT TESTS PASSED! 🎉🎉🎉")
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
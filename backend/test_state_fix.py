import asyncio
import uuid
from app.agents.graph.graph import app as langgraph_app
from app.core.orchard_state import OrchardState
from app.core.database import SessionLocal
from app import crud, schemas

async def test_state_passing():
    """Test if dynamic engine state is properly returned"""
    print("=== Testing State Passing in Dynamic Engine ===")

    # Setup test data
    db = SessionLocal()
    try:
        user = crud.user.get_user_by_email(db, email="test@example.com")
        if not user:
            user_create = schemas.UserCreate(email="test@example.com", password="password", full_name="Test User")
            user = crud.user.create_user(db, user=user_create)

        orchard = crud.orchard.get_orchards_by_user(db, user_id=user.id)
        if not orchard:
            orchard_create = schemas.OrchardCreate(name="Test Orchard")
            orchard = crud.orchard.create_user_orchard(db, orchard=orchard_create, user_id=user.id)
        else:
            orchard = orchard[0]
    finally:
        db.close()

    # Test dynamic engine directly
    session_id = str(uuid.uuid4())
    initial_state = OrchardState(
        messages=[],
        user_query="What should I be concerned about today?",
        image_urls=None,
        intent="general_qa",
        session_id=session_id,
        orchard_profile={"id": orchard.id},
        is_profile_fetched=False,
        realtime_weather={"temp": 25, "humidity": 70},
        historical_cases_retrieved=[],
        initial_diagnosis_suggestion=None,
        intermediate_reasoning=None,
        working_diagnosis=None,
        decision=None,
        clarification_needed=False,
        clarification_count=0,
        clarification_question=None,
        final_diagnosis_report=None,
        final_report=None,
        confidence_score=None,
        workflow_step="Session started"
    )

    print(f"Initial state keys: {list(initial_state.keys())}")
    print(f"Initial final_report: {initial_state.get('final_report')}")

    try:
        # Run only the dynamic engine part with proper config
        config = {"configurable": {"thread_id": session_id}}
        final_state = None
        async for step in langgraph_app.astream(initial_state, config=config):
            step_name = list(step.keys())[0]
            final_state = list(step.values())[0]
            print(f"Step: {step_name}")
            print(f"State keys after step: {list(final_state.keys())}")
            print(f"final_report after step: {final_state.get('final_report')}")

        if final_state:
            print(f"\nFinal state keys: {list(final_state.keys())}")
            print(f"Final final_report: {final_state.get('final_report')}")

            if final_state.get('final_report'):
                print("✅ SUCCESS: final_report is preserved!")
                return True
            else:
                print("❌ FAILED: final_report is missing!")
                return False
        else:
            print("❌ FAILED: No final state returned!")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_state_passing())
    print(f"\nTest result: {'PASSED' if result else 'FAILED'}")
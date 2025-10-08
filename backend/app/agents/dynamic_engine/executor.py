from app.core.orchard_state import OrchardState
from app.agents.dynamic_engine.planner import get_plan
from app.agents.tools.fetch_weather_data import fetch_weather_data
from app.agents.tools.retrieve_historical_cases import retrieve_historical_cases
from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app import schemas

# A simple tool registry mapping tool names to functions
tool_registry = {
    "fetch_weather_data": fetch_weather_data,
    "retrieve_historical_cases": retrieve_historical_cases,
}

def generate_daily_briefing(state: OrchardState) -> OrchardState:
    """A simple node to generate a summary based on collected data."""
    print("---GENERATING DAILY BRIEFING---")
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful farm assistant. Based on the provided weather and historical data, write a short, friendly daily briefing for the user."),
            ("user", "Weather: {weather}\nHistory: {history}\nPlease generate the briefing.")
        ])
        chain = prompt | llm | StrOutputParser()
        briefing = chain.invoke({
            "weather": state.get("realtime_weather"),
            "history": state.get("historical_cases_retrieved")
        })
        print(f"DEBUG: Generated briefing: {briefing[:100]}...")
        state["final_report"] = {"briefing": briefing} # Use a consistent key for final output
    except Exception as e:
        print(f"Error generating daily briefing: {e}")
        state["final_report"] = {"briefing": "Could not generate briefing due to an error."}
    return state

tool_registry["generate_daily_briefing"] = generate_daily_briefing

from app.services.websocket_service import manager
import asyncio

# ... (tool_registry and generate_daily_briefing)

def dynamic_engine_executor(state: OrchardState) -> OrchardState:
    """
    The main executor for the dynamic engine.
    It gets a plan and then executes each step, broadcasting progress.
    """
    print("---EXECUTING DYNAMIC ENGINE---")
    user_query = state.get("user_query")
    session_id = state.get("session_id") # Assuming session_id is now in the state
    
    plan = get_plan(user_query)
    
    # Execute the plan step by step
    for step in plan:
        if step in tool_registry:
            # Broadcast progress before executing the tool
            # await manager.broadcast_to_session(session_id, f"PROGRESS:Running:{step}")
            # await asyncio.sleep(1) # Small delay for UX

            tool_function = tool_registry[step]
            state = tool_function(state)
            # Debug info removed for cleaner output
        else:
            print(f"Warning: Tool '{step}' not found in registry.")

    state["workflow_step"] = "Dynamic engine run complete"

    # 关键调试：确认状态完整性
    print(f"DEBUG: Before return - state keys: {list(state.keys())}")
    print(f"DEBUG: Before return - final_report: {state.get('final_report')}")

    # Broadcast the final message from the dynamic engine
    final_report = state.get("final_report", {})
    if final_report is None:
        final_briefing = "Could not generate a briefing."
    else:
        final_briefing = final_report.get("briefing", "Could not generate a briefing.")
    # final_message = schemas.AIResponse(type="text", content=final_briefing)
    # await manager.broadcast_to_session(session_id, f"MESSAGE:{final_message.json()}")

    # 确保返回的是同一个state对象
    print(f"DEBUG: Returning state type: {type(state)}")
    return state

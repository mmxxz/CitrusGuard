from app.core.orchard_state import OrchardState
from app.agents.tools.fetch_weather_data import fetch_weather_data
from app.agents.tools.retrieve_historical_cases import retrieve_historical_cases

def parallel_context_acquisition(state: OrchardState) -> OrchardState:
    """
    Node that runs weather and historical case fetching sequentially.
    Supports re-retrieval based on flags for multi-turn conversations.
    """
    print("---ACQUIRING CONTEXT IN PARALLEL---")
    
    try:
        # Check if we need to re-fetch weather data (usually not needed in multi-turn)
        need_weather = not state.get("realtime_weather") or state.get("need_reretrieve_weather", False)
        if need_weather:
            print("重新获取天气数据...")
            weather_state = fetch_weather_data(state.copy())
            state["realtime_weather"] = weather_state["realtime_weather"]
        else:
            print("使用缓存的天气数据")
        
        # Check if we need to re-fetch historical cases (important for multi-turn)
        need_history = not state.get("historical_cases_retrieved") or state.get("need_reretrieve_historical_cases", False)
        if need_history:
            print("重新检索历史病例...")
            history_state = retrieve_historical_cases(state.copy())
            state["historical_cases_retrieved"] = history_state["historical_cases_retrieved"]
            # Clear the flag after retrieval
            if "need_reretrieve_historical_cases" in state:
                del state["need_reretrieve_historical_cases"]
        else:
            print("使用缓存的历史病例数据")
        
        state["workflow_step"] = "Fetched weather and history"
        
    except Exception as e:
        print(f"ERROR in parallel_context_acquisition: {e}")
        # Set default values on error
        state["realtime_weather"] = {
            "temperature": 25.0,
            "humidity": 70,
            "precipitation_chance": 0.5,
            "forecast": "Weather data unavailable"
        }
        state["historical_cases_retrieved"] = []
        state["workflow_step"] = f"Context acquisition failed: {str(e)[:50]}"
    
    return state

from app.services.llm_service import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import List

def get_plan(user_query: str) -> List[str]:
    """
    Generates a step-by-step plan based on the user's query.
    """
    print("---PLANNING DYNAMIC ENGINE RUN---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert planner for an agricultural assistant.
        Your task is to break down a user's general query into a sequence of concrete, executable steps.
        You have access to the following tools:
        - fetch_weather_data: Gets the current weather.
        - retrieve_historical_cases: Retrieves similar past cases.
        - generate_daily_briefing: Creates a summary and recommendation for the day.

        Based on the user's query, create a plan. Respond with a JSON list of tool names to be called in sequence.
        For example, if the user asks "what should I do today?", a good plan would be:
        ["fetch_weather_data", "retrieve_historical_cases", "generate_daily_briefing"]
        """),
        ("user", "{query}")
    ])
    
    parser = JsonOutputParser()
    chain = prompt | llm | parser
    
    try:
        plan = chain.invoke({"query": user_query})
        print(f"--> Generated Plan: {plan}")
        return plan
    except Exception as e:
        print(f"LLM API error in planner: {e}")
        # Fallback plan
        return ["generate_daily_briefing"]

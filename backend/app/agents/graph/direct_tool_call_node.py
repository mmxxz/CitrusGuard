from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from app.agents.tools.fetch_weather_data import fetch_weather_data
from app.agents.tools.retrieve_historical_cases import retrieve_historical_cases
from app.agents.tools.fetch_orchard_profile import fetch_orchard_profile
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any
import json

def direct_tool_call_node(state: OrchardState) -> OrchardState:
    """
    直接工具调用节点 - 识别用户意图中的特定工具并直接执行
    """
    print("---DIRECT TOOL CALL NODE---")
    
    user_query = state.get("user_query", "")
    if not user_query:
        state["final_report"] = {"error": "没有提供查询问题"}
        return state
    
    try:
        # 1. 识别需要的工具
        tool_needed = identify_required_tool(user_query)
        print(f"识别到需要的工具: {tool_needed}")
        
        # 2. 执行相应的工具
        if tool_needed == "weather":
            result = execute_weather_tool(state)
        elif tool_needed == "historical_cases":
            result = execute_historical_cases_tool(state)
        elif tool_needed == "orchard_profile":
            result = execute_orchard_profile_tool(state)
        else:
            result = {
                "type": "tool_call_response",
                "tool": "unknown",
                "message": "无法识别需要调用的工具",
                "suggestion": "请尝试询问天气、历史案例或果园信息"
            }
        
        state["final_report"] = result
        state["workflow_step"] = f"Direct Tool Call - {tool_needed}"
        
        print(f"工具调用完成: {tool_needed}")
        
    except Exception as e:
        print(f"直接工具调用节点错误: {e}")
        state["final_report"] = {
            "type": "tool_call_response",
            "tool": "error",
            "message": f"工具调用失败: {str(e)}",
            "suggestion": "请重试或联系技术支持"
        }
        state["workflow_step"] = "Direct Tool Call 错误"
    
    return state

def identify_required_tool(query: str) -> str:
    """识别查询中需要的工具"""
    query_lower = query.lower()
    
    # 天气相关关键词
    weather_keywords = ["天气", "温度", "湿度", "降雨", "雨", "风", "weather", "temperature", "humidity", "rain"]
    if any(keyword in query_lower for keyword in weather_keywords):
        return "weather"
    
    # 历史案例相关关键词
    historical_keywords = ["历史", "案例", "类似", "以前", "之前", "historical", "cases", "similar", "previous"]
    if any(keyword in query_lower for keyword in historical_keywords):
        return "historical_cases"
    
    # 果园档案相关关键词
    orchard_keywords = ["果园", "档案", "信息", "我的", "orchard", "profile", "information", "my"]
    if any(keyword in query_lower for keyword in orchard_keywords):
        return "orchard_profile"
    
    return "unknown"

def execute_weather_tool(state: OrchardState) -> Dict[str, Any]:
    """执行天气工具"""
    try:
        # 获取果园信息
        orchard_profile = state.get("orchard_profile", {})
        if not orchard_profile:
            # 如果没有果园信息，先获取
            state = fetch_orchard_profile(state)
            orchard_profile = state.get("orchard_profile", {})
        
        # 调用天气工具
        updated_state = fetch_weather_data(state)
        weather_data = updated_state.get("realtime_weather", {})
        
        # 生成用户友好的天气报告
        if weather_data and weather_data.get("source") != "error_fallback":
            from app.services.sync_weather_service import sync_weather_service
            summary = sync_weather_service.get_weather_summary(weather_data)
            
            return {
                "type": "tool_call_response",
                "tool": "weather",
                "data": weather_data,
                "summary": summary,
                "message": "天气信息获取成功",
                "briefing": summary  # 添加briefing字段供前端使用
            }
        else:
            return {
                "type": "tool_call_response",
                "tool": "weather",
                "data": weather_data,
                "message": "天气信息获取失败，请检查网络连接或稍后重试",
                "briefing": "天气信息获取失败，请检查网络连接或稍后重试"
            }
    except Exception as e:
        return {
            "type": "tool_call_response",
            "tool": "weather",
            "error": str(e),
            "message": "天气信息获取失败",
            "briefing": f"天气信息获取失败: {str(e)}"
        }

def execute_historical_cases_tool(state: OrchardState) -> Dict[str, Any]:
    """执行历史案例工具"""
    try:
        # 调用历史案例工具
        updated_state = retrieve_historical_cases(state)
        historical_cases_data = updated_state.get("historical_cases_retrieved", [])
        
        return {
            "type": "tool_call_response",
            "tool": "historical_cases",
            "data": historical_cases_data,
            "message": "历史案例获取成功",
            "briefing": f"已获取 {len(historical_cases_data) if historical_cases_data else 0} 个相关历史案例"
        }
    except Exception as e:
        return {
            "type": "tool_call_response",
            "tool": "historical_cases",
            "error": str(e),
            "message": "历史案例获取失败",
            "briefing": f"历史案例获取失败: {str(e)}"
        }

def execute_orchard_profile_tool(state: OrchardState) -> Dict[str, Any]:
    """执行果园档案工具"""
    try:
        # 调用果园档案工具
        updated_state = fetch_orchard_profile(state)
        orchard_profile = updated_state.get("orchard_profile", {})
        
        return {
            "type": "tool_call_response",
            "tool": "orchard_profile",
            "data": orchard_profile,
            "message": "果园档案获取成功",
            "briefing": f"果园档案: {orchard_profile.get('name', '未知果园')} - {orchard_profile.get('main_variety', '未知品种')}"
        }
    except Exception as e:
        return {
            "type": "tool_call_response",
            "tool": "orchard_profile",
            "error": str(e),
            "message": "果园档案获取失败",
            "briefing": f"果园档案获取失败: {str(e)}"
        }

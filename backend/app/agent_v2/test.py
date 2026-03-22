import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import asyncio
import json
import requests
import numpy as np
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from app.services.agent_callbacks import WebSocketCallbackHandler
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage as _HumanMsg, AIMessage as _AIMsg

# ── Agent & Memory —— 兼容 langchain 0.3.x 和 langchain 1.x ─────────────────
# langchain 1.2+ 全面重构，删除了 create_tool_calling_agent / AgentExecutor /
# ConversationBufferMemory，改用 LangGraph 原生接口。
# 此处先尝试加载旧版 API，失败时回退到 langgraph.prebuilt 实现相同功能。

try:
    from langchain.agents import create_tool_calling_agent, AgentExecutor  # 0.3.x
    try:
        from langchain.memory import ConversationBufferMemory  # 0.3.x
    except ImportError:
        from langchain_community.memory import ConversationBufferMemory  # type: ignore
    _LEGACY_AGENT = True

except ImportError:
    _LEGACY_AGENT = False

    # ── 用 langgraph.prebuilt 实现等价的 create_tool_calling_agent + AgentExecutor ──
    from langgraph.prebuilt import create_react_agent as _langgraph_create_react_agent

    class ConversationBufferMemory:  # type: ignore[no-redef]
        """最简 ConversationBufferMemory 兼容层"""
        def __init__(self, memory_key: str = "chat_history", return_messages: bool = True):
            self.memory_key = memory_key
            self.return_messages = return_messages
            self._messages: list = []

        def load_memory_variables(self, inputs: dict) -> dict:
            return {self.memory_key: list(self._messages)}

        def save_context(self, inputs: dict, outputs: dict) -> None:
            self._messages.append(_HumanMsg(content=inputs.get("input", "")))
            self._messages.append(_AIMsg(content=outputs.get("output", "")))

        def clear(self) -> None:
            self._messages.clear()

    class AgentExecutor:  # type: ignore[no-redef]
        """将 langgraph.prebuilt.create_react_agent 包装为 AgentExecutor 接口"""
        def __init__(self, agent, tools, memory=None, verbose: bool = False, **kw):
            self._graph = agent   # create_react_agent 返回的 LangGraph app
            self.memory = memory
            self._verbose = verbose

        def _build_messages(self, user_input: str) -> list:
            messages: list = []
            if self.memory:
                hist = self.memory.load_memory_variables({}).get("chat_history", [])
                if isinstance(hist, list):
                    messages.extend(hist)
            messages.append(_HumanMsg(content=user_input))
            return messages

        def _extract_output(self, result: dict, user_input: str) -> dict:
            """取**最后一条有正文的 AIMessage**，避免末尾是 ToolMessage 时 output 非自然语言、档案无法解析。"""
            out_msgs = result.get("messages", []) or []
            output = ""
            for m in reversed(out_msgs):
                if m.__class__.__name__ != "AIMessage":
                    continue
                c = getattr(m, "content", None)
                if isinstance(c, str) and c.strip():
                    output = c
                    break
            if not output and out_msgs:
                last = out_msgs[-1]
                c = getattr(last, "content", None)
                output = c if isinstance(c, str) else (str(c) if c is not None else "")
            if self.memory:
                self.memory.save_context({"input": user_input}, {"output": output})
            return {"output": output}

        def invoke(self, inputs: dict, config: dict | None = None) -> dict:
            user_input = inputs.get("input", "")
            messages = self._build_messages(user_input)
            cfg = dict(config or {})
            cfg.setdefault("recursion_limit", 50)
            result = self._graph.invoke({"messages": messages}, config=cfg)
            return self._extract_output(result, user_input)

        async def ainvoke(self, inputs: dict, config: dict | None = None) -> dict:
            user_input = inputs.get("input", "")
            messages = self._build_messages(user_input)
            cfg = dict(config or {})
            cfg.setdefault("recursion_limit", 50)
            result = await self._graph.ainvoke({"messages": messages}, config=cfg)
            return self._extract_output(result, user_input)

    def create_tool_calling_agent(llm, tools, prompt):  # type: ignore[misc]
        """langchain 1.x 兼容：用 langgraph.prebuilt 创建 tool-calling 智能体"""
        # 从 prompt 提取已 partial 的 system 文本
        try:
            # prompt 已经 .partial(tools_overview=...) 过，直接 format 不含占位符的部分
            sys_text = prompt.messages[0].prompt.template
            # 删掉 {tools} / {tool_names} 占位符行（对 langgraph 无意义）
            import re
            sys_text = re.sub(r"\n?You have access to the following tools:.*?(?=\n\n|\Z)", "",
                              sys_text, flags=re.S)
            sys_text = re.sub(r"\n?Valid tool names:.*?(?=\n\n|\Z)", "", sys_text, flags=re.S)
        except Exception:
            sys_text = "你是一名专业的柑橘病虫害诊断助手。"
        # tools_overview 已 partial 注入，直接格式化（不含动态占位符）
        try:
            sys_text = sys_text.format(tools_overview="")
        except Exception:
            pass
        from langchain_core.messages import SystemMessage as _SysMsg
        return _langgraph_create_react_agent(llm, tools, prompt=_SysMsg(content=sys_text.strip()) if sys_text.strip() else None)
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from urllib.parse import urlparse
import base64
import mimetypes
import sys
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.retrievers import BM25Retriever
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.crud import orchard as orchard_crud
from app.services.session_orchard_registry import get_current_session, get_orchard_id

"""
柑橘病虫害预测系统的核心预测器模块。
"""
import numpy as np


# ===== 疾病名称映射 =====
DISEASE_MAPPING = {
    "炭疽病",
    "疮痂病", 
    "溃疡病",
    "脂点黄斑病",
    "木虱",
    "潜叶蛾",
    "锈壁虱",
    "红蜘蛛"
}
OUTPUT_DISEASES = list(DISEASE_MAPPING)

class CitrusDiseasePredictor:
    """基于专家规则的柑橘病虫害预测器"""
    
    def __init__(self):
        self.history = []
        self.accumulated = {
            'eat': 0.0,   # 有效积温
            'chd': 0,     # 连续高湿天数
            'rcr': 0.0    # 近期累计降雨
        }
        
        # 英文到中文的映射
        self.english_to_chinese = {
            "anthracnose": "炭疽病",
            "scab": "疮痂病", 
            "canker": "溃疡病",
            "greasy_spot": "脂点黄斑病",
            "psyllid": "木虱",
            "leaf_miner": "潜叶蛾",
            "rust_mite": "锈壁虱",
            "red_spider": "红蜘蛛"
        }
    
    def add_daily_data(self, data):
        """添加每日数据并更新累积变量"""
        # 保存数据
        self.history.append(data.copy())
        
        # 更新有效积温 (发育起点12℃)
        daily_eat = max(data['avg_temp'] - 12, 0)
        self.accumulated['eat'] += daily_eat
        
        # 更新连续高湿天数
        if data['avg_rh'] >= 85:
            self.accumulated['chd'] += 1
        else:
            self.accumulated['chd'] = 0
        
        # 更新近期累计降雨 (3天)
        if len(self.history) >= 3:
            self.accumulated['rcr'] = sum(d['rainfall'] for d in self.history[-3:])
        else:
            self.accumulated['rcr'] = sum(d['rainfall'] for d in self.history)
        
        # 限制最大值
        self.accumulated['eat'] = min(self.accumulated['eat'], 400)
        self.accumulated['chd'] = min(self.accumulated['chd'], 14)
        self.accumulated['rcr'] = min(self.accumulated['rcr'], 150)
    
    def predict_disease_risk(self, disease, data):
        """基于规则预测特定疾病的风险"""
        avg_temp = data['avg_temp']
        avg_rh = data['avg_rh']
        lwd = data['lwd']
        rainfall = data['rainfall']
        wind_speed = data['wind_speed']
        host_susceptibility = data.get('host_susceptibility', 0.7)
        host_phenology = data.get('host_phenology', 0.7)
        eat = self.accumulated['eat']
        chd = self.accumulated['chd']
        rcr = self.accumulated['rcr']
        
        risk_score = 0.0
        
        if disease == "炭疽病":
            # 规则1: 温度适宜 + 湿度湿润 + 高感病性 = 高风险
            if 18 <= avg_temp <= 30 and avg_rh >= 70 and host_susceptibility >= 0.7:
                risk_score += 0.8
            
            # 规则2: 温度偏高 + 大雨 + 生长期 = 高风险
            if avg_temp >= 28 and rainfall >= 15 and host_phenology >= 0.6:
                risk_score += 0.7
            
            # 规则3: 温度偏低 + 长高湿日 + 高感病性 = 高风险
            if avg_temp <= 20 and chd >= 5 and host_susceptibility >= 0.7:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 小雨 + 微风 = 高风险
            if 18 <= avg_temp <= 30 and 5 <= rainfall <= 15 and wind_speed <= 5:
                risk_score += 0.5
            
            # 规则5: 温度适宜 + 湿度湿润 + 中感病性 = 中风险
            if 18 <= avg_temp <= 30 and avg_rh >= 60 and 0.4 <= host_susceptibility < 0.7:
                risk_score += 0.4
            
            # 规则6: 抗病 + 干燥 = 低风险
            if host_susceptibility <= 0.3 and avg_rh <= 50:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则7: 休眠期 + 低温 = 低风险
            if host_phenology <= 0.3 and avg_temp <= 15:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则8: 适宜温度 + 无雨 + 短湿润时间 = 低风险
            if 18 <= avg_temp <= 30 and rainfall <= 2 and lwd <= 6:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "疮痂病":
            # 规则1: 温度适宜 + 小雨 + 萌芽期 + 高感病性 = 高风险
            if 18 <= avg_temp <= 30 and 5 <= rainfall <= 15 and 0.4 <= host_phenology <= 0.6 and host_susceptibility >= 0.7:
                risk_score += 0.8
            
            # 规则2: 长湿润时间 + 温度适宜 + 生长期 = 高风险
            if lwd >= 12 and 18 <= avg_temp <= 30 and host_phenology >= 0.6:
                risk_score += 0.7
            
            # 规则3: 长高湿日 + 温度适宜 + 高感病性 = 高风险
            if chd >= 5 and 18 <= avg_temp <= 30 and host_susceptibility >= 0.7:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 湿度湿润 + 中感病性 + 生长期 = 中风险
            if 18 <= avg_temp <= 30 and avg_rh >= 60 and 0.4 <= host_susceptibility < 0.7 and host_phenology >= 0.6:
                risk_score += 0.4
            
            # 规则5: 温度偏高 = 低风险
            if avg_temp >= 32:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则6: 休眠期 = 低风险
            if host_phenology <= 0.3:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则7: 干燥 + 无雨 = 低风险
            if avg_rh <= 50 and rainfall <= 2:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "溃疡病":
            # 规则1: 温度偏高 + 湿度饱和 + 生长期 = 高风险
            if avg_temp >= 28 and avg_rh >= 90 and host_phenology >= 0.6:
                risk_score += 0.8
            
            # 规则2: 温度适宜 + 大雨 + 微风 + 高感病性 = 高风险
            if 18 <= avg_temp <= 30 and rainfall >= 20 and wind_speed <= 5 and host_susceptibility >= 0.7:
                risk_score += 0.7
            
            # 规则3: 长湿润时间 + 温度偏高 + 萌芽期 = 高风险
            if lwd >= 12 and avg_temp >= 28 and 0.4 <= host_phenology <= 0.6:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 湿度湿润 + 高感病性 + 生长期 = 中风险
            if 18 <= avg_temp <= 30 and avg_rh >= 60 and host_susceptibility >= 0.7 and host_phenology >= 0.6:
                risk_score += 0.4
            
            # 规则5: 温度偏高 + 小雨 + 中感病性 = 中风险
            if avg_temp >= 28 and 5 <= rainfall <= 15 and 0.4 <= host_susceptibility < 0.7:
                risk_score += 0.3
            
            # 规则6: 休眠期 = 低风险
            if host_phenology <= 0.3:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则7: 干燥 + 无雨 = 低风险
            if avg_rh <= 50 and rainfall <= 2:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则8: 低温 + 短湿润时间 = 低风险
            if avg_temp <= 15 and lwd <= 6:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "脂点黄斑病":
            # 规则1: 温度适宜 + 大雨 + 湿度饱和 = 高风险
            if 18 <= avg_temp <= 30 and rainfall >= 20 and avg_rh >= 90:
                risk_score += 0.8
            
            # 规则2: 温度偏高 + 长湿润时间 + 高感病性 = 高风险
            if avg_temp >= 28 and lwd >= 12 and host_susceptibility >= 0.7:
                risk_score += 0.7
            
            # 规则3: 长高湿日 + 温度偏高 = 高风险
            if chd >= 5 and avg_temp >= 28:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 小雨 + 中感病性 = 中风险
            if 18 <= avg_temp <= 30 and 5 <= rainfall <= 15 and 0.4 <= host_susceptibility < 0.7:
                risk_score += 0.4
            
            # 规则5: 温度偏高 + 湿度湿润 + 中等湿润时间 = 中风险
            if avg_temp >= 28 and avg_rh >= 60 and 6 <= lwd <= 12:
                risk_score += 0.3
            
            # 规则6: 干燥 + 无雨 = 低风险
            if avg_rh <= 50 and rainfall <= 2:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则7: 低温 = 低风险
            if avg_temp <= 15:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则8: 抗病 + 短湿润时间 = 低风险
            if host_susceptibility <= 0.3 and lwd <= 6:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "木虱":
            # 规则1: 生长期 + 温度适宜 = 高风险
            if host_phenology >= 0.6 and 18 <= avg_temp <= 30:
                risk_score += 0.8
            
            # 规则2: 生长期 + 温度偏高 = 高风险
            if host_phenology >= 0.6 and avg_temp >= 28:
                risk_score += 0.7
            
            # 规则3: 生长期 + 高积温 = 高风险
            if host_phenology >= 0.6 and eat >= 200:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 中积温 = 高风险
            if 18 <= avg_temp <= 30 and 100 <= eat < 200:
                risk_score += 0.5
            
            # 规则5: 萌芽期 + 低温 = 中风险
            if 0.4 <= host_phenology <= 0.6 and avg_temp <= 20:
                risk_score += 0.3
            
            # 规则6: 温度偏高 + 休眠期 = 中风险
            if avg_temp >= 28 and host_phenology <= 0.3:
                risk_score += 0.2
            
            # 规则7: 休眠期 + 温度适宜 = 低风险
            if host_phenology <= 0.3 and 18 <= avg_temp <= 30:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则8: 休眠期 + 低温 = 低风险
            if host_phenology <= 0.3 and avg_temp <= 15:
                risk_score = max(0, risk_score - 0.2)
        
        elif disease == "潜叶蛾":
            # 规则1: 生长期 + 温度适宜 + 湿度湿润 = 高风险
            if host_phenology >= 0.6 and 18 <= avg_temp <= 30 and avg_rh >= 60:
                risk_score += 0.8
            
            # 规则2: 生长期 + 高积温 = 高风险
            if host_phenology >= 0.6 and eat >= 200:
                risk_score += 0.7
            
            # 规则3: 萌芽期 + 温度适宜 + 中积温 = 高风险
            if 0.4 <= host_phenology <= 0.6 and 18 <= avg_temp <= 30 and 100 <= eat < 200:
                risk_score += 0.6
            
            # 规则4: 萌芽期 + 温度适宜 + 干燥 = 中风险
            if 0.4 <= host_phenology <= 0.6 and 18 <= avg_temp <= 30 and avg_rh <= 50:
                risk_score += 0.4
            
            # 规则5: 生长期 + 低温 + 湿度湿润 = 中风险
            if host_phenology >= 0.6 and avg_temp <= 20 and avg_rh >= 60:
                risk_score += 0.3
            
            # 规则6: 休眠期 = 低风险
            if host_phenology <= 0.3:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则7: 低温 + 休眠期 = 低风险
            if avg_temp <= 15 and host_phenology <= 0.3:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则8: 生长期 + 低温 + 干燥 = 低风险
            if host_phenology >= 0.6 and avg_temp <= 20 and avg_rh <= 50:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "锈壁虱":
            # 规则1: 温度偏高 + 干燥 + 无雨 = 高风险
            if avg_temp >= 28 and avg_rh <= 50 and rainfall <= 2:
                risk_score += 0.8
            
            # 规则2: 温度偏高 + 干燥 + 中积温 = 高风险
            if avg_temp >= 28 and avg_rh <= 50 and 100 <= eat < 200:
                risk_score += 0.7
            
            # 规则3: 高积温 + 干燥 = 高风险
            if eat >= 200 and avg_rh <= 50:
                risk_score += 0.6
            
            # 规则4: 温度适宜 + 干燥 + 生长期 = 中风险
            if 18 <= avg_temp <= 30 and avg_rh <= 50 and host_phenology >= 0.6:
                risk_score += 0.4
            
            # 规则5: 温度偏高 + 低积温 = 中风险
            if avg_temp >= 28 and eat <= 100:
                risk_score += 0.3
            
            # 规则6: 低温 = 低风险
            if avg_temp <= 15:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则7: 湿度饱和 + 大雨 = 低风险
            if avg_rh >= 90 and rainfall >= 20:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则8: 休眠期 = 低风险
            if host_phenology <= 0.3:
                risk_score = max(0, risk_score - 0.1)
        
        elif disease == "红蜘蛛":
            # 规则1: 温度适宜 + 湿度饱和 = 高风险
            if 18 <= avg_temp <= 30 and avg_rh >= 90:
                risk_score += 0.8
            
            # 规则2: 温度适宜 + 中积温 = 高风险
            if 18 <= avg_temp <= 30 and 100 <= eat < 200:
                risk_score += 0.7
            
            # 规则3: 温度适宜 + 高积温 = 高风险
            if 18 <= avg_temp <= 30 and eat >= 200:
                risk_score += 0.6
            
            # 规则4: 低温 + 湿度湿润 = 中风险
            if avg_temp <= 20 and avg_rh >= 60:
                risk_score += 0.4
            
            # 规则5: 温度适宜 + 低积温 = 中风险
            if 18 <= avg_temp <= 30 and eat <= 100:
                risk_score += 0.3
            
            # 规则6: 温度适宜 + 萌芽期 = 中风险
            if 18 <= avg_temp <= 30 and 0.4 <= host_phenology <= 0.6:
                risk_score += 0.2
            
            # 规则7: 温度偏高 = 低风险
            if avg_temp >= 32:
                risk_score = max(0, risk_score - 0.3)
            
            # 规则8: 低温 + 低积温 = 低风险
            if avg_temp <= 15 and eat <= 100:
                risk_score = max(0, risk_score - 0.2)
            
            # 规则9: 温度偏高 + 高积温 = 低风险
            if avg_temp >= 32 and eat >= 200:
                risk_score = max(0, risk_score - 0.1)
        
        # 应用寄主感病性
        risk_score = min(1.0, risk_score * host_susceptibility)
        
        # 添加随机噪声，模拟真实环境的不确定性
        noise = np.random.normal(0, 0.02)
        risk_score = np.clip(risk_score + noise, 0, 1)
        
        return risk_score * 100  # 转换为百分比
    
    def predict(self, data):
        """预测所有疾病风险"""
        risk_results = {}
        
        for disease in OUTPUT_DISEASES:
            risk = self.predict_disease_risk(disease, data)
            risk_results[disease] = risk
        
        return risk_results
    
    def predict_multi_days(self, weather_forecast):
        """多天预测"""
        predictions = []
        # Create a new temporary predictor instance for multi-day forecasting
        temp_predictor = CitrusDiseasePredictor()
        
        # 复制当前状态
        temp_predictor.history = self.history.copy()
        temp_predictor.accumulated = self.accumulated.copy()
        
        for day_data in weather_forecast:
            full_data = {
                **day_data,
                'host_susceptibility': day_data.get('host_susceptibility', 0.7),
                'host_phenology': day_data.get('host_phenology', 0.7)
            }
            
            temp_predictor.add_daily_data(full_data)
            risk_predictions = temp_predictor.predict(full_data)
            predictions.append(risk_predictions)
        
        return predictions
    
    def generate_report(self, risk_results):
        """生成风险评估报告"""
        report = "柑橘病虫害风险评估报告\n"
        report += "=" * 50 + "\n"
        
        # 按风险等级分类
        high_risk = [(d, r) for d, r in risk_results.items() if r >= 70]
        med_risk = [(d, r) for d, r in risk_results.items() if 40 <= r < 70]
        low_risk = [(d, r) for d, r in risk_results.items() if r < 40]
        
        # 高风险疾病
        if high_risk:
            report += "🔴 高风险疾病 (≥70%):\n"
            for disease, risk in sorted(high_risk, key=lambda x: x[1], reverse=True):
                report += f"  - {disease}: {risk:.1f}%\n"
        
        # 中风险疾病
        if med_risk:
            report += "\n🟡 中风险疾病 (40-70%):\n"
            for disease, risk in sorted(med_risk, key=lambda x: x[1], reverse=True):
                report += f"  - {disease}: {risk:.1f}%\n"
        
        # 低风险疾病
        if low_risk:
            report += "\n🟢 低风险疾病 (<40%):\n"
            for disease, risk in sorted(low_risk, key=lambda x: x[1], reverse=True):
                report += f"  - {disease}: {risk:.1f}%\n"
        
        # 关键环境因素分析
        report += "\n📊 关键环境因素:\n"
        report += f"  - 有效积温(EAT): {self.accumulated['eat']:.1f}℃·日\n"
        report += f"  - 连续高湿天数(CHD): {self.accumulated['chd']}天\n"
        report += f"  - 近期累计降雨(RCR): {self.accumulated['rcr']:.1f}mm\n"
        
        return report
    



# --- 配置加载 ---
# 从 .env 文件加载环境变量
load_dotenv()

# API密钥 / 模型配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
KIMI_API_KEY = os.getenv("KIMI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")  # deepseek | kimi

# 文件路径（使用相对路径）
# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
STRUCTURED_DATA_PATH = os.path.join(SCRIPT_DIR, "结构化数据.json")

# --- RAG 管理器 ---
class RAGManager:
    """使用 LangChain 内置检索器的 RAG 管理器"""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.documents = []
        self.retriever = None
        self._load_and_build()

    def _flatten_record_to_text(self, record: dict) -> str:
        """将嵌套的JSON记录拍平成可检索文本"""
        parts = []
        # 优先处理关键字段
        for key in ["名称","分类","别名"]:
            if key in record:
                value = record[key]
                if isinstance(value, list):
                    parts.append(f"{key}: " + ", ".join(map(str, value)))
                else:
                    parts.append(f"{key}: {value}")
        
        def walk(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ["名称", "分类", "别名"]:
                        continue
                    walk(v, prefix=f"{prefix}{k} -> ")
            elif isinstance(obj, list):
                for item in obj:
                    walk(item, prefix=prefix)
            else:
                parts.append(f"{prefix}{obj}")

        walk({k: v for k, v in record.items() if k not in ["名称", "分类", "别名"]})
        return "\n".join(parts)

    def _load_and_build(self):
        """加载数据文件并构建检索器"""
        try:
            from langchain_core.documents import Document
            
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_docs = data if isinstance(data, list) else [data]
            for rec in raw_docs:
                if isinstance(rec, dict):
                    text = self._flatten_record_to_text(rec)
                    # 使用 LangChain Document 格式
                    doc = Document(
                        page_content=text,
                        metadata={
                            "disease_name": rec.get("名称", "未命名条目"),
                            "category": rec.get("分类", ""),
                            "aliases": rec.get("别名", []),
                            "source": "structured_data"
                        }
                    )
                    self.documents.append(doc)
            
            if not self.documents:
                print("[RAG] 警告：未从结构化数据文件中解析到有效记录。")
                return

            print(f"[RAG] 已加载 {len(self.documents)} 条结构化记录用于检索。")
            
            # 构建 BM25 检索器，设置更好的参数
            try:
                self.retriever = BM25Retriever.from_documents(
                    self.documents,
                    k=10  # 增加检索数量，后续再筛选
                )
                print(f"[RAG] BM25 检索器已构建，文档数={len(self.documents)}")
            except Exception as e:
                print(f"[RAG] 构建 BM25 检索器失败: {e}")
                self.retriever = None

        except FileNotFoundError:
            print(f"[RAG] 错误：未找到结构化数据文件: {self.filepath}")
        except json.JSONDecodeError as e:
            print(f"[RAG] 错误：结构化数据JSON解析失败: {e}")
        except Exception as e:
            print(f"[RAG] 错误：加载或构建RAG时出错: {e}")

    def search(self, query: str, k: int = 3) -> list:
        """执行检索并返回结构化结果"""
        if not self.documents:
            return []
        
        # 术语归一化
        query = self.normalize_terms(query)
        
        # 如果检索器可用，先尝试 BM25 检索
        if self.retriever:
            try:
                docs = self.retriever.invoke(query)
            except Exception as e:
                print(f"[RAG] BM25 检索失败，回退到关键词检索: {e}")
                docs = self.documents
        else:
            docs = self.documents
        
        # 计算相关性评分
        results = []
        for doc in docs:
            # 计算改进的关键词匹配评分
            content = doc.page_content.lower()
            query_lower = query.lower()
            
            # 基础评分
            score = 0.0
            
            # 名称完全匹配
            disease_name = doc.metadata.get("disease_name", "").lower()
            if query_lower in disease_name:
                score += 20.0
            
            # 别名匹配
            aliases = doc.metadata.get("aliases", [])
            for alias in aliases:
                if query_lower in alias.lower():
                    score += 15.0
            
            # 分类匹配
            category = doc.metadata.get("category", "").lower()
            if query_lower in category:
                score += 10.0
            
            # 内容完全匹配
            if query_lower in content:
                score += 8.0
            
            # 分词匹配（提高权重）
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 1:  # 忽略单字符
                    if word in content:
                        score += 3.0
                    if word in disease_name:
                        score += 5.0
            
            # 症状关键词特殊匹配
            symptom_keywords = ["黄化", "斑点", "病斑", "卷曲", "变形", "流胶", "枯萎", "白粉", "煤烟", "变小", "变硬", "褪绿", "红鼻子果"]
            for keyword in symptom_keywords:
                if keyword in query_lower and keyword in content:
                    score += 6.0
            
            # 疾病关键词特殊匹配
            disease_keywords = ["炭疽", "溃疡", "疮痂", "黄龙病", "蓟马", "红蜘蛛", "潜叶蛾", "锈壁虱", "脂点黄斑"]
            for keyword in disease_keywords:
                if keyword in query_lower and keyword in content:
                    score += 8.0
            
            results.append({
                "disease_name": doc.metadata.get("disease_name", "未命名条目"),
                "document": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "rag_score": score,
                "meta": doc.metadata
            })
        
        # 按评分排序并返回前k个
        results.sort(key=lambda x: x["rag_score"], reverse=True)
        return results[:k]

    def normalize_terms(self, text: str) -> str:
        """将常见同义/俗称统一为标准术语以增强检索召回。"""
        if not text:
            return text
        mapping = {
            # 形态
            "油渍样": "油渍状", "水渍样": "油渍状", "油浸样": "油渍状",
            "火山口": "火山口状", "中心凹陷": "火山口状",
            "煤污": "煤烟", "黑霉": "煤烟",
            "卷叶": "叶片卷曲",
            # 媒介/虫害
            "红蜘蛛": "螨", "螨虫": "螨",
            # 病名常见简写
            "溃疡": "溃疡病", "疮痂": "疮痂病",
            # 症状描述
            "叶子": "叶片", "叶子黄": "叶片黄化",
            "果实小": "果实变小", "果实硬": "果实变硬",
            "叶子黄化": "叶片黄化", "叶子卷曲": "叶片卷曲",
            "叶子斑点": "叶片斑点", "叶子病斑": "叶片病斑",
            # 疾病别名
            "黄梢病": "黄龙病", "立枯病": "黄龙病", "退死病": "黄龙病",
            "梢枯病": "黄龙病", "叶斑病": "黄龙病", "青果病": "黄龙病",
        }
        t = text
        for k, v in mapping.items():
            t = t.replace(k, v)
        return t

# --- 初始化 ---
# 预先实例化 RAG 管理器和 LLM，避免在多线程环境中延迟加载引发问题

try:
    rag_manager = RAGManager(STRUCTURED_DATA_PATH)
    print("✅ RAG 管理器初始化成功")

except Exception as e:
    print(f"❌ RAG 管理器初始化失败: {e}")
    import traceback
    print(f"🔍 RAG 错误详情:\n{traceback.format_exc()}")


try:
    if LLM_PROVIDER == "kimi":
        if not KIMI_API_KEY:
            raise RuntimeError("缺少 KIMI_API_KEY 环境变量")
        # Kimi/ Moonshot OpenAI 兼容接口
        llm = ChatOpenAI(
            model=os.getenv("KIMI_MODEL", "moonshot-v1-8k-vision-preview"),
            api_key=KIMI_API_KEY,
            base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            temperature=0.7,
        )
        print("ℹ️ 使用 Kimi 作为 LLM 基座")
    else:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量")
        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=DEEPSEEK_API_KEY,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            temperature=0.7,
        )
        print("ℹ️ 使用 DeepSeek 作为 LLM 基座")

except Exception as e:
    print(f"❌ LLM 初始化失败: {e}")
    import traceback
    print(f"🔍 LLM 错误详情:\n{traceback.format_exc()}")

def get_rag_manager():
    """获取已初始化的 RAG 管理器实例。"""
    return rag_manager

def get_llm():
    """获取已初始化的 LLM 实例。"""
    return llm
# --- 多模态辅助 ---
def _url_to_local_path(url: str) -> str | None:
    """将 /uploads/xxx 形式的 URL 解析为本地文件绝对路径"""
    try:
        parsed = urlparse(url)
        path_part = parsed.path or ""
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "uploads")
        if path_part.startswith("/uploads/"):
            rel = path_part[len("/uploads/"):]
            local_path = os.path.join(uploads_dir, rel)
            if os.path.exists(local_path):
                return local_path
        # data URL / base64 直接返回原始 URL，让 vision_engine 处理
        if url.startswith("data:"):
            return url
    except Exception:
        pass
    return None


def _vision_engine_summary(image_urls: list[str]) -> str | None:
    """尝试用本地 CitrusHVT 视觉模型分析图片，返回结构化摘要文本。
    若模型不可用或全部失败则返回 None。
    """
    try:
        from app.services.vision_engine import vision_engine
        parts: list[str] = []
        for url in image_urls:
            try:
                local = _url_to_local_path(url)
                if local and not local.startswith("data:"):
                    result = vision_engine.predict_from_path(local)
                elif url.startswith("data:"):
                    result = vision_engine.predict_from_url(url)
                else:
                    continue
                if result:
                    top = result.get("top_k", [])
                    ood = result.get("is_ood", False)
                    if ood:
                        parts.append("图片超出模型识别范围（非柑橘病害图片）")
                    elif top:
                        best = top[0]
                        zh  = best.get("class_zh") or best.get("zh_name") or best.get("name", "未知")
                        prob = best.get("probability", 0)
                        coarse = best.get("coarse_class") or best.get("coarse", "")
                        parts.append(f"本地视觉模型识别：{zh}（{coarse}），置信度 {prob:.1%}")
            except Exception:
                continue
        return "\n".join(parts) if parts else None
    except ImportError:
        return None


async def summarize_images(image_urls: list[str], instruction: str | None = None) -> str:
    """对上传的图片进行简述提取关键信息。
    优先用本地视觉模型；若不可用且 LLM_PROVIDER 支持 vision 则用多模态；
    否则回退为纯文本提示（不发送 image_url，避免不支持视觉的模型报 400）。
    """
    if not image_urls:
        return ""

    # 优先：本地 vision_engine
    local_summary = _vision_engine_summary(image_urls)
    if local_summary:
        return local_summary

    prompt = instruction or (
        "请查看这些柑橘图片，总结可见的病症/虫害线索：\n"
        "- 关注病斑形态、颜色、分布部位（叶片/果实/枝干）\n"
        "- 是否有煤污/霉层/流胶/虫害痕迹\n"
        "- 给出2-4条要点，简短即可"
    )

    # 支持 vision 的 provider（如 kimi）才发 image_url
    if LLM_PROVIDER == "kimi":
        def to_data_url(url: str) -> str:
            try:
                local = _url_to_local_path(url)
                if local and not local.startswith("data:"):
                    with open(local, "rb") as f:
                        data = f.read()
                    mime, _ = mimetypes.guess_type(local)
                    mime = mime or "image/jpeg"
                    return f"data:{mime};base64,{base64.b64encode(data).decode()}"
            except Exception:
                pass
            return url

        try:
            safe_urls = [to_data_url(u) for u in image_urls]
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": u}} for u in safe_urls
            ]
            msg = HumanMessage(content=content)
            resp = await get_llm().ainvoke([msg])
            return getattr(resp, "content", "") or str(resp)
        except Exception:
            pass

    # 回退：纯文本，不发 image_url（DeepSeek 等不支持视觉的模型）
    text_prompt = (
        f"{prompt}\n\n"
        f"（用户上传了 {len(image_urls)} 张图片，请根据以上诊断提示和对话上下文进行分析）"
    )
    resp = await get_llm().ainvoke(text_prompt)
    return getattr(resp, "content", "") or str(resp)


# ─────────────────────────────────────────────────────────────────────────────
# 并行双路视觉分析
# ─────────────────────────────────────────────────────────────────────────────

def _vision_engine_raw(image_urls: list[str]) -> dict | None:
    """同步：用本地 CitrusHVT 推理第一张有效图片，返回原始结果字典。"""
    try:
        from app.services.vision_engine import vision_engine
        if not vision_engine.is_available:
            return None
        for url in image_urls:
            local = _url_to_local_path(url)
            try:
                if local and not local.startswith("data:"):
                    result = vision_engine.predict_from_path(local)
                else:
                    result = vision_engine.predict_from_url(url)
                if result and result.get("available"):
                    return result
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"[VisionRaw] CNN 推理失败: {e}")
        return None


# 与 LangGraph calculate_confidence_node 快通路阈值对齐（论文 5.4.4.6）
_FAST_PATH_VISION_THRESHOLD = 0.85
_FAST_PATH_ENV_CONFLICT_MAX = 20.0


def _cnn_hint_lines(cnn: dict | None) -> str:
    """供多模态/文本解释用的 CNN 摘要文本。"""
    if not cnn or not cnn.get("available"):
        return "（本地模型无有效输出）"
    lines = []
    for item in (cnn.get("top_k") or [])[:3]:
        lines.append(
            f"  Top{item.get('rank', '?')}: {item.get('class_zh', '?')} "
            f"({item.get('probability', 0):.1%}) — {item.get('coarse_class', '')}"
        )
    ood = cnn.get("is_ood", False)
    if ood:
        lines.append("  （OOD：分布外样本，标签仅供参考）")
    return "\n".join(lines) if lines else "（无 Top-K）"


async def _llm_vision_describe(
    image_urls: list[str],
    cnn_hint: dict | None = None,
) -> str | None:
    """
    多模态 LLM（Kimi 等）：在**已得到 CNN 标签之后**看图描述，实现「标签引导的视觉解释」
    （符合论文 late fusion：感知层特征 + 决策层语义解释）。
    """
    if LLM_PROVIDER != "kimi":
        return None
    base = (
        "你是柑橘植保专家。请结合下方图片，用中文简洁描述可见情况。\n"
        "1. 病斑/症状的颜色、形态、分布部位（叶/果/枝等）\n"
        "2. 是否有虫害痕迹、霉层、流胶等\n"
        "3. 与本地模型结论是否一致；若不一致，说明可能原因（拍摄角度、非柑橘、复合症状等）\n"
        "用 3-6 句话，不要编造图中没有的细节。"
    )
    if cnn_hint and cnn_hint.get("available"):
        base += (
            "\n\n【本地 CitrusHVT 模型输出（请先参考再对照实图）】\n"
            f"{_cnn_hint_lines(cnn_hint)}"
        )
    prompt_text = base
    try:
        def to_data_url(url: str) -> str:
            try:
                local = _url_to_local_path(url)
                if local and not local.startswith("data:"):
                    with open(local, "rb") as f:
                        raw = f.read()
                    mime, _ = mimetypes.guess_type(local)
                    return f"data:{mime or 'image/jpeg'};base64,{base64.b64encode(raw).decode()}"
            except Exception:
                pass
            return url

        safe_urls = [to_data_url(u) for u in image_urls]
        content = [{"type": "text", "text": prompt_text}] + [
            {"type": "image_url", "image_url": {"url": u}} for u in safe_urls
        ]
        resp = await get_llm().ainvoke([HumanMessage(content=content)])
        return getattr(resp, "content", "") or str(resp)
    except Exception as e:
        print(f"[VisionLLM] 多模态描述失败: {e}")
        return None


async def _llm_text_explain_from_cnn(cnn: dict) -> str | None:
    """
    文本 LLM（如 DeepSeek）：无法看图时，根据 CNN 标签做「面向农户的症状学解释」，
    明确说明未直接读图，避免与多模态路径混淆。
    """
    if not cnn or not cnn.get("available"):
        return None
    hint = _cnn_hint_lines(cnn)
    prompt = (
        "本地柑橘病害识别模型输出如下（你当前**无法查看用户图片**，仅根据标签做科普解释）：\n"
        f"{hint}\n\n"
        "请用 4-7 句中文写给农户：（1）按模型最可能的一类，描述田间常见症状与受害部位；"
        "（2）提醒最终以田间观察与农技人员判断为准；（3）不要编造模型未给出的病虫类别名称。"
        "开头请用一句说明：「以下为结合识别结果的症状学说明，非直接读图」。"
    )
    try:
        resp = await get_llm().ainvoke(prompt)
        return getattr(resp, "content", "") or str(resp)
    except Exception as e:
        print(f"[VisionTextLLM] 文本解释失败: {e}")
        return None


async def _sequential_vision_analyze(image_urls: list[str]) -> dict:
    """
    串行视觉链（符合「先感知标签、再语义解释」）：
      1) 本地 CNN（CitrusHVT）→ top-k / OOD / fuzzy_disease_key
      2) Kimi：图片 + CNN 标签 → 对照实图的描述；
         DeepSeek 等：仅根据 CNN 做文本层症状解释（不声称已读图）。
    """
    loop = asyncio.get_event_loop()
    cnn_result = await loop.run_in_executor(None, _vision_engine_raw, image_urls)
    if isinstance(cnn_result, Exception):
        print(f"[Vision] CNN 出错: {cnn_result}")
        cnn_result = None

    llm_desc: str | None = None
    if LLM_PROVIDER == "kimi":
        llm_desc = await _llm_vision_describe(image_urls, cnn_hint=cnn_result)
    else:
        llm_desc = await _llm_text_explain_from_cnn(cnn_result or {})

    return {"cnn": cnn_result, "llm_desc": llm_desc}


async def _load_environmental_risk(session_id: str) -> dict:
    """
    与 LangGraph parallel_context 一致：果园坐标天气 + CitrusFuzzyEngine →
    {病名: {risk_score, risk_level}}，供快通路环境一致性核验。
    """
    oid = get_orchard_id(session_id)
    if not oid:
        return {}
    db = SessionLocal()
    try:
        o = orchard_crud.get_orchard(db, orchard_id=oid)
        if not o:
            return {}
        phenology = 0.7
        if getattr(o, "current_phenology", None):
            _ph_map = {
                "休眠期": 0.2,
                "萌芽期": 0.5,
                "生长期": 0.8,
                "花期": 0.7,
                "结果期": 0.6,
            }
            phenology = float(_ph_map.get(o.current_phenology, 0.7))
        temp, hum, rain = 25.0, 65.0, 0.0
        if o.location_latitude is not None and o.location_longitude is not None:
            try:
                from app.services.weather_service import weather_service

                w = await weather_service.get_weather_by_coordinates(
                    float(o.location_latitude),
                    float(o.location_longitude),
                )
                if w:
                    cur = w.get("current") or {}
                    temp = float(cur.get("temperature", 25) or 25)
                    hum = float(cur.get("humidity", 65) or 65)
                    fc = w.get("forecast") or []
                    if fc:
                        rain = float(fc[0].get("precipitation_total", 0) or 0)
            except Exception as e:
                print(f"[EnvRisk] 天气获取失败: {e}")

        from app.services.fuzzy_engine import CitrusFuzzyEngine

        raw = CitrusFuzzyEngine().predict(
            {
                "temp": temp,
                "humidity": hum,
                "rainfall": rain,
                "phenology": phenology,
            }
        )
        return {
            disease: {
                "risk_score": float(info.get("risk_score", 0.0)),
                "risk_level": str(info.get("risk_level", "")),
            }
            for disease, info in raw.items()
        }
    except Exception as e:
        print(f"[EnvRisk] 模糊推理失败: {e}")
        return {}
    finally:
        try:
            db.close()
        except Exception:
            pass


def _evaluate_fast_path_gate(cnn: dict | None, env_risk: dict) -> tuple[bool, list[str]]:
    """
    论文快通路：高置信视觉 + 与模糊环境风险无显著冲突（对齐 graph calculate_confidence_node）。
    返回 (是否允许快通路, 人类可读说明行)。
    """
    notes: list[str] = []
    if not cnn or not cnn.get("available"):
        notes.append("  · 无有效 CNN 输出 → 不走快通路")
        return False, notes
    if cnn.get("is_ood", False):
        notes.append("  · OOD 样本 → 不走快通路")
        return False, notes
    top1_prob = float(cnn.get("top1_prob", 0.0))
    if top1_prob < _FAST_PATH_VISION_THRESHOLD:
        notes.append(
            f"  · 视觉 Top-1 置信度 {top1_prob:.1%} < {_FAST_PATH_VISION_THRESHOLD:.0%} → 不走快通路"
        )
        return False, notes

    fuzzy_key = cnn.get("fuzzy_disease_key") or ""
    if fuzzy_key and env_risk:
        info = env_risk.get(fuzzy_key)
        if not isinstance(info, dict):
            info = {}
        env_score = float(info.get("risk_score", 50.0))
        if fuzzy_key not in env_risk:
            notes.append(
                f"  · 环境表中未单独列出「{fuzzy_key}」，按默认风险分 {env_score:.0f}/100 参与门控"
            )
        if env_score < _FAST_PATH_ENV_CONFLICT_MAX:
            notes.append(
                f"  · 环境核验：**冲突** — 模糊推理中「{fuzzy_key}」风险仅 {env_score:.0f}/100 "
                f"(<{_FAST_PATH_ENV_CONFLICT_MAX:.0f})，与高置信视觉不一致 → **禁止快通路**，走慢通路"
            )
            return False, notes
        notes.append(
            f"  · 环境核验：「{fuzzy_key}」风险 {env_score:.0f}/100，未出现极低风险冲突 → 快通路可用"
        )
    elif fuzzy_key and not env_risk:
        notes.append(
            "  · 环境核验：**未完成**（无果园绑定或模糊推理结果为空）→ 不满足论文「视觉-环境一致」"
            "门控，**禁止快通路**，请走慢通路并调用 `fuzzy_risk_check` 或 `fetch_orchard_context`"
        )
        return False, notes
    else:
        notes.append("  · 无 fuzzy_disease_key（如健康类）→ 跳过病害-环境冲突项，仅凭视觉门控")

    notes.append(
        f"  · ✅ 快通路条件满足：视觉 Top-1 {cnn.get('top1_class_zh', '?')} @ {top1_prob:.1%}"
    )
    return True, notes


def _format_env_risk_brief(env_risk: dict, highlight_key: str | None, max_items: int = 6) -> str:
    if not env_risk:
        return ""
    lines = ["【环境模糊推理（当前果园气象+物候）】"]
    items = sorted(
        env_risk.items(),
        key=lambda x: x[1].get("risk_score", 0),
        reverse=True,
    )[:max_items]
    for name, info in items:
        mark = " ← 与 CNN 对齐" if highlight_key and name == highlight_key else ""
        lines.append(
            f"  · {name}: {info.get('risk_level', '')}（{float(info.get('risk_score', 0)):.0f}/100）{mark}"
        )
    return "\n".join(lines)


def _format_vision_slot(slot: dict) -> str:
    """将 vision_slot 格式化为注入 Agent 的文本摘要（含环境门控后的快慢通路提示）。"""
    parts: list[str] = []
    cnn = slot.get("cnn")
    llm_desc = slot.get("llm_desc")
    gate = slot.get("fast_path_gate") or {}
    env_brief = slot.get("env_risk_brief") or ""

    if cnn and cnn.get("available"):
        top_k = cnn.get("top_k", [])
        is_ood = cnn.get("is_ood", False)
        top1_prob = cnn.get("top1_prob", 0.0)
        top1_zh = cnn.get("top1_class_zh", "未知")

        parts.append("【视觉识别（本地CNN · CitrusHVT）】")
        if is_ood:
            parts.append("  ⚠️ 图片超出训练分布（OOD），识别可靠性低，请结合症状文字判断")
        else:
            for item in top_k[:3]:
                parts.append(
                    f"  Top{item['rank']}: {item['class_zh']} "
                    f"({item['probability']:.1%}) — {item['coarse_class']}"
                )
            # 快慢通路由环境门控结果决定（与论文 5.4 一致），不再仅看置信度
            if gate.get("allowed"):
                parts.append(
                    f"  ✅ **快通路已许可**：视觉 Top-1「{top1_zh}」（{top1_prob:.1%}）"
                    "且通过环境一致性核验，可按快通路出具确诊型答复（仍需检索防治知识）。"
                )
            else:
                if top1_prob >= _FAST_PATH_VISION_THRESHOLD and not is_ood:
                    parts.append(
                        f"  ⚠️ 视觉置信度较高（{top1_prob:.1%}），但**未满足快通路**（见下方门控说明）→ 走**慢通路**"
                    )
                elif top1_prob >= 0.55:
                    parts.append(
                        f"  ⚠️ 置信度中等（{top1_prob:.1%}），建议结合症状与环境走慢通路"
                    )
                else:
                    parts.append(f"  ❓ 置信度较低（{top1_prob:.1%}）→ 走慢通路")

        if gate.get("notes"):
            parts.append("\n【快通路门控（视觉 + 环境模糊推理）】")
            parts.extend(gate["notes"])

    if env_brief:
        parts.append("\n" + env_brief)

    if llm_desc:
        prov = "多模态LLM（已读图）" if LLM_PROVIDER == "kimi" else "文本LLM（结合CNN标签的症状学说明，非直接读图）"
        parts.append(f"\n【视觉解释（{prov}）】\n{llm_desc}")

    return "\n".join(parts)


# --- 工具定义 ---
@tool
def rag_search(query: str) -> str:
    """
    当需要回答关于技术、定义或特定知识库内部的问题时，使用此工具。
    返回格式化的字符串，包含名称、分数和文档片段。
    """
    print(f"--- 正在进行 RAG 检索: {query} ---")
    if not query: 
        return "请输入有效的检索问题。"
    
    try:
        results = get_rag_manager().search(query)
        if not results: 
            return f"未在知识库中检索到与'{query}'相关的信息。"

        lines = []
        for i, item in enumerate(results, 1):
            title = item["disease_name"]
            lines.append(f"[{i}] {title}\n{item['document']}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ 检索过程中发生错误: {e}"

@tool
def knowledge_base_retrieval(context: str, top_k: int = 3) -> list:
    """
    基于输入上下文，在知识库中检索并返回结构化的Top-K候选列表。
    输出: [{"disease_name", "document", "rag_score"}]
    """
    print("[诊断] 步骤2/5: 知识库检索 Top-3 候选…")
    if not context: 
        return []
    
    try:
        results = get_rag_manager().search(context, k=top_k)
        print(f"[诊断] 检索完成，命中 {len(results)} 条候选。")
        return results
    except Exception as e:
        print(f"[诊断] 检索失败: {e}")
        return []



@tool
def get_weather(city: str, future_days: int = 0, past_days: int = 0) -> str:
    "当用户询问某个城市的天气时，使用此工具查询基于今天的相对时间范围：future_days（未来天数，0-5），past_days（过去天数，暂不支持）。未提供则默认当天。查询之前需要先将地名转化为英文如'Chongqing'。" 
    print(f"--- 正在查询天气: {city} ---")
    if not OPENWEATHER_API_KEY: return "❌ 未配置OpenWeather API密钥。"
    
    def fmt_current(data):
        weather_info = data['weather'][0] if data.get('weather') else {}
        main_info = data.get('main', {})
        wind_info = data.get('wind', {})
        return (
            f"🌤️ {city} 当前天气：\n"
            f"• 天气状况：{weather_info.get('description', '未知')}\n"
            f"• 温度：{main_info.get('temp', 'N/A')}°C (体感: {main_info.get('feels_like', 'N/A')}°C)\n"
            f"• 湿度：{main_info.get('humidity', 'N/A')}% | 气压：{main_info.get('pressure', 'N/A')} hPa\n"
            f"• 风速：{wind_info.get('speed', 0)} m/s | 能见度：{data.get('visibility', 'N/A')} 米"
        )
    
    def aggregate_day(items):
        if not items: return None
        temps = [it.get('main', {}).get('temp') for it in items if it.get('main')]
        hums = [it.get('main', {}).get('humidity') for it in items if it.get('main')]
        winds = [it.get('wind', {}).get('speed') for it in items if it.get('wind')]
        descs = [it.get('weather', [{}])[0].get('description', '') for it in items if it.get('weather')]
        def avg(vals):
            vals = [v for v in vals if isinstance(v, (int, float))]
            return round(sum(vals)/len(vals), 1) if vals else None
        return {
            'temp_avg': avg(temps),
            'humidity_avg': avg(hums),
            'wind_avg': avg(winds),
            'desc_top': max(set(descs), key=descs.count) if descs else '未知'
        }
    
    try:
        today = datetime.now().date()
        # 仅当天（默认）
        if (future_days is None or future_days <= 0) and (past_days is None or past_days <= 0):
            params = {'q': city, 'appid': OPENWEATHER_API_KEY, 'units': 'metric', 'lang': 'zh_cn'}
            resp = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params, timeout=10)
            data = resp.json()
            if resp.status_code == 200:
                return fmt_current(data)
            return f"❌ 查询失败({resp.status_code}): {data.get('message', '未知错误')}"
        
        # 过去天数（历史）目前不支持（OpenWeather需付费 One Call Timemachine）
        if past_days and past_days > 0:
            return "❌ 暂不支持查询历史天气（past_days）。请仅提供 future_days（0-5）。"
        
        # 未来天数（最多支持5天，使用5日/3小时预报聚合）
        fd = max(0, int(future_days or 0))
        if fd > 5:
            return "❌ 仅支持查询未来5天以内。"
        
        params = {'q': city, 'appid': OPENWEATHER_API_KEY, 'units': 'metric', 'lang': 'zh_cn'}
        resp = requests.get("http://api.openweathermap.org/data/2.5/forecast", params=params, timeout=10)
        data = resp.json()
        if resp.status_code != 200:
            return f"❌ 预报查询失败({resp.status_code}): {data.get('message', '未知错误')}"
        lst = data.get('list', [])
        if not lst:
            return "❌ 未获取到预报数据。"
        
        # 范围：今天 至 今天+fd
        from_day = today
        to_day = today if fd == 0 else (today + timedelta(days=fd))
        by_day = {}
        for item in lst:
            dt_txt = item.get('dt_txt')
            if not dt_txt: continue
            d = datetime.strptime(dt_txt[:10], "%Y-%m-%d").date()
            if from_day <= d <= to_day:
                by_day.setdefault(d, []).append(item)
        if not by_day:
            return "❌ 指定范围内无可用预报数据。"
        
        lines = [f"📆 {city} 天气（{from_day} 至 {to_day}）:"]
        for d in sorted(by_day.keys()):
            agg = aggregate_day(by_day[d])
            if not agg: continue
            lines.append(
                f"- {d}: {agg['desc_top']} | 平均温度 {agg['temp_avg']}°C | 平均湿度 {agg['humidity_avg']}% | 平均风速 {agg['wind_avg']} m/s"
            )
        return "\n".join(lines)
    
    except requests.exceptions.Timeout:
        return "❌ 天气查询超时。"
    except Exception as e:
        return f"❌ 天气查询出错: {e}"


# --- 通用工具集 ---

# 使用 LangChain 官方集成替换手动实现
web_search_tool = DuckDuckGoSearchRun()

@tool
def web_search(query: str) -> str:
    """当需要获取实时信息、最新新闻或网络数据时，使用此工具。"""
    print(f"--- 正在进行网络搜索: {query} ---")
    try:
        return web_search_tool.run(query)
    except Exception as e:
        return f"❌ 网络搜索出错: {e}"


# --- 预测与维护工具集 ---

# 检查是否可以使用预测模块
FUZZY_TRAMS_AVAILABLE = True

# 预加载预测器实例以避免在多线程环境中重复初始化
_predictor_instance = None
if FUZZY_TRAMS_AVAILABLE:
    try:
        _predictor_instance = CitrusDiseasePredictor()

    except Exception as e:
        print(f"❌ 预测器实例化失败: {e}")
        print(f"🔍 错误类型: {type(e).__name__}")
        import traceback
        print(f"🔍 详细错误信息:\n{traceback.format_exc()}")
        print("⚠️ [警告] 预测功能将不可用。")
        FUZZY_TRAMS_AVAILABLE = False

@tool
def disease_risk_prediction(weather_forecast: list, soil_info: str, host_susceptibility: float = 0.7, host_phenology: float = 0.7) -> str:
    """
    (预测) 根据未来的天气预报和土壤信息，预测柑橘病虫害风险。
    weather_forecast: 未来几天的天气数据列表，每天一个字典，包含 'avg_temp', 'avg_rh', 'lwd', 'rainfall', 'wind_speed'。
    soil_info: 关于土壤条件的文本描述 (pH, 肥力, 土质等)。可以通过使用 `web_search` 查找该城市的**土壤条件** (如酸碱度pH, 肥力, 土质)。
    host_susceptibility: 寄主感病性 (0.0-1.0)。
    host_phenology: 寄主物候期 (0.0-1.0, e.g., 0.7 for 生长期).
    """
    if not FUZZY_TRAMS_AVAILABLE or _predictor_instance is None:
        return "❌ 预测模块未能加载或初始化失败，无法执行预测。请检查 `predictor.py` 文件及依赖是否正确。"
    
    print("[预测] 步骤1/2: 运行基于规则的风险预测模型…")
    try:
        predictor = _predictor_instance # 使用预加载的实例
        
        forecast_with_host_data = []
        for day_data in weather_forecast:
            required_keys = ['avg_temp', 'avg_rh', 'lwd', 'rainfall', 'wind_speed']
            if not all(key in day_data for key in required_keys):
                return f"❌ 天气数据格式错误，缺少必要字段。需要: {required_keys}, 实际数据: {day_data}"
            
            day_data['host_susceptibility'] = host_susceptibility
            day_data['host_phenology'] = host_phenology
            forecast_with_host_data.append(day_data)

        predictions = predictor.predict_multi_days(forecast_with_host_data)
        
        if not predictions:
            return "未能生成预测结果，请检查天气数据格式是否正确。"

        final_risks = predictions[-1]
        report = predictor.generate_report(final_risks)
        
        print("[预测] 步骤2/2: 结合土壤信息生成综合建议…")
        synthesis_prompt = f"""
        你是一位柑橘种植专家。请根据以下病虫害风险预测报告和土壤信息，生成一份综合性的预测和管理建议。

        土壤信息:
        {soil_info}

        风险预测报告:
        {report}

        请综合分析，指出土壤条件可能如何影响(加重或减轻)预测出的高风险病虫害，并提供针对性的土壤管理和预防建议。
        """
        response = get_llm().invoke(synthesis_prompt)
        return response.content

    except Exception as e:
        import traceback
        return f"❌ 预测模型运行出错: {e}\n{traceback.format_exc()}"


@tool
def treatment_maintenance_advice(diagnosed_disease: str, treatment_used: str, treatment_feedback: str, recent_weather: str) -> str:
    """
    (维护) 根据历史诊断、治疗反馈和近期天气，提供后续维护建议。
    diagnosed_disease: 之前确诊的病虫害名称。
    treatment_used: 已采用的治理措施，如使用的药剂。
    treatment_feedback: 用户反馈的治疗效果，如 "好转", "无效", "恶化"。
    recent_weather: 近期的天气概况。
    """
    print("[维护] 正在生成维护建议…")
    try:
        prompt = f"""
        你是一名经验丰富的柑橘植保专家，正在进行一次诊后回访。

        历史诊断信息:
        - 病虫害名称: {diagnosed_disease}
        - 已用措施: {treatment_used}
        - 治疗效果: {treatment_feedback}

        近期天气概况:
        {recent_weather}

        请根据以上所有信息，提供一份详细的后续维护计划，包括：
        1.  **效果评估**: 分析当前治疗效果(好/一般/差)的可能原因。
        2.  **措施调整**: 根据效果和天气，建议是否需要更换药剂、调整用药频率或采用其他物理/生物防治方法。
        3.  **后续观察**: 指出未来几天需要重点观察哪些症状或指标。
        4.  **预防性建议**: 结合天气情况，给出预防复发或继发其他病虫害的建议。

        请以专业、清晰、可操作性强的方式提供建议。
        """
        response = get_llm().invoke(prompt)
        return response.content
    except Exception as e:
        return f"❌ 生成维护建议时出错: {e}"


# --- 诊断工具集 ---
@tool
def analyze_candidates(context: str, candidates: list) -> dict:
    """(诊断) 调用LLM对候选进行三元交叉验证打分。返回结构化JSON。"""
    print("[诊断] 步骤3/5: 三元交叉验证评分（症状/环境/病因）…")
    
    # 类型检查和错误处理
    if not isinstance(candidates, list):
        print(f"[诊断] 错误：candidates参数类型错误，期望list，实际{type(candidates)}")
        return {"items": []}
    
    if not candidates:
        return {"items": []}
    
    # 并行处理每个候选
    import concurrent.futures
    import threading
    
    def score_single_candidate(candidate):
        """为单个候选打分"""
        print(f"🔍 开始处理候选: {candidate.get('disease_name', '未知')}")
        prompt = (
            "你是一名柑橘病虫害诊断专家。基于上下文与候选信息，为该候选进行三维打分并给出理由，严格输出JSON。\n"
            "维度: sym(症状匹配,0-10), env(环境/时空匹配,0-10), causality(病因推理一致性,0-10)。每维度给≤2条证据要点。\n"
            "给出可观察的区分点discriminators（1-2条），用于与其他常见候选（如溃疡病/疮痂病/煤烟/日灼/缺素/虫害）在现场快速区分。\n\n"
            f"上下文:\n{context}\n\n"
            f"候选信息:\n{json.dumps(candidate, ensure_ascii=False)}\n\n"
            "仅输出形如: {\"disease_name\":...,\"scores\":{\"sym\":X,\"env\":Y,\"causality\":Z},\"evidence\":{\"symptom_evidence\":[\"...\",\"...\"],\"env_evidence\":[\"...\"],\"causality_evidence\":[\"...\"]},\"discriminators\":[\"...\"]}"
        )
        try:
            print(f"🔍 调用LLM为候选 {candidate.get('disease_name', '未知')} 评分...")
            resp = get_llm().invoke(prompt)
            content = getattr(resp, "content", None) or str(resp)
            data = json.loads(content)
            if isinstance(data, dict) and "disease_name" in data and "scores" in data:
                print(f"✅ 候选 {candidate.get('disease_name', '未知')} 评分成功")
                return data
        except Exception as e:
            print(f"❌ 候选 {candidate.get('disease_name', '未知')} 评分失败: {e}")
            import traceback
            print(f"🔍 评分错误详情:\n{traceback.format_exc()}")
        
        # 回退评分
        return {
            "disease_name": candidate.get("disease_name", "未知"),
            "scores": {"sym": 6.0, "env": 6.0, "causality": 6.0},
            "rationale": "回退评分：建议补充关键信息以提升判断。"
        }
    
    # 并行执行（最多3个线程，避免API限制）
    print(f"🔍 开始并行处理 {len(candidates)} 个候选，使用最多3个线程...")
    items = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(candidates))) as executor:
            print("🔍 ThreadPoolExecutor 创建成功")
            future_to_candidate = {executor.submit(score_single_candidate, c): c for c in candidates}
            print(f"🔍 已提交 {len(future_to_candidate)} 个任务到线程池")
            
            for future in concurrent.futures.as_completed(future_to_candidate):
                try:
                    print("🔍 等待任务完成...")
                    result = future.result()
                    items.append(result)
                    print(f"✅ 任务完成，当前已处理 {len(items)} 个候选")
                except Exception as e:
                    candidate = future_to_candidate[future]
                    print(f"❌ 候选 {candidate.get('disease_name', '未知')} 处理异常: {e}")
                    import traceback
                    print(f"🔍 任务异常详情:\n{traceback.format_exc()}")
                    items.append({
                        "disease_name": candidate.get("disease_name", "未知"),
                        "scores": {"sym": 6.0, "env": 6.0, "causality": 6.0},
                        "rationale": "处理异常，使用默认评分。"
                    })
    except Exception as e:
        print(f"❌ ThreadPoolExecutor 执行失败: {e}")
        import traceback
        print(f"🔍 线程池错误详情:\n{traceback.format_exc()}")
        # 回退到串行处理
        print("🔍 回退到串行处理...")
        for candidate in candidates:
            try:
                result = score_single_candidate(candidate)
                items.append(result)
            except Exception as e:
                print(f"❌ 串行处理候选失败: {e}")
                items.append({
                    "disease_name": candidate.get("disease_name", "未知"),
                    "scores": {"sym": 6.0, "env": 6.0, "causality": 6.0},
                    "rationale": "串行处理异常，使用默认评分。"
                })
    
    print(f"[诊断] 三元评分完成，处理了 {len(items)} 个候选。")
    return {"items": items}


@tool
def calculate_confidence(candidates: list, analysis: dict, w1: float = 0.35, w2: float = 0.55, w3: float = 0.10) -> dict:
    """(诊断) 融合RAG分数与三元评分，输出排序结果。"""
    # 类型检查和错误处理
    if not isinstance(candidates, list):
        print(f"[诊断] 错误：candidates参数类型错误，期望list，实际{type(candidates)}")
        return {"ranked": [], "level": "low", "decision": "clarify", "top": 0.0, "second": 0.0}
    
    if not isinstance(analysis, dict):
        print(f"[诊断] 错误：analysis参数类型错误，期望dict，实际{type(analysis)}")
        return {"ranked": [], "level": "low", "decision": "clarify", "top": 0.0, "second": 0.0}
    
    # 映射 disease_name -> rag_score
    name_to_rag = {c.get("disease_name"): float(c.get("rag_score", 0.5)) for c in candidates if isinstance(c, dict)}
    items = analysis.get("items", [])
    # 计算match平均分
    scored = []
    sym_list = [it.get("scores", {}).get("sym", 0) for it in items]
    top_sym = max(sym_list) if sym_list else 0
    second_sym = sorted(sym_list, reverse=True)[1] if len(sym_list) > 1 else 0
    dist = max(0.0, (top_sym - second_sym) / 10.0) if top_sym else 0.0
    for it in items:
        name = it.get("disease_name")
        s = it.get("scores", {})
        s_match = (float(s.get("sym", 0)) + float(s.get("env", 0)) + float(s.get("causality", 0))) / 30.0
        s_rag = min(1.0, max(0.0, name_to_rag.get(name, 0.5)))
        c = w1 * s_rag + w2 * s_match + w3 * dist
        scored.append({"disease_name": name, "confidence": float(round(c, 4))})
    ranked = sorted(scored, key=lambda x: x["confidence"], reverse=True)
    level = "low"
    decision = "clarify"
    top = 0.0
    sec = 0.0
    if ranked:
        top = ranked[0]["confidence"]
        sec = ranked[1]["confidence"] if len(ranked) > 1 else 0.0
        lead = top - sec
        # 分级规则
        if top > 0.80 and lead > 0.25:
            level = "high"
            decision = "report"
        elif top > 0.60:
            level = "medium"
            decision = "clarify"
        elif top > 0.40:
            level = "low"
            decision = "clarify"
        else:
            level = "very_low"
            decision = "unknown"
        print(f"[诊断] 步骤4/5: 置信度计算完成。Top={top:.3f}，差值={lead:.3f}，等级={level}，决策={decision}")
    else:
        print("[诊断] 步骤4/5: 无可计算对象。")
    return {"ranked": ranked, "level": level, "decision": decision, "top": top, "second": sec}

@tool
def generate_clarifying_question(analysis: dict, ranked) -> dict:
    """(诊断) 当不确定时，生成区分Top-2的关键提问。"""
    items = analysis.get("items", [])
    # 兼容两种输入格式
    if isinstance(ranked, list):
        ranked_list = ranked
        decision = "clarify"
        top_val = ranked[0].get("confidence", 0) if ranked else 0
    else:
        ranked_list = ranked.get("ranked", [])
        decision = ranked.get("decision", "clarify")
        top_val = ranked.get("top", 0)

    # 处理极低置信度的情况（系统不知道）
    if decision == "unknown" or top_val < 0.40:
        print(f"[诊断] 步骤5/5: 置信度过低 ({top_val:.2f})，请求补充信息而非强行区分。")
        return {
            "type": "clarification",
            "question": "当前的症状特征与已知病害匹配度均较低，可能是特征不明显或属于未收录病害。请问能否拍摄更清晰的病斑细节，或描述是否有其他部位（如枝干、根部）的异常？",
            "options": ["补充症状描述", "上传更多图片", "结束诊断"]
        }

    top2 = [r.get("disease_name") for r in ranked_list[:2]]
    prompt = (
        "根据以下分析，生成一个能够区分Top-2病害的关键问题（简短、可观察、明确），并提供3个选项：\n\n" 
        f"分析: {json.dumps(items, ensure_ascii=False)}\nTop-2: {json.dumps(top2, ensure_ascii=False)}\n\n" 
        "请输出JSON格式：{\"question\": \"问题内容\", \"options\": [\"选项1\", \"选项2\", \"选项3\"]}"
    )
    try:
        resp = get_llm().invoke(prompt)
        content = getattr(resp, "content", None) or str(resp)
        print("[诊断] 步骤5/5: 生成关键追问完成。")
        # 尝试解析JSON，如果失败则使用默认格式
        try:
            result = json.loads(content.strip())
            return result
        except:
            return {
                "question": content.strip(),
                "options": ["是", "否", "不确定"]
            }
    except Exception:
        print("[诊断] 步骤5/5: 关键追问回退。")
        return {
            "question": "请问是否观察到典型症状的关键差异（如病斑形态/是否流胶/是否有煤污）？",
            "options": ["是", "否", "不确定"]
        }


@tool
def create_final_report(analysis: dict, ranked) -> dict:
    """(诊断) 当高置信时，生成最终报告。"""
    # 兼容两种输入格式：直接传入ranked列表 或 包含ranked字段的字典
    if isinstance(ranked, list):
        top = ranked[:1]
    else:
        top = ranked.get("ranked", [])[:1]
    
    if not top:
        return {
            "type": "diagnosis_report",
            "content": "无法生成诊断报告，请提供更多信息。",
            "primary_diagnosis": "未知",
            "confidence": 0.0,
            "secondary_diagnoses": [],
            "prevention_advice": "请咨询专业农技人员",
            "treatment_advice": "请咨询专业农技人员"
        }
    
    primary = top[0]
    primary_name = primary.get("disease_name", "未知")
    confidence = primary.get("confidence", 0.0)
    
    prompt = (
        "你是一名柑橘病虫害诊断专家，请基于以下分析结果生成最终中文报告，使用JSON格式输出：\n" 
        "{\n"
        '  "content": "报告内容（使用\\n换行）",\n'
        '  "primary_diagnosis": "主要诊断",\n'
        '  "confidence": 0.85,\n'
        '  "secondary_diagnoses": [{"name": "次要诊断", "confidence": 0.15}],\n'
        '  "prevention_advice": "预防建议（使用\\n换行）",\n'
        '  "treatment_advice": "治疗建议（使用\\n换行）"\n'
        "}\n\n"
        f"Top: {json.dumps(top, ensure_ascii=False)}\n分析: {json.dumps(analysis.get('items', []), ensure_ascii=False)}\n\n" 
        "请确保JSON格式正确，文本内容使用\\n进行换行。"
    )
    try:
        resp = get_llm().invoke(prompt)
        content = getattr(resp, "content", None) or str(resp)
        print("[诊断] 步骤5/5: 最终报告生成完成。")
        # 尝试解析JSON，如果失败则使用默认格式
        try:
            result = json.loads(content.strip())
            result["type"] = "diagnosis_report"
            return result
        except:
            return {
                "type": "diagnosis_report",
                "content": content.strip(),
                "primary_diagnosis": primary_name,
                "confidence": confidence,
                "secondary_diagnoses": [],
                "prevention_advice": "请咨询专业农技人员",
                "treatment_advice": "请咨询专业农技人员"
            }
    except Exception:
        print("[诊断] 步骤5/5: 报告生成失败。")
        return {
            "type": "diagnosis_report",
            "content": "报告生成失败，请稍后重试。",
            "primary_diagnosis": primary_name,
            "confidence": confidence,
            "secondary_diagnoses": [],
            "prevention_advice": "请咨询专业农技人员",
            "treatment_advice": "请咨询专业农技人员"
        }




@tool
def fetch_orchard_context(orchard_id: str | None = None) -> str:
    """读取果园上下文信息（名称/品种/树龄/地理/土壤等），返回 JSON 字符串。
    - 若未提供 orchard_id，则使用当前会话绑定的默认 orchard_id。
    """
    try:
        db = SessionLocal()
        from uuid import UUID
        if not orchard_id:
            sid = get_current_session()
            if sid:
                oid = get_orchard_id(sid)
            else:
                oid = None
        else:
            oid = UUID(orchard_id) if isinstance(orchard_id, str) else orchard_id
        o = orchard_crud.get_orchard(db, orchard_id=oid)
        if not o:
            return json.dumps({"error": "not_found", "orchard_id": orchard_id}, ensure_ascii=False)
        ctx = {
            "id": str(o.id),
            "name": o.name,
            "main_variety": o.main_variety,
            "avg_tree_age": o.avg_tree_age,
            "phenology": o.current_phenology,
            "location": {
                "lat": o.location_latitude,
                "lon": o.location_longitude,
                "address": o.address_detail,
            },
            "soil_type": o.soil_type,
        }
        return json.dumps(ctx, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "orchard_id": orchard_id}, ensure_ascii=False)
    finally:
        try:
            db.close()
        except Exception:
            pass

@tool
def fuzzy_risk_check(temperature: float, humidity: float, rainfall: float = 0.0, phenology: float = 0.7) -> str:
    """
    (环境风险) 调用模糊推理引擎，评估当前气象条件下各病虫害的发生风险评分。
    temperature : 气温 (°C)
    humidity    : 相对湿度 (%)
    rainfall    : 降雨量 (mm，默认 0)
    phenology   : 物候期 (0~1; 0.2=休眠 0.5=萌芽 0.7=生长 0.8=花期 0.9=果期，默认 0.7)
    输出各病虫害的风险等级和评分 (0~100)。
    在慢通路中，可用此工具的输出作为 calculate_confidence 的环境加权依据。
    """
    try:
        from app.services.fuzzy_engine import CitrusFuzzyEngine
        engine = CitrusFuzzyEngine()
        result = engine.predict({
            "temp": float(temperature),
            "humidity": float(humidity),
            "rainfall": float(rainfall),
            "phenology": float(phenology),
        })
        lines = ["【模糊推理环境风险评估】"]
        for disease, info in sorted(result.items(), key=lambda x: x[1].get("risk_score", 0), reverse=True):
            score = info.get("risk_score", 0.0)
            level = info.get("risk_level", "低风险")
            lines.append(f"  {disease}: {level}（{score:.0f}/100）")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 模糊推理失败: {e}"


# --- Agent 初始化 ---
# 将所有工具放入列表
tools = [
    rag_search, knowledge_base_retrieval, get_weather, web_search,
    analyze_candidates, calculate_confidence, generate_clarifying_question, create_final_report,
    disease_risk_prediction, treatment_maintenance_advice,
    fetch_orchard_context, fuzzy_risk_check]
    
    
# 从 LangChain Hub 加载提示词模板并补充自定义指导
today_str = datetime.now().date().strftime("%Y-%m-%d")
tools_overview=(
        "你是一个多功能的智能助手，特别擅长柑橘病虫害诊断、预测和维护。\n\n"
        "--- 输出格式要求 ---\n"
        "1. 支持 Markdown 内容：可以使用**加粗**、*斜体*、`代码`、```代码块```、[链接](https://example.com) 和列表。\n"
        "2. 所有文本输出必须使用 \\n 进行换行，以兼容前端渲染。\n"
        "2. 追问选项必须使用以下JSON格式：\n"
        "   {\"type\": \"clarification\", \"content\": \"问题内容\", \"options\": [\"选项1\", \"选项2\", \"选项3\"]}\n"
        "3. 诊断报告必须使用以下JSON格式：\n"
        "   {\"type\": \"diagnosis_report\", \"content\": \"报告内容\", \"primary_diagnosis\": \"主要诊断\", \"confidence\": 0.85, \"secondary_diagnoses\": [{\"name\": \"次要诊断\", \"confidence\": 0.15}], \"prevention_advice\": \"预防建议\", \"treatment_advice\": \"治疗建议\"}\n"
        "4. 普通文本消息使用：\n"
        "   {\"type\": \"text\", \"content\": \"消息内容\"}\n\n"
        "--- 主要工作流 ---\n\n"
        "**0. 果园上下文**\n"
        "如果用户没有强调地址，就默认可以通过'fetch_orchard_context'自主调用用户果园有关的上下文，包含品种、生育期、树龄、地理坐标、土壤等。应在推理中恰当利用，但不可编造缺失字段。\n\n"
        "**1. 诊断流程（意图：'诊断/症状/什么病'）**\n"
        "系统已注入：①本地 CNN Top-K；②在 CNN 标签引导下的视觉解释（Kimi 为读图描述，DeepSeek 为基于标签的症状学说明）；"
        "③果园气象驱动的模糊环境风险摘要；④**快通路门控**（高置信视觉 + 与 Top-1 对应病害的环境风险无「极低分」冲突，与论文 5.4 一致）。\n"
        "请严格根据上下文【快通路门控】结论选路（勿仅凭主观判断绕过门控）：\n\n"
        "🔵 **快通路**（仅当上下文写明「快通路已许可」时）：\n"
        "  1) 以 CNN Top-1 为主诊断，并充分采纳【视觉解释】段落面向农户表述\n"
        "  2) `knowledge_base_retrieval` + `create_final_report` 输出防治建议\n\n"
        "🟡 **慢通路**（门控未许可 / OOD / 置信不足 / 纯文字无图 等）：\n"
        "  1) `knowledge_base_retrieval` 获取 Top-3 候选（传入症状描述 + CNN 摘要）\n"
        "  2) `analyze_candidates` 三维评分（症状/环境/病因）\n"
        "  3) [可选] 若已知气温/湿度，调用 `fuzzy_risk_check` 获取环境风险作为加权参考\n"
        "  4) `calculate_confidence` 融合评分\n"
        "  5) 置信度 ≥ 0.7 → `create_final_report`；否则 → `generate_clarifying_question` 追问\n"
        "  6) 追问最多 3 次，第 3 次后强制出具带不确定性说明的报告\n\n"
        "**2. 预测流程 (意图: '预测/预报/风险')**\n"
        "当用户想要预测未来病虫害风险时，按以下步骤操作：\n"
        "1) 询问用户目标城市和需要预测的天数(例如，未来7天)。日期需要根据当前提供的当前日期作为参考。\n"
        f"当前日期：{today_str}\n"
        "2) 使用 `web_search` 查找该城市的**土壤条件** (如酸碱度pH, 肥力, 土质)。\n"
        "3) 使用 `web_search` 查找未来几天的**天气预报**，并整理成`disease_risk_prediction`工具需要的格式 (列表，包含 'avg_temp', 'avg_rh', 'lwd', 'rainfall', 'wind_speed')。\n"
        "4) 调用 `disease_risk_prediction` 工具，传入天气和土壤信息。\n"
        "5) 将最终的综合报告呈现给用户。\n\n"
        "**3. 维护流程 (意图: '维护/复查/效果怎么样')**\n"
        "当用户咨询关于已确诊病害的后续维护时，按以下步骤操作：\n"
        "1) 询问并确认：之前确诊的**病害名称**、使用的**治理措施**(如药剂)、以及**治疗效果**如何。\n"
        "2) 询问用户所在的城市，并调用 `get_weather` 获取**近期天气**。\n"
        "3) 调用 `treatment_maintenance_advice` 工具，传入以上所有信息。\n"
        "4) 将生成的维护建议呈现给用户。\n\n"
        "**重要提醒：**\n"
        "- 所有回复必须使用上述JSON格式\n"
        "- 文本内容使用 \\n 进行换行\n"
        "- 确保前端能够正确解析和显示"
    )

# 提示词模板：仅保留 create_tool_calling_agent 实际需要的占位符
# {tools} / {tool_names} 是旧版 ReAct 专用，tool-calling agent 不注入它们，
# 留在模板里会引发 KeyError，已移除。
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "{tools_overview}",
        ),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
).partial(tools_overview=tools_overview)

# 创建 Agent（无状态，memory 由各 session_ctx 持有）
_agent_graph = create_tool_calling_agent(get_llm(), tools, prompt)


# ── SessionCtx：每个 session 的完整上下文对象 ────────────────────────────────
from dataclasses import dataclass, field as _dc_field

@dataclass
class _SessionCtx:
    """
    对话记忆（chat_history）与图像分析槽（image_slot）分开管理：
    - chat_history  : 文字对话记忆，永久保留（最多 20 轮）
    - image_slot    : 本轮图片的并行视觉分析结果，新图片到来时替换
    - image_turn    : 图片上传时的 turn 编号（用于判断"图片是否仍新鲜"）
    """
    executor: "AgentExecutor"
    current_turn: int = 0
    image_slot: dict | None = None         # {"cnn": {...}, "llm_desc": str|None}
    image_turn: int = -99
    image_urls: list = _dc_field(default_factory=list)

    def has_fresh_image(self, staleness: int = 3) -> bool:
        """当前轮次距图片上传 ≤ staleness 轮 → 图片"仍新鲜"，可注入上下文"""
        return (
            self.image_slot is not None
            and (self.current_turn - self.image_turn) <= staleness
        )

    def set_image(self, slot: dict, urls: list[str]) -> None:
        self.image_slot = slot
        self.image_turn = self.current_turn
        self.image_urls = list(urls)

    def advance_turn(self) -> None:
        self.current_turn += 1


_session_contexts: dict[str, "_SessionCtx"] = {}

def _get_session_ctx(session_id: str) -> "_SessionCtx":
    """获取或创建 session 级别的上下文对象（含独立 memory + image_slot）"""
    if session_id not in _session_contexts:
        mem = (
            ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            if ConversationBufferMemory is not None
            else None
        )
        executor = AgentExecutor(
            agent=_agent_graph,
            tools=tools,
            memory=mem,
            verbose=True,
        )
        _session_contexts[session_id] = _SessionCtx(executor=executor)
    return _session_contexts[session_id]


# 全局 executor 仅供 agent_respond / main() 使用（无 session 上下文时的兜底）
agent_executor = _get_session_ctx("__global__").executor

# --- 诊断表单 ---
def run_diagnostic_form() -> str:
    """运行命令行表单以收集诊断信息"""
    print("\n--- 柑橘病虫害诊断表单 ---")
    print("请根据提示输入数字选项，可输入多个数字（如 '1 3'），按回车确认。" )

    form_data = {}

    # 问题0: 基本信息
    form_data["basic"] = {
        "品种": input("\n- 品种（可留空）: ").strip() or "",
        "砧木": input("- 砧木（可留空）: ").strip() or "",
        "树龄": input("- 树龄（年, 可留空）: ").strip() or "",
        "生育期": input("- 当前生育期（春梢/夏梢/秋梢/开花/幼果/膨大/转色/采后）: ").strip() or "",
    }

    # 问题1: 主要问题部位
    parts = ["叶片", "果实", "枝干", "根部", "整株"]
    form_data["parts"] = _ask_question("主要问题部位", parts, multi=True)

    # 问题2: 症状描述
    symptoms = {}
    if "叶片" in form_data["parts"]:
        symptoms["叶片"] = {
            "颜色异常": _ask_question("叶片颜色异常", ["黄化", "斑点", "干枯", "其他"]),
            "形状异常": _ask_question("叶片形状异常", ["卷曲", "畸形", "穿孔", "其他"]),
            "斑点颜色": _ask_question("叶片斑点颜色", ["黄", "褐", "黑", "灰白", "其他"]),
            "斑点形状": _ask_question("叶片斑点形状", ["圆形", "不规则", "轮纹状"]),
            "斑点质感": _ask_question("叶片斑点质感", ["平滑", "凸起", "油渍状", "霉层"]),
        }
    if "果实" in form_data["parts"]:
        symptoms["果实"] = {
            "果皮症状": _ask_question("果实果皮症状", ["斑点", "腐烂", "畸形", "开裂"]),
        }
    form_data["symptoms"] = symptoms

    # 问题3: 环境与管理
    form_data["env"] = {
        "天气": _ask_question("近期天气", ["持续晴热", "连续阴雨", "干旱", "大风/台风", "雾/霜冻", "其他"]),
        "施肥": _ask_question("近期施肥", ["是", "否"]),
        "用药": _ask_question("近期用药", ["是", "否"]),
        "灌溉/排水": _ask_question("灌溉/排水情况", ["干旱", "适中", "渍涝"], multi=False),
        "土壤pH": input("- 土壤pH（可估计/留空）: ").strip() or "",
    }

    # 问题4: 病情发展
    form_data["dev"] = {
        "速度": _ask_question("发生速度", ["缓慢", "快速蔓延"]),
        "程度": _ask_question("严重程度", ["个别植株", "小片发生", "大面积发生"]),
        "空间分布": _ask_question("空间分布", ["向阳面", "内膛", "下部", "顶部", "低洼处", "随机"]),
        "首发季节": _ask_question("首次出现季节", ["春", "夏", "秋", "冬", "不详"], multi=False),
    }

    # 问题5: 媒介/虫态
    form_data["vector"] = {
        "观察到的害虫": _ask_question("是否观察到典型害虫/虫态", ["木虱", "蚜虫", "粉虱", "螨类", "未见"], multi=True)
    }

    return _format_form_data(form_data)

def _ask_question(question: str, options: list, multi: bool = False) -> list:
    """在命令行中提问并获取用户的选择"""
    print(f"\n- {question} ({'可多选' if multi else '单选'})")
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    
    while True:
        try:
            inp = input("请选择: ").strip().split()
            choices = [int(i) for i in inp]
            if all(1 <= c <= len(options) for c in choices):
                if not multi and len(choices) > 1:
                    print("错误：此问题仅限单选。" )
                    continue
                return [options[c - 1] for c in choices]
        except (ValueError, IndexError):
            print("错误：请输入有效的数字选项。" )

def _format_form_data(data: dict) -> str:
    """将收集的表单数据格式化为自然语言描述"""
    desc = ["以下是收集到的柑橘病症信息："]
    if data.get("basic"):
        b = data["basic"]
        desc.append("- 基本信息: " + ", ".join([
            f"品种:{b.get('品种') or '未知'}",
            f"砧木:{b.get('砧木') or '未知'}",
            f"树龄:{b.get('树龄') or '未知'}",
            f"生育期:{b.get('生育期') or '未知'}",
        ]) + "。")

    if data.get("parts"):
        desc.append(f"- 主要问题部位: {', '.join(data['parts'])}。" )
    
    symptoms_desc = []
    for part, symps in data.get("symptoms", {}).items():
        part_desc = [f"在 {part} 上观察到"]
        details = []
        for key, val in symps.items():
            if val:
                details.append(f"{key}为'{', '.join(val)}'")
        if details:
            part_desc.append('；'.join(details) + "。" )
            symptoms_desc.append(' '.join(part_desc))
    if symptoms_desc:
        desc.append("- 具体症状: " + ' '.join(symptoms_desc))

    env_desc = []
    if data.get("env", {}).get("天气"):
        env_desc.append(f"近期天气为'{', '.join(data['env']['天气'])}'")
    if data.get("env", {}).get("施肥"):
        env_desc.append(f"近期{'有' if data['env']['施肥'][0] == '是' else '无'}施肥")
    if data.get("env", {}).get("用药"):
        env_desc.append(f"近期{'有' if data['env']['用药'][0] == '是' else '无'}用药")
    if data.get("env", {}).get("灌溉/排水"):
        env_desc.append(f"水分状况为{''.join(data['env']['灌溉/排水'])}")
    if data.get("env", {}).get("土壤pH"):
        env_desc.append(f"土壤pH≈{data['env']['土壤pH']}")
    if env_desc:
        desc.append(f"- 环境与管理: {', '.join(env_desc)}。" )

    dev_desc = []
    if data.get("dev", {}).get("速度"):
        dev_desc.append(f"病情发展速度{''.join(data['dev']['速度'])}")
    if data.get("dev", {}).get("程度"):
        dev_desc.append(f"严重程度为{''.join(data['dev']['程度'])}")
    if data.get("dev", {}).get("空间分布"):
        dev_desc.append(f"空间分布于{', '.join(data['dev']['空间分布'])}")
    if data.get("dev", {}).get("首发季节"):
        dev_desc.append(f"首发季节为{''.join(data['dev']['首发季节'])}")
    if dev_desc:
        desc.append(f"- 病情发展: {', '.join(dev_desc)}。" )

    if data.get("vector", {}).get("观察到的害虫"):
        vec = data['vector']['观察到的害虫']
        desc.append(f"- 媒介与虫态: {'、'.join(vec)}。")
        
    desc.append("\n请根据以上信息进行诊断。" )
    return "\n".join(desc)


# --- 主程序 ---
def main():
    """主函数：实现终端交互对话"""
    print("🤖 欢迎使用智能助手！(输入 'quit' 退出, 'clear' 清除记忆, 'diagnose' 进入诊断模式)")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n👤 您: ").strip()
            if not user_input: continue
            
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("👋 再见！")
                break
            
            if user_input.lower() in ['clear', '清除', '清空']:
                agent_executor.memory.clear()
                print("🧹 对话记忆已清除！")
                continue

            if user_input.lower() in ['diagnose', '诊断']:
                # 进入诊断模式
                diagnostic_context = run_diagnostic_form()
                print("\n[诊断] 步骤1/5: 汇总上下文…")
                print("\n📝 表单信息已汇总如下:")
                print(diagnostic_context)
                user_input = diagnostic_context
            today_str = datetime.now().date().strftime("%Y-%m-%d")
            # 把今天日期注入给 Agent（关键）
            enriched_input = f"【关于日期相关的问题，当前日期请以该日期为准】{today_str}\n{user_input}"

            print("\n🤖 正在思考...")
            
            # 简单路由：对特定关键词直接调用RAG并由LLM总结
            '''direct_rag_keywords = ["症状", "防治", "发生规律", "危害"]
            if any(k in user_input for k in direct_rag_keywords) and 'diagnose' not in user_input.lower():
                rag_results_str = rag_search(user_input)
                summary_prompt = (
                    "你是一名专业的农业技术助手。请基于下面检索到的片段，用简洁中文回答用户问题。\n" 
                    f"要求：先给直接答案，再用要点列出关键信息，并注明来源条目。\n\n" 
                    f"【用户问题】\n{user_input}\n\n【检索片段】\n{rag_results_str}"
                )
                final_text = get_llm().invoke(summary_prompt).content
                print(f"\n🤖 助手: {final_text}")
            else:
                # 走完整的Agent逻辑（包括诊断模式）'''
            response = agent_executor.invoke({"input": user_input})
            print(f"\n🤖 助手: {response['output']}")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")

def agent_respond(user_input: str) -> str:
    """供后端调用的一次性响应函数，不进行交互式输入。"""
    try:
        resp = agent_executor.invoke({"input": user_input})
        output = resp.get("output", "")
        
        # 尝试解析输出是否为JSON格式
        try:
            # 如果输出是JSON格式，直接返回
            json.loads(output)
            return output
        except:
            # 如果不是JSON格式，包装为普通文本消息
            return json.dumps({
                "type": "text",
                "content": output
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "type": "text", 
            "content": f"❌ 调用智能体失败: {e}"
        }, ensure_ascii=False)


def agent_respond_stream(session_id: str, user_input: str) -> str:
    """同步版本（带 WebSocket 回调）。"""
    try:
        ctx = _get_session_ctx(session_id)
        ctx.advance_turn()
        callbacks = [WebSocketCallbackHandler(session_id)]
        # 图片槽仍新鲜时（追问场景），把图片摘要带进来
        inject = []
        if ctx.has_fresh_image():
            v = _format_vision_slot(ctx.image_slot)
            if v:
                inject.append(v)
        clean_input = _strip_url_lines(user_input)
        final_input = "\n\n".join(inject + [clean_input]) if inject else clean_input
        resp = ctx.executor.invoke({"input": final_input}, config={"callbacks": callbacks})
        output = resp.get("output", "")
        try:
            json.loads(output)
            return output
        except Exception:
            return json.dumps({"type": "text", "content": output}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"type": "text", "content": f"❌ 调用智能体失败: {e}"}, ensure_ascii=False)


def _strip_url_lines(text: str) -> str:
    """去掉纯 URL 行（如 agent_v2_service 拼接的图片 URL），避免 URL 被 LLM 误读。"""
    lines = [l for l in (text or "").splitlines() if not l.strip().startswith("http")]
    return "\n".join(lines).strip()


def _pick_urls_for_independent_recognition(
    image_urls: list[str],
    previous_urls: list[str],
) -> list[str]:
    """
    每次新传图独立识别，不把历史图片与本轮多张图叠加入 CNN/多模态：
    - 相对上次会话绑定的 URL，找出本轮**新增** URL，只取其中**最后一张**做识别；
    - 若本次列表全是旧 URL（前端重复带全量），则只对**本次列表最后一张**再跑一遍识别；
    - 一次视觉推理只针对一张图，避免多张图塞进同一个 prompt。
    """
    if not image_urls:
        return []
    prev = {(u or "").strip() for u in (previous_urls or []) if u and str(u).strip()}
    novel: list[str] = []
    for u in image_urls:
        s = (u or "").strip()
        if not s:
            continue
        if s not in prev:
            novel.append(s)
    if novel:
        return [novel[-1]]
    all_clean = [(u or "").strip() for u in image_urls if (u or "").strip()]
    return [all_clean[-1]] if all_clean else []


async def agent_respond_stream_async(
    session_id: str,
    user_input: str,
    image_urls: list[str] | None = None,
) -> str:
    """
    异步主入口：
    1. 新图片 → CNN 先行，再以 CNN 标签引导多模态/文本 LLM 解释；更新 image_slot
    2. 拉取果园气象 + 模糊推理，做快通路「视觉-环境」门控（对齐论文 5.4 / LangGraph 节点）
    3. 追问（无新图但图片仍新鲜）→ 携带上轮 image_slot（含门控结论）
    4. 图片过期 → 不再自动注入
    """
    ctx = _get_session_ctx(session_id)
    # 在 advance 之前快照上一轮已绑定的图 URL，用于判断「本轮是否新图」
    prev_bound_urls = list(ctx.image_urls)
    ctx.advance_turn()
    callbacks = [WebSocketCallbackHandler(session_id)]

    try:
        # ── Step 1：串行视觉链 + 环境门控（仅本轮独立的一张新图）──────────
        urls_for_vision: list[str] = []
        if image_urls:
            urls_for_vision = _pick_urls_for_independent_recognition(
                image_urls, prev_bound_urls
            )
            if len(image_urls) > 1:
                print(
                    f"[AgentV2] 独立识别：本轮请求 {len(image_urls)} 个图片 URL，"
                    f"视觉模型仅处理其中 1 张 → {urls_for_vision[0] if urls_for_vision else 'none'}"
                )
        if urls_for_vision:
            print("[AgentV2] CNN → 标签引导 LLM 解释（单图）…")
            slot = await _sequential_vision_analyze(urls_for_vision)
            cnn = slot.get("cnn") or {}
            env_risk = await _load_environmental_risk(session_id)
            allowed, gate_notes = _evaluate_fast_path_gate(cnn if cnn.get("available") else None, env_risk)
            hk = (cnn.get("fuzzy_disease_key") or "") if cnn.get("available") else None
            slot["fast_path_gate"] = {"allowed": allowed, "notes": gate_notes}
            slot["env_risk_brief"] = _format_env_risk_brief(env_risk, hk or None)
            ctx.set_image(slot, urls_for_vision)
            print(
                f"[AgentV2] 视觉+环境门控完成 → CNN: {cnn.get('top1_class_zh', 'N/A')} "
                f"({cnn.get('top1_prob', 0):.1%}), 快通路={'是' if allowed else '否'}, "
                f"解释={'有' if slot.get('llm_desc') else '无'}"
            )

        # ── Step 2：构建注入上下文 ───────────────────────────────────
        inject_parts: list[str] = []

        # 本轮确实跑了新图识别时，明确声明与历史图片脱钩
        if urls_for_vision:
            inject_parts.append(
                "【重要】以下视觉结论仅针对本轮新上传的**这一张**图片；"
                "请勿与对话中更早的其他图片结论合并或混淆。"
            )

        # 图片上下文：本轮有图 OR 图片仍新鲜（追问同一图）
        if ctx.image_slot and (urls_for_vision or ctx.has_fresh_image()):
            vision_text = _format_vision_slot(ctx.image_slot)
            if vision_text:
                inject_parts.append(vision_text)

        # 清理用户文本（去掉 URL 行，避免 DeepSeek 等文本模型报错）
        clean_input = _strip_url_lines(user_input) or "请根据图片信息进行诊断"

        final_input = "\n\n".join(inject_parts + [clean_input]) if inject_parts else clean_input

        # ── Step 3：调用 Agent ───────────────────────────────────────
        resp = await ctx.executor.ainvoke(
            {"input": final_input},
            config={"callbacks": callbacks},
        )
        output = resp.get("output", "")
        try:
            json.loads(output)
            return output
        except Exception:
            return json.dumps({"type": "text", "content": output}, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {"type": "text", "content": f"❌ 调用智能体失败: {e}"},
            ensure_ascii=False,
        )

if __name__ == "__main__":
    # 检查关键配置
    if not DEEPSEEK_API_KEY:
        print("错误：请在 .env 文件中设置 DEEPSEEK_API_KEY")
    else:
        main()
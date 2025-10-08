import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import json
import requests
import numpy as np
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from app.services.agent_callbacks import WebSocketCallbackHandler
from langchain import hub
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
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
    



# 检索方案：改用 BM25 稀疏检索（避免本地向量嵌入引发的互斥锁）
faiss = None
SentenceTransformer = None
print("ℹ️ [RAG] 使用 BM25 稀疏检索器（已禁用本地向量嵌入）。")

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
# 默认嵌入模型路径（可被环境变量覆盖）
DEFAULT_EMBED_MODEL_PATH = "/Users/letaotao/.cache/modelscope/BAAI/bge-small-zh-v1.5"
#DEFAULT_EMBED_MODEL_PATH = os.path.join(SCRIPT_DIR, ".rag_cache", "bge-small-zh-v1.5")


# --- RAG 管理器 ---
class RAGManager:
    """封装RAG数据加载、索引和检索逻辑"""
    def __init__(self, filepath: str, embed_model_path: str):
        self.filepath = filepath
        self.embed_model_path = embed_model_path
        self.docs = []
        self.doc_texts = []
        self.doc_metas = []
        self.faiss_index = None  # 兼容属性
        self.embedder = None     # 兼容属性
        self.bm25 = None
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
        """加载数据文件并构建向量索引"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_docs = data if isinstance(data, list) else [data]
            for rec in raw_docs:
                if isinstance(rec, dict):
                    text = self._flatten_record_to_text(rec)
                    self.docs.append({"text": text, "meta": rec})
            
            if not self.docs:
                print("[RAG] 警告：未从结构化数据文件中解析到有效记录。" )
                return

            print(f"[RAG] 已加载 {len(self.docs)} 条结构化记录用于检索。" )
            self.doc_texts = [d["text"] for d in self.docs]
            self.doc_metas = [d["meta"] for d in self.docs]

            # 构建 BM25 检索器
            try:
                self.bm25 = BM25Retriever.from_texts(self.doc_texts, metadatas=self.doc_metas)
                print(f"[RAG] BM25 检索器已构建，文档数={len(self.doc_texts)}")
            except Exception as e:
                print(f"[RAG] 构建 BM25 检索器失败，将回退到关键词检索: {e}")

        except FileNotFoundError:
            print(f"[RAG] 错误：未找到结构化数据文件: {self.filepath}")
        except json.JSONDecodeError as e:
            print(f"[RAG] 错误：结构化数据JSON解析失败: {e}")
        except Exception as e:
            print(f"[RAG] 错误：加载或构建RAG时出错: {e}")

    def search(self, query: str, k: int = 3) -> list:
        """执行混合检索并返回结构化结果"""
        if not self.docs:
            return []
        # 术语归一
        query = self.normalize_terms(query)

        # 方案1: BM25 稀疏检索
        if self.bm25:
            try:
                docs = self.bm25.get_relevant_documents(query)
                results = []
                for doc in docs[:k]:
                    text = getattr(doc, "page_content", "")
                    meta = getattr(doc, "metadata", {}) or {}
                    kw_score = self._calculate_kw_score(text, query, is_fallback=True)
                    results.append({
                        "disease_name": meta.get("名称", "未命名条目"),
                        "document": (text[:500] + "...") if text else "",
                        "rag_score": kw_score,
                        "meta": meta
                    })
                if results:
                    return results
            except Exception as e:
                print(f"[RAG] BM25 检索失败，回退至关键词检索: {e}")

        # 方案2: 关键词检索 (回退)
        ranked = sorted(
            (
                {
                    "score": self._calculate_kw_score(doc["text"], query, is_fallback=True),
                    "name": doc["meta"].get("名称", "未命名条目"),
                    "snippet": doc["text"][:500] + "...",
                    "meta": doc["meta"]
                }
                for doc in self.docs
            ),
            key=lambda x: x["score"],
            reverse=True
        )
        top = [r for r in ranked if r["score"] > 0][:k]
        return [
            {
                "disease_name": item["name"],
                "document": item["snippet"],
                "rag_score": item["score"],
                "meta": item["meta"]
            } for item in top
        ]

    def _calculate_kw_score(self, text: str, q: str, is_fallback=False) -> float:
        """计算关键词匹配分数"""
        score = 0.0
        if q in text:
            score += 1.5 if not is_fallback else 2.0
        
        tokens = [t for t in q.replace("/", " ").replace("\\", " ").split() if t]
        if not tokens:
            score += sum(text.count(c) for c in q) * (0.05 if not is_fallback else 1.0)
        else:
            score += sum(text.count(t) for t in tokens) * (0.2 if not is_fallback else 1.0)
        return score

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
            # 病名常见简写（示例）
            "溃疡": "溃疡病", "疮痂": "疮痂病",
        }
        t = text
        for k, v in mapping.items():
            t = t.replace(k, v)
        return t

# --- 初始化 ---
# 预先实例化 RAG 管理器和 LLM，避免在多线程环境中延迟加载引发问题

try:
    rag_manager = RAGManager(STRUCTURED_DATA_PATH, DEFAULT_EMBED_MODEL_PATH)

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
async def summarize_images(image_urls: list[str], instruction: str | None = None) -> str:
    """对上传的图片进行简述提取关键信息。
    如果底层模型支持 vision（如 Kimi），用 image_url 多模态消息；否则回退为文本提示。
    """
    if not image_urls:
        return ""
    prompt = instruction or (
        "请查看这些柑橘图片，总结可见的病症/虫害线索：\n"
        "- 关注病斑形态、颜色、分布部位（叶片/果实/枝干）\n"
        "- 是否有煤污/霉层/流胶/虫害痕迹\n"
        "- 给出2-4条要点，简短即可"
    )
    # 将本地/私网URL转为 data URL，避免外部模型无法访问
    def to_data_url(url: str) -> str:
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            if parsed.scheme in ("http", "https") and host not in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                return url
            # 解析本地 uploads 目录文件
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "uploads")
            path_part = parsed.path or ""
            if path_part.startswith("/uploads/"):
                rel = path_part[len("/uploads/"):]
                local_path = os.path.join(uploads_dir, rel)
                if os.path.exists(local_path):
                    with open(local_path, "rb") as f:
                        data = f.read()
                    mime, _ = mimetypes.guess_type(local_path)
                    mime = mime or "image/jpeg"
                    b64 = base64.b64encode(data).decode("utf-8")
                    return f"data:{mime};base64,{b64}"
        except Exception:
            pass
        return url

    try:
        safe_urls = [to_data_url(u) for u in image_urls]
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": url}}
            for url in safe_urls
        ]
        msg = HumanMessage(content=content)
        resp = await get_llm().ainvoke([msg])
        return getattr(resp, "content", "") or str(resp)
    except Exception:
        # 回退：将URL作为文本交给模型参考
        joined = "\n".join(image_urls)
        text_prompt = f"以下是用户上传的图片URL（模型若不支持图像，可按文字参考）：\n{joined}\n\n{prompt}"
        resp = await get_llm().ainvoke(text_prompt)
        return getattr(resp, "content", "") or str(resp)


# --- 工具定义 ---
@tool
def rag_search(query: str) -> str:
    """
    当需要回答关于技术、定义或特定知识库内部的问题时，使用此工具。
    返回格式化的字符串，包含名称、分数和文档片段。
    """
    print(f"--- 正在进行 RAG 检索: {query} ---")
    if not query: return "请输入有效的检索问题。"
    
    results = get_rag_manager().search(query)
    if not results: return f"未在知识库中检索到与'{query}'相关的信息。"

    lines = []
    for i, item in enumerate(results, 1):
        title = item["disease_name"]
        score_info = f"score={item['rag_score']:.3f}"
        if "vector_score" in item:
            score_info += f", vec={item['vector_score']:.3f}"
        lines.append(f"[{i}] {title} ({score_info})\n{item['document']}")
    return "\n\n".join(lines)

@tool
def knowledge_base_retrieval(context: str, top_k: int = 3) -> list:
    """
    基于输入上下文，在知识库中检索并返回结构化的Top-K候选列表。
    输出: [{"disease_name", "document", "rag_score"}]
    """
    print("[诊断] 步骤2/5: 知识库检索 Top-3 候选…")
    if not context: return []
    results = get_rag_manager().search(get_rag_manager().normalize_terms(context), k=top_k)
    print(f"[诊断] 检索完成，命中 {len(results)} 条候选。")
    return results



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
        else:
            level = "low"
            decision = "clarify"
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
    else:
        ranked_list = ranked.get("ranked", [])
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

# --- Agent 初始化 ---
# 将所有工具放入列表
tools = [
    rag_search, knowledge_base_retrieval, get_weather, web_search,
    analyze_candidates, calculate_confidence, generate_clarifying_question, create_final_report,
    disease_risk_prediction, treatment_maintenance_advice,
    fetch_orchard_context]
    
    
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
        "**1. 诊断流程 (意图: '诊断/症状/什么病')**\n"
        "当识别到用户意图涉及诊断时，必须按以下工具链顺序执行：\n"
        "1) `knowledge_base_retrieval` 获取Top-3候选。\n"
        "2) `analyze_candidates` 三维评分。\n"
        "3) `calculate_confidence` 计算置信度。\n"
        "4) 高置信 → `create_final_report`；否则 → `generate_clarifying_question`。\n"
        "5) 用户回答后，将新信息融入上下文，重复流程。\n\n"
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
    
prompt = hub.pull("hwchase17/openai-tools-agent").partial(
    tools_overview=tools_overview
)

# 创建 Agent
agent = create_tool_calling_agent(get_llm(), tools, prompt)

# 创建带记忆的 Agent 执行器
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=ConversationBufferMemory(memory_key="chat_history", return_messages=True),
    verbose=True
)

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
    """带回调的响应：将 LLM/工具进度通过 WebSocket 推送到 session。
    返回最终输出（JSON字符串），实时状态由回调推送。
    """
    try:
        callbacks = [WebSocketCallbackHandler(session_id)]
        resp = agent_executor.invoke({"input": user_input}, config={"callbacks": callbacks})
        output = resp.get("output", "")
        try:
            json.loads(output)
            return output
        except:
            return json.dumps({
                "type": "text",
                "content": output
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "type": "text", 
            "content": f"❌ 调用智能体失败: {e}"
        }, ensure_ascii=False)


async def agent_respond_stream_async(session_id: str, user_input: str, image_urls: list[str] | None = None) -> str:
    """异步版本：
    - 若提供 image_urls，则走多模态（HumanMessage content=[text,image_url...]）
    - 否则走 Agent 执行器（工具链）
    两种方式均通过回调实时推送到前端。
    """
    callbacks = [WebSocketCallbackHandler(session_id)]
    try:
        if image_urls:
            # 多模态：同次调用中传入文本 + 图像
            # 将本地/私网URL转成 data URL，避免云端不可访问
            def to_data_url(url: str) -> str:
                try:
                    parsed = urlparse(url)
                    host = parsed.hostname or ""
                    if parsed.scheme in ("http", "https") and host not in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                        return url
                    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "uploads")
                    path_part = parsed.path or ""
                    if path_part.startswith("/uploads/"):
                        rel = path_part[len("/uploads/"):]
                        local_path = os.path.join(uploads_dir, rel)
                        if os.path.exists(local_path):
                            with open(local_path, "rb") as f:
                                data = f.read()
                            mime, _ = mimetypes.guess_type(local_path)
                            mime = mime or "image/jpeg"
                            b64 = base64.b64encode(data).decode("utf-8")
                            return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
                return url

            safe_urls = [to_data_url(u) for u in image_urls]
            content = ([{"type": "text", "text": user_input or "请结合图片进行分析"}] +
                       [{"type": "image_url", "image_url": {"url": u}} for u in safe_urls])
            msg = HumanMessage(content=content)
            resp = await get_llm().ainvoke([msg], config={"callbacks": callbacks})
            text = getattr(resp, "content", "") or str(resp)
            return json.dumps({"type": "text", "content": text}, ensure_ascii=False)

        # 纯文本：走 Agent 工具链
        resp = await agent_executor.ainvoke({"input": user_input}, config={"callbacks": callbacks})
        output = resp.get("output", "")
        try:
            json.loads(output)
            return output
        except Exception:
            return json.dumps({"type": "text", "content": output}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"type": "text", "content": f"❌ 调用智能体失败: {e}"}, ensure_ascii=False)

if __name__ == "__main__":
    # 检查关键配置
    if not DEEPSEEK_API_KEY:
        print("错误：请在 .env 文件中设置 DEEPSEEK_API_KEY")
    else:
        main()
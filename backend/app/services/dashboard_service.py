import asyncio
import uuid
from typing import Any, Dict, List, Optional
import json
from datetime import datetime
import re

from app.core.database import SessionLocal
from app import crud, schemas, models
from app.models.orchard import Orchard
from app.services.weather_service import weather_service
from app.services.fuzzy_engine import create_engine
from app.agent_v2.predictor import DISEASE_SYMPTOMS

def _map_phenology_to_score(phenology: Optional[str]) -> float:
    """将物候期映射为数值分数"""
    if not phenology: return 0.7
    mapping = {"休眠期": 0.2, "萌芽期": 0.5, "生长期": 0.8, "花期": 0.7, "结果期": 0.6}
    return float(mapping.get(phenology, 0.7))

def _build_fuzzy_engine_inputs(orchard: Optional[Orchard], weather: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """构建 fuzzy_engine.CitrusFuzzyEngine.predict() 所需数值输入（与 fuzzy_engine 变量域一致）。"""
    current = (weather or {}).get("current", {})
    forecast = (weather or {}).get("forecast", [])
    today_precip = float(forecast[0].get("precipitation_total", 0) or 0) if forecast else 0.0

    temp = float(current.get("temperature", 22.0) or 22.0)
    humidity = float(current.get("humidity", 60) or 60)
    # 降雨模糊变量论域 0–100（mm），与规则库中「无/小雨/大雨」一致
    rainfall = float(min(100.0, max(0.0, today_precip)))
    phenology = _map_phenology_to_score(getattr(orchard, "current_phenology", None))

    return {
        "temp": temp,
        "humidity": humidity,
        "rainfall": rainfall,
        "phenology": phenology,
    }


def _fuzzy_output_to_risk_results(fuzzy_output: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """将 CitrusFuzzyEngine 输出转为仪表盘/预警使用的 risk + basis + symptoms 结构。"""
    out: Dict[str, Dict[str, Any]] = {}
    for disease, info in fuzzy_output.items():
        basis: List[str] = []
        for fr in info.get("fired_rules") or []:
            desc = (fr.get("description") or "").strip()
            if desc:
                basis.append(desc)
            else:
                rt = (fr.get("rule_text") or "").strip()
                if rt:
                    basis.append(rt)
        out[disease] = {
            "risk": float(info["risk_score"]),
            "basis": basis,
            "symptoms": DISEASE_SYMPTOMS.get(disease, "暂无详细症状信息。"),
            "risk_level": info.get("risk_level"),
        }
    return out

def _calculate_health_score(risk_results: Dict[str, Dict[str, Any]]) -> int:
    """基于风险预测结果计算健康度分数"""
    if not risk_results: return 75
    
    risk_values = [data['risk'] for data in risk_results.values()]
    avg_risk = sum(risk_values) / len(risk_values) if risk_values else 0
    
    health_score = max(0, min(100, int(100 - avg_risk)))
    return health_score

def _generate_risk_briefing(risk_results: Dict[str, Dict[str, Any]], weather: Optional[Dict[str, Any]]) -> str:
    """生成风险简报"""
    if not risk_results: return "当前无显著病虫害风险，建议继续常规管理。"
    
    top_risk_name = max(risk_results, key=lambda k: risk_results[k]['risk'])
    top_risk_data = risk_results[top_risk_name]
    risk_score = top_risk_data['risk']
    
    # 与 fuzzy_engine.CitrusFuzzyEngine._risk_level 一致：>=65 高，>=35 中，否则低
    if risk_score >= 65: risk_level, advice = "高风险", "建议立即采取防控措施"
    elif risk_score >= 35: risk_level, advice = "中风险", "建议加强监测，准备防控"
    else: risk_level, advice = "低风险", "继续常规管理"
    
    weather_info = ""
    if weather and "current" in weather:
        temp = weather["current"].get("temperature", "未知")
        humidity = weather["current"].get("humidity", "未知")
        weather_info = f"当前天气：{temp}°C，湿度{humidity}%。"
    
    return f"【{risk_level}预警】{top_risk_name}风险达到{risk_score:.1f}%。{weather_info}{advice}。"

async def get_dashboard_data(orchard_id: uuid.UUID) -> Dict[str, Any]:
    """获取主界面数据：天气、风险预测、健康度、简报"""
    db = SessionLocal()
    try:
        orchard: Optional[Orchard] = db.query(Orchard).filter(Orchard.id == orchard_id).first()
        
        weather_data = await _get_weather_for_orchard(orchard)
        
        fuzzy_inputs = _build_fuzzy_engine_inputs(orchard, weather_data)
        risk_results = _fuzzy_output_to_risk_results(create_engine().predict(fuzzy_inputs))
        
        health_score = _calculate_health_score(risk_results)
        briefing = _generate_risk_briefing(risk_results, weather_data)
        
        current_weather = None
        if weather_data and "current" in weather_data:
            current = weather_data["current"]
            current_weather = {
                "temperature": current.get("temperature", 22),
                "humidity": current.get("humidity", 60),
                "condition": "sunny" if "晴" in current.get("description", "") else "cloudy"
            }
        
        risk_alerts = _format_risk_alerts(risk_results)
        
        risk_distribution = {disease: data['risk'] for disease, data in risk_results.items()}

        return {
            "current_weather": current_weather,
            "health_score": health_score,
            "ai_daily_briefing": briefing,
            "risk_alerts": risk_alerts,
            "has_new_alerts": len(risk_alerts) > 0,
            "risk_distribution": risk_distribution
        }
        
    except Exception as e:
        print(f"Error in get_dashboard_data: {e}")
        return {
            "current_weather": None, "health_score": 75,
            "ai_daily_briefing": "数据获取失败，请稍后重试。",
            "risk_alerts": [], "has_new_alerts": False, "risk_distribution": {}
        }
    finally:
        db.close()

def _format_risk_alerts(risk_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将风险预测结果格式化为风险预警"""
    alerts = []
    for disease, data in risk_results.items():
        risk_score = data['risk']
        # 与 fuzzy_engine：中风险及以上生成预警（>=35）
        if risk_score >= 35:
            description = f"预测依据：{' '.join(data['basis']) if data['basis'] else '综合环境因素（模糊推理）'}\n" \
                          f"识别症状：{data['symptoms']}"
            alerts.append({
                "id": f"risk_{disease}",
                "type": "risk",
                "risk_item": disease,
                "title": f"{disease}风险预警 ({risk_score:.1f}%)",
                "description": description,
                "basis": data['basis'],
                "symptoms": data['symptoms'],
                "severity": "high" if risk_score >= 65 else "medium",
                "timestamp": datetime.now().isoformat()
            })
    return sorted(alerts, key=lambda x: x['title'], reverse=True)

async def _get_weather_for_orchard(orchard: Optional[Orchard]) -> Optional[Dict[str, Any]]:
    """根据果园信息获取天气数据"""
    if not orchard: return None
    
    if orchard.location_latitude and orchard.location_longitude:
        return await weather_service.get_weather_by_coordinates(
            float(orchard.location_latitude), float(orchard.location_longitude)
        )
    
    if orchard.address_detail:
        city_name = _extract_city_from_address(orchard.address_detail)
        if city_name:
            return await weather_service.get_weather_by_city(city_name)
    return None

def _extract_city_from_address(address: str) -> Optional[str]:
    """从详细地址中提取城市名称（支持中文/英文逗号；无逗号时整段解析「xx省xx市」）。"""
    if not address or not str(address).strip():
        return None
    text = str(address).strip()
    last_part = text
    for sep in ("，", ","):
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) >= 2:
                last_part = parts[-1]
            break
    # 四川省成都市 / 四川省成都市武侯区
    m = re.search(r"省(.+?)市", last_part)
    if m:
        return m.group(1).strip()
    # 仅「成都市」
    if last_part.endswith("市") and "省" not in last_part:
        return last_part.replace("市", "").strip()
    return last_part.strip() or None

class DashboardService:
    async def get_dashboard_data(self, orchard_id: uuid.UUID) -> Dict[str, Any]:
        return await get_dashboard_data(orchard_id)

dashboard_service = DashboardService()

import asyncio
import uuid
from typing import Any, Dict, List, Optional
import json

from app.core.database import SessionLocal
from app import crud, schemas, models
from app.models.orchard import Orchard
from app.services.websocket_service import manager
from app.services.weather_service import weather_service

# 引入 agent-v2 预测器与配置
from app.agent_v2.predictor import CitrusDiseasePredictor
from app.agent_v2.config import CONTROL_MEASURES, PREVENTION_MEASURES
from app.agent_v2.test import agent_respond, agent_respond_stream, agent_respond_stream_async, summarize_images
from app.services.turn_registry import next_turn
from app.services.session_orchard_registry import register as register_session_orchard, set_current_session


def _map_phenology_to_score(phenology: Optional[str]) -> float:
    if not phenology:
        return 0.7
    mapping = {
        "休眠期": 0.2,
        "萌芽期": 0.5,
        "生长期": 0.8,
        "花期": 0.7,
        "结果期": 0.6,
    }
    return float(mapping.get(phenology, 0.7))


def _build_daily_input_from_sources(
    orchard: Optional[Orchard], weather: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    # 天气映射（若获取失败，提供合理默认值）
    current = (weather or {}).get("current", {})
    forecast = (weather or {}).get("forecast", [])
    today_precip = 0.0
    if forecast:
        today_precip = float(forecast[0].get("precipitation_total", 0) or 0)

    avg_temp = float(current.get("temperature", 22.0) or 22.0)
    avg_rh = float(current.get("humidity", 60) or 60)
    wind_speed = float(current.get("wind_speed", 3.0) or 3.0)
    rainfall = float(today_precip)

    # 估算叶面湿润时长：简化模型（湿度与降雨共同影响）
    lwd = 0.0
    if avg_rh >= 90 or rainfall > 0:
        lwd = 12.0
    elif avg_rh >= 70:
        lwd = 6.0
    else:
        lwd = 2.0

    host_phenology = _map_phenology_to_score(getattr(orchard, "current_phenology", None))
    # 易感性先采用默认值，未来可由品种或历史健康记录推断
    host_susceptibility = 0.7

    return {
        "avg_temp": avg_temp,
        "avg_rh": avg_rh,
        "lwd": lwd,
        "rainfall": rainfall,
        "wind_speed": wind_speed,
        "host_susceptibility": host_susceptibility,
        "host_phenology": host_phenology,
    }


async def _run_inference(
    session_id: str,
    orchard_id: uuid.UUID,
    initial_query: Optional[str],
    image_urls: Optional[List[str]],
) -> None:
    # 给前端 WebSocket 一点时间完成连接，避免首条消息丢失
    await asyncio.sleep(0.2)
    turn = next_turn(session_id)
    await manager.broadcast_to_session(session_id, f"TURN:{turn}|PROGRESS:Running:agent_v2")

    db = SessionLocal()
    try:
        # 取果园信息
        orchard: Optional[Orchard] = db.query(Orchard).filter(Orchard.id == orchard_id).first()
        # 建立 session -> orchard 关联，供工具默认查询
        try:
            register_session_orchard(session_id, orchard.id if orchard else orchard_id)
            set_current_session(session_id)
        except Exception:
            pass

        # 拉取天气（若有经纬度）
        weather_data: Optional[Dict[str, Any]] = None
        if orchard and orchard.location_latitude is not None and orchard.location_longitude is not None:
            weather_data = await weather_service.get_weather_by_coordinates(
                float(orchard.location_latitude), float(orchard.location_longitude)
            )

        daily_input = _build_daily_input_from_sources(orchard, weather_data)

        predictor = CitrusDiseasePredictor()
        predictor.add_daily_data(daily_input)

        # 先发送天气摘要（若可用）
        if weather_data:
            try:
                loc = (weather_data.get("location") or {}).get("name") or "当前位置"
                temp = (weather_data.get("current") or {}).get("temperature")
                desc = (weather_data.get("current") or {}).get("description") or ""
                msg = f"📍 {loc} 天气：{temp}°C，{desc}"
                payload = json.dumps({"type": "text", "content": msg}, ensure_ascii=False)
                await manager.broadcast_to_session(session_id, f"TURN:{turn}|MESSAGE:{payload}")
            except Exception:
                pass

        # 智能体对初始用户输入进行回复（改为带回调的流式推送）
        if initial_query or (image_urls and len(image_urls) > 0):
            try:
                # 异步流式执行，避免阻塞事件循环，实时经回调推送
                # 直接将图片URL文本附加到用户描述，让Agent与工具自行处理
                user_text = (initial_query or "").strip()
                if image_urls:
                    joined_urls = "\n".join(image_urls)
                    user_text = (user_text + f"\n\n[图片URL]\n{joined_urls}").strip()
                # 注入果园上下文，增强 Agent 推理
                
                agent_response = await agent_respond_stream_async(session_id, f"\n{user_text}", image_urls or None)
                if agent_response:
                    await manager.broadcast_to_session(session_id, f"TURN:{turn}|MESSAGE:{agent_response}")
            except Exception:
                pass

        risk_results = predictor.predict(daily_input)

        # 选择主诊断与置信度
        sorted_items = sorted(risk_results.items(), key=lambda x: x[1], reverse=True)
        primary_name, primary_score = sorted_items[0]
        secondary = [
            {"name": name, "confidence": round(score / 100.0, 4)}
            for name, score in sorted_items[1:4]
        ]

        # 风险分布消息已移至主界面，诊断界面不再显示

        # 生成与入库
        prevention = PREVENTION_MEASURES.get(primary_name, "加强田间管理与监测")
        treatment = CONTROL_MEASURES.get(primary_name, "请咨询当地农技人员进行针对性用药")
        result_create = schemas.DiagnosisResultCreate(
            primary_diagnosis=primary_name,
            confidence=round(float(primary_score) / 100.0, 4),
            secondary_diagnoses=secondary,
            prevention_advice=prevention,
            treatment_advice=treatment,
            follow_up_plan="7天后复查并根据实地情况调整防控方案。",
        )
        created = crud.diagnosis.create_diagnosis_result(db, session_id=uuid.UUID(session_id), result_data=result_create)

        # 通知前端结果已就绪
        await manager.broadcast_to_session(session_id, f"TURN:{turn}|RESULT_READY:{created.id}")
    except Exception as e:
        await manager.broadcast_to_session(session_id, f"ERROR:AgentV2 failed: {e}")
    finally:
        db.close()


class AgentV2Service:
    async def start_new_session(
        self,
        session_id: str,
        orchard_id: uuid.UUID,
        initial_query: Optional[str],
        image_urls: Optional[List[str]]
    ) -> None:
        # 与现有服务对齐：后台运行，不阻塞请求
        asyncio.create_task(_run_inference(session_id, orchard_id, initial_query, image_urls))

    async def continue_session(self, session_id: str, user_input: Optional[str]) -> None:
        # 多轮：调用智能体生成回复并推送
        try:
            turn = next_turn(session_id)
            await manager.broadcast_to_session(session_id, f"TURN:{turn}|PROGRESS:Running:agent_v2_reply")
            if user_input:
                # 使用带回调的版本，实时推送进度/思考
                agent_response = await agent_respond_stream_async(session_id, user_input)
                if agent_response:
                    await manager.broadcast_to_session(session_id, f"TURN:{turn}|MESSAGE:{agent_response}")
        except Exception as e:
            await manager.broadcast_to_session(session_id, f"ERROR:AgentV2 continue failed: {e}")


agent_v2_service = AgentV2Service()



import asyncio
import re
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
from app.agent_v2.test import agent_respond_stream_async, _get_session_ctx, get_llm
from app.services.turn_registry import next_turn
from app.services.session_orchard_registry import register as register_session_orchard, set_current_session


def _agent_reply_text(agent_response: Optional[str]) -> str:
    """
    前端/智能体常返回整段 JSON：{"type":"text","content":"……大段 Markdown……"}。
    档案抽取必须对 content 解包，否则永远解析不到结构化诊断。
    """
    if not agent_response:
        return ""
    raw = str(agent_response).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            if data.get("type") == "text" and data.get("content") is not None:
                return str(data.get("content") or "")
            if data.get("type") == "diagnosis_report":
                # 保留整段 JSON 给 _parse_diagnosis_payload
                return raw
    except json.JSONDecodeError:
        pass
    return raw


def _looks_like_diagnosis_prose(text: str) -> bool:
    """判断是否为「已给出诊断结论+防治」的长回复（非仅追问）。"""
    if not text or len(text) < 120:
        return False
    keys = ("防治", "诊断", "置信度", "危害", "建议措施", "农业防治", "化学防治", "生物防治")
    hits = sum(1 for k in keys if k in text)
    return hits >= 2 or ("置信度" in text and "防治" in text)


def _parse_diagnosis_payload(agent_response: Optional[str]) -> Optional[dict]:
    """
    从 agent 返回的 JSON 字符串中解析可入库的诊断结构。
    支持：type=diagnosis_report，或顶层含 primary_diagnosis+confidence 的对象。
    """
    if not agent_response or not str(agent_response).strip():
        return None
    raw = str(agent_response).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    if data.get("type") == "diagnosis_report":
        return data
    # 有时把业务字段放在 content 里的 JSON 字符串
    if data.get("type") == "text" and data.get("content"):
        try:
            inner = json.loads(str(data["content"]))
            if isinstance(inner, dict) and inner.get("type") == "diagnosis_report":
                return inner
            if isinstance(inner, dict) and inner.get("primary_diagnosis"):
                return inner
        except (json.JSONDecodeError, TypeError):
            pass
    if data.get("primary_diagnosis") and data.get("confidence") is not None:
        return data
    return None


def _diagnosis_create_from_agent_dict(
    d: dict,
    image_urls: Optional[List[str]],
    fallback: schemas.DiagnosisResultCreate,
) -> Optional[schemas.DiagnosisResultCreate]:
    primary = (d.get("primary_diagnosis") or "").strip()
    if not primary:
        return None
    try:
        conf = float(d.get("confidence", fallback.confidence))
    except (TypeError, ValueError):
        conf = fallback.confidence
    conf = max(0.0, min(1.0, conf))
    sec = d.get("secondary_diagnoses")
    if not isinstance(sec, list):
        sec = fallback.secondary_diagnoses
    prev = d.get("prevention_advice") or PREVENTION_MEASURES.get(primary, fallback.prevention_advice)
    treat = d.get("treatment_advice") or CONTROL_MEASURES.get(primary, fallback.treatment_advice)
    follow = d.get("follow_up_plan") or fallback.follow_up_plan
    imgs = list(image_urls or []) or list(fallback.original_image_urls or [])
    return schemas.DiagnosisResultCreate(
        primary_diagnosis=primary,
        confidence=round(conf, 4),
        secondary_diagnoses=sec,
        prevention_advice=str(prev),
        treatment_advice=str(treat),
        follow_up_plan=str(follow),
        original_image_urls=imgs,
    )


def _diagnosis_create_from_cnn_session(
    session_id: str,
    image_urls: Optional[List[str]],
    fallback: schemas.DiagnosisResultCreate,
) -> Optional[schemas.DiagnosisResultCreate]:
    """智能体未输出正式报告时，用会话内 CNN Top-K 写入档案（优于纯环境预测器）。"""
    try:
        ctx = _get_session_ctx(session_id)
        cnn = (ctx.image_slot or {}).get("cnn") or {}
    except Exception:
        return None
    if not cnn.get("available") or cnn.get("is_ood"):
        return None
    name = (cnn.get("top1_class_zh") or "").strip() or "未知"
    conf = float(cnn.get("top1_prob", 0.0))
    conf = max(0.0, min(1.0, conf))
    secondary: List[dict] = []
    for item in (cnn.get("top_k") or [])[1:4]:
        secondary.append(
            {
                "name": item.get("class_zh", ""),
                "confidence": round(float(item.get("probability", 0.0)), 4),
            }
        )
    imgs = list(image_urls or []) or list(fallback.original_image_urls or [])
    return schemas.DiagnosisResultCreate(
        primary_diagnosis=name,
        confidence=round(conf, 4),
        secondary_diagnoses=secondary,
        prevention_advice=PREVENTION_MEASURES.get(name, fallback.prevention_advice),
        treatment_advice=CONTROL_MEASURES.get(name, fallback.treatment_advice),
        follow_up_plan=fallback.follow_up_plan,
        original_image_urls=imgs,
    )


def _predictor_risk_score(entry: Any) -> float:
    """CitrusDiseasePredict.predict 返回值为 {{病名: {{"risk": 0~100, ...}}}}。"""
    if isinstance(entry, dict):
        return float(entry.get("risk", 0) or 0)
    try:
        return float(entry)
    except (TypeError, ValueError):
        return 0.0


def _build_predictor_fallback_result(
    daily_input: dict,
    image_urls: Optional[List[str]],
) -> schemas.DiagnosisResultCreate:
    predictor = CitrusDiseasePredictor()
    predictor.add_daily_data(daily_input)
    risk_results = predictor.predict(daily_input)
    sorted_items = sorted(
        risk_results.items(),
        key=lambda x: _predictor_risk_score(x[1]),
        reverse=True,
    )
    primary_name, primary_info = sorted_items[0]
    primary_risk = _predictor_risk_score(primary_info)
    secondary = [
        {"name": name, "confidence": round(_predictor_risk_score(info) / 100.0, 4)}
        for name, info in sorted_items[1:4]
    ]
    prevention = PREVENTION_MEASURES.get(primary_name, "加强田间管理与监测")
    treatment = CONTROL_MEASURES.get(primary_name, "请咨询当地农技人员进行针对性用药")
    return schemas.DiagnosisResultCreate(
        primary_diagnosis=primary_name,
        confidence=round(primary_risk / 100.0, 4),
        secondary_diagnoses=secondary,
        prevention_advice=prevention,
        treatment_advice=treatment,
        follow_up_plan="7天后复查并根据实地情况调整防控方案。",
        original_image_urls=list(image_urls or []),
    )


async def _merge_prose_advice_into_cnn_archive(
    prose: str,
    cnn_row: schemas.DiagnosisResultCreate,
) -> schemas.DiagnosisResultCreate:
    """
    已有 CNN 主诊断/置信度时，用 LLM 从自然语言长文中抽取防治段落写入 prevention/treatment/follow_up。
    """
    prompt = (
        "从下面柑橘问诊助手的回复中，只抽取可写入病历的三个文本字段。\n"
        "要求：只输出一个 JSON 对象，键为 prevention_advice、treatment_advice、follow_up_plan，"
        "不要 markdown 代码块，不要其它说明。\n"
        "— prevention_advice：农业防治、修剪、施肥、保护天敌、预防类内容合并为一段。\n"
        "— treatment_advice：化学防治、药剂名称与用法、生物防治、施药时机等合并为一段。\n"
        "— follow_up_plan：监测与复查建议，一两句话。\n\n"
        f"助手回复：\n{prose[:14000]}"
    )
    try:
        resp = await get_llm().ainvoke(prompt)
        text = (getattr(resp, "content", None) or str(resp)).strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        adv = json.loads(text)
        if not isinstance(adv, dict):
            return cnn_row
        return schemas.DiagnosisResultCreate(
            primary_diagnosis=cnn_row.primary_diagnosis,
            confidence=cnn_row.confidence,
            secondary_diagnoses=cnn_row.secondary_diagnoses,
            prevention_advice=str(adv.get("prevention_advice") or cnn_row.prevention_advice)[:8000],
            treatment_advice=str(adv.get("treatment_advice") or cnn_row.treatment_advice)[:8000],
            follow_up_plan=str(adv.get("follow_up_plan") or cnn_row.follow_up_plan)[:2000],
            original_image_urls=list(cnn_row.original_image_urls or []),
        )
    except Exception as e:
        print(f"[Archive] 从长文抽取防治字段失败，档案仅保留 CNN 结构化项: {e}")
        return cnn_row


async def _extract_full_diagnosis_via_llm_from_prose(
    prose: str,
    session_id: str,
    image_urls: Optional[List[str]],
    fallback: schemas.DiagnosisResultCreate,
) -> Optional[schemas.DiagnosisResultCreate]:
    """无 CNN 时，完全由 LLM 从长文抽取病历字段（弱于 CNN 路径）。"""
    try:
        ctx = _get_session_ctx(session_id)
        cnn = (ctx.image_slot or {}).get("cnn") or {}
        hint = ""
        if cnn.get("available"):
            hint = f"CNN参考 Top1: {cnn.get('top1_class_zh')} ({float(cnn.get('top1_prob', 0)):.2f})"
    except Exception:
        hint = ""
    prompt = (
        "从下面助手回复中抽取病历字段，只输出一个 JSON，键为：\n"
        'primary_diagnosis, confidence(0~1), secondary_diagnoses(数组元素含name与confidence),\n'
        "prevention_advice, treatment_advice, follow_up_plan。\n"
        "置信度把百分数换算为小数。不要 markdown。\n"
        f"{hint}\n\n助手回复：\n{prose[:14000]}"
    )
    try:
        resp = await get_llm().ainvoke(prompt)
        text = (getattr(resp, "content", None) or str(resp)).strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        data["type"] = "diagnosis_report"
        return _diagnosis_create_from_agent_dict(data, image_urls, fallback)
    except Exception as e:
        print(f"[Archive] 全文 LLM 抽取失败: {e}")
        return None


async def _resolve_diagnosis_for_archive_async(
    session_id: str,
    agent_response: Optional[str],
    image_urls: Optional[List[str]],
    predictor_fallback: schemas.DiagnosisResultCreate,
) -> schemas.DiagnosisResultCreate:
    """
    档案优先级：
    1) 严格 JSON（diagnosis_report 等）
    2) 自然语言长文 + CNN → CNN 定主诊断，LLM 抽防治段落
    3) 自然语言长文、无 CNN → LLM 全字段抽取
    4) 仅 CNN
    5) 环境预测器
    """
    parsed = _parse_diagnosis_payload(agent_response)
    if parsed:
        got = _diagnosis_create_from_agent_dict(parsed, image_urls, predictor_fallback)
        if got:
            return got

    prose = _agent_reply_text(agent_response)
    if prose and _looks_like_diagnosis_prose(prose):
        cnn_got = _diagnosis_create_from_cnn_session(session_id, image_urls, predictor_fallback)
        if cnn_got:
            try:
                return await asyncio.wait_for(
                    _merge_prose_advice_into_cnn_archive(prose, cnn_got),
                    timeout=45.0,
                )
            except asyncio.TimeoutError:
                print("[Archive] 防治字段 LLM 抽取超时(45s)，直接入库 CNN 结论")
                return cnn_got
        try:
            llm_full = await asyncio.wait_for(
                _extract_full_diagnosis_via_llm_from_prose(
                    prose, session_id, image_urls, predictor_fallback
                ),
                timeout=45.0,
            )
            if llm_full:
                return llm_full
        except asyncio.TimeoutError:
            print("[Archive] 全文抽取 LLM 超时(45s)")

    cnn_only = _diagnosis_create_from_cnn_session(session_id, image_urls, predictor_fallback)
    if cnn_only:
        return cnn_only
    return predictor_fallback


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

    # ── 阶段1：短连接读果园/天气，随即关闭 Session。
    #    智能体可能跑数分钟，长时间占用同一 db 连接易导致连接失效，入库失败。
    daily_input: Dict[str, Any] = {}
    orchard: Optional[Orchard] = None
    db_read = SessionLocal()
    try:
        orchard = db_read.query(Orchard).filter(Orchard.id == orchard_id).first()
        weather_data: Optional[Dict[str, Any]] = None
        if orchard and orchard.location_latitude is not None and orchard.location_longitude is not None:
            weather_data = await weather_service.get_weather_by_coordinates(
                float(orchard.location_latitude), float(orchard.location_longitude)
            )
        daily_input = _build_daily_input_from_sources(orchard, weather_data)

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
    finally:
        db_read.close()

    try:
        register_session_orchard(session_id, orchard.id if orchard else orchard_id)
        set_current_session(session_id)
    except Exception:
        pass

    agent_response: Optional[str] = None
    if initial_query or (image_urls and len(image_urls) > 0):
        try:
            user_text = (initial_query or "").strip()
            if image_urls:
                joined_urls = "\n".join(image_urls)
                user_text = (user_text + f"\n\n[图片URL]\n{joined_urls}").strip()
            agent_response = await agent_respond_stream_async(
                session_id, f"\n{user_text}", image_urls or None
            )
            if agent_response:
                await manager.broadcast_to_session(session_id, f"TURN:{turn}|MESSAGE:{agent_response}")
        except Exception as e:
            print(f"[AgentV2] agent 调用异常: {e}")

    predictor_fallback = _build_predictor_fallback_result(daily_input, image_urls)
    try:
        result_create = await asyncio.wait_for(
            _resolve_diagnosis_for_archive_async(
                session_id, agent_response, image_urls, predictor_fallback
            ),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        print("[Archive] 档案解析总超时(90s)，使用 CNN/预测器兜底")
        result_create = _diagnosis_create_from_cnn_session(
            session_id, image_urls, predictor_fallback
        ) or predictor_fallback
    except Exception as e:
        print(f"[Archive] 档案解析异常: {e}")
        result_create = _diagnosis_create_from_cnn_session(
            session_id, image_urls, predictor_fallback
        ) or predictor_fallback

    db_write = SessionLocal()
    try:
        created = crud.diagnosis.upsert_diagnosis_result(
            db_write, session_id=uuid.UUID(session_id), result_data=result_create
        )
        print(
            f"[Archive] 已写入 diagnoses id={created.id} session={session_id} "
            f"primary={result_create.primary_diagnosis!r} conf={result_create.confidence}"
        )
        await manager.broadcast_to_session(
            session_id, f"TURN:{turn}|RESULT_READY:{created.id}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await manager.broadcast_to_session(session_id, f"ERROR:Archive failed: {e}")
    finally:
        db_write.close()


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

    async def continue_session(
        self,
        session_id: str,
        user_input: Optional[str],
        image_urls: Optional[List[str]] = None,
    ) -> None:
        # 多轮：调用智能体生成回复并推送（continue 也可带新图，走独立单图识别）
        try:
            turn = next_turn(session_id)
            await manager.broadcast_to_session(session_id, f"TURN:{turn}|PROGRESS:Running:agent_v2_reply")
            agent_response: Optional[str] = None
            if user_input or (image_urls and len(image_urls) > 0):
                text = (user_input or "").strip()
                if image_urls:
                    joined = "\n".join(image_urls)
                    text = (text + f"\n\n[图片URL]\n{joined}").strip()
                agent_response = await agent_respond_stream_async(
                    session_id, text or "\n", image_urls
                )
                if agent_response:
                    await manager.broadcast_to_session(session_id, f"TURN:{turn}|MESSAGE:{agent_response}")

            # 多轮：JSON 或「诊断长文」均尝试同步档案
            parsed = _parse_diagnosis_payload(agent_response)
            prose_ok = _looks_like_diagnosis_prose(_agent_reply_text(agent_response))
            if parsed or prose_ok:
                db = SessionLocal()
                try:
                    sid = uuid.UUID(session_id)
                    existing = crud.diagnosis.get_diagnosis_result_by_session(db, sid)
                    if existing:
                        fb = schemas.DiagnosisResultCreate(
                            primary_diagnosis=existing.primary_diagnosis,
                            confidence=float(existing.confidence or 0.0),
                            secondary_diagnoses=list(existing.secondary_diagnoses or []),
                            prevention_advice=existing.prevention_advice or "",
                            treatment_advice=existing.treatment_advice or "",
                            follow_up_plan=existing.follow_up_plan or "",
                            original_image_urls=list(existing.original_image_urls or []),
                        )
                    else:
                        fb = schemas.DiagnosisResultCreate(
                            primary_diagnosis="待诊断",
                            confidence=0.0,
                            secondary_diagnoses=[],
                            prevention_advice="请结合田间情况咨询农技人员。",
                            treatment_advice="请咨询当地农技人员。",
                            follow_up_plan="7天后复查。",
                            original_image_urls=list(image_urls or []),
                        )
                    new_data = None
                    if parsed:
                        new_data = _diagnosis_create_from_agent_dict(parsed, image_urls, fb)
                    if new_data is None:
                        new_data = await _resolve_diagnosis_for_archive_async(
                            session_id, agent_response, image_urls, fb
                        )
                    if new_data:
                        row = crud.diagnosis.upsert_diagnosis_result(db, sid, new_data)
                        await manager.broadcast_to_session(
                            session_id, f"TURN:{turn}|RESULT_READY:{row.id}"
                        )
                finally:
                    db.close()
        except Exception as e:
            await manager.broadcast_to_session(session_id, f"ERROR:AgentV2 continue failed: {e}")


agent_v2_service = AgentV2Service()



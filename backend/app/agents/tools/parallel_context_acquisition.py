"""
并行上下文获取节点
==================
论文 5.4.4.4：并行上下文获取节点

优化策略：使用 ThreadPoolExecutor 并发执行三项独立 I/O 任务：
  Task-A  fetch_weather_data      — 调用天气 API（外部网络，约 1-2s）
  Task-B  retrieve_historical_cases — 向量数据库检索（本地 I/O，约 0.2s）
  Task-C  run_fuzzy_inference     — 模糊推理引擎（纯 Python，约 0.05s）

三任务并发后，总延迟 ≈ max(A, B, C) ≈ 1-2s，而非串行的 A+B+C ≈ 2-4s。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import Dict, Any, Optional

from app.core.orchard_state import OrchardState

logger = logging.getLogger(__name__)

# 单任务超时（秒）
_TASK_TIMEOUT = 8.0


# ── Task A: 天气数据 ─────────────────────────────────────────
def _task_weather(state: OrchardState) -> Dict[str, Any]:
    """获取果园所在地实时气象数据"""
    from app.agents.tools.fetch_weather_data import fetch_weather_data
    result = fetch_weather_data(state.copy())
    return result.get("realtime_weather") or {}


# ── Task B: 历史病例检索 ──────────────────────────────────────
def _task_history(state: OrchardState) -> list:
    """从向量数据库检索相似历史病例"""
    from app.agents.tools.retrieve_historical_cases import retrieve_historical_cases
    result = retrieve_historical_cases(state.copy())
    return result.get("historical_cases_retrieved") or []


# ── Task C: 模糊推理 ──────────────────────────────────────────
def _task_fuzzy(weather: Optional[Dict[str, Any]], orchard_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    调用模糊推理引擎，输出 8 种病虫害的环境风险评分。
    输入：天气数据 + 果园档案（物候期）
    """
    try:
        from app.services.fuzzy_engine import CitrusFuzzyEngine
        engine = CitrusFuzzyEngine()

        # 从天气数据提取数值输入
        current = (weather or {}).get("current", {})
        temp = current.get("temperature") or current.get("temp") or 25.0
        humidity = current.get("humidity") or 65.0
        rainfall = current.get("rainfall") or current.get("precipitation", 0.0)

        # 从果园档案获取物候期
        phenology = 0.7  # 默认生长期
        if orchard_profile:
            pheno_str = orchard_profile.get("current_phenology") or orchard_profile.get("phenology", "")
            phenology = _phenology_to_float(pheno_str)

        inputs = {
            "temp": float(temp),
            "humidity": float(humidity),
            "rainfall": float(rainfall),
            "phenology": float(phenology),
        }
        logger.debug(f"[Fuzzy] 输入: {inputs}")
        result = engine.predict(inputs)
        # 简化输出：只保留 risk_score 和 risk_level
        simplified = {
            disease: {
                "risk_score": info.get("risk_score", 0.0),
                "risk_level": info.get("risk_level", "低风险"),
            }
            for disease, info in result.items()
        }
        logger.debug(f"[Fuzzy] 推理完成: {len(simplified)} 种病虫害")
        return simplified

    except Exception as e:
        logger.warning(f"[Fuzzy] 推理失败: {e}")
        return {}


def _phenology_to_float(pheno_str: str) -> float:
    """将物候期描述字符串转换为数值（0~1）"""
    if not pheno_str:
        return 0.7
    mapping = {
        "休眠": 0.1, "冬": 0.1,
        "萌芽": 0.4, "春": 0.45,
        "幼果": 0.6, "花": 0.55, "开花": 0.55,
        "生长": 0.7, "夏": 0.7, "膨大": 0.75,
        "秋": 0.65, "转色": 0.8, "成熟": 0.85,
        "采后": 0.3,
    }
    pheno_lower = pheno_str.lower()
    for keyword, val in mapping.items():
        if keyword in pheno_lower:
            return val
    return 0.7


# ── 主节点函数 ────────────────────────────────────────────────
def parallel_context_acquisition(state: OrchardState) -> OrchardState:
    """
    并行获取三类上下文信息：
      A. 实时天气（外部 API）
      B. 历史病例（向量数据库）
      C. 环境风险（本地模糊推理引擎）
    """
    print("---PARALLEL CONTEXT ACQUISITION (3 tasks concurrent)---")

    need_weather = not state.get("realtime_weather") or state.get("need_reretrieve_weather", False)
    need_history = not state.get("historical_cases_retrieved") or state.get("need_reretrieve_historical_cases", False)

    orchard_profile = state.get("orchard_profile")

    # ── 提交并发任务 ────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}

        if need_weather:
            futures["weather"] = executor.submit(_task_weather, state)
        if need_history:
            futures["history"] = executor.submit(_task_history, state)
        # 模糊推理总是执行（纯本地计算，无副作用）
        # 先提交（天气还没拿到时用默认值，后面可以用已有天气）
        cached_weather = state.get("realtime_weather")
        futures["fuzzy"] = executor.submit(_task_fuzzy, cached_weather, orchard_profile)

        # ── 收集结果 ──────────────────────────────────────
        results = {}
        for key, future in futures.items():
            try:
                results[key] = future.result(timeout=_TASK_TIMEOUT)
                print(f"  ✓ Task [{key}] 完成")
            except FuturesTimeout:
                print(f"  ✗ Task [{key}] 超时（>{_TASK_TIMEOUT}s）")
                results[key] = None
            except Exception as e:
                print(f"  ✗ Task [{key}] 失败: {e}")
                results[key] = None

    # ── 写回状态 ──────────────────────────────────────────
    if need_weather:
        weather = results.get("weather")
        if weather:
            state["realtime_weather"] = weather
        else:
            state["realtime_weather"] = state.get("realtime_weather") or _default_weather()

    if need_history:
        history = results.get("history")
        state["historical_cases_retrieved"] = history if history is not None else []
        state.pop("need_reretrieve_historical_cases", None)

    # 如果天气数据刚拿到，重跑一次模糊推理（用真实天气）
    weather_for_fuzzy = state.get("realtime_weather")
    fuzzy_result = results.get("fuzzy") or {}
    if need_weather and weather_for_fuzzy and results.get("weather"):
        # 用真实天气重算（成本极低，< 10ms）
        fuzzy_result = _task_fuzzy(weather_for_fuzzy, orchard_profile)

    state["environmental_risk"] = fuzzy_result

    # 清理重取标志
    state.pop("need_reretrieve_weather", None)

    print(f"  环境风险评估完成: {len(fuzzy_result)} 种病虫害")
    state["workflow_step"] = "Parallel context acquired (weather + history + fuzzy)"
    return state


def _default_weather() -> Dict[str, Any]:
    return {
        "current": {"temperature": 25.0, "humidity": 70, "rainfall": 0.0, "description": "数据获取失败"},
        "forecast": [],
        "location": {"name": "未知位置"},
        "source": "fallback",
    }

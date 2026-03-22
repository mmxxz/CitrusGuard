"""
置信度计算节点 — 快慢双回路
============================
论文 5.4.4.6：置信度计算节点，实现感知层与推理层的双回路协同。

快通路（Fast-path）条件（全部满足时跳过 LLM）：
  ① 视觉 Top-1 置信度 ≥ FAST_PATH_VISION_THRESHOLD（默认 0.85）
  ② 图像未被判定为 OOD
  ③ 环境风险中该疾病评分 ≥ FAST_PATH_ENV_MIN（默认 30，即不与环境显著冲突）
  ④ 追问次数为 0（首轮无需追问）

慢通路（Slow-path）：
  - 调用 LLM 进行综合评判（原有逻辑）
  - 模糊推理的环境风险作为加权依据
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from app.core.orchard_state import OrchardState
from app.schemas.evidence import EvidenceMatrix, EvidenceGap, ConfidenceResult, EvidenceType

logger = logging.getLogger(__name__)

# ── 快通路阈值配置 ────────────────────────────────────────────
FAST_PATH_VISION_THRESHOLD = 0.85   # 视觉 Top-1 概率门限
FAST_PATH_ENV_MIN = 30.0            # 环境风险评分下限（0~100），低于此视为冲突
FAST_PATH_ENV_CONFLICT_MAX = 20.0   # 若环境给该疾病打分极低（< 此值），则认为视觉-环境冲突


def calculate_confidence_node(state: OrchardState) -> OrchardState:
    """置信度计算节点 — 快慢双回路门控"""
    print("---CALCULATE CONFIDENCE NODE---")

    # ── 获取视觉推理结果 ──────────────────────────────────
    vision_result = state.get("vision_result") or {}
    top1_prob = vision_result.get("top1_prob", 0.0)
    is_ood = vision_result.get("is_ood", False)
    top1_class = vision_result.get("top1_class_zh") or vision_result.get("top1_class", "")
    fuzzy_disease_key = vision_result.get("fuzzy_disease_key")  # 中文病名，用于对照模糊引擎

    # ── 获取环境风险 ──────────────────────────────────────
    environmental_risk = state.get("environmental_risk") or {}
    clarification_count = state.get("clarification_count") or 0

    print(f"[Confidence] 视觉 top1={top1_class}({top1_prob:.2f}), "
          f"OOD={is_ood}, 追问次数={clarification_count}")

    # ── 快通路判断 ────────────────────────────────────────
    fast_path = _can_use_fast_path(
        top1_prob, is_ood, fuzzy_disease_key, environmental_risk, clarification_count
    )

    if fast_path:
        print(f"[Confidence] ✅ 快通路触发 → 直接确诊: {top1_class} ({top1_prob:.1%})")
        state = _apply_fast_path(state, vision_result, top1_class, top1_prob)
        return state

    # ── 慢通路：LLM 综合评判 ──────────────────────────────
    print("[Confidence] 📊 慢通路：调用 LLM 进行综合评判...")
    try:
        state = _slow_path_llm(state, vision_result, environmental_risk)
    except Exception as e:
        logger.error(f"[Confidence] 慢通路失败: {e}", exc_info=True)
        state["confidence_result"] = ConfidenceResult(
            confidence_score=0.3,
            reasoning=f"置信度计算失败: {e}"
        ).model_dump()
        state["need_clarification"] = True
        state["workflow_step"] = "Confidence calculation error"

    return state


# ================================================================
# 快通路实现
# ================================================================

def _can_use_fast_path(
    top1_prob: float,
    is_ood: bool,
    fuzzy_disease_key: Optional[str],
    environmental_risk: Dict[str, Any],
    clarification_count: int,
) -> bool:
    """判断是否满足快通路条件"""
    # 条件①：视觉置信度足够高
    if top1_prob < FAST_PATH_VISION_THRESHOLD:
        print(f"  [FastPath] ✗ 视觉置信度不足 {top1_prob:.2f} < {FAST_PATH_VISION_THRESHOLD}")
        return False

    # 条件②：图像不是 OOD
    if is_ood:
        print("  [FastPath] ✗ OOD 图像，不走快通路")
        return False

    # 条件③：环境不显著冲突（仅当有对应模糊疾病时检查）
    if fuzzy_disease_key and environmental_risk:
        env_info = environmental_risk.get(fuzzy_disease_key, {})
        env_score = env_info.get("risk_score", 50.0)  # 默认中等风险
        if env_score < FAST_PATH_ENV_CONFLICT_MAX:
            print(f"  [FastPath] ✗ 环境冲突: {fuzzy_disease_key} 环境风险={env_score:.1f} < {FAST_PATH_ENV_CONFLICT_MAX}")
            return False

    # 条件④：首轮（未追问过）
    if clarification_count > 0:
        print(f"  [FastPath] ✗ 已追问 {clarification_count} 次，走慢通路综合评判")
        return False

    print("  [FastPath] ✓ 所有快通路条件满足")
    return True


def _apply_fast_path(
    state: OrchardState,
    vision_result: Dict[str, Any],
    top1_class_zh: str,
    top1_prob: float,
) -> OrchardState:
    """快通路：直接设置诊断结果，跳过 LLM 评判"""
    top_k = vision_result.get("top_k", [])
    secondary = [
        {"disease_name": item["class_zh"], "confidence": round(item["probability"], 4)}
        for item in top_k[1:]
    ]

    confidence_result = ConfidenceResult(
        disease_candidates=[
            {"disease_name": item["class_zh"], "match_score": item["probability"]}
            for item in top_k
        ],
        top_candidate={
            "disease_name": top1_class_zh,
            "match_score": top1_prob,
        },
        confidence_score=top1_prob,
        reasoning=(
            f"快通路确诊：视觉模型高置信度识别为【{top1_class_zh}】"
            f"（{top1_prob:.1%}），环境风险无冲突。"
        ),
        evidence_gaps=[],
        differentiation_points=[],
    )

    state["confidence_result"] = confidence_result.model_dump()
    state["working_diagnosis"] = top1_class_zh
    state["confidence_score"] = top1_prob
    state["decision"] = "report"
    state["need_clarification"] = False
    state["clarification_focus"] = ""
    state["fast_path"] = True
    state["workflow_step"] = f"Fast-path confidence: {top1_class_zh} ({top1_prob:.1%})"
    return state


# ================================================================
# 慢通路实现（LLM 综合评判）
# ================================================================

def _slow_path_llm(
    state: OrchardState,
    vision_result: Dict[str, Any],
    environmental_risk: Dict[str, Any],
) -> OrchardState:
    """慢通路：LLM + 模糊推理 + 历史证据综合评判"""
    from app.schemas.disease_profile import DiseaseProfile
    from app.crud.disease_profile import get_disease_profile_crud
    from app.core.database import SessionLocal
    from app.services.llm_service import llm
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    import json

    evidence_matrix_data = state.get("evidence_matrix")
    if not evidence_matrix_data:
        evidence_matrix = EvidenceMatrix()
    else:
        evidence_matrix = EvidenceMatrix(**evidence_matrix_data)

    # 候选病害检索
    db = SessionLocal()
    try:
        disease_crud = get_disease_profile_crud(db)
        candidate_diseases = disease_crud.get_candidates_for_evidence(evidence_matrix, limit=10)
    finally:
        db.close()

    if not candidate_diseases:
        logger.warning("[Confidence] 没有找到候选病害档案")
        state["confidence_result"] = ConfidenceResult(
            confidence_score=0.0,
            reasoning="没有找到候选病害档案"
        ).model_dump()
        state["need_clarification"] = True
        state["fast_path"] = False
        return state

    # 构建发送给 LLM 的上下文
    disease_profiles_json = _build_disease_profiles_json(candidate_diseases)
    evidence_json = _build_evidence_json(evidence_matrix)
    vision_summary = _build_vision_summary(vision_result)
    fuzzy_summary = _build_fuzzy_summary(environmental_risk)

    messages = state.get("messages", [])
    conv_ctx = "\n".join(
        f"{'用户' if m.__class__.__name__ == 'HumanMessage' else 'AI'}: {m.content}"
        for m in messages[-4:]
        if hasattr(m, "content")
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是柑橘病害诊断专家。根据多源证据给出置信度评判。

【评判维度】
- 症状匹配度：主要/次要症状与病害特征的对应程度
- 视觉一致性：视觉模型预测结果与症状描述是否一致
- 环境适配性：模糊推理给出的环境风险是否支持该病害
- 历史支撑度：历史病例和档案是否有相似记录

【置信度规则】
- 0.85~1.0：高度确信，可直接报告
- 0.70~0.85：较确信，少量补充信息即可
- 0.50~0.70：中等，需澄清 1~2 个关键点
- <0.50：不足，需较多补充信息

【输出格式（严格 JSON）】
{
  "disease_candidates": [{"disease_name": "...", "match_score": 0.0, "reasoning": "..."}],
  "top_candidate": {"disease_name": "...", "match_score": 0.0},
  "confidence_score": 0.0,
  "evidence_gaps": ["..."],
  "differentiation_points": ["..."],
  "reasoning": "...",
  "need_clarification": false,
  "clarification_focus": "..."
}"""),
        ("user", """【对话上下文】
{conv_ctx}

【感知层输出（视觉模型）】
{vision_summary}

【推理层输出（模糊推理）】
{fuzzy_summary}

【证据矩阵】
{evidence_json}

【候选病害档案】
{disease_profiles}

请综合以上多源证据进行置信度评判，注意：
1. 当视觉与环境证据一致时，提高对应病害的置信度
2. 当视觉结论与环境风险冲突时，在 reasoning 中说明并降低置信度
3. evidence_gaps 填写明确缺失的诊断信息""")
    ])

    parser = JsonOutputParser()
    chain = prompt | llm | parser

    result = chain.invoke({
        "conv_ctx": conv_ctx,
        "vision_summary": vision_summary,
        "fuzzy_summary": fuzzy_summary,
        "evidence_json": evidence_json,
        "disease_profiles": disease_profiles_json,
    })

    logger.debug(f"[Confidence] LLM 评判结果: {result}")

    # 解析结果
    disease_candidates = result.get("disease_candidates", [])
    top_candidate = result.get("top_candidate")
    if isinstance(top_candidate, str):
        top_candidate = next(
            (c for c in disease_candidates if c.get("disease_name") == top_candidate), None
        )

    evidence_gaps = []
    for i, gap_desc in enumerate(result.get("evidence_gaps", [])):
        if isinstance(gap_desc, str):
            evidence_gaps.append(EvidenceGap(
                evidence_type=EvidenceType.VISUAL.value,
                field_name=f"gap_{i}",
                description=gap_desc,
                importance=max(0.5, 0.9 - i * 0.1),
                suggested_question=f"请提供关于{gap_desc}的更多信息",
            ))

    clarification_focus = result.get("clarification_focus", "")
    if isinstance(clarification_focus, list):
        clarification_focus = " | ".join(clarification_focus)

    confidence_result = ConfidenceResult(
        disease_candidates=disease_candidates,
        top_candidate=top_candidate,
        confidence_score=result.get("confidence_score", 0.0),
        evidence_gaps=evidence_gaps,
        differentiation_points=result.get("differentiation_points", []),
        reasoning=result.get("reasoning", "LLM评判完成"),
    )

    state["confidence_result"] = confidence_result.model_dump()
    state["need_clarification"] = result.get("need_clarification", False)
    state["clarification_focus"] = clarification_focus
    state["fast_path"] = False

    if top_candidate:
        state["working_diagnosis"] = top_candidate.get("disease_name", "")
        state["confidence_score"] = confidence_result.confidence_score

    print(f"[Confidence] 慢通路完成: score={confidence_result.confidence_score:.2f}, "
          f"top={top_candidate.get('disease_name') if top_candidate else 'None'}, "
          f"need_clarification={result.get('need_clarification')}")
    state["workflow_step"] = "Slow-path LLM confidence calculated"
    return state


# ── 辅助函数 ──────────────────────────────────────────────────

def _build_vision_summary(vision_result: Dict[str, Any]) -> str:
    if not vision_result or not vision_result.get("available"):
        desc = vision_result.get("description", "无视觉证据")
        return f"本地视觉模型未启用，多模态描述：{desc}"
    top_k = vision_result.get("top_k", [])
    lines = ["CitrusHVT 本地模型预测："]
    for item in top_k:
        lines.append(
            f"  Top{item['rank']}: {item['class_zh']} ({item['probability']:.1%}) [{item['coarse_class']}]"
        )
    if vision_result.get("is_ood"):
        lines.append("  ⚠️ OOD 警告：该图片超出训练分布")
    return "\n".join(lines)


def _build_fuzzy_summary(environmental_risk: Dict[str, Any]) -> str:
    if not environmental_risk:
        return "模糊推理结果不可用"
    lines = ["环境风险评估（模糊推理引擎，0-100分）："]
    sorted_risks = sorted(environmental_risk.items(), key=lambda x: x[1].get("risk_score", 0), reverse=True)
    for disease, info in sorted_risks[:5]:
        score = info.get("risk_score", 0)
        level = info.get("risk_level", "")
        lines.append(f"  {disease}: {score:.1f}分 [{level}]")
    return "\n".join(lines)


def _build_evidence_json(evidence_matrix: EvidenceMatrix) -> str:
    import json
    return json.dumps({
        "visual": evidence_matrix.visual.model_dump() if evidence_matrix.visual else {},
        "symptom": evidence_matrix.symptom.model_dump() if evidence_matrix.symptom else {},
        "environmental": evidence_matrix.environmental.model_dump() if evidence_matrix.environmental else {},
        "historical": evidence_matrix.historical.model_dump() if evidence_matrix.historical else {},
    }, ensure_ascii=False, indent=2)


def _build_disease_profiles_json(candidate_diseases) -> str:
    import json
    profiles = []
    for d in candidate_diseases:
        profiles.append({
            "disease_name": d.disease_name,
            "category": d.category,
            "key_diagnostic_features": d.key_diagnostic_features,
            "visual_symptoms_checklist": d.visual_symptoms_checklist,
            "environmental_triggers_checklist": d.environmental_triggers_checklist,
        })
    return json.dumps(profiles, ensure_ascii=False, indent=2)

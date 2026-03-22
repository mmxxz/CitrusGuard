"""
图像诊断节点
============
优化策略（论文 5.4.4.3）：
1. 优先调用本地 CitrusHVT 模型（< 0.5s）
   - 输出 Top-K 预测、粗类别、OOD 能量分值
2. 仅在以下情况降级到多模态 LLM（~5-10s）：
   - 本地模型不可用（未安装 PyTorch / 权重未找到）
   - 图像被判定为 OOD（能量分值超阈值）
   - 未上传图片（纯文字描述，用 LLM 解析症状文字）
"""

import logging
from app.core.orchard_state import OrchardState

logger = logging.getLogger(__name__)


def run_image_diagnosis(state: OrchardState) -> OrchardState:
    """图像诊断节点 — 本地模型优先，多模态 LLM 降级"""
    print("---RUN IMAGE DIAGNOSIS---")

    image_urls = state.get("image_urls") or []
    user_query = state.get("user_query", "") or ""

    # ── 无图片：仅记录文字症状描述 ────────────────────────
    if not image_urls:
        print("[ImageDiag] 无图片，跳过视觉推理")
        state["vision_result"] = {
            "available": False,
            "reason": "no_image",
            "description": f"用户文字描述: {user_query[:200]}",
        }
        state["initial_diagnosis_suggestion"] = user_query
        state["workflow_step"] = "Image diagnosis: no image"
        return state

    # ── 尝试本地 CitrusHVT 模型 ────────────────────────────
    try:
        from app.services.vision_engine import vision_engine

        if vision_engine.is_available:
            print(f"[ImageDiag] 本地模型推理 {len(image_urls)} 张图片...")
            result = vision_engine.predict_from_url(image_urls[0])

            if result.get("available"):
                top1 = result.get("top1_class_zh", "未知")
                prob = result.get("top1_prob", 0.0)
                is_ood = result.get("is_ood", False)

                print(f"[ImageDiag] 本地推理完成: {top1} ({prob:.1%})"
                      f"{' [OOD]' if is_ood else ''}")

                # 拼接供后续节点阅读的自然语言摘要
                top_k = result.get("top_k", [])
                summary_lines = [f"视觉模型预测结果（CitrusHVT）："]
                for item in top_k:
                    summary_lines.append(
                        f"  Top{item['rank']}: {item['class_zh']} "
                        f"({item['probability']:.1%}) — {item['coarse_class']}"
                    )
                if is_ood:
                    summary_lines.append("  ⚠️ OOD 警告：该图片超出训练分布，预测可靠性低")

                result["description"] = "\n".join(summary_lines)
                state["vision_result"] = result
                state["initial_diagnosis_suggestion"] = result["description"]
                state["workflow_step"] = f"Image diagnosis: local model ({top1}, {prob:.1%})"

                # OOD 时降级补充多模态 LLM 描述
                if is_ood:
                    print("[ImageDiag] OOD 检测，追加多模态 LLM 补充描述...")
                    llm_desc = _llm_image_describe(image_urls, user_query)
                    result["description"] += f"\n\n多模态 LLM 补充描述：\n{llm_desc}"
                    state["vision_result"] = result
                    state["initial_diagnosis_suggestion"] = result["description"]

                return state
            else:
                print(f"[ImageDiag] 本地推理失败: {result.get('error')}, 降级 LLM")
        else:
            print("[ImageDiag] 本地模型不可用，降级到多模态 LLM")

    except Exception as e:
        logger.warning(f"[ImageDiag] 本地模型异常: {e}")

    # ── 降级：多模态 LLM ───────────────────────────────────
    print("[ImageDiag] 使用多模态 LLM 进行图像分析...")
    llm_desc = _llm_image_describe(image_urls, user_query)

    state["vision_result"] = {
        "available": False,
        "reason": "local_model_unavailable",
        "description": llm_desc,
    }
    state["initial_diagnosis_suggestion"] = llm_desc
    state["workflow_step"] = "Image diagnosis: LLM fallback"
    return state


def _llm_image_describe(image_urls: list, user_query: str) -> str:
    """调用多模态 LLM 对图片进行描述（降级路径）"""
    try:
        import base64, mimetypes, os
        from urllib.parse import urlparse
        from langchain_core.messages import HumanMessage
        from app.services.llm_service import llm

        def _to_safe_url(url: str) -> str:
            """将本地 uploads URL 转为 base64 data URL"""
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ""
                if parsed.scheme in ("http", "https") and host not in (
                    "localhost", "127.0.0.1", "0.0.0.0", "::1"
                ):
                    return url
                path_part = parsed.path or ""
                if path_part.startswith("/uploads/"):
                    from pathlib import Path
                    uploads_dir = Path(__file__).parent.parent.parent / "uploads"
                    local = uploads_dir / path_part[len("/uploads/"):]
                    if local.exists():
                        with open(local, "rb") as f:
                            data = f.read()
                        mime, _ = mimetypes.guess_type(str(local))
                        mime = mime or "image/jpeg"
                        b64 = base64.b64encode(data).decode()
                        return f"data:{mime};base64,{b64}"
            except Exception:
                pass
            return url

        safe_urls = [_to_safe_url(u) for u in image_urls[:3]]
        prompt_text = (
            "请分析这些柑橘图片，从植物病理学角度提供关键观察：\n"
            "1. 病斑/异常颜色/形状\n2. 受影响部位（叶/果/枝）\n"
            "3. 可能的病害或虫害迹象\n4. 简要初步判断\n\n"
            f"用户描述：{user_query}"
        )
        content = [{"type": "text", "text": prompt_text}] + [
            {"type": "image_url", "image_url": {"url": u}} for u in safe_urls
        ]
        msg = HumanMessage(content=content)
        resp = llm.invoke([msg])
        return getattr(resp, "content", "") or str(resp)
    except Exception as e:
        return f"图像分析降级失败（{e}），请根据用户文字描述进行诊断。"

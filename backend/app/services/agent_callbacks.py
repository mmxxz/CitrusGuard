from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from .websocket_service import manager
from .turn_registry import get_turn


class WebSocketCallbackHandler(BaseCallbackHandler):
    """LangChain 回调：将关键状态通过 WebSocket 推送到前端。

    事件前缀：
    - PROGRESS:Running:<stage>
    - THOUGHT:<text> （模型思考/中间推理/工具信息）
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def _send(self, text: str):
        try:
            # 调试：打印发送的事件（截断）
            try:
                print(f"[WS-SEND][session={self.session_id}] {text[:160]}")
            except Exception:
                pass
            turn = get_turn(self.session_id)
            await manager.broadcast_to_session(self.session_id, f"TURN:{turn}|{text}")
        except Exception:
            pass

    # LLM 事件
    async def on_llm_start(self, serialized: Optional[Dict[str, Any]], prompts: Optional[List[str]], **kwargs: Any) -> None:
        await self._send("PROGRESS:Running:llm")
        try:
            if prompts and len(prompts) > 0 and isinstance(prompts[0], str):
                await self._send(f"THOUGHT:Prompt: {prompts[0][:500]}")
        except Exception:
            pass

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if token and token.strip():
            await self._send(f"THOUGHT:{token}")

    async def on_llm_end(self, response, **kwargs: Any) -> None:
        await self._send("PROGRESS:Running:llm_done")

    # Chain 事件
    async def on_chain_start(self, serialized: Optional[Dict[str, Any]], inputs: Optional[Dict[str, Any]], **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or "chain"
        # 统一把最终答案组织阶段标记为 compose，便于前端识别为“开始生成答案”
        if name == "ChatPromptTemplate":
            await self._send("PROGRESS:Running:compose")
        else:
            await self._send(f"PROGRESS:Running:{name}")

    async def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        await self._send("PROGRESS:Running:chain_done")

    # Tool 事件
    async def on_tool_start(self, serialized: Optional[Dict[str, Any]], input_str: Optional[str], **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or "tool"
        await self._send(f"PROGRESS:Running:tool:{name}")
        if input_str:
            await self._send(f"THOUGHT:Tool[{name}] input: {input_str[:500]}")

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        await self._send("PROGRESS:Running:tool_done")
        if output:
            await self._send(f"THOUGHT:Tool output: {str(output)[:500]}")



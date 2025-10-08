from app.agents.graph.graph import app as langgraph_app, workflow
from app.core.orchard_state import OrchardState
import uuid
from app.services.websocket_service import manager
import asyncio
from app.core.database import SessionLocal
from app import crud, schemas
from langchain_core.messages import HumanMessage

class LangGraphService:
    async def start_new_session(self, session_id: str, orchard_id: uuid.UUID, initial_query: str, image_urls: list[str] | None):
        config = {"configurable": {"thread_id": session_id}}
        initial_state = {
            "messages": [HumanMessage(content=initial_query)],
            "user_query": initial_query,
            "image_urls": image_urls,
            "orchard_profile": {"id": orchard_id},
            "session_id": session_id
        }
        asyncio.create_task(self.run_graph(config, initial_state))

    async def continue_session(self, session_id: str, user_input: str):
        config = {"configurable": {"thread_id": session_id}}
        
        # 获取当前状态，确保多轮对话的上下文得以保持
        current_state = langgraph_app.get_state(config)
        if current_state and current_state.values:
            # 从当前状态中提取关键信息
            state_values = current_state.values
            print(f"DEBUG: 继续会话，当前状态键: {state_values.keys()}")
            
            # 确保澄清标记被正确传递
            if state_values.get("clarification_needed"):
                print("DEBUG: 检测到澄清标记，保持多轮对话状态")
                # 只传递新消息，让LangGraph自动添加到现有消息历史
                new_message = HumanMessage(content=user_input)
                asyncio.create_task(self.run_graph(config, {"messages": [new_message]}))
            else:
                # 如果没有澄清标记，按新对话处理
                print("DEBUG: 没有澄清标记，按新对话处理")
                asyncio.create_task(self.run_graph(config, {"user_query": user_input}))
        else:
            # 如果没有现有状态，按新对话处理
            print("DEBUG: 没有现有状态，按新对话处理")
            asyncio.create_task(self.run_graph(config, {"user_query": user_input}))

    async def run_graph(self, config: dict, state: dict):
        session_id = config["configurable"]["thread_id"]
        try:
            async for event in langgraph_app.astream_events(state, config=config, version="v1"):
                kind = event["event"]
                
                if kind == "on_chain_start":
                    node_name = event["name"]
                    if node_name in workflow.nodes:
                        await manager.broadcast_to_session(session_id, f"PROGRESS:Running:{node_name}")

                if kind == "on_chain_end":
                    node_name = event["name"]
                    if node_name == "smart_questioning":
                        node_output = event["data"].get("output", {})
                        if "clarification_question" in node_output:
                            clarification_question = node_output.get("clarification_question")
                            if isinstance(clarification_question, dict):
                                ai_response = schemas.AIResponse(
                                    type="clarification",
                                    content=clarification_question.get("question", "Agent Error: Malformed question object."),
                                    options=clarification_question.get("options", [])
                                )
                                await manager.broadcast_to_session(session_id, f"MESSAGE:{ai_response.json()}")
                                print(f"DEBUG: Sent clarification question from '{node_name}' output for session {session_id}")
                                return

            final_state_snapshot = langgraph_app.get_state(config)
            final_state = final_state_snapshot.values

            if not final_state:
                print(f"ERROR: Final state is empty for session {session_id}")
                await manager.broadcast_to_session(session_id, "ERROR:An unknown error occurred.")
                return

            report_data = final_state.get("final_diagnosis_report")
            if report_data:
                db = SessionLocal()
                try:
                    result_schema = schemas.DiagnosisResultCreate(**report_data)
                    result = crud.diagnosis.create_diagnosis_result(db, session_id=uuid.UUID(session_id), result_data=result_schema)
                    await manager.broadcast_to_session(session_id, f"RESULT_READY:{result.id}")
                except Exception as e:
                    print(f"Error creating diagnosis result in DB: {e}")
                    await manager.broadcast_to_session(session_id, "ERROR:Failed to process diagnosis report.")
                finally:
                    db.close()
                return

            if final_state.get("final_report"):
                final_briefing = final_state.get("final_report", {}).get("briefing", "Could not generate briefing.")
                ai_response = schemas.AIResponse(type="text", content=final_briefing)
                await manager.broadcast_to_session(session_id, f"MESSAGE:{ai_response.json()}")
                return

            print(f"WARNING: Graph for session {session_id} ended without a report or question.")

        except Exception as e:
            print(f"ERROR: Exception in run_graph for session {session_id}: {e}")
            import traceback
            traceback.print_exc()
            await manager.broadcast_to_session(session_id, f"ERROR:An unexpected error occurred: {e}")

langgraph_service = LangGraphService()
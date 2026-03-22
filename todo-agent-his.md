# CitrusGuard Agent 开发待办清单

本文件由 Gemini Agent 创建并维护，用于跟踪 CitrusGuard AI Agent 的开发进度。

**核心架构**: LangGraph "安全核心" + 动态“创意引擎”
**LLM Provider**: OpenRouter
**Primary Model**: `moonshotai/kimi-k2:free`

---

### Phase 1-6: 混合 Agent 架构 (已完成)
- [x] **Phase 1:** 环境设置与核心组件
- [x] **Phase 2:** LangGraph 工具节点实现
- [x] **Phase 3:** LangGraph 图谱构建
- [x] **Phase 4:** 后端 API 与 Agent 对接
- [x] **Phase 5:** Agent 性能与流程优化
- [x] **Phase 6:** 混合 Agent 架构实现

---

### Phase 7: 记忆与持久化 (P2)
- [x] **7.1: 短期记忆 - LangGraph Checkpointer**
- [x] **7.2: 长期记忆 - RAG 知识库构建**
    - [x] 安装 RAG 相关的新依赖：`pgvector` (适配 aysncpg), `langchain-postgres`。
    - [x] 在 `docker-compose.yml` 中确认 PGVector 扩展已启用。
    - [x] 创建 `app/services/vector_store_service.py`，用于初始化和管理 PGVector 向量存储。
    - [x] 创建一个一次性运行的 `scripts/ingest_knowledge_base.py` 脚本，用于读取、处理和嵌入您提供的 `结构化数据.json` 文件，并将其存入数据库。
- [x] **7.3: 长期记忆 - RAG 工具节点实现**
    - [x] 重写 `retrieve_historical_cases.py` 和 `retrieve_treatment_knowledge.py`，移除模拟数据，改为调用 `vector_store_service.py` 进行相似性搜索。
- [x] **7.4: 记忆应用 - 优化 Prompt**
    - [x] 重构 `reasoning_nodes.py` 中的所有 Prompt，使其能够接收并利用从 RAG 系统中检索到的上下文信息 (`context`) 和完整的对话历史 (`messages`)。

### Phase 8: 端到端 RAG 验证
- [ ] **8.1:** 更新 `test_agent.py` 脚本。
- [ ] **8.2:** 添加新的测试用例，专门验证当提出与知识库中特定病害（如“溃疡病”）相关的问题时，Agent 是否能够检索并利用正确的知识来给出回答。

---

## 进展记录
- **2025-09-20:** 完成 Phase 1-6，成功搭建并对接了具备初步智能的混合 Agent 架构。
- **2025-09-20:** 完成 Phase 7.1，为 Agent 集成了 LangGraph Checkpointer 以实现短期记忆。
- **2025-09-20:** 完成 Phase 7.2 & 7.3，成功构建了 RAG 知识库并将其集成到 Agent 的工具节点中。
- **2025-09-20:** 完成 Phase 7.4，优化了 Agent 的核心 Prompt，使其能够利用 RAG 检索到的知识和多轮对话历史。

---

## 问题与解决方案
- **LangGraph 并行错误**: `InvalidUpdateError` 和 `TypeError`。**解决方案**: 重构图谱，使用一个专门的异步节点来管理并行工具的执行，而不是依赖 `add_edge` 的隐式并行。
- **Agent 逻辑死循环**: `AttributeError: 'NoneType' object has no attribute 'get'`。**解决方案**: 调整 Agent 逻辑，使其依赖于中间的 `working_diagnosis` 而不是尚不存在的 `final_diagnosis_report`。
- **API 时序问题**: 前端在后端完成数据库写入前就请求结果，导致 `404`。**解决方案**: 后端在写入完成后通过 WebSocket 发送一个 `RESULT_READY` 信号，前端收到该信号后再去请求结果。
- **Pydantic Validation Error**: `ValidationError` 发生在 `langgraph_service` 中，因为 LLM 的输出缺少 `confidence` 等必需字段。**解决方案**: 更新 `generate_final_report` 的 Prompt，要求 LLM 输出所有必需字段，并创建一个 `DiagnosisResultCreate` schema 来验证 LLM 的输出。
- **ImportError & NameError**: 由于缺少 `__init__.py` 文件或忘记导入模块，导致 `AttributeError` 和 `NameError`。**解决方案**: 为 `crud` 和 `schemas` 包创建 `__init__.py` 文件，并修复所有缺失的导入。
- **ForeignKeyViolation**: 在测试脚本中，由于 API 层的数据库会话创建逻辑被绕过，导致 Agent 无法找到 `session_id`。**解决方案**: 在测试脚本中手动创建 `diagnosis_sessions` 记录，模拟 API 层的行为。
项目整体待办清单（可勾选）

说明：
- 本清单覆盖前端、后端、Agent、数据库四个板块；按优先级分 P0（必须）、P1（重要）、P2（增强）。
- 完成后请在方括号中打勾 [x]，并在旁边标注日期与简短说明。

一、前端（React + TS + Vite + Tailwind）
- [ ] P0 引入 React Router，拆分 `App.tsx` 为 `pages/` 与 `components/`
- [ ] P0 引入 Zustand，设计全局状态（用户/果园/会话/预警/病例）
- [ ] P0 建立 `services/` 与 Axios 客户端（鉴权头、错误拦截、重试策略）
- [ ] P0 定义 `types/` 与后端契约（与 Pydantic 字段名对齐）
- [ ] P0 接入 GET `/orchards/{id}/health_overview`（健康度/天气/AI简报）
- [ ] P0 接入 GET `/orchards/{id}/alerts` + 忽略/前往确认交互
- [ ] P0 文件上传组件 + POST `/upload/image`
- [ ] P0 诊断会话：POST `diagnosis/start` 落地首条 AI 消息
- [ ] P0 诊断续写：POST `diagnosis/{session_id}/continue` + 追问卡片组件
- [ ] P0 WebSocket 进度订阅（进度可视化步骤）
- [ ] P0 结果卡片 + GET `diagnosis/{session_id}/result`
- [ ] P1 病例库：GET `/cases` 列表/筛选；详情占位
- [ ] P1 农事记录表单：POST `/cases/{diagnosis_id}/operation`
- [ ] P1 效果反馈表单：PUT `/operations/{operation_id}/feedback`
- [ ] P1 错误处理与离线：输入缓存、本地暂存、自动重试
- [ ] P1 UI/UX 打磨：Skeleton、空状态、无障碍与移动端优化
- [ ] P1 环境与部署：`.env`、Vercel/Netlify 路由、预览环境
- [ ] P2 基础认证：登录态/JWT 持久化、过期续签、登出入口

二、后端（FastAPI + PostgreSQL + PGVector）
- [x] P0 搭建 FastAPI 项目结构（`main.py`、`api/v1/`、`schemas/`、`crud/`、`services/`） (2025-01-04)
- [x] P0 配置数据库连接与迁移工具（SQLAlchemy + Alembic/Supabase 迁移） (2025-01-04)
- [x] P0 用户认证：注册/登录/JWT 中间件、密码加密、安全策略 (2025-01-04)
- [x] P0 果园管理：POST/GET/PUT/DELETE `/orchards*` (2025-01-04)
- [x] P0 健康度与预警：GET `/orchards/{id}/health_overview`、GET `/orchards/{id}/alerts` (2025-01-04)
- [x] P0 文件上传服务：POST `/upload/image`（Supabase Storage 或 S3/OSS） (2025-01-04)
- [x] P0 诊断工作流 API：`/diagnosis/start`、`/diagnosis/{session_id}/continue`、`/diagnosis/{session_id}/result` (2025-01-04)
- [x] P0 诊断进度 WebSocket：事件模型、心跳与鉴权 (2025-01-04)
- [ ] P1 病例与农事：GET `/cases`、`/cases/{id}`、POST `operation`、PUT `feedback`
- [ ] P1 通知服务：效果评估提醒（7天）、每日简报推送
- [ ] P2 观测与日志：请求追踪、结构化日志、速率限制

三、Agent（LangGraph 安全核心 + 动态创意引擎）
- [x] P0 定义 `OrchardState`（核心上下文）与节点接口 (2025-01-04)
- [x] P0 实现 LangGraph 节点：
  - [x] fetch_orchard_profile (2025-01-04)
  - [x] run_image_diagnosis（Vision 模型占位） (2025-01-04)
  - [x] fetch_weather_data (2025-01-04)
  - [x] retrieve_historical_cases（向量检索占位） (2025-01-04)
  - [x] reflect_and_evaluate_initial / secondary (2025-01-04)
  - [x] initiate_clarification（追问生成） (2025-01-04)
  - [x] retrieve_treatment_knowledge (2025-01-04)
  - [x] generate_final_report (2025-01-04)
  - [x] build_evidence_matrix_node (2025-01-04)
  - [x] process_user_response_node (2025-01-04)
  - [x] calculate_confidence_node (2025-01-04)
  - [x] smart_questioning_node (2025-01-04)
- [x] P0 编译 `core/graph.py` 与暂停/恢复机制（用户输入再进入） (2025-01-04)
- [x] P0 将 `current_progress` 步骤化输出以供前端 UI 显示 (2025-01-04)
- [ ] P1 动态创意引擎：`dynamic_task_executor`（每日简报/宽泛问答）
- [ ] P1 与后端服务对接（天气/知识库/病例检索等工具）

四、数据库与向量库（PostgreSQL + PGVector）
- [x] P0 关系表落库：`users`、`orchards`、`alerts`、`diagnosis_sessions`、`diagnosis_messages`、`diagnoses`、`farm_operations` (2025-01-04)
- [x] P0 建立索引与约束（外键、唯一键、时间索引） (2025-01-04)
- [ ] P1 PGVector：`historical_cases_embeddings`、`knowledge_base_embeddings` 结构与扩展启用
- [ ] P1 数据闭环流水线：从 `diagnoses`+`farm_operations` 聚合生成 embeddings
- [ ] P1 初始知识库导入流程与增量更新策略
- [ ] P2 数据治理：脱敏、归档、备份与恢复演练

五、里程碑（建议节奏）
- 第1周（P0 骨架打通）✅ **已完成** (2025-01-04)
  - 前端：Router+Zustand+services/types；接入 health_overview/alerts；文件上传占位
  - 后端：项目骨架、用户与果园、health_overview/alerts、上传接口 ✅
  - Agent：OrchardState 与核心节点定义，Graph 编译运行到 initiate_clarification ✅
  - DB：关系表创建与基础索引 ✅
- 第2周（P0 诊断闭环）
  - 前端：诊断 start/continue/result、进度 WS、追问与结果卡片、病例只读
  - 后端：诊断 API + WS、病例只读、简单通知队列占位
  - Agent：节点全链路、进度输出、最小可用诊断报告
  - DB：病例与农事写入链路可用
- 第3周（P1 强化与数据闭环）
  - 前端：农事记录/效果反馈表单、错误与离线策略、UI 打磨
  - 后端：农事/反馈、通知（7天提醒）、观测与限流
  - Agent：dynamic_task_executor（日更简报）、知识检索工具融合
  - DB：PGVector 启用、闭环 embedding 生成与检索

更新日志
- 2025-01-04 完成P0后端核心功能：FastAPI项目结构、数据库配置、用户认证、果园管理、诊断工作流API、WebSocket进度推送
- 2025-01-04 完成P0 Agent核心功能：OrchardState定义、所有LangGraph节点实现、图编译与暂停恢复机制、进度输出
- 2025-01-04 完成P0数据库功能：关系表创建、索引约束、Alembic迁移
- 2025-01-04 修复多轮对话中置信度更新问题：消息解析、证据矩阵更新、置信度重新计算
- 2025-09-19 创建 TODO.md（初始化清单）


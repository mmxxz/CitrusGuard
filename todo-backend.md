# CitrusGuard 后端开发待办清单

本文件由 Gemini Agent 创建并维护，用于跟踪 CitrusGuard 后端服务的开发进度。

**核心技术栈**: FastAPI, PostgreSQL, SQLAlchemy, PGVector, LangGraph

---

## 开发环境启动指南

**需要两个独立的终端窗口。**

1.  **终端 1: 启动数据库**
    -   确保 Docker Desktop 正在运行。
    -   在项目根目录 (`/Users/letaotao/Desktop/CitrusGuard`) 下运行:
        ```bash
        docker-compose up -d
        ```

2.  **终端 2: 启动后端 API 服务器**
    -   导航到后端目录:
        ```bash
        cd /Users/letaotao/Desktop/CitrusGuard/backend
        ```
    -   启动开发服务器:
        ```bash
        uvicorn app.main:app --reload
        ```

---

### Phase 1: 项目搭建与核心模型 (P0)
- [x] **1.1:** 初始化 FastAPI 项目，搭建 `app/api/v1/`, `app/schemas/`, `app/crud/`, `app/services/`, `app/core/` 等目录结构。
- [x] **1.2:** 安装核心依赖 (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic`, `passlib`)。
- [x] **1.3:** 配置数据库连接 (`database.py`) 与环境变量 (`.env`)。
- [x] **1.4:** 实现用户模型 (`users`) 与认证：
  - [x] Pydantic Schemas (`schemas/user.py`)
  - [x] SQLAlchemy Model (`models/user.py`)
  - [x] CRUD 操作 (`crud/user.py`)
  - [x] 注册/登录 API (`api/v1/users.py`)
  - [x] JWT 认证与密码服务 (`services/auth_service.py`)
- [x] **1.5:** 实现果园模型 (`orchards`):
  - [x] Pydantic Schemas (`schemas/orchard.py`)
  - [x] SQLAlchemy Model (`models/orchard.py`)
  - [x] CRUD 操作 (`crud/orchard.py`)
  - [x] 果园管理 API (`api/v1/orchards.py`)

### Phase 1.5: 数据库容器化与全模型创建 (P0)
- [x] **1.5.1:** 创建 `docker-compose.yml` 文件，用于一键启动 PostgreSQL + PGVector 数据库服务。
- [x] **1.5.2:** 根据 PRD，创建所有数据表的 SQLAlchemy 模型 (`models/orchard.py`, `models/alert.py`, `models/diagnosis.py`, `models/farm_operation.py` 等)。
- [x] **1.5.3:** 更新 `alembic/env.py` 以导入所有新创建的模型。
- [x] **1.5.4:** 指导用户启动 Docker 数据库。
- [x] **1.5.5:** 生成一个包含所有表结构的 Alembic 迁移脚本。
- [x] **1.5.6:** 将迁移应用到数据库，完成所有表的创建。

### Phase 2: 核心服务 API (P0)
- [x] **2.1:** 实现健康度与预警 API：`GET /orchards/{id}/health_overview` 和 `GET /orchards/{id}/alerts`。
- [x] **2.2:** 实现文件上传服务：`POST /upload/image`，集成云存储。

### Phase 3: AI 诊断工作流 API (P0)
- [x] **3.1:** 实现诊断会话 API：`POST /diagnosis/start` 和 `POST /diagnosis/{session_id}/continue`。
- [x] **3.2:** 实现诊断结果 API：`GET /diagnosis/{session_id}/result`。
- [x] **3.3:** 搭建 WebSocket 端点，用于实时推送诊断进度。

### Phase 3.5: API 集成与验证 (P0)
- [x] **3.5.1:** 扩展 `test_api.py` 以覆盖所有已实现的端点，确保端到端的功能完整性和正确性。

---

## 进展记录
- **2025-09-19:** 完成 Phase 1.1-1.4，后端项目骨架与用户认证模块搭建完毕。
- **2025-09-19:** 完成 Phase 1.5，通过 Docker 和 Alembic 成功初始化了完整的数据库 schema。
- **2025-09-19:** 完成 Phase 1.5，实现了完整的果园管理 CRUD API。
- **2025-09-19:** 完成 Phase 2.1，实现了健康度和预警的 API 端点（使用模拟数据）。
- **2025-09-19:** 完成 Phase 2.2，实现了本地文件上传服务。
- **2025-09-19:** 完成 Phase 3.1，实现了诊断会话的启动与续写 API（使用模拟 Agent）。
- **2025-09-19:** 完成 Phase 3.5，通过测试脚本验证了核心 API 链路的正确性。
- **2025-09-19:** 完成 Phase 3.2，实现了诊断结果的创建与获取 API。
- **2025-09-19:** 完成 Phase 3.3，实现了用于实时进度更新的 WebSocket 服务。
- **2025-09-20:** 修复了所有导入错误和测试问题，包括 schema 导入、图片上传验证、异步任务数据库会话和果园删除约束问题。所有 API 测试现在完全通过。

---

## 问题与解决方案
- **CORS Error**: 前端无法访问后端 API，因为缺少 CORS 头。**解决方案**: 在 `main.py` 中添加 FastAPI 的 `CORSMiddleware`。
- **ProxyError**: `requests` 库因系统代理配置无法连接本地服务。**解决方案**: 在 `test_api.py` 中为 `requests` 调用明确禁用代理。
- **Pydantic V1->V2 Migration**: FastAPI 启动失败，因为 Pydantic Schema 中使用了过时的 `orm_mode = True`。**解决方案**: 更新为 `from_attributes = True`。
- **IndentationError**: FastAPI 启动失败，因为 `api/v1/users.py` 中存在缩进错误。**解决方案**: 修正代码缩进。
- **AttributeError**: FastAPI 启动失败，因为 `crud` 包下的模块未被正确导入。**解决方案**: 在 `app/crud/__init__.py` 文件中明确导入所有 CRUD 模块。
- **pydantic-settings missing**: `alembic revision` 命令失败，因为 `pydantic_settings` 未安装。已将其添加到 `requirements.txt` 并安装。
- **DB Connection Refused**: `alembic revision` 命令失败，因为无法连接到 PostgreSQL。原因是本地尚未安装和配置数据库。**解决方案**: 切换到 Docker 进行数据库管理。
- **NameError in Model**: `alembic revision` 失败，因为 SQLAlchemy 模型中缺少 `Float` 类型的导入。已在 `models/diagnosis.py` 中修复。
- **ImportError: DiagnosisSession**: 测试脚本失败，因为 `app/schemas/__init__.py` 中导入了不存在的类。**解决方案**: 更新导入配置，正确导入所有 schema 类。
- **Missing Schema Classes**: 多个 API 端点失败，因为缺少必要的 schema 类导入。**解决方案**: 在 `schemas/__init__.py` 中添加所有缺失的类导入。
- **Image Upload Validation**: 测试脚本中图片上传失败，因为创建的是无效的图片文件。**解决方案**: 使用 PIL 库创建有效的 JPEG 文件。
- **Async Task Database Session**: 异步诊断工作流程失败，因为使用了已关闭的数据库会话。**解决方案**: 在异步任务中创建独立的数据库会话。
- **Orchard Deletion Constraint Violation**: 删除果园时违反外键约束，因为相关诊断数据未被正确清理。**解决方案**: 在删除果园前先删除所有相关的诊断会话、消息和结果。
# CitrusGuard 系统架构分析

本文档旨在分析 CitrusGuard 项目的前后端系统架构、交互逻辑和接口完整性，为后续的开发和维护提供一致性参考。

## 1. 后端 (Backend) 架构

后端是一个基于 **Python** 和 **FastAPI** 框架构建的现代 Web 服务，其核心特色是集成了一个由 **LangGraph** 驱动的复杂 AI 代理系统，现已演进为基于结构化证据的智能诊断系统。

### 1.1. 技术栈

-   **Web 框架**: FastAPI
-   **数据库 ORM**: SQLAlchemy
-   **数据库迁移**: Alembic
-   **数据库**: PostgreSQL (从配置文件推断)
-   **AI 与语言模型**:
    -   `langchain` & `langgraph`: 用于构建和运行具有状态的、多步骤的 AI 代理。
    -   `sentence-transformers`: 用于文本嵌入，支持向量数据库的语义搜索。
    -   `paraphrase-multilingual-MiniLM-L12-v2`: 多语言文本嵌入模型
-   **数据校验**: Pydantic
-   **认证**: JWT (JSON Web Tokens) + OAuth2PasswordBearer
-   **外部 API 集成**: OpenWeatherMap API (实时天气数据)

### 1.2. 架构模式

后端采用经典的分层架构，代码结构清晰，职责分离：

-   **`models/`**: 定义了 SQLAlchemy 的数据表模型（如 `User`, `Orchard`, `Diagnosis`, `DiseaseProfile`），与数据库结构直接对应。新增疾病档案模型支持详细的疾病特征描述。
-   **`schemas/`**: 定义了 Pydantic 的数据模型，用于 API 请求和响应的数据校验、序列化和文档生成。新增证据矩阵(evidence matrix)和疾病档案相关的复杂模式定义。
-   **`crud/`**: (Create, Read, Update, Delete) 包含了与数据库直接交互的函数，将 SQLAlchemy 查询逻辑封装起来。新增疾病档案的完整CRUD操作。
-   **`api/v1/`**: API 路由层。使用 FastAPI 的 `APIRouter` 定义了所有 HTTP 端点（如用户、果园、诊断等），负责处理请求、调用服务并返回响应。
-   **`services/`**: 业务逻辑层。封装了更复杂的操作，如用户认证 (`auth_service`)、AI 代理的调用 (`langgraph_service`)、向量数据库操作 (`vector_store_service`)、WebSocket 通信 (`websocket_service`) 和新增的天气服务 (`weather_service`, `sync_weather_service`)。
-   **`core/`**: 包含应用的核心配置 (`config.py`)、数据库连接设置 (`database.py`) 和果园状态管理 (`orchard_state.py`)。
-   **`agents/`**: **项目核心特色**。这里定义了 AI 代理的行为，现已演进为基于结构化证据的诊断系统。
    -   **`graph/`**: 使用 `langgraph` 构建了一个状态机 (`StateGraph`)。这个图定义了 AI 诊断的完整流程，包括意图识别、证据矩阵构建、置信度计算、多轮澄清和生成最终报告等步骤。新增证据矩阵构建节点和置信度计算节点。
    -   **`tools/`**: 定义了 AI 代理可以使用的工具，例如获取实时天气数据、查询历史病例、运行图像诊断等。天气工具已从模拟数据改为真实API调用。

### 1.3. AI 代理核心 (LangGraph)

AI 代理已从简单的LLM驱动演进为基于结构化证据的智能诊断系统，其工作流在 `agents/graph/graph.py` 中定义：

1.  **入口点 (`intent_recognition`)**: 接收用户查询，通过 LLM 判断用户意图（诊断 `diagnosis`、询问治疗方案 `treatment` 或通用问答 `general_qa`）。
2.  **证据矩阵构建 (`build_evidence_matrix`)**: 新增节点，将用户输入、图像分析结果转化为结构化的证据矩阵，包含视觉证据、症状证据、环境证据和历史证据四个维度。
3.  **置信度计算 (`calculate_confidence`)**: 新增节点，使用非LLM的数学方法基于证据矩阵和疾病档案计算诊断置信度，提供客观的置信评分。
4.  **条件路由**: 根据意图和证据完整性将流程导向不同的分支。
    -   **诊断分支**: 依次执行证据矩阵构建、置信度计算、并行获取实时天气和历史病例、基于证据缺口分析决定是否需要澄清或直接进入报告生成。
    -   **通用问答分支 (`dynamic_engine`)**: 启动一个动态计划引擎，该引擎能根据问题自行规划步骤（如先查天气，再查历史，最后生成简报）。
5.  **多轮交互优化**: 基于证据缺口分析生成澄清问题，使问题更具针对性和诊断价值。
6.  **状态管理**: 整个流程通过一个增强的 `OrchardState` TypedDict 在不同节点间传递和更新状态，包含证据矩阵和置信度信息。
7.  **异步与实时通信**: 诊断流程是异步执行的，并通过 WebSocket (`websocket_service`) 将每一步的进展 (`PROGRESS:Running:step_name`) 和最终结果实时推送给前端。

## 2. 前端 (Frontend) 架构

前端是基于 **React** 和 **Vite** 构建的现代化单页应用 (SPA)，现已发展为功能完整的农场管理系统界面。

### 2.1. 技术栈

-   **核心框架**: React 18
-   **构建工具**: Vite
-   **语言**: TypeScript
-   **路由**: `react-router-dom` (v7.9.1)
-   **状态管理**: Zustand (v5.0.8)
-   **HTTP 请求**: Axios (v1.12.2)
-   **样式**: Tailwind CSS
-   **图标**: `lucide-react`
-   **模态框**: `react-modal` (新增，用于病例和诊断交互)
-   **实时数据库**: `@supabase/supabase-js` (已集成，备用)

### 2.2. 架构模式

前端代码结构同样清晰，按功能和职责划分，现已扩展为完整的农场管理系统：

-   **`pages/`**: 定义了应用的主要页面/视图，现已完整实现所有核心功能：
    -   `Dashboard`: 主控制台，集成风险预警和病例管理入口
    -   `Diagnosis`: 诊断页面，新增农事操作记录模态框
    -   `Cases`: **新增并完整实现**，病例档案管理，支持详细查看和农事操作记录
    -   `Login/Register/OrchardSetup`: 用户认证和果园设置流程
-   **`components/`**: 包含了可在多个页面中复用的 UI 组件：
    -   `Layout`: 底部导航布局，新增病例档案导航项
    -   `FarmOperationForm`: **新增**，农事操作记录表单组件
    -   `Spinner`, `ResultCard`, `ClarificationCard`: 诊断交互组件
-   **`services/`**: 负责与外部服务通信：
    -   **`apiClient.ts`**: 使用 Axios 封装了所有对后端 RESTful API 的请求。新增 `getCaseDetail` 和 `recordFarmOperation` 函数，支持完整的病例管理功能。
    -   **`ws.ts`**: 封装了 WebSocket 客户端逻辑，用于处理来自后端的实时消息。
    -   **`mock.ts`**: 提供完整的模拟数据，支持开发和测试。
-   **`lib/store.ts`**: 使用 Zustand 定义了全局状态存储。管理用户信息、当前果园信息，并提供 `fetchInitialData` 方法。
-   **`types/`**: 存放了整个应用的 TypeScript 类型定义，新增 `FarmOperationCreate` 接口和增强的病例相关类型。

## 3. 前后端交互分析

### 3.1. 认证流程

1.  **注册 (`/register`)**: 前端提交邮箱和密码，后端创建新用户。
2.  **登录 (`/login`)**: 前端提交邮箱和密码，后端验证凭据，成功后返回一个 JWT `access_token`。
3.  **Token 存储**: 前端将 `access_token` 存储在 `localStorage` 中。
4.  **认证请求**: `apiClient.ts` 中的 Axios 拦截器会自动从 `localStorage` 读取 Token，并将其添加到之后所有请求的 `Authorization` 头中。
5.  **路由保护**: 前端使用 `AuthWrapper` 组件保护需要登录才能访问的路由。

### 3.2. 核心诊断流程 (闭环分析)

这是一个完整的闭环交互：

1.  **发起诊断**: 用户在 `Diagnosis` 页面输入问题或上传图片。前端调用 `startDiagnosis` API。
2.  **后端处理**: 后端 `diagnosis.py` 中的 `/start` 接口创建一个诊断会话 (Session)，并异步启动 LangGraph 代理任务。
3.  **实时反馈**:
    -   前端 `ws.ts` 连接到该会话的 WebSocket 端点。
    -   LangGraph 在执行每个节点时，后端通过 WebSocket 发送 `PROGRESS:` 消息，前端可以据此显示 AI 正在工作的状态。
4.  **多轮交互**:
    -   如果 AI 代理需要更多信息，它会生成一个澄清问题，并通过 WebSocket 发送 `MESSAGE:` 消息。
    -   前端 `Diagnosis` 页面接收到该消息，渲染 `ClarificationCard` 组件。
    -   用户点击选项，前端调用 `continueDiagnosis` API 将用户的回答发送回后端。
    -   后端继续执行 LangGraph 流程。
5.  **返回结果**:
    -   当 LangGraph 流程结束并生成最终报告后，后端将结果存入数据库，并通过 WebSocket 发送 `RESULT_READY:` 消息。
    -   前端收到此消息后，调用 `getDiagnosisResult` API 获取完整的诊断报告。
    -   前端渲染 `ResultCard` 组件展示报告。

### 3.3. 接口对应性检查

| 前端 apiClient 函数          | HTTP 方法 | 路径                                                     | 后端 API 路由 (`@router.*`)                  | 匹配状态 |
| ---------------------------- | --------- | -------------------------------------------------------- | -------------------------------------------- | -------- |
| `register`                   | `POST`    | `/users/register`                                        | `users.py`                                   | ✅ 匹配  |
| `login`                      | `POST`    | `/users/login/token`                                     | `users.py`                                   | ✅ 匹配  |
| `getCurrentUser` / `getUser` | `GET`     | `/users/me`                                              | `users.py`                                   | ✅ 匹配  |
| `createOrchard`              | `POST`    | `/orchards/`                                             | `orchards.py`                                | ✅ 匹配  |
| `getMyOrchards`              | `GET`     | `/orchards/`                                             | `orchards.py`                                | ✅ 匹配  |
| `getOrchard`                 | `GET`     | `/orchards/{id}`                                         | `orchards.py`                                | ✅ 匹配  |
| `updateOrchard`              | `PUT`     | `/orchards/{id}`                                         | `orchards.py`                                | ✅ 匹配  |
| `getOrchardHealth`           | `GET`     | `/orchards/{id}/health_overview`                         | `orchards.py`                                | ✅ 匹配  |
| `getOrchardAlerts`           | `GET`     | `/orchards/{id}/alerts`                                  | `orchards.py`                                | ✅ 匹配  |
| `uploadImage`                | `POST`    | `/upload/image`                                          | `upload.py`                                  | ✅ 匹配  |
| `startDiagnosis`             | `POST`    | `/orchards/{id}/diagnosis/start`                         | `diagnosis.py`                               | ✅ 匹配  |
| `continueDiagnosis`          | `POST`    | `/orchards/{id}/diagnosis/{sid}/continue`                | `diagnosis.py`                               | ✅ 匹配  |
| `getDiagnosisResult`         | `GET`     | `/orchards/{id}/diagnosis/{sid}/result`                  | `diagnosis.py`                               | ✅ 匹配  |
| `getCases`                   | `GET`     | `/orchards/{id}/cases`                                   | `orchards.py`                                | ✅ 匹配  |
| `getCaseDetail`              | `GET`     | `/orchards/{id}/cases/{diagnosis_id}/detail`             | `orchards.py`                                | ✅ 新增  |
| `recordFarmOperation`        | `POST`    | `/orchards/{id}/cases/{diagId}/operation`                | `orchards.py`                                | ✅ 匹配  |
| **WebSocket**                | `WS`      | `/orchards/{id}/diagnosis/{sid}/ws`                      | `diagnosis.py`                               | ✅ 匹配  |

### 3.4. 完整性与逻辑性评估

-   **逻辑性**: 系统的核心交互逻辑（认证、诊断、数据展示）是完整且闭环的。用户从登录到获取诊断结果的整个流程设计合理，通过 WebSocket 提供的实时反馈也提升了用户体验。新增的证据驱动诊断流程使诊断更加科学和可靠。
-   **完整性**:
    -   **真实数据集成**: 后端天气数据已从模拟数据升级为真实的 OpenWeatherMap API 集成
    -   **病例管理**: 前端 `Cases` 页面已完整实现，支持详细的病例查看和农事操作记录
    -   **农事操作**: 完整的农事操作记录功能，支持多种操作类型（喷药、施肥、灌溉、修剪等）
    -   **证据系统**: 新增结构化证据收集和置信度评分系统，提供更科学的诊断依据

## 4. 总结与建议

### 4.1. 总结

CitrusGuard 项目已从原型系统演进为功能完整的智能农业诊断平台。

-   **后端** 实现了从简单 LLM 驱动到结构化证据驱动的重要升级，通过疾病档案系统、证据矩阵分析和数学置信度计算，提供了更加科学和可靠的诊断能力。真实天气数据的集成标志着系统开始与实际农业生产数据对接。
-   **前端** 发展为功能完整的农场管理系统界面，新增的病例档案管理和农事操作记录功能使系统具备了完整的农业生产管理闭环。界面设计保持了高可用性和现代化特征。
-   **前后端交互** 在保持原有实时通信优势的基础上，新增了完整的病例管理流程，支持从诊断到治疗再到效果评估的完整闭环管理。

系统现已具备：
✅ **智能诊断**: 基于结构化证据的 AI 诊断系统
✅ **实时通信**: WebSocket 实时反馈机制
✅ **病例管理**: 完整的病例档案系统
✅ **农事记录**: 详细的农事操作跟踪
✅ **效果评估**: 治疗效果量化评估
✅ **数据集成**: 真实天气数据接入
✅ **多语言支持**: 多语言文本嵌入能力

### 4.2. 建议

1.  **扩展数据集成**: 接入更多农业数据源（土壤检测、病虫害监测、卫星遥感等），丰富证据矩阵的维度
2.  **优化诊断算法**: 基于积累的病例数据，持续优化置信度计算模型和疾病匹配算法
3.  **增强移动端**: 考虑开发移动端应用，方便农场工人在田间实时记录操作和查看诊断结果
4.  **数据分析**: 增加农场运营数据分析功能，提供种植建议和趋势预测
5.  **专家系统**: 建立专家知识库，支持更复杂的农业咨询和决策支持
6.  **多语言界面**: 利用已有的多语言模型能力，提供多语言用户界面支持

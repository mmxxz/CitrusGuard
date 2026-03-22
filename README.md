# CitrusGuard: 您的柑橘果园AI守护者 🍊🤖

**一个面向柑橘种植领域的、基于大语言模型（LLM）和多智能体（Multi-Agent）协作的智能诊断与决策支持系统。**

---

### 🎯 项目背景：解决什么问题？

传统的柑橘种植业面临诸多挑战：病虫害识别不及时、依赖人工经验、天气变化应对迟缓、缺乏数据驱动的精细化管理。这些问题导致了产量下降和资源浪费。"CitrusGuard"旨在通过AI技术，为果园管理者提供一个智能“大脑”，解决以下核心痛点


**诊断难**
如何快速准确地识别柑橘的病虫害？
**决策慢**
如何根据实时天气和果园状态，做出最优的农事操作（如灌溉、施肥、打药）决策？
**信息杂**
如何从海量的农业知识中，获取针对我这片果园的、个性化的建议？

### ✨ 解决方案：CitrusGuard如何工作？

CitrusGuard 的核心是基于 `LangChain` 构建的 **AI Agent**。它并非一个简单的问答机器人，而是由一个**精心设计的系统提示词 (System Prompt)** 驱动的智能执行体。这个提示词中定义了三大核心工作流（**诊断、预测、维护**），指导 Agent 如何根据用户意图，按预设逻辑顺序调用一系列“专家工具”来解决复杂问题。

```mermaid
flowchart TD
    subgraph UC["用户端 User Client"]
        User[用户]
    end

    subgraph FE["前端 Frontend"]
        WebApp["React SPA Vite 用户界面与状态管理"]
    end

    subgraph BE["后端 Backend FastAPI"]
        APIGateway["API 层 REST"]
        ServiceLayer["服务层 核心业务"]
        Agent["AI Agent LangChain 诊断预测维护"]
        Tools["Agent Tools 视觉知识库数据库"]
        CRUDLayer["数据访问层 SQLAlchemy CRUD"]
    end

    subgraph DM["数据与模型 Data and Models"]
        Database[("PostgreSQL")]
        FileStorage["文件存储 上传图片"]
        MLModel["嵌入与视觉模型"]
    end

    User -->|1 浏览器访问| WebApp
    WebApp -->|2 API 请求 HTTPS| APIGateway
    APIGateway -->|3 路由到服务| ServiceLayer
    ServiceLayer -->|4 调用 Agent 诊断等| Agent
    ServiceLayer -->|5 直接 CRUD| CRUDLayer
    Agent -->|6 使用工具| Tools
    Tools -->|7 经 CRUD 取数| CRUDLayer
    Agent -->|8 语义与向量| MLModel
    CRUDLayer -->|9 读写| Database
    APIGateway -->|文件上传| FileStorage

    classDef frontend fill:#e0f7fa,stroke:#00796b
    classDef backend fill:#fff3e0,stroke:#f57c00
    classDef data fill:#f1f8e9,stroke:#558b2f
    classDef userclient fill:#fce4ec,stroke:#c2185b

    class User userclient
    class WebApp frontend
    class APIGateway,ServiceLayer,Agent,Tools,CRUDLayer backend
    class Database,FileStorage,MLModel data
```

### 核心功能

*   **📸 多模态诊断**：用户可上传柑橘叶片或果实的图片。Agent 能够调用多模态大模型（`moonshot-v1-8k-vision-preview`），将本地图片转为 data URL 进行分析，直接从图像中提取病斑、虫害等关键视觉特征。

*   **🧠 混合检索知识库 (Hybrid RAG)**：内置柑橘种植专业知识库。系统采用混合检索策略，结合了 `BM25` 稀疏检索的关键词匹配能力和 `BGE` 嵌入模型的语义理解能力。同时，通过自定义的 **农业术语归一化** 引擎，进一步提升了检索的精准度与召回率。

*   **🛠️ 结构化工具链调用 (Tool Chains)**：Agent拥有一个强大的工具箱，并能以工作流的形式将它们串联起来，模拟专家解决问题的完整流程：
    *   **诊断链**: `知识库检索` -> `三元交叉验证` -> `置信度计算` -> `生成报告`或`生成追问`。
    *   **预测链**: `获取天气` -> `查询土壤` -> `调用病虫害风险预测模型` -> `生成综合建议`。
    *   **果园档案查询**: 查询数据库中特定果园的历史数据（如过往病害、施肥记录），进行个性化分析。

*   **📝 多轮对话与案例管理**：系统能够理解上下文，进行多轮对话。每一次的诊断和处理过程都会被记录下来，形成一个完整的“病例”，方便追踪和复盘。

*   **🤖 工作流驱动的智能体 (Workflow-Driven Agent)**：系统的核心是一个由**系统提示词**定义的智能 Agent。它不依赖复杂的状态机，而是通过理解提示词中描述的**诊断、预测、维护**三大工作流，自主地、按逻辑地编排和执行工具链，高效地模拟专家解决问题的完整流程。

### 🖥️ 前端应用概览

前端应用是一个使用 `React`, `Vite`, 和 `TypeScript` 构建的现代化单页应用 (SPA)，为用户提供了与后端 AI 智能体交互的直观界面。

#### 主要功能模块

1.  **智能诊断对话 (Chat Interface)**
    *   用户可以通过一个类似聊天机器人的界面，与 `CitrusGuard` Agent 进行实时对话。用户可以描述问题、上传病害图片，并接收 Agent 的提问和最终诊断报告。
    *   
        ![诊断对话界面](screen/智能对话png.png)

2.  **案例管理与历史追溯 (Case Management)**
    *   每一次诊断会话都会被保存为一个独立的“案例”。用户可以随时查看历史诊断记录，包括当时的图片、对话流程、以及最终的专家建议，方便进行效果追踪和复盘。
    *   
        ![案例列表界面](screen/案例管理.png)

3.  **果园档案管理 (Orchard Profile)**
    *   用户可以创建和维护自己果园的数字档案，记录果园的基本信息、主要柑橘品种、历史病害等。这些信息将作为 Agent 进行个性化诊断的重要依据。
    *   
        ![果园档案界面](screen/园档案管理.png)

4.  **总览看板(Dashboard)**
     - 健康度、天气、提醒红点等即时呈现
     - 显示 AI 每日简报
    *   
     - ![总览看板](screen/总览看板.png)

5. **风险预警中心(Alerts)**
     - 风险分布 Top3 以色条/百分比可视化；列表按严重程度高亮。
    *  
     - ![风险预警](screen/风险预警看板.png)


### 📖 使用说明

#### 环境要求

* **Python** 3.11 及以上  
* **Node.js** 18 及以上（前端）  
* **Docker**（推荐）：用于启动带 **pgvector** 的 PostgreSQL  
* **Git LFS**：若仓库包含大体积权重（如 `backend/models/convnext/best.pt`），克隆前请执行 `git lfs install`  

#### 1. 获取代码

```bash
git lfs install   # 若使用 LFS 跟踪的权重文件
git clone https://github.com/mmxxz/CitrusGuard.git
cd CitrusGuard
```

#### 2. 启动数据库

在仓库根目录执行（与 `docker-compose.yml` 中账号库名一致）：

```bash
docker compose up -d
```

默认连接串为：`postgresql://user:password@localhost:5432/citrusguard`，需与 `backend/.env` 里 `DATABASE_URL` 一致。

#### 3. 配置并启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 再编辑 .env 填入密钥与数据库地址
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

说明：

* 请在 **`backend` 目录下** 运行 `uvicorn`，以便上传目录、静态资源等相对路径正确。  
* 在 `.env` 中至少配置实际使用的 **大模型 API**（如 `OPENROUTER_API_KEY` 或 `DEEPSEEK_API_KEY` 等，与当前路由/服务商一致即可）。  
* **向量嵌入**：默认可在 `.env` 中设置 `EMBEDDING_MODEL_NAME`；不设置时可用 Hugging Face 模型 ID（首次运行会下载权重，需能访问外网），或改为本机模型目录的绝对路径。  
* **本地 CitrusHVT 图像推理**：将 `best.pt` 置于 `backend/models/convnext/`，并自行安装 **PyTorch**、**timm** 等（`requirements.txt` 未强制包含时按环境补齐）。未安装或缺少权重时，系统会按代码逻辑降级（例如走多模态 LLM）。  
* 天气类能力需配置 `OPENWEATHER_API_KEY`。  
* 诊断后端可在 `.env` 中设置 `DIAGNOSIS_AGENT_BACKEND`：`agent_v2`（默认）或 `langgraph`。

自检：

* 接口根路径：<http://127.0.0.1:8000/>  
* OpenAPI 文档：<http://127.0.0.1:8000/docs>  

#### 4. 启动前端

```bash
cd project
npm install
npm run dev
```

默认通过环境变量 **`VITE_API_BASE_URL`** 指向后端（未设置时为 `http://127.0.0.1:8000`）。若后端地址或端口不同，可在 `project` 下新建 `.env.local`：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

浏览器访问：<http://localhost:5173>（与后端 CORS 中允许的本地开发源一致）。

#### 5. 生产构建（可选）

```bash
cd project
npm run build
npm run preview    # 本地预览构建结果，注意配置好正式环境的 API 地址与 CORS
```

后端 CORS 当前默认允许 `localhost:5173`；若部署域名或端口变化，请在 `backend/app/main.py` 的 `origins` 中补充。


### 🚀 技术栈

*   **后端**:
    *   **语言**: Python 3.11
    *   **Web框架**: FastAPI
    *   **AI Agent框架**: LangChain (使用 `Tool Calling Agent` 和 `AgentExecutor`)
    *   **大语言模型 (LLM)**: 支持 `DeepSeek` 和 `moonshot-v1-8k-vision-preview` 等多种模型，可灵活配置
    *   **数据库**: PostgreSQL (通过 SQLAlchemy 操作)
    *   **数据库迁移**: Alembic
    *   **知识库检索**: 混合检索 (`BM25` + `BGE` 嵌入模型)
*   **前端**:
    *   **框架**: React, Vite
    *   **语言**: TypeScript
    *   **UI库**: Tailwind CSS
*   **部署**: Docker, Docker Compose
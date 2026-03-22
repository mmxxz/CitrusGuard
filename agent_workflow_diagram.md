# 柑橘病虫害智能Agent工作机制流程图

## 系统架构概览

```mermaid
graph TB
    A[用户输入] --> B{意图识别}
    B -->|诊断意图| C[诊断流程]
    B -->|预测意图| D[预测流程]
    B -->|维护意图| E[维护流程]
    B -->|其他| F[通用对话]
    
    C --> G[诊断结果]
    D --> H[预测报告]
    E --> I[维护建议]
    F --> J[文本回复]
```

## 详细工作流程

### 1. 诊断流程 (Diagnosis Workflow)

```mermaid
graph TD
    A[用户输入症状描述/上传图片] --> B[获取果园上下文]
    B --> C[知识库检索 Top-3候选]
    C --> D[三维交叉验证评分]
    D --> E[计算置信度]
    E --> F{置信度判断}
    F -->|高置信度| G[生成最终诊断报告]
    F -->|低置信度| H[生成澄清问题]
    H --> I[用户回答]
    I --> C
    G --> J[输出诊断结果]
```

### 2. 预测流程 (Prediction Workflow)

```mermaid
graph TD
    A[用户请求预测] --> B[询问目标城市和天数]
    B --> C[Web搜索土壤条件]
    C --> D[调用天气工具获取天气预报]
    D --> E[整理天气数据格式]
    E --> F[调用疾病风险预测器]
    F --> G[生成综合预测报告]
    G --> H[输出预测结果]
```

### 3. 维护流程 (Maintenance Workflow)

```mermaid
graph TD
    A[用户咨询维护] --> B[确认病害名称]
    B --> C[确认治理措施]
    C --> D[确认治疗效果]
    D --> E[获取近期天气]
    E --> F[生成维护建议]
    F --> G[输出维护方案]
```

## 核心组件详解

### 工具集 (Tools)

```mermaid
graph LR
    A[工具集] --> B[RAG检索工具]
    A --> C[天气查询工具]
    A --> D[网络搜索工具]
    A --> E[诊断分析工具]
    A --> F[预测工具]
    A --> G[维护建议工具]
    A --> H[果园上下文工具]
    
    B --> B1[rag_search]
    B --> B2[knowledge_base_retrieval]
    C --> C1[get_weather]
    D --> D1[web_search]
    E --> E1[analyze_candidates]
    E --> E2[calculate_confidence]
    E --> E3[generate_clarifying_question]
    E --> E4[create_final_report]
    F --> F1[disease_risk_prediction]
    G --> G1[treatment_maintenance_advice]
    H --> H1[fetch_orchard_context]
```

### 预测器模块 (Predictor Module)

```mermaid
graph TD
    A[CitrusDiseasePredictor] --> B[数据累积]
    A --> C[风险预测]
    A --> D[报告生成]
    
    B --> B1[有效积温 EAT]
    B --> B2[连续高湿天数 CHD]
    B --> B3[近期累计降雨 RCR]
    
    C --> C1[炭疽病规则]
    C --> C2[疮痂病规则]
    C --> C3[溃疡病规则]
    C --> C4[脂点黄斑病规则]
    C --> C5[木虱规则]
    C --> C6[潜叶蛾规则]
    C --> C7[锈壁虱规则]
    C --> C8[红蜘蛛规则]
    
    D --> D1[高风险疾病]
    D --> D2[中风险疾病]
    D --> D3[低风险疾病]
    D --> D4[环境因素分析]
```

## 数据流转图

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as Agent
    participant T as 工具集
    participant P as 预测器
    participant R as RAG检索
    participant W as 天气API
    
    U->>A: 输入问题
    A->>A: 意图识别
    A->>T: 调用相应工具
    
    alt 诊断流程
        A->>R: 知识库检索
        R-->>A: 返回候选疾病
        A->>T: 三维评分分析
        T-->>A: 返回评分结果
        A->>T: 计算置信度
        T-->>A: 返回置信度
        A->>T: 生成诊断报告
        T-->>A: 返回报告
    end
    
    alt 预测流程
        A->>W: 查询天气数据
        W-->>A: 返回天气信息
        A->>P: 调用预测器
        P-->>A: 返回风险预测
        A->>T: 生成综合报告
        T-->>A: 返回预测报告
    end
    
    A-->>U: 返回最终结果
```

## 关键技术特点

1. **多模态支持**: 支持文本和图像输入
2. **实时回调**: 通过WebSocket推送处理进度
3. **记忆管理**: 使用ConversationBufferMemory保持对话上下文
4. **并行处理**: 使用ThreadPoolExecutor并行处理候选疾病评分
5. **规则引擎**: 基于专家规则的疾病风险预测
6. **RAG检索**: 使用BM25稀疏检索器进行知识库查询
7. **置信度评估**: 三维交叉验证评分机制
8. **JSON格式输出**: 结构化输出便于前端解析

## 输出格式

- **诊断报告**: `{"type": "diagnosis_report", "content": "...", "primary_diagnosis": "...", "confidence": 0.85, ...}`
- **澄清问题**: `{"type": "clarification", "content": "...", "options": [...]}`
- **普通文本**: `{"type": "text", "content": "..."}`

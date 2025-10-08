from app.core.orchard_state import OrchardState
from app.services.llm_service import llm
from app.services.vector_store_service import get_vector_store
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any
import json

def rag_qa_node(state: OrchardState) -> OrchardState:
    """
    RAG快速问答节点 - 实现精简的RAG流程
    接收问题 -> 向量检索 -> LLM结合Top-K结果生成综合答案 -> 存入State
    """
    print("---RAG QA NODE---")
    
    user_query = state.get("user_query", "")
    if not user_query:
        state["final_report"] = {"error": "没有提供查询问题"}
        return state
    
    try:
        # 1. 向量检索 - 获取相关文档
        print(f"正在检索相关文档: {user_query}")
        vector_store = get_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(user_query)
        
        # 2. 构建上下文
        context_parts = []
        for i, doc in enumerate(relevant_docs, 1):
            context_parts.append(f"文档 {i}:\n{doc.page_content}\n")
        
        context = "\n".join(context_parts)
        
        # 3. 构建LLM提示
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的柑橘种植专家助手。请基于提供的相关文档，回答用户的问题。

要求：
1. 答案要准确、专业、易懂
2. 如果文档中没有相关信息，请明确说明
3. 答案要结构化，便于理解
4. 如果涉及具体操作，请提供详细的步骤
5. 保持回答的简洁性，避免冗余

请用中文回答。"""),
            ("user", """用户问题：{query}

相关文档：
{context}

请基于以上文档回答用户的问题。""")
        ])
        
        # 4. 生成回答
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({
            "query": user_query,
            "context": context
        })
        
        # 5. 构建响应
        response = {
            "type": "rag_qa_response",
            "question": user_query,
            "answer": answer,
            "sources": [
                {
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in relevant_docs
            ],
            "confidence": "high" if len(relevant_docs) >= 3 else "medium" if len(relevant_docs) >= 1 else "low",
            "briefing": answer  # 添加briefing字段供前端使用
        }
        
        state["final_report"] = response
        state["workflow_step"] = "RAG QA 完成"
        
        print(f"RAG QA 回答生成完成，置信度: {response['confidence']}")
        
    except Exception as e:
        print(f"RAG QA 节点错误: {e}")
        state["final_report"] = {
            "type": "rag_qa_response",
            "question": user_query,
            "answer": f"抱歉，在处理您的问题时出现了错误：{str(e)}",
            "sources": [],
            "confidence": "error",
            "briefing": f"抱歉，在处理您的问题时出现了错误：{str(e)}"
        }
        state["workflow_step"] = "RAG QA 错误"
    
    return state

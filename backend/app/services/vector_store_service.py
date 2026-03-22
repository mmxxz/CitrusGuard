from langchain_postgres import PGVector
from langchain_core.documents import Document
from typing import List, Optional
from app.services.llm_service import llm # We need an embedding model
from app.core.config import settings

# Use a local multilingual sentence-transformer to avoid external API issues
from langchain_community.embeddings import HuggingFaceEmbeddings

# 完全延迟初始化，避免导入时的问题
_embeddings = None
_vector_store = None

class MockVectorStore:
    """临时模拟向量存储，用于测试状态管理"""
    def __init__(self):
        self.documents = []

    def add_documents(self, documents: List[Document]):
        self.documents.extend(documents)
        print(f"Mock: Added {len(documents)} documents")

    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        # 返回模拟结果
        mock_results = [
            Document(page_content=f"模拟结果1: {query}", metadata={"confidence": 0.8}),
            Document(page_content=f"模拟结果2: {query}", metadata={"confidence": 0.7}),
        ]
        print(f"Mock: Searching for '{query}', returning {len(mock_results)} results")
        return mock_results[:k]

    def as_retriever(self, search_kwargs: Optional[dict] = None, **kwargs):
        """与 PGVector 对齐，供 rag_qa_node：as_retriever().get_relevant_documents()"""
        sk = search_kwargs or kwargs.get("search_kwargs") or {}
        k = int(sk.get("k", 5))
        parent = self

        class _MockRetriever:
            def get_relevant_documents(self, query: str) -> List[Document]:
                return parent.similarity_search(query, k=k)

        return _MockRetriever()

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        print("Initializing embeddings model...")
        try:
            _embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
        except Exception as e:
            print(f"Failed to initialize embeddings: {e}")
            return None
    return _embeddings

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        print("Initializing vector store...")
        try:
            CONNECTION_STRING = str(settings.DATABASE_URL)
            COLLECTION_NAME = "citrus_knowledge_base"
            embeddings = get_embeddings()
            if embeddings:
                _vector_store = PGVector(
                    collection_name=COLLECTION_NAME,
                    connection=CONNECTION_STRING,
                    embeddings=embeddings,
                )
            else:
                print("Using mock vector store for testing")
                _vector_store = MockVectorStore()
        except Exception as e:
            print(f"Failed to initialize vector store: {e}, using mock")
            _vector_store = MockVectorStore()
    return _vector_store

def add_documents_to_store(documents: List[Document]):
    """Adds a list of LangChain documents to the vector store (sync)."""
    store = get_vector_store()
    store.add_documents(documents)
    print(f"Successfully added {len(documents)} documents to the vector store.")

def _simple_keyword_score(text: str, keywords: List[str]) -> float:
    text_l = text or ""
    score = 0.0
    for kw in keywords:
        if not kw:
            continue
        score += text_l.count(kw)
    return float(score)

def search_similar_documents(query: str, k: int = 20) -> List[Document]:
    """
    Hybrid search: vector retrieval + heuristic reranking.
    - Increase k by default to improve recall.
    - Boost results whose metadata.name matches the query.
    - Boost results containing intent keywords (e.g., 防治/治疗) when present in query.
    """
    print(f"Searching for documents similar to: {query}")
    store = get_vector_store()
    # Step 1: vector retrieval with larger k
    base_k = max(k, 20)
    vec_results: List[Document] = store.similarity_search(query, k=base_k)

    # Step 2: heuristic reranking
    q = (query or "")
    intent_keywords = []
    if any(x in q for x in ["防治", "治疗", "治理", "用药", "药剂"]):
        intent_keywords = ["防治", "治疗", "药剂"]

    # 提取疾病关键词：去空格并移除意图词
    q_compact = q.replace(" ", "")
    for kw in ["防治", "治疗", "治理", "用药", "药剂"]:
        q_compact = q_compact.replace(kw, "")

    def score_doc(doc: Document, idx: int) -> float:
        # Higher is better
        base = 1.0 / (idx + 1)  # original rank prior
        name = (doc.metadata or {}).get("name", "")
        name_bonus = 0.0
        if name:
            # 强匹配：与疾病关键词相互包含
            if q_compact and (name in q_compact or q_compact in name):
                name_bonus = 20.0
            # 次强匹配：与原查询相互包含
            elif name in q or q in name:
                name_bonus = 5.0
        intent_bonus = 0.0
        if intent_keywords:
            intent_bonus = _simple_keyword_score(doc.page_content or "", intent_keywords) * 0.5
        return base + name_bonus + intent_bonus

    scored = [(score_doc(d, i), i, d) for i, d in enumerate(vec_results)]
    scored.sort(key=lambda x: x[0], reverse=True)
    re_ranked = [d for _, _, d in scored[:k]]
    return re_ranked

def extract_treatment_summary(doc: Document) -> str:
    """
    从文档内容中提取“防治方法”段落的简要摘要。
    当前实现：基于行规则截取包含“防治”/“治疗”关键词的若干行。
    """
    text = (doc.page_content or "").splitlines()
    key_lines: List[str] = []
    for line in text:
        if any(kw in line for kw in ["防治", "治疗", "药剂", "农业措施", "生物防治", "化学防治"]):
            s = line.strip()
            if s:
                key_lines.append(s)
        if len(key_lines) >= 8:
            break
    return "\n".join(key_lines[:8]) if key_lines else "未找到明确的防治方法条目"

def search_with_treatment_focus(query: str, k: int = 20) -> List[dict]:
    """
    混合检索 + 简要摘要：返回结构化结果，包含名称、类别与防治方法摘要。
    """
    docs = search_similar_documents(query, k=k)
    results: List[dict] = []
    for d in docs:
        results.append({
            "name": (d.metadata or {}).get("name"),
            "type": (d.metadata or {}).get("type"),
            "treatment_summary": extract_treatment_summary(d),
        })
    return results

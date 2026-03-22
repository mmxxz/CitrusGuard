import sys
from pathlib import Path
from types import SimpleNamespace
import types

sys.path.append(str(Path(__file__).resolve().parent))

# 避免导入真实 LLM/向量库依赖导致测试环境崩溃
fake_llm_module = types.ModuleType("app.services.llm_service")
fake_llm_module.llm = object()
sys.modules["app.services.llm_service"] = fake_llm_module

fake_vs_module = types.ModuleType("app.services.vector_store_service")
fake_vs_module.get_vector_store = lambda: None
fake_vs_module.search_with_treatment_focus = lambda diagnosis, k=8: []
fake_vs_module.search_similar_documents = lambda query, k=5: []
sys.modules["app.services.vector_store_service"] = fake_vs_module

# 避免 langchain_core 在导入阶段拉起 transformers/torch
fake_prompts_module = types.ModuleType("langchain_core.prompts")


class _StubChatPromptTemplate:
    @staticmethod
    def from_messages(messages):
        return object()


fake_prompts_module.ChatPromptTemplate = _StubChatPromptTemplate
sys.modules["langchain_core.prompts"] = fake_prompts_module

fake_output_module = types.ModuleType("langchain_core.output_parsers")


class _StubStrOutputParser:
    pass


class _StubJsonOutputParser:
    pass


fake_output_module.StrOutputParser = _StubStrOutputParser
fake_output_module.JsonOutputParser = _StubJsonOutputParser
sys.modules["langchain_core.output_parsers"] = fake_output_module

from app.agents.graph.graph import route_by_intent, should_continue
from app.agents.graph.calculate_confidence_node import calculate_confidence_node
from app.agents.graph.rag_qa_node import rag_qa_node


def test_5_6_1_high_confidence_direct_diagnosis():
    """
    场景A：高置信度直接确诊（不触发追问）
    """
    state = {
        "intent": "Complex Diagnostic",
        "initial_diagnosis_suggestion": {
            "top1": {"name": "炭疽病", "confidence": 0.87},
            "coarse_class": "病害",
        },
        "environmental_reasoning": {
            "anthracnose_risk": 82,
            "risk_level": "high",
            "consistent_with_visual": True,
        },
        "confidence_result": {
            "top_candidate": {"disease_name": "炭疽病"},
            "confidence_score": 0.92,
        },
        "need_clarification": False,
        "clarification_count": 0,
    }

    assert route_by_intent(state) == "fetch_orchard_profile"
    assert should_continue(state) == "retrieve_treatment_knowledge"


def test_5_6_2_low_confidence_triggers_clarification():
    """
    场景B：低置信度触发追问
    """
    state = {
        "intent": "Complex Diagnostic",
        "initial_diagnosis_suggestion": {
            "top1": {"name": "疑似缺素", "confidence": 0.41},
            "coarse_class": "生理性问题",
        },
        "environmental_reasoning": {
            "risk_level": "medium",
            "consistency": "uncertain",
        },
        "confidence_result": {
            "top_candidate": {"disease_name": "柑橘缺镁症"},
            "confidence_score": 0.64,
        },
        "need_clarification": True,
        "clarification_count": 0,
    }

    assert should_continue(state) == "smart_questioning"


def test_5_6_3_ood_rejection(monkeypatch):
    """
    场景C：非目标图像（OOD）应拒识，不应强行给病害结论
    """

    class _DummyCrud:
        def get_candidates_for_evidence(self, evidence_matrix, limit=10):
            return []

    monkeypatch.setattr(
        "app.agents.graph.calculate_confidence_node.get_disease_profile_crud",
        lambda db: _DummyCrud(),
    )
    monkeypatch.setattr(
        "app.agents.graph.calculate_confidence_node.SessionLocal",
        lambda: SimpleNamespace(close=lambda: None),
    )

    state = {
        "evidence_matrix": {
            "visual": {"leaf_color": None, "leaf_spots": [], "confidence": 0.12},
            "symptom": {"primary_symptoms": [], "secondary_symptoms": [], "confidence": 0.1},
            "environmental": {"temperature": None, "humidity": None, "confidence": 0.0},
            "historical": {"similar_cases": [], "confidence": 0.0},
            "completeness_score": 0.0,
        }
    }

    out = calculate_confidence_node(state)
    result = out["confidence_result"]
    confidence_score = result["confidence_score"] if isinstance(result, dict) else result.confidence_score
    disease_candidates = result["disease_candidates"] if isinstance(result, dict) else result.disease_candidates
    reasoning = result["reasoning"] if isinstance(result, dict) else result.reasoning

    assert confidence_score == 0.0
    assert disease_candidates == []
    assert "没有找到候选病害档案" in reasoning


def test_5_6_4_simple_qa_rag_answer(monkeypatch):
    """
    场景D：知识问答（Simple Q&A）应走RAG并返回可追溯答案
    """

    class _FakeDoc:
        def __init__(self, text):
            self.page_content = text
            self.metadata = {"source": "kb_citrus_canker"}

    class _FakeRetriever:
        def get_relevant_documents(self, query):
            return [
                _FakeDoc("带菌苗木和接穗调运会传播溃疡病。"),
                _FakeDoc("暴风雨导致伤口侵染，雨水飞溅可传播病菌。"),
                _FakeDoc("潜叶蛾等昆虫造成伤口，增加侵染机会。"),
            ]

    class _FakeVectorStore:
        def as_retriever(self, search_kwargs=None):
            return _FakeRetriever()

    class _FakeChain:
        def __or__(self, other):
            return self

        def invoke(self, payload):
            return (
                "柑橘溃疡病主要通过带菌苗木/接穗调运传播，"
                "其次是暴风雨伤口与雨水飞溅传播，"
                "以及潜叶蛾等昆虫造成伤口后侵入。"
            )

    monkeypatch.setattr("app.agents.graph.rag_qa_node.get_vector_store", lambda: _FakeVectorStore())
    monkeypatch.setattr("app.agents.graph.rag_qa_node.ChatPromptTemplate.from_messages", lambda _: _FakeChain())

    assert route_by_intent({"intent": "Simple Q&A"}) == "rag_qa_node"

    state = {"intent": "Simple Q&A", "user_query": "柑橘溃疡病的传播途径有哪些？"}
    out = rag_qa_node(state)
    final_report = out["final_report"]

    assert "带菌苗木" in final_report["answer"]
    assert "暴风雨" in final_report["answer"]
    assert "潜叶蛾" in final_report["answer"]
    assert final_report["confidence"] == "high"
    assert len(final_report["sources"]) == 3

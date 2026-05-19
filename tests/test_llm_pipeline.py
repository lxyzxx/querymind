import json

from querymind.agent.semantic_layer import SemanticLayer
from querymind.core import (
    Insight,
    QueryPlan,
    QueryResult,
    generate_basic_insight,
    generate_insight_with_optional_llm,
    plan_with_optional_llm,
)
from querymind.llm.openai_compatible_client import OpenAICompatibleLLMClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class _FakePlannerClient:
    def generate_query_plan(self, question, semantic_context):
        return QueryPlan(
            question=question,
            question_type="diagnosis",
            metric="gmv",
            comparison="month_over_month",
            breakdowns=["channel"],
            limit=20,
        )

    def generate_insight(self, question, plan, result):
        return Insight(answer="llm insight")


class _BadPlannerClient:
    def generate_query_plan(self, question, semantic_context):
        return QueryPlan(question=question, question_type="fact", metric="not_exists")

    def generate_insight(self, question, plan, result):
        return Insight(answer="bad")


class _ClarifyingPlannerClient:
    def generate_query_plan(self, question, semantic_context):
        return QueryPlan(
            question=question,
            question_type="comparison",
            metric="gmv",
            dimensions=["order_date"],
            comparison={"type": "period_over_period", "period": "month"},
            breakdowns=["channel"],
            limit=50,
            needs_clarification=True,
            clarification_question="是否需要按渠道拆解？",
        )

    def generate_insight(self, question, plan, result):
        return Insight(answer="clarifying")


def test_openai_compatible_client_generates_insight_from_json_response():
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "answer": "GMV 下降主要来自 ads。",
                            "observations": ["GMV 下降 1500。"],
                            "possible_causes": ["ads 渠道下降最大。"],
                            "recommended_actions": ["检查 ads 投放。"],
                            "evidence": [{"label": "delta", "value": -1500, "source": "query_result"}],
                        },
                        ensure_ascii=False,
                    )
                }
            }
        ]
    }
    client = OpenAICompatibleLLMClient(
        api_key="test",
        transport=lambda request, timeout: _FakeResponse(payload),
    )

    insight = client.generate_insight(
        "为什么销售额下降？",
        QueryPlan(question="为什么销售额下降？", question_type="diagnosis", metric="gmv"),
        QueryResult(sql="select 1 as gmv", rows=[{"gmv": 1}]),
    )

    assert insight.answer == "GMV 下降主要来自 ads。"
    assert insight.evidence[0].label == "delta"


def test_plan_with_optional_llm_uses_valid_semantic_objects():
    layer = SemanticLayer.from_file("querymind/example/semantic_layer.yaml")

    generation = plan_with_optional_llm(
        layer,
        "为什么上个月的销售额比上上个月的少？",
        limit=20,
        use_llm=True,
        llm_client=_FakePlannerClient(),
    )

    assert generation.source == "llm"
    assert generation.plan.metric == "gmv"
    assert generation.plan.breakdowns == ["channel"]


def test_plan_with_optional_llm_falls_back_when_metric_is_not_in_semantic_layer():
    layer = SemanticLayer.from_file("querymind/example/semantic_layer.yaml")

    generation = plan_with_optional_llm(
        layer,
        "GMV情况如何",
        limit=20,
        use_llm=True,
        llm_client=_BadPlannerClient(),
    )

    assert generation.source == "deterministic_fallback"
    assert generation.plan.metric == "gmv"
    assert "Unknown semantic metric" in generation.error


def test_plan_with_optional_llm_uses_basic_plan_when_llm_clarifies_unnecessarily():
    layer = SemanticLayer.from_file("querymind/example/semantic_layer.yaml")

    generation = plan_with_optional_llm(
        layer,
        "为什么上个月的销售额比上上个月的少，怎么优化？",
        limit=20,
        use_llm=True,
        llm_client=_ClarifyingPlannerClient(),
    )

    assert generation.source == "llm"
    assert generation.plan.needs_clarification is False
    assert generation.plan.metric == "gmv"
    assert generation.plan.comparison == "month_over_month"
    assert generation.plan.breakdowns == ["channel"]


def test_generate_insight_with_optional_llm_falls_back_without_client(monkeypatch):
    monkeypatch.setattr("querymind.core.insight_pipeline.create_llm_client_from_env", lambda: None)
    plan = QueryPlan(question="GMV情况如何", question_type="fact", metric="gmv")
    result = QueryResult(sql="select 1 as gmv", rows=[{"gmv": 1}])

    generation = generate_insight_with_optional_llm(
        "GMV情况如何",
        plan,
        result,
        deterministic=generate_basic_insight,
        use_llm=True,
        llm_client=None,
    )

    assert generation.source == "deterministic_fallback"
    assert generation.insight.answer == "gmv 的查询结果为 1。"

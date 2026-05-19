from datetime import date

import pytest

from querymind.core import Insight, InsightEvidence, QueryPlan, QueryResult


def test_query_plan_normalizes_and_serializes():
    plan = QueryPlan.from_dict(
        {
            "question": "这个月销售额多少？",
            "question_type": "FACT",
            "metric": "sales_amount",
            "dimensions": "region",
            "filters": {"month": "current"},
            "named_filters": ["paid_orders"],
            "limit": "20",
        }
    )

    assert plan.question_type == "fact"
    assert plan.dimensions == ["region"]
    assert plan.limit == 20
    assert plan.to_dict()["filters"] == {"month": "current"}


def test_query_plan_rejects_unknown_question_type():
    with pytest.raises(ValueError, match="Unsupported question_type"):
        QueryPlan(question="why", question_type="unknown", metric="sales_amount")


def test_query_result_sets_row_count():
    result = QueryResult(sql="select 1", rows=[{"sales_amount": 100}])

    assert result.row_count == 1
    assert result.to_dict()["rows"] == [{"sales_amount": 100}]


def test_query_result_serializes_dates_for_llm_payloads():
    result = QueryResult(sql="select current_date as d", rows=[{"d": date(2026, 5, 19)}])

    assert result.to_dict()["rows"] == [{"d": "2026-05-19"}]


def test_insight_requires_traceable_answer():
    insight = Insight(
        answer="本月销售额为 100。",
        observations=["销售额来自 1 行查询结果。"],
        evidence=[InsightEvidence(label="sales_amount", value=100)],
    )

    assert insight.to_dict()["evidence"] == [
        {"label": "sales_amount", "value": 100, "source": "query_result"}
    ]

from querymind.agent.semantic_layer import SemanticLayer
from querymind.core import BasicQueryPlanner, QueryPlan


def test_basic_query_planner_matches_chinese_semantic_aliases():
    layer = SemanticLayer.from_file("querymind/example/semantic_layer.yaml")
    planner = BasicQueryPlanner(layer)

    plan = planner.plan("按用户状态统计活跃用户数", limit=20)

    assert plan.to_dict() == {
        "question": "按用户状态统计活跃用户数",
        "question_type": "fact",
        "metric": "user_count",
        "dimensions": ["status"],
        "filters": {},
        "named_filters": ["active_only"],
        "comparison": None,
        "breakdowns": [],
        "limit": 20,
        "needs_clarification": False,
        "clarification_question": None,
    }


def test_query_plan_allows_clarification_without_metric():
    plan = QueryPlan(
        question="查一下",
        question_type="fact",
        metric="",
        needs_clarification=True,
        clarification_question="没有识别到可用指标。",
    )

    assert plan.needs_clarification is True
    assert plan.metric == ""

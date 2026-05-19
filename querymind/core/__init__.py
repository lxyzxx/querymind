"""Core model objects for QueryMind."""

from querymind.core.models import (
    Insight,
    InsightEvidence,
    QueryPlan,
    QueryResult,
)
from querymind.core.insight_generator import BasicInsightGenerator, generate_basic_insight
from querymind.core.query_planner import BasicQueryPlanner
from querymind.core.comparison import (
    build_month_over_month_sql,
    can_build_comparison_query,
    generate_comparison_insight,
)
from querymind.core.insight_pipeline import InsightGeneration, generate_insight_with_optional_llm
from querymind.core.planning_pipeline import PlanGeneration, plan_with_optional_llm
from querymind.core.trend import build_recent_7_days_sql, can_build_trend_query

__all__ = [
    "BasicInsightGenerator",
    "BasicQueryPlanner",
    "Insight",
    "InsightEvidence",
    "InsightGeneration",
    "PlanGeneration",
    "QueryPlan",
    "QueryResult",
    "build_month_over_month_sql",
    "build_recent_7_days_sql",
    "can_build_comparison_query",
    "can_build_trend_query",
    "generate_basic_insight",
    "generate_comparison_insight",
    "generate_insight_with_optional_llm",
    "plan_with_optional_llm",
]

from dataclasses import dataclass
from typing import Any, Optional

from querymind.core.models import QueryPlan
from querymind.core.query_planner import BasicQueryPlanner
from querymind.llm.base import LLMClient
from querymind.llm.factory import create_llm_client_from_env


@dataclass(frozen=True)
class PlanGeneration:
    plan: QueryPlan
    source: str
    error: str = ""


def plan_with_optional_llm(
    semantic_layer: Any,
    question: str,
    limit: Optional[int] = None,
    use_llm: bool = False,
    llm_client: Optional[LLMClient] = None,
) -> PlanGeneration:
    basic_plan = BasicQueryPlanner(semantic_layer).plan(question, limit=limit)
    if not use_llm:
        return PlanGeneration(plan=basic_plan, source="deterministic")

    try:
        client = llm_client or create_llm_client_from_env()
        if client is None:
            return PlanGeneration(
                plan=basic_plan,
                source="deterministic_fallback",
                error="LLM is not configured.",
            )

        plan = _normalize_llm_plan(client.generate_query_plan(question, semantic_layer.prompt_context()))
        if limit is not None and plan.limit is None:
            raw = plan.to_dict()
            raw["limit"] = limit
            plan = QueryPlan.from_dict(raw)
        if plan.needs_clarification and not basic_plan.needs_clarification:
            plan = _prefer_executable_basic_plan(plan, basic_plan)
        _validate_plan_against_semantic_layer(semantic_layer, plan)
        return PlanGeneration(plan=plan, source="llm")
    except Exception as exc:
        return PlanGeneration(
            plan=basic_plan,
            source="deterministic_fallback",
            error=str(exc),
        )


def _validate_plan_against_semantic_layer(semantic_layer: Any, plan: QueryPlan) -> None:
    if plan.needs_clarification:
        return
    table, _ = semantic_layer._find_metric(plan.metric)
    for dimension in plan.dimensions:
        semantic_layer._find_dimension(table, dimension)
    for breakdown in plan.breakdowns:
        semantic_layer._find_dimension(table, breakdown)
    for named_filter in plan.named_filters:
        semantic_layer._find_filter(table, named_filter)


def _normalize_llm_plan(plan: QueryPlan) -> QueryPlan:
    raw = plan.to_dict()
    raw["comparison"] = _normalize_comparison(raw.get("comparison"))
    raw["filters"] = raw.get("filters") or {}
    raw["dimensions"] = raw.get("dimensions") or []
    raw["named_filters"] = raw.get("named_filters") or []
    raw["breakdowns"] = raw.get("breakdowns") or []
    return QueryPlan.from_dict(raw)


def _normalize_comparison(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        text = " ".join(str(item).lower() for item in value.values())
    else:
        text = str(value).strip().lower()
    if not text:
        return None
    if "recent_7" in text or "last 7" in text or "7_days" in text:
        return "recent_7_days"
    if "month_over_month" in text or "period_over_period" in text or "month" in text or "mom" in text:
        return "month_over_month"
    return text


def _prefer_executable_basic_plan(llm_plan: QueryPlan, basic_plan: QueryPlan) -> QueryPlan:
    raw = basic_plan.to_dict()
    raw["question"] = llm_plan.question or basic_plan.question
    return QueryPlan.from_dict(raw)

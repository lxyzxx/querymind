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

        plan = client.generate_query_plan(question, semantic_layer.prompt_context())
        if limit is not None and plan.limit is None:
            raw = plan.to_dict()
            raw["limit"] = limit
            plan = QueryPlan.from_dict(raw)
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

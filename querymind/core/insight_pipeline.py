from dataclasses import dataclass
from typing import Callable, Optional

from querymind.core.models import Insight, QueryPlan, QueryResult
from querymind.llm.base import LLMClient
from querymind.llm.factory import create_llm_client_from_env


@dataclass(frozen=True)
class InsightGeneration:
    insight: Insight
    source: str
    error: str = ""


def generate_insight_with_optional_llm(
    question: str,
    plan: QueryPlan,
    result: QueryResult,
    deterministic: Callable[[QueryPlan, QueryResult], Insight],
    use_llm: bool = False,
    llm_client: Optional[LLMClient] = None,
) -> InsightGeneration:
    deterministic_insight = deterministic(plan, result)
    if not use_llm:
        return InsightGeneration(insight=deterministic_insight, source="deterministic")

    try:
        client = llm_client or create_llm_client_from_env()
        if client is None:
            return InsightGeneration(
                insight=deterministic_insight,
                source="deterministic_fallback",
                error="LLM is not configured.",
            )
        return InsightGeneration(
            insight=client.generate_insight(question, plan, result),
            source="llm",
        )
    except Exception as exc:
        return InsightGeneration(
            insight=deterministic_insight,
            source="deterministic_fallback",
            error=str(exc),
        )

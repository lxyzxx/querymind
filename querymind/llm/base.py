from typing import Protocol

from querymind.core.models import Insight, QueryPlan, QueryResult


class LLMClient(Protocol):
    """Model-provider neutral interface used by QueryMind workflows."""

    def generate_query_plan(self, question: str, semantic_context: str) -> QueryPlan:
        """Convert a natural-language question into a structured query plan."""

    def generate_insight(self, question: str, plan: QueryPlan, result: QueryResult) -> Insight:
        """Generate a business-facing explanation from query results."""

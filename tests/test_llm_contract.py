from querymind.core import Insight, QueryPlan, QueryResult
from querymind.llm.base import LLMClient


class FakeLLMClient:
    def generate_query_plan(self, question: str, semantic_context: str) -> QueryPlan:
        return QueryPlan(question=question, question_type="fact", metric="user_count")

    def generate_insight(self, question: str, plan: QueryPlan, result: QueryResult) -> Insight:
        return Insight(answer=f"{plan.metric} returned {result.row_count} rows.")


def test_fake_llm_client_matches_contract():
    client: LLMClient = FakeLLMClient()
    plan = client.generate_query_plan("用户数多少？", "{}")
    result = QueryResult(sql="select count(*) as user_count from users", rows=[{"user_count": 3}])

    insight = client.generate_insight("用户数多少？", plan, result)

    assert plan.metric == "user_count"
    assert insight.answer == "user_count returned 1 rows."

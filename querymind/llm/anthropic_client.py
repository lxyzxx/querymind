import json
from typing import Any, Dict, Optional

from querymind.core.models import Insight, QueryPlan, QueryResult


class AnthropicLLMClient:
    """Optional Anthropic SDK adapter for QueryMind's provider-neutral LLM API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        api_key: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic SDK is not installed. Run: python3 -m pip install anthropic"
            ) from exc

        self._client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def generate_query_plan(self, question: str, semantic_context: str) -> QueryPlan:
        prompt = (
            "Return only JSON for a QueryPlan. Supported question_type values are "
            "fact, ranking, trend, comparison, diagnosis, suggestion.\n\n"
            f"Semantic layer:\n{semantic_context}\n\n"
            f"Question:\n{question}"
        )
        payload = self._complete_json(prompt)
        payload.setdefault("question", question)
        return QueryPlan.from_dict(payload)

    def generate_insight(self, question: str, plan: QueryPlan, result: QueryResult) -> Insight:
        prompt = (
            "Return only JSON with keys answer, observations, possible_causes, "
            "recommended_actions, and evidence. Keep observations traceable to the "
            "query result and clearly separate facts from possible causes.\n\n"
            f"Question:\n{question}\n\n"
            f"QueryPlan:\n{json.dumps(plan.to_dict(), ensure_ascii=False)}\n\n"
            f"QueryResult:\n{json.dumps(result.to_dict(), ensure_ascii=False)}"
        )
        payload = self._complete_json(prompt)
        return Insight(
            answer=str(payload.get("answer", "")),
            observations=payload.get("observations", []),
            possible_causes=payload.get("possible_causes", []),
            recommended_actions=payload.get("recommended_actions", []),
        )

    def _complete_json(self, prompt: str) -> Dict[str, Any]:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system="You are QueryMind's structured data analysis planner.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = _message_text(message)
        return json.loads(text)


def _message_text(message: Any) -> str:
    parts = []
    for item in getattr(message, "content", []):
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()

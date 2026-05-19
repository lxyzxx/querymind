import json
import urllib.request
from typing import Any, Dict, Optional

from querymind.core.models import Insight, InsightEvidence, QueryPlan, QueryResult


class OpenAICompatibleLLMClient:
    """LLM adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        max_tokens: int = 2048,
        timeout: int = 60,
        transport: Any = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._transport = transport or urllib.request.urlopen

    def generate_query_plan(self, question: str, semantic_context: str) -> QueryPlan:
        prompt = (
            "只返回 JSON，不要 Markdown。JSON 必须符合 QueryPlan 字段：question, "
            "question_type, metric, dimensions, filters, named_filters, comparison, "
            "breakdowns, limit, needs_clarification, clarification_question。\n\n"
            f"语义层:\n{semantic_context}\n\n问题:\n{question}"
        )
        payload = self._complete_json(prompt)
        payload.setdefault("question", question)
        return QueryPlan.from_dict(payload)

    def generate_insight(self, question: str, plan: QueryPlan, result: QueryResult) -> Insight:
        prompt = (
            "你是严谨的数据分析助手。只返回 JSON，不要 Markdown。"
            "JSON 字段必须包含 answer, observations, possible_causes, "
            "recommended_actions, evidence。\n"
            "要求：\n"
            "1. 只能基于 QueryPlan 和 QueryResult 中的数据下结论。\n"
            "2. observations 写已观测事实。\n"
            "3. possible_causes 写可能原因，并明确是推断。\n"
            "4. recommended_actions 写可执行的优化建议。\n"
            "5. evidence 数组中的每项包含 label, value, source。\n\n"
            f"用户问题:\n{question}\n\n"
            f"QueryPlan:\n{json.dumps(plan.to_dict(), ensure_ascii=False)}\n\n"
            f"QueryResult:\n{json.dumps(result.to_dict(), ensure_ascii=False)}"
        )
        payload = self._complete_json(prompt)
        return Insight(
            answer=str(payload.get("answer", "")),
            observations=payload.get("observations", []),
            possible_causes=payload.get("possible_causes", []),
            recommended_actions=payload.get("recommended_actions", []),
            evidence=[
                InsightEvidence(
                    label=str(item.get("label", "")),
                    value=item.get("value"),
                    source=str(item.get("source", "llm")),
                )
                for item in payload.get("evidence", [])
                if isinstance(item, dict) and str(item.get("label", "")).strip()
            ],
        )

    def _complete_json(self, prompt: str) -> Dict[str, Any]:
        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are QueryMind's governed data analysis assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": self._max_tokens,
        }
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "authorization": f"Bearer {self._api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        with self._transport(request, timeout=self._timeout) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
        return json.loads(_json_object_text(content))


def _json_object_text(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("LLM response did not contain a JSON object.")
    return text[start : end + 1]

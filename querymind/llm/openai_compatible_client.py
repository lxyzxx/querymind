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
            "你是 QueryMind 的 QueryPlan 生成器。只返回 JSON，不要 Markdown。\n"
            "SQL 不是你生成的，SQL 会由语义层编译器生成。你的任务只是从语义层中选择合法对象。\n\n"
            "JSON 必须包含字段：question, question_type, metric, dimensions, filters, "
            "named_filters, comparison, breakdowns, limit, needs_clarification, clarification_question。\n"
            "字段约束：\n"
            "- question_type 只能是 fact, ranking, trend, comparison, diagnosis, suggestion。\n"
            "- metric 必须使用语义层 metrics.name 中的规范名称，不要使用同义词。\n"
            "- dimensions 和 breakdowns 必须使用语义层 dimensions.name 中的规范名称。\n"
            "- named_filters 必须使用语义层 filters.name 中的规范名称。\n"
            "- comparison 只能是 null, month_over_month, recent_7_days。\n"
            "- filters 必须是 JSON object；没有筛选条件时用 {}。\n"
            "- dimensions, named_filters, breakdowns 必须是 JSON array；没有时用 []。\n"
            "- 如果语义层中存在可匹配指标，不要因为缺少更细拆解而 needs_clarification。\n"
            "- 对“上个月比上上个月少/下降/减少/环比”使用 question_type=diagnosis, comparison=month_over_month。\n"
            "- 对销售额/GMV 使用 metric=gmv；对订单数使用 metric=order_count；对客单价使用 metric=avg_order_value。\n"
            "- 对下降原因类问题，如语义层有 channel 维度，breakdowns 使用 [\"channel\"]。\n"
            "- 对“最近7天...趋势”使用 question_type=trend, comparison=recent_7_days。\n\n"
            "示例：\n"
            "{\n"
            '  "question": "为什么上个月的销售额比上上个月的少，怎么优化？",\n'
            '  "question_type": "diagnosis",\n'
            '  "metric": "gmv",\n'
            '  "dimensions": [],\n'
            '  "filters": {},\n'
            '  "named_filters": [],\n'
            '  "comparison": "month_over_month",\n'
            '  "breakdowns": ["channel"],\n'
            '  "limit": 20,\n'
            '  "needs_clarification": false,\n'
            '  "clarification_question": null\n'
            "}\n\n"
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

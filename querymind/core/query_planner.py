from typing import Any, List, Optional, Tuple

from querymind.core.models import QueryPlan


class BasicQueryPlanner:
    """Rule-based planner for demos and tests.

    This is a deterministic fallback, not a replacement for an LLM planner.
    It matches metric, dimensions, and named filters from the semantic layer's
    governed names and synonyms.
    """

    def __init__(self, semantic_layer: Any) -> None:
        self._semantic_layer = semantic_layer

    def plan(self, question: str, limit: Optional[int] = None) -> QueryPlan:
        text = question.strip()
        if not text:
            return QueryPlan(
                question="",
                question_type="fact",
                metric="",
                limit=limit,
                needs_clarification=True,
                clarification_question="请输入要查询的业务问题。",
            )

        metric = self._match_metric(text)
        if metric is None:
            return QueryPlan(
                question=text,
                question_type=_question_type(text),
                metric="",
                limit=limit,
                needs_clarification=True,
                clarification_question="没有识别到可用指标，请补充要查询的指标口径。",
            )

        table, metric_name = metric
        dimensions = self._match_dimensions(text, table)
        named_filters = self._match_filters(text, table)

        return QueryPlan(
            question=text,
            question_type=_question_type(text),
            metric=metric_name,
            dimensions=dimensions,
            named_filters=named_filters,
            limit=limit,
        )

    def _match_metric(self, text: str) -> Optional[Tuple[Any, str]]:
        best: Optional[Tuple[int, Any, str]] = None
        for table in self._semantic_layer.tables:
            for metric in table.metrics:
                score = _best_alias_score(text, [metric.name, *metric.synonyms])
                if score and (best is None or score > best[0]):
                    best = (score, table, metric.name)

        if best is not None:
            return best[1], best[2]

        for table in self._semantic_layer.tables:
            if table.metrics:
                return table, table.metrics[0].name
        return None

    def _match_dimensions(self, text: str, table: Any) -> List[str]:
        matches = []
        for dimension in table.dimensions:
            score = _best_alias_score(text, [dimension.name, *dimension.synonyms])
            if score:
                matches.append((score, dimension.name))
        matches.sort(reverse=True)
        return [name for _, name in matches]

    def _match_filters(self, text: str, table: Any) -> List[str]:
        matches = []
        for filter_ in table.filters:
            score = _best_alias_score(text, [filter_.name, *filter_.synonyms])
            if score:
                matches.append((score, filter_.name))
        matches.sort(reverse=True)
        return [name for _, name in matches]


def _question_type(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("为什么", "原因", "下降", "减少", "少了", "diagnose", "why")):
        return "diagnosis"
    if any(token in lowered for token in ("top", "排名", "最高", "最低", "最多", "最少")):
        return "ranking"
    if any(token in lowered for token in ("趋势", "trend", "最近", "每天", "每周", "每月")):
        return "trend"
    if any(token in lowered for token in ("对比", "相比", "环比", "同比", "compare")):
        return "comparison"
    if any(token in lowered for token in ("建议", "应该", "recommend")):
        return "suggestion"
    return "fact"


def _best_alias_score(text: str, aliases: List[str]) -> int:
    normalized_text = _normalize(text)
    best = 0
    for alias in aliases:
        normalized_alias = _normalize(alias)
        if normalized_alias and normalized_alias in normalized_text:
            best = max(best, len(normalized_alias))
    return best


def _normalize(value: str) -> str:
    return "".join(str(value).lower().split())

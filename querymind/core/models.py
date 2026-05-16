from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence


SUPPORTED_QUESTION_TYPES = {
    "fact",
    "ranking",
    "trend",
    "comparison",
    "diagnosis",
    "suggestion",
}


@dataclass(frozen=True)
class QueryPlan:
    """Structured intent extracted from a natural-language data question."""

    question: str
    question_type: str
    metric: str
    dimensions: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    named_filters: List[str] = field(default_factory=list)
    comparison: Optional[str] = None
    breakdowns: List[str] = field(default_factory=list)
    limit: Optional[int] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.question.strip() and not self.needs_clarification:
            raise ValueError("QueryPlan.question must not be empty.")
        if not self.metric.strip() and not self.needs_clarification:
            raise ValueError("QueryPlan.metric must not be empty.")
        normalized_type = self.question_type.strip().lower()
        if normalized_type not in SUPPORTED_QUESTION_TYPES:
            allowed = ", ".join(sorted(SUPPORTED_QUESTION_TYPES))
            raise ValueError(f"Unsupported question_type: {self.question_type}. Allowed: {allowed}")

        object.__setattr__(self, "question_type", normalized_type)
        object.__setattr__(self, "dimensions", _string_list(self.dimensions))
        object.__setattr__(self, "named_filters", _string_list(self.named_filters))
        object.__setattr__(self, "breakdowns", _string_list(self.breakdowns))
        object.__setattr__(self, "filters", dict(self.filters))

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "QueryPlan":
        return cls(
            question=str(raw.get("question", "")),
            question_type=str(raw.get("question_type", "fact")),
            metric=str(raw.get("metric", "")),
            dimensions=_string_list(raw.get("dimensions", [])),
            filters=dict(raw.get("filters", {}) or {}),
            named_filters=_string_list(raw.get("named_filters", [])),
            comparison=_optional_string(raw.get("comparison")),
            breakdowns=_string_list(raw.get("breakdowns", [])),
            limit=_optional_int(raw.get("limit")),
            needs_clarification=bool(raw.get("needs_clarification", False)),
            clarification_question=_optional_string(raw.get("clarification_question")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "question_type": self.question_type,
            "metric": self.metric,
            "dimensions": list(self.dimensions),
            "filters": dict(self.filters),
            "named_filters": list(self.named_filters),
            "comparison": self.comparison,
            "breakdowns": list(self.breakdowns),
            "limit": self.limit,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
        }


@dataclass(frozen=True)
class QueryResult:
    """Rows returned by a governed SQL query."""

    sql: str
    rows: List[Dict[str, Any]]
    row_count: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.sql.strip():
            raise ValueError("QueryResult.sql must not be empty.")
        rows = [dict(row) for row in self.rows]
        object.__setattr__(self, "rows", rows)
        if self.row_count is None:
            object.__setattr__(self, "row_count", len(rows))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "row_count": self.row_count,
            "rows": [dict(row) for row in self.rows],
        }


@dataclass(frozen=True)
class InsightEvidence:
    """A traceable fact used to support an insight."""

    label: str
    value: Any
    source: str = "query_result"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("InsightEvidence.label must not be empty.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "source": self.source,
        }


@dataclass(frozen=True)
class Insight:
    """Business-facing answer generated from a query plan and result."""

    answer: str
    observations: List[str] = field(default_factory=list)
    possible_causes: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    evidence: List[InsightEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.answer.strip():
            raise ValueError("Insight.answer must not be empty.")
        object.__setattr__(self, "observations", _string_list(self.observations))
        object.__setattr__(self, "possible_causes", _string_list(self.possible_causes))
        object.__setattr__(self, "recommended_actions", _string_list(self.recommended_actions))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "observations": list(self.observations),
            "possible_causes": list(self.possible_causes),
            "recommended_actions": list(self.recommended_actions),
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    raise ValueError("Expected a string or sequence of strings.")


def _optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)

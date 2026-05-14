from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import yaml

from querymind.agent.semantic_layer import SemanticLayer
from querymind.agent.sql_guard import validate_readonly_sql


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    question: str
    metric: str
    dimensions: Sequence[str]
    filters: Mapping[str, Any]
    named_filters: Sequence[str]
    limit: Optional[int]
    expected_sql: str


@dataclass(frozen=True)
class GoldenQuestionResult:
    id: str
    question: str
    passed: bool
    generated_sql: str
    expected_sql: str
    error: str = ""


def load_golden_questions(path: str) -> List[GoldenQuestion]:
    raw_path = Path(path)
    with raw_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    questions = raw.get("questions", [])
    if not isinstance(questions, list) or not questions:
        raise ValueError("Golden questions file must define a non-empty questions list.")
    return [_golden_question_from_dict(item) for item in questions]


def evaluate_golden_questions(
    semantic_layer: SemanticLayer,
    questions: Sequence[GoldenQuestion],
) -> List[GoldenQuestionResult]:
    allowed_tables = [table.physical_name for table in semantic_layer.tables]
    results = []
    for question in questions:
        try:
            generated_sql = semantic_layer.build_metric_query(
                metric_name=question.metric,
                dimensions=question.dimensions,
                filters=question.filters,
                named_filters=question.named_filters,
                limit=question.limit,
            )
            validate_readonly_sql(generated_sql, allowed_tables=allowed_tables)
            expected_sql = _normalize_sql(question.expected_sql)
            passed = _normalize_sql(generated_sql) == expected_sql
            results.append(
                GoldenQuestionResult(
                    id=question.id,
                    question=question.question,
                    passed=passed,
                    generated_sql=generated_sql,
                    expected_sql=question.expected_sql,
                )
            )
        except Exception as exc:
            results.append(
                GoldenQuestionResult(
                    id=question.id,
                    question=question.question,
                    passed=False,
                    generated_sql="",
                    expected_sql=question.expected_sql,
                    error=str(exc),
                )
            )
    return results


def summarize_results(results: Sequence[GoldenQuestionResult]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
    }


def _golden_question_from_dict(raw: Mapping[str, Any]) -> GoldenQuestion:
    request = raw.get("semantic_request", {})
    if not isinstance(request, Mapping):
        raise ValueError(f"Golden question {raw.get('id', '<unknown>')} must define semantic_request.")
    return GoldenQuestion(
        id=str(raw["id"]),
        question=str(raw["question"]),
        metric=str(request["metric"]),
        dimensions=tuple(str(item) for item in request.get("dimensions", [])),
        filters=dict(request.get("filters", {})),
        named_filters=tuple(str(item) for item in request.get("named_filters", [])),
        limit=request.get("limit"),
        expected_sql=str(raw["expected_sql"]),
    )


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").split())

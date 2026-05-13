import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml


@dataclass(frozen=True)
class SemanticColumn:
    name: str
    expr: str
    description: str = ""
    synonyms: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SemanticMetric:
    name: str
    expr: str
    description: str = ""
    synonyms: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SemanticFilter:
    name: str
    expr: str
    description: str = ""
    synonyms: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SemanticTable:
    name: str
    physical_name: str
    description: str = ""
    dimensions: Tuple[SemanticColumn, ...] = field(default_factory=tuple)
    metrics: Tuple[SemanticMetric, ...] = field(default_factory=tuple)
    filters: Tuple[SemanticFilter, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SemanticLayer:
    name: str
    description: str
    default_limit: int
    tables: Tuple[SemanticTable, ...]

    @classmethod
    def from_file(cls, path: str) -> "SemanticLayer":
        raw_path = Path(path)
        with raw_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SemanticLayer":
        tables = tuple(_table_from_dict(item) for item in raw.get("tables", []))
        if not tables:
            raise ValueError("Semantic layer must define at least one table.")
        return cls(
            name=str(raw.get("name", "default")),
            description=str(raw.get("description", "")),
            default_limit=int(raw.get("default_limit", 50)),
            tables=tables,
        )

    def prompt_context(self) -> str:
        payload = {
            "name": self.name,
            "description": self.description,
            "default_limit": self.default_limit,
            "tables": [
                {
                    "name": table.name,
                    "physical_name": table.physical_name,
                    "description": table.description,
                    "dimensions": [_column_context(col) for col in table.dimensions],
                    "metrics": [_metric_context(metric) for metric in table.metrics],
                    "filters": [_filter_context(filter_) for filter_ in table.filters],
                }
                for table in self.tables
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def build_metric_query(
        self,
        metric_name: str,
        dimensions: Sequence[str],
        filters: Mapping[str, Any],
        named_filters: Sequence[str],
        limit: Optional[int] = None,
    ) -> str:
        table, metric = self._find_metric(metric_name)
        selected_dimensions = [self._find_dimension(table, item) for item in dimensions]
        where_exprs = [self._find_filter(table, item).expr for item in named_filters]
        where_exprs.extend(_compile_dimension_filters(table, filters))

        select_parts = [f"{dimension.expr} AS {dimension.name}" for dimension in selected_dimensions]
        select_parts.append(f"{metric.expr} AS {metric.name}")

        sql = f"SELECT {', '.join(select_parts)} FROM {table.physical_name}"
        if where_exprs:
            sql += " WHERE " + " AND ".join(f"({expr})" for expr in where_exprs)
        if selected_dimensions:
            sql += " GROUP BY " + ", ".join(dimension.expr for dimension in selected_dimensions)
            sql += f" ORDER BY {metric.name} DESC"

        safe_limit = _safe_limit(limit, self.default_limit)
        return f"{sql} LIMIT {safe_limit}"

    def _find_metric(self, name: str) -> Tuple[SemanticTable, SemanticMetric]:
        wanted = _normalize_name(name)
        for table in self.tables:
            for metric in table.metrics:
                names = (metric.name, *metric.synonyms)
                if wanted in {_normalize_name(item) for item in names}:
                    return table, metric
        raise ValueError(f"Unknown semantic metric: {name}")

    def _find_dimension(self, table: SemanticTable, name: str) -> SemanticColumn:
        wanted = _normalize_name(name)
        for dimension in table.dimensions:
            names = (dimension.name, *dimension.synonyms)
            if wanted in {_normalize_name(item) for item in names}:
                return dimension
        raise ValueError(f"Unknown dimension for table {table.name}: {name}")

    def _find_filter(self, table: SemanticTable, name: str) -> SemanticFilter:
        wanted = _normalize_name(name)
        for filter_ in table.filters:
            names = (filter_.name, *filter_.synonyms)
            if wanted in {_normalize_name(item) for item in names}:
                return filter_
        raise ValueError(f"Unknown named filter for table {table.name}: {name}")


def parse_name_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array.")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_filters(value: Any) -> Dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    parsed = json.loads(str(value))
    if not isinstance(parsed, dict):
        raise ValueError("filters_json must be a JSON object.")
    return parsed


def _table_from_dict(raw: Mapping[str, Any]) -> SemanticTable:
    physical_name = raw.get("physical_name") or raw.get("table")
    if not physical_name:
        raise ValueError(f"Semantic table {raw.get('name', '<unknown>')} must define physical_name.")
    return SemanticTable(
        name=str(raw["name"]),
        physical_name=str(physical_name),
        description=str(raw.get("description", "")),
        dimensions=tuple(_column_from_dict(item) for item in raw.get("dimensions", [])),
        metrics=tuple(_metric_from_dict(item) for item in raw.get("metrics", [])),
        filters=tuple(_filter_from_dict(item) for item in raw.get("filters", [])),
    )


def _column_from_dict(raw: Mapping[str, Any]) -> SemanticColumn:
    return SemanticColumn(
        name=str(raw["name"]),
        expr=str(raw.get("expr", raw["name"])),
        description=str(raw.get("description", "")),
        synonyms=tuple(str(item) for item in raw.get("synonyms", [])),
    )


def _metric_from_dict(raw: Mapping[str, Any]) -> SemanticMetric:
    return SemanticMetric(
        name=str(raw["name"]),
        expr=str(raw["expr"]),
        description=str(raw.get("description", "")),
        synonyms=tuple(str(item) for item in raw.get("synonyms", [])),
    )


def _filter_from_dict(raw: Mapping[str, Any]) -> SemanticFilter:
    return SemanticFilter(
        name=str(raw["name"]),
        expr=str(raw["expr"]),
        description=str(raw.get("description", "")),
        synonyms=tuple(str(item) for item in raw.get("synonyms", [])),
    )


def _column_context(column: SemanticColumn) -> Dict[str, Any]:
    return {
        "name": column.name,
        "expr": column.expr,
        "description": column.description,
        "synonyms": list(column.synonyms),
    }


def _metric_context(metric: SemanticMetric) -> Dict[str, Any]:
    return {
        "name": metric.name,
        "expr": metric.expr,
        "description": metric.description,
        "synonyms": list(metric.synonyms),
    }


def _filter_context(filter_: SemanticFilter) -> Dict[str, Any]:
    return {
        "name": filter_.name,
        "expr": filter_.expr,
        "description": filter_.description,
        "synonyms": list(filter_.synonyms),
    }


def _compile_dimension_filters(table: SemanticTable, filters: Mapping[str, Any]) -> List[str]:
    expressions = []
    dimensions = {_normalize_name(dimension.name): dimension for dimension in table.dimensions}
    aliases = {
        _normalize_name(alias): dimension
        for dimension in table.dimensions
        for alias in dimension.synonyms
    }
    dimensions.update(aliases)

    for key, value in filters.items():
        dimension = dimensions.get(_normalize_name(str(key)))
        if dimension is None:
            raise ValueError(f"Unknown dimension filter for table {table.name}: {key}")
        expressions.append(_comparison_expr(dimension.expr, value))
    return expressions


def _comparison_expr(expr: str, value: Any) -> str:
    if isinstance(value, list):
        if not value:
            raise ValueError("List filters must not be empty.")
        return f"{expr} IN ({', '.join(_sql_literal(item) for item in value)})"
    if value is None:
        return f"{expr} IS NULL"
    return f"{expr} = {_sql_literal(value)}"


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _normalize_name(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _safe_limit(limit: Optional[int], default_limit: int) -> int:
    if limit is None:
        limit = default_limit
    return max(1, min(int(limit), 500))

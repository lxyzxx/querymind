from pathlib import Path
from typing import Any, Dict

from querymind.agent.postgres import execute_readonly_sql
from querymind.agent.semantic_layer import SemanticLayer
from querymind.core import (
    BasicQueryPlanner,
    QueryPlan,
    QueryResult,
    build_month_over_month_sql,
    can_build_comparison_query,
    generate_basic_insight,
    generate_comparison_insight,
)


DEFAULT_SEMANTIC_LAYER = "querymind/example/semantic_layer.yaml"


def create_app():
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI is not installed. Run: python3 -m pip install -r requirements-server.txt"
        ) from exc

    app = FastAPI(
        title="QueryMind API",
        description="Governed AI2SQL / NL2Query API for business data querying.",
        version="0.1.0",
    )

    @app.get("/", response_class=HTMLResponse)
    def playground() -> str:
        return playground_html()

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/plan")
    def plan_query(payload: Dict[str, Any]) -> Dict[str, Any]:
        return plan_payload(payload)

    @app.post("/compile-sql")
    def compile_sql(payload: Dict[str, Any]) -> Dict[str, Any]:
        return compile_sql_payload(payload)

    @app.post("/analyze-demo")
    def analyze_demo(payload: Dict[str, Any]) -> Dict[str, Any]:
        return analyze_demo_payload(payload)

    @app.post("/analyze-pg")
    def analyze_pg(payload: Dict[str, Any]) -> Dict[str, Any]:
        return analyze_pg_payload(payload)

    @app.post("/insight")
    def insight(payload: Dict[str, Any]) -> Dict[str, Any]:
        return insight_payload(payload)

    return app


def playground_html() -> str:
    path = Path(__file__).with_name("static").joinpath("index.html")
    return path.read_text(encoding="utf-8")


def plan_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    layer = _load_layer(payload)
    planner = BasicQueryPlanner(layer)
    plan = planner.plan(str(payload.get("question", "")), limit=payload.get("limit"))
    return {"plan": plan.to_dict()}


def compile_sql_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    layer = _load_layer(payload)
    plan = QueryPlan.from_dict(payload.get("plan", {}))
    if plan.needs_clarification:
        return {"plan": plan.to_dict(), "sql": "", "needs_clarification": True}
    sql = layer.build_metric_query(
        metric_name=plan.metric,
        dimensions=plan.dimensions,
        filters=plan.filters,
        named_filters=plan.named_filters,
        limit=plan.limit,
    )
    return {"plan": plan.to_dict(), "sql": sql}


def analyze_demo_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    layer = _load_layer(payload)
    planner = BasicQueryPlanner(layer)
    plan = planner.plan(str(payload.get("question", "")), limit=payload.get("limit"))
    if plan.needs_clarification:
        return {
            "plan": plan.to_dict(),
            "sql": "",
            "result": {"sql": "", "row_count": 0, "rows": [], "source": "mock"},
            "insight": {
                "answer": plan.clarification_question or "需要补充查询条件。",
                "observations": [],
                "possible_causes": [],
                "recommended_actions": [],
                "evidence": [],
            },
        }

    sql = layer.build_metric_query(
        metric_name=plan.metric,
        dimensions=plan.dimensions,
        filters=plan.filters,
        named_filters=plan.named_filters,
        limit=plan.limit,
    )
    result = QueryResult(sql=sql, rows=_mock_rows(plan))
    insight = generate_basic_insight(plan, result)
    return {
        "plan": plan.to_dict(),
        "sql": sql,
        "result": {**result.to_dict(), "source": "mock"},
        "insight": insight.to_dict(),
    }


def analyze_pg_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    layer = _load_layer(payload)
    planner = BasicQueryPlanner(layer)
    plan = planner.plan(str(payload.get("question", "")), limit=payload.get("limit"))
    if plan.needs_clarification:
        return _clarification_response(plan)

    if can_build_comparison_query(plan):
        sql = build_month_over_month_sql(layer, plan)
    else:
        sql = layer.build_metric_query(
            metric_name=plan.metric,
            dimensions=plan.dimensions,
            filters=plan.filters,
            named_filters=plan.named_filters,
            limit=plan.limit,
        )
    allowed_tables = [table.physical_name for table in layer.tables]
    pg_result = execute_readonly_sql(sql, plan.limit, allowed_tables=allowed_tables)
    result = QueryResult(sql=sql, rows=pg_result["rows"], row_count=pg_result["row_count"])
    insight = (
        generate_comparison_insight(plan, result)
        if can_build_comparison_query(plan)
        else generate_basic_insight(plan, result)
    )
    return {
        "plan": plan.to_dict(),
        "sql": sql,
        "result": {**result.to_dict(), "source": "postgres"},
        "insight": insight.to_dict(),
    }


def insight_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    plan = QueryPlan.from_dict(payload.get("plan", {}))
    result_payload = payload.get("result", {})
    result = QueryResult(
        sql=str(result_payload.get("sql", "")),
        rows=result_payload.get("rows", []),
        row_count=result_payload.get("row_count"),
    )
    return generate_basic_insight(plan, result).to_dict()


def _load_layer(payload: Dict[str, Any]) -> SemanticLayer:
    return SemanticLayer.from_file(str(payload.get("semantic_layer", DEFAULT_SEMANTIC_LAYER)))


def _clarification_response(plan: QueryPlan) -> Dict[str, Any]:
    return {
        "plan": plan.to_dict(),
        "sql": "",
        "result": {"sql": "", "row_count": 0, "rows": [], "source": "none"},
        "insight": {
            "answer": plan.clarification_question or "需要补充查询条件。",
            "observations": [],
            "possible_causes": [],
            "recommended_actions": [],
            "evidence": [],
        },
    }


def _mock_rows(plan: QueryPlan) -> list:
    metric = plan.metric or "value"
    if plan.dimensions:
        dimension = plan.dimensions[0]
        if dimension == "status" and "active_only" in plan.named_filters:
            return [{dimension: "active", metric: 1280}]
        return [
            {dimension: "active", metric: 1280},
            {dimension: "inactive", metric: 320},
        ]
    return [{metric: 1600}]


app = create_app()

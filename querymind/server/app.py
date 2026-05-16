from typing import Any, Dict

from querymind.agent.semantic_layer import SemanticLayer
from querymind.core import QueryPlan, QueryResult, generate_basic_insight


def create_app():
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI is not installed. Run: python3 -m pip install -r requirements-server.txt"
        ) from exc

    app = FastAPI(
        title="QueryMind API",
        description="Governed AI2SQL / NL2Query API for business data querying.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/compile-sql")
    def compile_sql(payload: Dict[str, Any]) -> Dict[str, Any]:
        layer = SemanticLayer.from_file(
            str(payload.get("semantic_layer", "querymind/example/semantic_layer.yaml"))
        )
        plan = QueryPlan.from_dict(payload.get("plan", {}))
        sql = layer.build_metric_query(
            metric_name=plan.metric,
            dimensions=plan.dimensions,
            filters=plan.filters,
            named_filters=plan.named_filters,
            limit=plan.limit,
        )
        return {"plan": plan.to_dict(), "sql": sql}

    @app.post("/insight")
    def insight(payload: Dict[str, Any]) -> Dict[str, Any]:
        plan = QueryPlan.from_dict(payload.get("plan", {}))
        result_payload = payload.get("result", {})
        result = QueryResult(
            sql=str(result_payload.get("sql", "")),
            rows=result_payload.get("rows", []),
            row_count=result_payload.get("row_count"),
        )
        return generate_basic_insight(plan, result).to_dict()

    return app


app = create_app()

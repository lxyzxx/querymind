from datetime import date, timedelta
from typing import Any, Optional

from querymind.core.models import QueryPlan


def can_build_trend_query(plan: QueryPlan) -> bool:
    return plan.question_type == "trend" and plan.comparison == "recent_7_days"


def build_recent_7_days_sql(
    semantic_layer: Any,
    plan: QueryPlan,
    today: Optional[date] = None,
) -> str:
    table, metric = semantic_layer._find_metric(plan.metric)
    dimension = _time_dimension(semantic_layer, table, plan)
    end_date = today or date.today()
    start_date = end_date - timedelta(days=6)
    next_date = end_date + timedelta(days=1)

    sql = (
        f"SELECT {dimension.expr} AS {dimension.name}, {metric.expr} AS {metric.name} "
        f"FROM {table.physical_name} "
        f"WHERE created_at >= DATE '{start_date}' AND created_at < DATE '{next_date}' "
        f"GROUP BY {dimension.expr} "
        f"ORDER BY {dimension.expr}"
    )
    if plan.limit:
        sql += f" LIMIT {max(1, min(int(plan.limit), 500))}"
    return sql


def _time_dimension(semantic_layer: Any, table: Any, plan: QueryPlan):
    for name in [*plan.dimensions, "order_date", "session_date", "signup_date"]:
        try:
            return semantic_layer._find_dimension(table, name)
        except ValueError:
            continue
    raise ValueError(f"No time dimension is defined for table {table.name}.")

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from querymind.core.models import Insight, InsightEvidence, QueryPlan, QueryResult


def can_build_comparison_query(plan: QueryPlan) -> bool:
    return plan.question_type == "diagnosis" and plan.comparison == "month_over_month"


def build_month_over_month_sql(
    semantic_layer: Any,
    plan: QueryPlan,
    today: Optional[date] = None,
) -> str:
    if plan.comparison != "month_over_month":
        raise ValueError(f"Unsupported comparison: {plan.comparison}")

    table, metric = semantic_layer._find_metric(plan.metric)
    breakdown = _find_breakdown(semantic_layer, table, plan.breakdowns)
    previous_start, current_start, next_start = _month_windows(today or date.today())
    filters = [f"created_at >= DATE '{previous_start}'", f"created_at < DATE '{next_start}'"]
    filters.extend(f"({semantic_layer._find_filter(table, item).expr})" for item in plan.named_filters)

    select_parts = [
        (
            "CASE "
            f"WHEN created_at >= DATE '{current_start}' AND created_at < DATE '{next_start}' "
            "THEN 'current_period' "
            f"WHEN created_at >= DATE '{previous_start}' AND created_at < DATE '{current_start}' "
            "THEN 'previous_period' "
            "END AS period"
        )
    ]
    group_parts = ["period"]
    order_parts = ["period"]
    if breakdown is not None:
        select_parts.append(f"{breakdown.expr} AS {breakdown.name}")
        group_parts.append(breakdown.expr)
        order_parts.append(breakdown.name)
    select_parts.append(f"{metric.expr} AS {metric.name}")

    sql = (
        f"SELECT {', '.join(select_parts)} FROM {table.physical_name} "
        f"WHERE {' AND '.join(filters)} "
        f"GROUP BY {', '.join(group_parts)} "
        f"ORDER BY {', '.join(order_parts)}"
    )
    if plan.limit:
        sql += f" LIMIT {max(1, min(int(plan.limit), 500))}"
    return sql


def generate_comparison_insight(plan: QueryPlan, result: QueryResult) -> Insight:
    rows = result.rows
    metric = plan.metric
    if not rows:
        return Insight(
            answer=f"没有查询到可用于对比 {metric} 的数据。",
            observations=["对比查询结果为空。"],
            recommended_actions=["确认对比周期、筛选条件和数据源是否正确。"],
            evidence=[InsightEvidence(label="row_count", value=result.row_count)],
        )

    current_total, previous_total = _period_totals(rows, metric)
    delta = current_total - previous_total
    pct = _pct(delta, previous_total)
    biggest_drop = _biggest_drop(rows, metric)

    observations = [
        f"当前周期 {metric} 为 {_fmt(current_total)}。",
        f"对比周期 {metric} 为 {_fmt(previous_total)}。",
        f"变化量为 {_fmt(delta)}，变化率为 {pct}。",
    ]
    causes = []
    actions = []
    if biggest_drop is not None:
        label, current_value, previous_value, contribution = biggest_drop
        causes.append(
            f"{label} 下降最明显，从 {_fmt(previous_value)} 降至 {_fmt(current_value)}，贡献变化 {_fmt(contribution)}。"
        )
        actions.append(f"优先检查 {label} 的投放、流量、转化和商品供给变化。")
    if delta < 0:
        answer = f"{metric} 当前周期比对比周期少 {_fmt(abs(delta))}，变化率 {pct}。"
        actions.append("继续按渠道、商品、地区和新老客拆解，定位贡献最大的下降项。")
    elif delta > 0:
        answer = f"{metric} 当前周期比对比周期高 {_fmt(delta)}，变化率 {pct}。"
        actions.append("复盘增长贡献最大的维度，判断是否可以扩大投入。")
    else:
        answer = f"{metric} 当前周期与对比周期基本持平。"
        actions.append("继续观察关键维度，确认是否存在结构性波动。")

    return Insight(
        answer=answer,
        observations=observations,
        possible_causes=causes,
        recommended_actions=actions,
        evidence=[
            InsightEvidence(label="metric", value=metric, source="query_plan"),
            InsightEvidence(label="current_total", value=current_total),
            InsightEvidence(label="previous_total", value=previous_total),
            InsightEvidence(label="delta", value=delta),
        ],
    )


def _find_breakdown(semantic_layer: Any, table: Any, breakdowns: List[str]):
    if not breakdowns:
        return None
    return semantic_layer._find_dimension(table, breakdowns[0])


def _month_windows(today: date) -> Tuple[date, date, date]:
    next_start = today.replace(day=1)
    current_month_last_day = next_start.toordinal() - 1
    current_start = date.fromordinal(current_month_last_day).replace(day=1)
    previous_month_last_day = current_start.toordinal() - 1
    previous_start = date.fromordinal(previous_month_last_day).replace(day=1)
    return previous_start, current_start, next_start


def _period_totals(rows: List[Dict[str, Any]], metric: str) -> Tuple[float, float]:
    current = sum(_number(row.get(metric)) for row in rows if row.get("period") == "current_period")
    previous = sum(_number(row.get(metric)) for row in rows if row.get("period") == "previous_period")
    return current, previous


def _biggest_drop(rows: List[Dict[str, Any]], metric: str) -> Optional[Tuple[str, float, float, float]]:
    values: Dict[str, Dict[str, float]] = {}
    for row in rows:
        label = _breakdown_label(row)
        if not label:
            continue
        period = str(row.get("period"))
        values.setdefault(label, {"current_period": 0.0, "previous_period": 0.0})
        values[label][period] = values[label].get(period, 0.0) + _number(row.get(metric))

    drops = []
    for label, periods in values.items():
        current = periods.get("current_period", 0.0)
        previous = periods.get("previous_period", 0.0)
        drops.append((current - previous, label, current, previous))
    if not drops:
        return None
    contribution, label, current, previous = min(drops)
    return label, current, previous, contribution


def _breakdown_label(row: Dict[str, Any]) -> str:
    for key, value in row.items():
        if key not in {"period"} and not isinstance(value, (int, float)):
            return f"{key}={value}"
    return ""


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _pct(delta: float, base: float) -> str:
    if base == 0:
        return "N/A"
    return f"{delta / base:.1%}"


def _fmt(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"

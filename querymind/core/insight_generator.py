from typing import Any, Dict, List, Optional, Tuple

from querymind.core.models import Insight, InsightEvidence, QueryPlan, QueryResult


class BasicInsightGenerator:
    """Deterministic fallback for turning query results into business insights."""

    def generate(self, plan: QueryPlan, result: QueryResult) -> Insight:
        if not result.rows:
            return Insight(
                answer=f"没有查询到与 {plan.metric} 相关的数据。",
                observations=["查询结果为空。"],
                recommended_actions=["确认筛选条件、时间范围和数据源是否正确。"],
                evidence=[InsightEvidence(label="row_count", value=result.row_count)],
            )

        metric_value = _first_metric_value(plan.metric, result.rows[0])
        evidence = [
            InsightEvidence(label="metric", value=plan.metric, source="query_plan"),
            InsightEvidence(label="row_count", value=result.row_count),
        ]
        if metric_value is not None:
            evidence.append(InsightEvidence(label=metric_value[0], value=metric_value[1]))

        observations = _observations(plan, result, metric_value)
        possible_causes = _possible_causes(plan, result)
        recommended_actions = _recommended_actions(plan, result)

        return Insight(
            answer=_answer(plan, result, metric_value),
            observations=observations,
            possible_causes=possible_causes,
            recommended_actions=recommended_actions,
            evidence=evidence,
        )


def generate_basic_insight(plan: QueryPlan, result: QueryResult) -> Insight:
    return BasicInsightGenerator().generate(plan, result)


def _first_metric_value(metric: str, row: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
    if metric in row:
        return metric, row[metric]

    normalized_metric = metric.lower()
    for key, value in row.items():
        if key.lower() == normalized_metric:
            return key, value

    numeric_items = [
        (key, value)
        for key, value in row.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if len(numeric_items) == 1:
        return numeric_items[0]
    return None


def _answer(
    plan: QueryPlan,
    result: QueryResult,
    metric_value: Optional[Tuple[str, Any]],
) -> str:
    if metric_value is None:
        return f"已查询到 {result.row_count} 行结果，但没有识别出单一的 {plan.metric} 指标值。"

    _, value = metric_value
    if plan.question_type == "trend":
        trend = _trend_values(plan, result)
        if trend is not None:
            first_label, first_value, last_label, last_value = trend
            delta = last_value - first_value
            return (
                f"{plan.metric} 最近趋势返回 {result.row_count} 个时间点，"
                f"最新 {last_label} 为 {_fmt_number(last_value)}，"
                f"较 {first_label} 变化 {_fmt_number(delta)}。"
            )
    if plan.question_type == "ranking":
        leader = _dimension_label(plan, result.rows[0])
        if leader:
            return f"{leader} 的 {plan.metric} 最高，为 {value}。"
    if plan.question_type == "diagnosis":
        return f"{plan.metric} 的当前查询结果为 {value}，需要结合拆解维度判断变化原因。"
    return f"{plan.metric} 的查询结果为 {value}。"


def _observations(
    plan: QueryPlan,
    result: QueryResult,
    metric_value: Optional[Tuple[str, Any]],
) -> List[str]:
    observations = [f"查询返回 {result.row_count} 行结果。"]
    if plan.filters:
        observations.append(f"已应用 {len(plan.filters)} 个显式筛选条件。")
    if plan.named_filters:
        observations.append(f"已应用命名过滤器：{', '.join(plan.named_filters)}。")
    if plan.comparison:
        observations.append(f"对比口径：{plan.comparison}。")
    if plan.question_type == "trend":
        trend = _trend_values(plan, result)
        if trend is not None:
            first_label, first_value, last_label, last_value = trend
            observations.append(
                f"趋势从 {first_label} 的 {_fmt_number(first_value)} 变化到 {last_label} 的 {_fmt_number(last_value)}。"
            )
    if plan.question_type in {"ranking", "diagnosis"} and result.rows:
        label = _dimension_label(plan, result.rows[0])
        if label:
            observations.append(f"首行结果对应 {label}。")
    if metric_value is not None:
        observations.append(f"指标字段 {metric_value[0]} 的首行值为 {metric_value[1]}。")
    return observations


def _possible_causes(plan: QueryPlan, result: QueryResult) -> List[str]:
    if plan.question_type != "diagnosis":
        return []

    causes = []
    if plan.breakdowns:
        causes.append(f"优先从 {', '.join(plan.breakdowns)} 这些拆解维度中定位贡献最大的变化项。")
    elif plan.dimensions:
        causes.append(f"当前按 {', '.join(plan.dimensions)} 拆解，异常可能集中在首行或头部维度值。")
    else:
        causes.append("当前结果缺少拆解维度，无法直接定位下降或异常的主要贡献项。")

    if result.row_count and result.row_count > 1:
        causes.append("结果包含多行，可进一步按指标差异或占比排序识别主要贡献。")
    return causes


def _recommended_actions(plan: QueryPlan, result: QueryResult) -> List[str]:
    if plan.question_type == "diagnosis":
        if plan.breakdowns:
            return [
                "对各拆解维度分别计算变化贡献度。",
                "优先检查贡献最大的维度项对应的业务动作、库存、渠道或客户变化。",
            ]
        return ["补充对比周期和拆解维度后再做归因分析。"]

    if plan.question_type == "trend":
        return ["继续查看同比、环比和异常日期，确认趋势是否由单日波动造成。"]
    if plan.question_type == "comparison":
        return ["查看差异最大的维度项，确认差异来自结构变化还是总体规模变化。"]
    if result.row_count == 1:
        return ["如需进一步分析，可增加时间、地区、渠道或品类维度。"]
    return ["可继续按关键维度排序或下钻查看明细。"]


def _dimension_label(plan: QueryPlan, row: Dict[str, Any]) -> Optional[str]:
    for dimension in plan.dimensions:
        if dimension in row:
            return f"{dimension}={row[dimension]}"
    for breakdown in plan.breakdowns:
        if breakdown in row:
            return f"{breakdown}={row[breakdown]}"
    return None


def _trend_values(plan: QueryPlan, result: QueryResult) -> Optional[Tuple[str, float, str, float]]:
    if not result.rows:
        return None
    first = result.rows[0]
    last = result.rows[-1]
    first_metric = _first_metric_value(plan.metric, first)
    last_metric = _first_metric_value(plan.metric, last)
    if first_metric is None or last_metric is None:
        return None
    first_label = _first_label(first)
    last_label = _first_label(last)
    if first_label is None or last_label is None:
        return None
    return first_label, float(first_metric[1]), last_label, float(last_metric[1])


def _first_label(row: Dict[str, Any]) -> Optional[str]:
    for value in row.values():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return str(value)
    return None


def _fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"

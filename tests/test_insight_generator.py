from querymind.core import QueryPlan, QueryResult, generate_basic_insight


def test_generate_basic_fact_insight():
    plan = QueryPlan(
        question="这个月销售额多少？",
        question_type="fact",
        metric="sales_amount",
        filters={"month": "current"},
    )
    result = QueryResult(
        sql="select sum(amount) as sales_amount from orders",
        rows=[{"sales_amount": 1286000}],
    )

    insight = generate_basic_insight(plan, result)

    assert insight.answer == "sales_amount 的查询结果为 1286000。"
    assert "已应用 1 个显式筛选条件。" in insight.observations
    assert insight.evidence[-1].label == "sales_amount"


def test_generate_basic_ranking_insight_uses_top_dimension():
    plan = QueryPlan(
        question="哪个地区销售额最高？",
        question_type="ranking",
        metric="sales_amount",
        dimensions=["region"],
    )
    result = QueryResult(
        sql="select region, sum(amount) as sales_amount from orders group by region",
        rows=[
            {"region": "华东", "sales_amount": 300},
            {"region": "华南", "sales_amount": 200},
        ],
    )

    insight = generate_basic_insight(plan, result)

    assert insight.answer == "region=华东 的 sales_amount 最高，为 300。"
    assert "首行结果对应 region=华东。" in insight.observations


def test_generate_basic_diagnosis_insight_recommends_breakdowns():
    plan = QueryPlan(
        question="为什么华南销售额下降？",
        question_type="diagnosis",
        metric="sales_amount",
        filters={"region": "华南"},
        breakdowns=["product_category", "channel"],
    )
    result = QueryResult(
        sql="select product_category, sales_amount from t",
        rows=[{"product_category": "家电", "sales_amount": -98000}],
    )

    insight = generate_basic_insight(plan, result)

    assert "需要结合拆解维度判断变化原因" in insight.answer
    assert insight.possible_causes == [
        "优先从 product_category, channel 这些拆解维度中定位贡献最大的变化项。"
    ]
    assert insight.recommended_actions[0] == "对各拆解维度分别计算变化贡献度。"


def test_generate_basic_empty_result_insight():
    plan = QueryPlan(question="查销售额", question_type="fact", metric="sales_amount")
    result = QueryResult(sql="select 1 where false", rows=[])

    insight = generate_basic_insight(plan, result)

    assert insight.answer == "没有查询到与 sales_amount 相关的数据。"
    assert insight.recommended_actions == ["确认筛选条件、时间范围和数据源是否正确。"]

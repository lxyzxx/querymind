from querymind.core import Insight, QueryPlan
from querymind.server.app import analyze_demo_payload, analyze_pg_payload, plan_payload, playground_html


DEMO_ALLOWED_TABLES = [
    "public.querymind_demo_users",
    "public.querymind_demo_orders",
    "public.querymind_demo_sessions",
]


def test_playground_page_loads():
    assert "QueryMind Playground" in playground_html()


def test_plan_and_analyze_demo_endpoints():
    payload = {"question": "按用户状态统计活跃用户数", "limit": 20}
    plan_response = plan_payload(payload)
    analyze_response = analyze_demo_payload(payload)

    assert plan_response["plan"]["metric"] == "user_count"
    assert "GROUP BY status" in analyze_response["sql"]
    assert analyze_response["result"]["source"] == "mock"
    assert analyze_response["result"]["rows"] == [{"status": "active", "user_count": 1280}]


def test_analyze_pg_endpoint_uses_postgres_executor(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "GROUP BY status" in sql
        assert limit == 20
        assert allowed_tables == DEMO_ALLOWED_TABLES
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"status": "active", "user_count": 3}],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "按用户状态统计活跃用户数", "limit": 20})

    assert response["result"]["source"] == "postgres"
    assert response["result"]["rows"] == [{"status": "active", "user_count": 3}]
    assert response["insight"]["recommended_actions"]


def test_analyze_pg_clarifies_unknown_metric():
    response = analyze_pg_payload({"question": "客诉率情况如何", "limit": 20})

    assert response["plan"]["needs_clarification"] is True
    assert response["sql"] == ""
    assert response["result"]["source"] == "none"
    assert response["plan_source"] == "deterministic"


def test_analyze_pg_handles_gmv_question(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "FROM public.querymind_demo_orders" in sql
        assert limit == 20
        assert allowed_tables == DEMO_ALLOWED_TABLES
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"gmv": 10100}],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "GMV情况如何", "limit": 20})

    assert response["plan"]["metric"] == "gmv"
    assert response["result"]["source"] == "postgres"
    assert response["result"]["rows"] == [{"gmv": 10100}]
    assert response["insight"]["answer"] == "gmv 的查询结果为 10100。"


def test_analyze_pg_handles_recent_gmv_trend(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "created_at >= DATE" in sql
        assert "GROUP BY date(created_at)" in sql
        assert "ORDER BY date(created_at)" in sql
        assert allowed_tables == DEMO_ALLOWED_TABLES
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 3,
            "rows": [
                {"order_date": "2026-05-13", "gmv": 900},
                {"order_date": "2026-05-15", "gmv": 1100},
                {"order_date": "2026-05-18", "gmv": 600},
            ],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "最近7天GMV趋势如何？", "limit": 20})

    assert response["plan"]["question_type"] == "trend"
    assert response["plan"]["comparison"] == "recent_7_days"
    assert response["result"]["row_count"] == 3


def test_analyze_pg_handles_channel_ranking(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "GROUP BY channel" in sql
        assert "ORDER BY gmv DESC" in sql
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"channel": "organic", "gmv": 4700}],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "哪个渠道GMV最高？", "limit": 20})

    assert response["plan"]["question_type"] == "ranking"
    assert response["plan"]["dimensions"] == ["channel"]
    assert response["insight"]["answer"] == "channel=organic 的 gmv 最高，为 4700。"


def test_analyze_pg_handles_conversion_rate(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "FROM public.querymind_demo_sessions" in sql
        assert "converted" in sql
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"conversion_rate": 0.5}],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "转化率情况如何？", "limit": 20})

    assert response["plan"]["metric"] == "conversion_rate"
    assert response["result"]["rows"] == [{"conversion_rate": 0.5}]


def test_analyze_pg_handles_sales_drop_diagnosis(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "CASE WHEN created_at" in sql
        assert "GROUP BY period, channel" in sql
        assert "FROM public.querymind_demo_orders" in sql
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 6,
            "rows": [
                {"period": "current_period", "channel": "ads", "gmv": 700},
                {"period": "current_period", "channel": "organic", "gmv": 1800},
                {"period": "current_period", "channel": "referral", "gmv": 500},
                {"period": "previous_period", "channel": "ads", "gmv": 1800},
                {"period": "previous_period", "channel": "organic", "gmv": 2000},
                {"period": "previous_period", "channel": "referral", "gmv": 700},
            ],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload(
        {"question": "为什么上个月的销售额比上上个月的少，怎么优化？", "limit": 20}
    )

    assert response["plan"]["metric"] == "gmv"
    assert response["plan"]["comparison"] == "month_over_month"
    assert response["plan"]["breakdowns"] == ["channel"]
    assert "少 1500" in response["insight"]["answer"]
    assert "channel=ads" in response["insight"]["possible_causes"][0]
    assert response["plan_source"] == "deterministic"
    assert response["insight_source"] == "deterministic"


def test_analyze_pg_uses_llm_plan_and_insight_when_enabled(monkeypatch):
    class FakeClient:
        def generate_query_plan(self, question, semantic_context):
            return QueryPlan(
                question=question,
                question_type="fact",
                metric="gmv",
                limit=20,
            )

        def generate_insight(self, question, plan, result):
            return Insight(answer="LLM 生成的 GMV 分析。")

    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"gmv": 10100}],
        }

    monkeypatch.setattr("querymind.core.planning_pipeline.create_llm_client_from_env", lambda: FakeClient())
    monkeypatch.setattr("querymind.core.insight_pipeline.create_llm_client_from_env", lambda: FakeClient())
    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "GMV情况如何", "limit": 20, "use_llm": True})

    assert response["plan_source"] == "llm"
    assert response["insight_source"] == "llm"
    assert response["insight"]["answer"] == "LLM 生成的 GMV 分析。"

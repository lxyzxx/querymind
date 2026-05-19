from querymind.server.app import analyze_demo_payload, analyze_pg_payload, plan_payload, playground_html


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
        assert allowed_tables == ["public.querymind_demo_users", "public.querymind_demo_orders"]
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


def test_analyze_pg_handles_gmv_question(monkeypatch):
    def fake_execute_readonly_sql(sql, limit, allowed_tables=None):
        assert "FROM public.querymind_demo_orders" in sql
        assert limit == 20
        assert allowed_tables == ["public.querymind_demo_users", "public.querymind_demo_orders"]
        return {
            "sql": sql,
            "wrapped_sql": "select * from (...)",
            "limit": 20,
            "row_count": 1,
            "rows": [{"gmv": 7500}],
        }

    monkeypatch.setattr("querymind.server.app.execute_readonly_sql", fake_execute_readonly_sql)

    response = analyze_pg_payload({"question": "GMV情况如何", "limit": 20})

    assert response["plan"]["metric"] == "gmv"
    assert response["result"]["source"] == "postgres"
    assert response["result"]["rows"] == [{"gmv": 7500}]
    assert response["insight"]["answer"] == "gmv 的查询结果为 7500。"


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

from querymind.server.app import analyze_demo_payload, plan_payload, playground_html


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

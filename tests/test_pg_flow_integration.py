import argparse
import os

import pytest

from querymind.example.run_pg_flow import run_flow


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_end_to_end_flow():
    args = argparse.Namespace(
        question="按用户状态统计活跃用户数",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["metric"] == "user_count"
    assert "GROUP BY status" in response["sql"]
    assert response["result"]["source"] == "postgres"
    assert response["result"]["rows"] == [{"status": "active", "user_count": 3}]
    assert response["insight"]["answer"]


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_gmv_flow():
    args = argparse.Namespace(
        question="GMV情况如何",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["metric"] == "gmv"
    assert "FROM public.querymind_demo_orders" in response["sql"]
    assert response["result"]["source"] == "postgres"
    assert response["result"]["rows"] == [{"gmv": 10100}]
    assert response["insight"]["answer"]


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_sales_drop_diagnosis_flow():
    args = argparse.Namespace(
        question="为什么上个月的销售额比上上个月的少，怎么优化？",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["metric"] == "gmv"
    assert response["plan"]["comparison"] == "month_over_month"
    assert response["plan"]["breakdowns"] == ["channel"]
    assert response["result"]["source"] == "postgres"
    assert "GROUP BY period, channel" in response["sql"]
    assert "少 1500" in response["insight"]["answer"]
    assert "channel=ads" in response["insight"]["possible_causes"][0]


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_recent_gmv_trend_flow():
    args = argparse.Namespace(
        question="最近7天GMV趋势如何？",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["question_type"] == "trend"
    assert response["plan"]["comparison"] == "recent_7_days"
    assert "GROUP BY date(created_at)" in response["sql"]
    assert response["result"]["row_count"] == 3


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_channel_ranking_flow():
    args = argparse.Namespace(
        question="哪个渠道GMV最高？",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["question_type"] == "ranking"
    assert response["plan"]["dimensions"] == ["channel"]
    assert response["result"]["rows"][0] == {"channel": "organic", "gmv": 4700}


@pytest.mark.skipif(
    os.getenv("QUERYMIND_TEST_PG") != "1",
    reason="Set QUERYMIND_TEST_PG=1 to run the PostgreSQL integration flow.",
)
def test_postgres_conversion_rate_flow():
    args = argparse.Namespace(
        question="转化率情况如何？",
        semantic_layer="querymind/example/semantic_layer.yaml",
        limit=20,
        setup_demo_data=True,
        pg_host=None,
        pg_port=None,
        pg_dbname=None,
        pg_user=None,
        pg_password=None,
        pg_connect_timeout=None,
    )

    response = run_flow(args)

    assert response["plan"]["metric"] == "conversion_rate"
    assert response["result"]["rows"] == [{"conversion_rate": 0.5}]

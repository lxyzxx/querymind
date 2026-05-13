import pytest

from querymind.agent.semantic_layer import SemanticLayer, parse_filters, parse_name_list


def _demo_layer():
    return SemanticLayer.from_dict(
        {
            "name": "demo",
            "default_limit": 50,
            "tables": [
                {
                    "name": "users",
                    "physical_name": "public.users",
                    "dimensions": [
                        {"name": "status", "expr": "status", "synonyms": ["user_status"]},
                        {"name": "signup_date", "expr": "date(created_at)"},
                    ],
                    "metrics": [
                        {"name": "user_count", "expr": "count(*)", "synonyms": ["users"]},
                    ],
                    "filters": [
                        {"name": "active_only", "expr": "status = 'active'", "synonyms": ["active users"]},
                    ],
                }
            ],
        }
    )


def test_build_metric_query_with_named_filter():
    sql = _demo_layer().build_metric_query(
        metric_name="user_count",
        dimensions=["status"],
        filters={},
        named_filters=["active_only"],
        limit=20,
    )

    assert sql == (
        "SELECT status AS status, count(*) AS user_count FROM public.users "
        "WHERE (status = 'active') GROUP BY status ORDER BY user_count DESC LIMIT 20"
    )


def test_build_metric_query_accepts_synonyms_and_escapes_values():
    sql = _demo_layer().build_metric_query(
        metric_name="users",
        dimensions=["user_status"],
        filters={"status": "vip's"},
        named_filters=[],
        limit=10,
    )

    assert "status = 'vip''s'" in sql
    assert sql.endswith("LIMIT 10")


def test_build_metric_query_clamps_limit():
    sql = _demo_layer().build_metric_query(
        metric_name="user_count",
        dimensions=[],
        filters={},
        named_filters=[],
        limit=9999,
    )

    assert sql == "SELECT count(*) AS user_count FROM public.users LIMIT 500"


def test_unknown_metric_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown semantic metric"):
        _demo_layer().build_metric_query(
            metric_name="revenue",
            dimensions=[],
            filters={},
            named_filters=[],
        )


def test_parse_tool_arguments():
    assert parse_name_list("status, signup_date") == ["status", "signup_date"]
    assert parse_name_list('["status", "signup_date"]') == ["status", "signup_date"]
    assert parse_filters('{"status": ["active", "trial"]}') == {"status": ["active", "trial"]}


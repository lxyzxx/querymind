from querymind.config import load_dotenv


def test_load_dotenv_reads_values_without_overriding_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "QUERYMIND_LLM_ENABLED=true",
                "QUERYMIND_LLM_API_KEY=from_file",
                "QUOTED_VALUE='hello world'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("QUERYMIND_LLM_API_KEY", "already_set")

    load_dotenv(str(env_file))

    assert "QUERYMIND_LLM_ENABLED" in __import__("os").environ
    assert __import__("os").environ["QUERYMIND_LLM_API_KEY"] == "already_set"
    assert __import__("os").environ["QUOTED_VALUE"] == "hello world"

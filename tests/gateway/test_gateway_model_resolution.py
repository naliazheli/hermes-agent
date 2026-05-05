from gateway.run import _resolve_gateway_model


def test_api_server_model_env_overrides_default_config(monkeypatch):
    monkeypatch.setenv("API_SERVER_MODEL_NAME", "deepseek-v4-pro")
    monkeypatch.setenv("HERMES_MODEL", "env-fallback-model")

    model = _resolve_gateway_model(
        {
            "model": {
                "default": "anthropic/claude-opus-4.6",
                "provider": "custom",
            }
        }
    )

    assert model == "deepseek-v4-pro"


def test_blank_api_server_model_env_does_not_override_config(monkeypatch):
    monkeypatch.setenv("API_SERVER_MODEL_NAME", " ")
    monkeypatch.setenv("HERMES_MODEL", "env-fallback-model")

    model = _resolve_gateway_model({"model": {"default": "config-model"}})

    assert model == "config-model"

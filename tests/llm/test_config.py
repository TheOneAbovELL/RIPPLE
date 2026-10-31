import pytest

from ripple.core.errors import ConfigurationError
from ripple.llm.config import ModelSpec, RouterConfig


def test_models_for_returns_primary_then_fallbacks_in_order():
    config = RouterConfig(
        tasks={"linker": [ModelSpec(provider="a", model="1"), ModelSpec(provider="b", model="2")]}
    )
    assert [s.model for s in config.models_for("linker")] == ["1", "2"]


def test_models_for_unknown_task_raises_configuration_error():
    with pytest.raises(ConfigurationError, match="no models configured"):
        RouterConfig(tasks={}).models_for("resolver")


def test_models_for_empty_list_raises_configuration_error():
    with pytest.raises(ConfigurationError, match="empty model list"):
        RouterConfig(tasks={"resolver": []}).models_for("resolver")

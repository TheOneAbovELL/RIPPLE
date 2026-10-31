"""Router configuration: which model serves which task, retry budgets, prices (ADR-0010, ADR-0027).

Tasks are named by the caller ("resolver", "linker", "jd_parser", ...). Each task lists
its models in order: the first is primary, the rest are fallbacks. Eval runs pin a
config and record it in results/<run>/config.json (NFR-5). Prices are configuration
with a source and date; a model without a price reports cost as None (I8).
"""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ripple.core.errors import ConfigurationError


class ModelSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    model: str


class ModelPrice(BaseModel):
    """USD per million tokens, with where the number came from and when."""

    model_config = ConfigDict(frozen=True)

    input: float = Field(ge=0.0)
    output: float = Field(ge=0.0)
    source: str = Field(min_length=1)
    recorded: str = Field(min_length=1)  # ISO date the price was copied


class RouterConfig(BaseModel):
    tasks: dict[str, list[ModelSpec]]
    # Attempts per model before moving to the next: 1 first try + max_retries retries.
    max_retries: int = Field(default=2, ge=0)
    # Transport retries (connection, timeout, rate limit) per model, with backoff.
    transport_retries: int = Field(default=2, ge=0)
    backoff_base_seconds: float = Field(default=0.5, ge=0.0)
    prices: dict[str, ModelPrice] = {}

    def models_for(self, task: str) -> list[ModelSpec]:
        specs = self.tasks.get(task)
        if specs is None:
            raise ConfigurationError(f"no models configured for task {task!r}")
        if not specs:
            raise ConfigurationError(f"task {task!r} has an empty model list")
        return specs

    def cost_for(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        price = self.prices.get(model)
        if price is None:
            return None
        return (input_tokens * price.input + output_tokens * price.output) / 1_000_000

    @classmethod
    def from_toml(cls, path: Path) -> "RouterConfig":
        try:
            raw: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"LLM config {path} does not exist") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigurationError(f"LLM config {path} is not valid TOML: {exc}") from exc
        return cls.model_validate(raw)

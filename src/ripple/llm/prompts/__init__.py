"""Versioned prompt files (prompts.md rule). `load_prompt("resolver", 1)` reads resolver.v1.md."""

from importlib import resources

from ripple.core.errors import ConfigurationError


def load_prompt(name: str, version: int) -> str:
    filename = f"{name}.v{version}.md"
    try:
        text = resources.files(__package__).joinpath(filename).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError(f"prompt {filename} does not exist") from exc
    body = text.split("---\n", 2)
    # Files start with a header block delimited by '---' lines; the prompt is what follows.
    return body[2].strip() if len(body) == 3 else text.strip()

from pathlib import Path

import pytest

from ripple.domains.jobs.sources.registry import (
    DEFAULT_SOURCES_CONFIG,
    ENV_SOURCES_CONFIG,
    SourceKind,
    SourceRegistryError,
    load_registry,
    parse_registry,
    registry_from_env,
)

REPO = Path(__file__).resolve().parents[3]

VALID = """
user_agent: "RippleScout/0.1 (test)"
sources:
  - id: forwarded_email
    kind: forwarded_email
    terms_note: the student forwards it
    robots_respected: true
    rate_limit_per_minute: 1
  - id: acme
    kind: career_page
    url: https://careers.acme.example/jobs
    terms_note: Mail from Acme HR dated 2026-10-01
    robots_respected: true
    rate_limit_per_minute: 6
    parser:
      css_selector: li.job
      follow_links: true
      detail_selector: article.job-description
"""


def test_parse_registry_loads_forwarded_email_and_career_page_sources():
    registry = parse_registry(VALID)
    assert [s.id for s in registry.sources] == ["forwarded_email", "acme"]
    acme = registry.get("acme")
    assert acme.kind is SourceKind.CAREER_PAGE
    assert acme.host == "careers.acme.example"
    assert acme.parser.follow_links is True
    assert [s.id for s in registry.fetchable()] == ["acme"]  # forwarded email is never fetched


def test_parse_registry_refuses_a_source_without_a_terms_note():
    text = VALID.replace("    terms_note: Mail from Acme HR dated 2026-10-01\n", "")
    with pytest.raises(SourceRegistryError, match="terms_note"):
        parse_registry(text)


def test_parse_registry_refuses_a_blank_terms_note():
    text = VALID.replace("terms_note: Mail from Acme HR dated 2026-10-01", 'terms_note: "   "')
    with pytest.raises(SourceRegistryError, match="terms_note"):
        parse_registry(text)


def test_parse_registry_refuses_robots_respected_false():
    text = VALID.replace(
        "robots_respected: true\n    rate_limit_per_minute: 6",
        "robots_respected: false\n    rate_limit_per_minute: 6",
    )
    with pytest.raises(SourceRegistryError, match="robots_respected"):
        parse_registry(text)


def test_parse_registry_refuses_a_duplicate_id():
    text = VALID.replace("id: acme", "id: forwarded_email")
    with pytest.raises(SourceRegistryError, match="appears twice"):
        parse_registry(text)


def test_parse_registry_refuses_an_unknown_kind_and_an_unknown_field():
    with pytest.raises(SourceRegistryError, match="kind"):
        parse_registry(VALID.replace("kind: career_page", "kind: scrape"))
    with pytest.raises(SourceRegistryError, match="login"):
        parse_registry(
            VALID.replace("    enabled: true\n", "").replace(
                "rate_limit_per_minute: 6", "rate_limit_per_minute: 6\n    login: secret"
            )
        )


def test_parse_registry_refuses_a_career_page_without_a_url_or_without_a_hint():
    with pytest.raises(SourceRegistryError, match="needs a url"):
        parse_registry(VALID.replace("    url: https://careers.acme.example/jobs\n", ""))
    without_hint = VALID.split("    parser:")[0]
    with pytest.raises(SourceRegistryError, match="css_selector"):
        parse_registry(without_hint)


def test_parse_registry_refuses_a_url_with_credentials_or_a_non_http_scheme():
    with pytest.raises(SourceRegistryError, match="credentials"):
        parse_registry(
            VALID.replace("https://careers.acme.example", "https://bob:pw@careers.acme.example")
        )
    with pytest.raises(SourceRegistryError, match="http"):
        parse_registry(VALID.replace("https://careers.acme.example", "ftp://careers.acme.example"))


def test_parse_registry_refuses_a_forwarded_email_source_with_a_url():
    text = VALID.replace(
        "    kind: forwarded_email\n",
        "    kind: forwarded_email\n    url: https://mail.example/x\n",
    )
    with pytest.raises(SourceRegistryError, match="forwarded_email source has no url"):
        parse_registry(text)


def test_parse_registry_refuses_a_public_api_without_json_hints():
    text = VALID.replace("kind: career_page", "kind: public_api")
    with pytest.raises(SourceRegistryError, match="json_items"):
        parse_registry(text)


def test_parse_registry_refuses_a_rate_limit_outside_1_to_600():
    with pytest.raises(SourceRegistryError, match="rate_limit_per_minute"):
        parse_registry(VALID.replace("rate_limit_per_minute: 6", "rate_limit_per_minute: 0"))


def test_parse_registry_refuses_invalid_yaml_and_a_non_mapping_document():
    with pytest.raises(SourceRegistryError, match="not valid YAML"):
        parse_registry("user_agent: [unclosed")
    with pytest.raises(SourceRegistryError, match="mapping"):
        parse_registry("- just\n- a list\n")


def test_default_sources_file_lists_only_forwarded_email_and_a_disabled_example():
    registry = load_registry(REPO / DEFAULT_SOURCES_CONFIG)
    kinds = {s.id: (s.kind, s.enabled) for s in registry.sources}
    assert kinds == {
        "forwarded_email": (SourceKind.FORWARDED_EMAIL, True),
        "example_careers": (SourceKind.CAREER_PAGE, False),
    }
    assert registry.fetchable() == []  # nothing is fetched until the author enables a source
    assert "PLACEHOLDER" in registry.get("example_careers").terms_note


def test_load_registry_reports_a_missing_file():
    with pytest.raises(SourceRegistryError, match="cannot be read"):
        load_registry(Path("does/not/exist.yaml"))


def test_registry_from_env_reads_the_override_path(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(VALID, encoding="utf-8")
    registry = registry_from_env({ENV_SOURCES_CONFIG: str(path)})
    assert [s.id for s in registry.fetchable()] == ["acme"]

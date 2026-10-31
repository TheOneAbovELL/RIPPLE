import json

import pytest

from ripple.domains.jobs.sources.extract import (
    extract_candidates,
    html_candidates,
    json_candidates,
    page_text,
)
from ripple.domains.jobs.sources.registry import ExtractionHint
from tests.domains.jobs_sources.support import ACME, fixture, public_api

LISTING = f"{ACME}/jobs"


def test_html_candidates_yield_one_candidate_per_selected_item_with_resolved_url_and_title():
    candidates = html_candidates(fixture("careers.html"), LISTING, "li.job")
    assert [c.title for c in candidates] == [
        "Software Engineer Intern",
        "Data Platform Engineer",
        "Partner role (off-site)",
    ]
    assert [c.url for c in candidates] == [
        f"{ACME}/jobs/42?utm_source=newsletter",
        f"{ACME}/jobs/43/",
        "https://partner.example.org/jobs/7",
    ]
    assert "Bengaluru · Internship · 2027 batch" in candidates[0].text


def test_html_candidates_skip_script_and_style_text():
    text = page_text(fixture("careers.html"))
    assert "should never appear" not in text
    assert "border" not in text
    assert "Open positions" in text


@pytest.mark.parametrize(
    ("selector", "count"),
    [
        ("li.job", 3),
        ("li.job.featured", 1),
        ("#openings > li", 3),
        ("ul#openings li.job h2", 3),
        ("li[class]", 3),
        ("li[class=job]", 2),
        ("li.job, nav a", 6),
        ("div.job", 0),
    ],
)
def test_selector_subset_supports_tag_class_id_attribute_child_and_alternatives(selector, count):
    assert len(html_candidates(fixture("careers.html"), LISTING, selector)) == count


def test_selector_rejects_an_empty_or_malformed_selector():
    with pytest.raises(ValueError):
        html_candidates("<p>x</p>", LISTING, " , ")
    with pytest.raises(ValueError):
        html_candidates("<p>x</p>", LISTING, ".")


def test_page_text_with_a_detail_selector_returns_only_the_jd_body():
    text = page_text(fixture("job-42.html"), "article.job-description")
    assert text.startswith("Software Engineer Intern")
    assert "CGPA 7.5 and above" in text
    assert "Recruiter login" not in text and "Share this job" not in text


def test_page_text_turns_block_elements_into_lines_and_collapses_whitespace():
    html = "<div>  Hello <b>there</b>\n   world </div><p>Second</p><br>Third<span>!</span>"
    assert page_text(html) == "Hello there world\nSecond\nThird!"


def test_html_parser_survives_unclosed_and_stray_tags():
    html = "<ul><li class=job><h2><a href=/x>One</h2><li class=job>Two</ul></li></p>"
    candidates = html_candidates(html, LISTING, "li.job")
    assert [c.title for c in candidates] == ["One", "Two"]
    assert candidates[0].url == f"{ACME}/x"


def test_json_candidates_follow_dotted_paths_and_strip_html_descriptions():
    data = json.loads(fixture("api.json"))
    candidates = json_candidates(data, "https://api.globex.example/v1/jobs", public_api().parser)
    assert [c.title for c in candidates] == ["Backend Developer Intern", "Research Intern"]
    assert candidates[0].url == "https://api.globex.example/postings/101"
    assert candidates[1].url is None  # the item has no url
    assert candidates[0].text.startswith("Globex Corp is hiring a Backend Developer Intern.")
    assert "<p>" not in candidates[0].text


def test_json_candidates_yield_nothing_for_a_missing_or_non_list_path():
    hint = ExtractionHint(json_items="data.nothing", json_text="description")
    assert json_candidates({"data": {}}, LISTING, hint) == []
    hint = ExtractionHint(json_items="data", json_text="description")
    assert json_candidates({"data": {"jobs": []}}, LISTING, hint) == []


def test_extract_candidates_dispatches_on_the_hint_and_content_type():
    api = public_api()
    body = fixture("api.json")
    assert len(extract_candidates(body, "application/json", api.url or "", api.parser)) == 2
    html_hint = ExtractionHint(css_selector="li.job")
    assert len(extract_candidates(fixture("careers.html"), "text/html", LISTING, html_hint)) == 3
    with pytest.raises(ValueError, match="invalid JSON"):
        extract_candidates("<html></html>", "application/json", LISTING, api.parser)
    assert extract_candidates("<html></html>", "text/html", LISTING, ExtractionHint()) == []

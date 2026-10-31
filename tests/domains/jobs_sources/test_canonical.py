import pytest

from ripple.domains.jobs.sources.canonical import canonical_url, fingerprint


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://Careers.Acme.Example/jobs/42", "https://careers.acme.example/jobs/42"),
        ("https://careers.acme.example:443/jobs/42/", "https://careers.acme.example/jobs/42"),
        ("https://careers.acme.example:8443/jobs/", "https://careers.acme.example:8443/jobs"),
        ("https://careers.acme.example/jobs/42#apply", "https://careers.acme.example/jobs/42"),
        (
            # `ref` stays: career sites use it as the job reference id.
            "https://careers.acme.example/jobs/42?utm_source=x&ref=mail&id=7&fbclid=1",
            "https://careers.acme.example/jobs/42?id=7&ref=mail",
        ),
        ("https://careers.acme.example/jobs?b=2&a=1", "https://careers.acme.example/jobs?a=1&b=2"),
        ("https://careers.acme.example//jobs///42", "https://careers.acme.example/jobs/42"),
        ("https://careers.acme.example", "https://careers.acme.example/"),
        ("https://careers.acme.example/?", "https://careers.acme.example/"),
    ],
)
def test_canonical_url_normalises_case_ports_fragments_tracking_and_slashes(raw, expected):
    assert canonical_url(raw) == expected


def test_canonical_url_is_idempotent():
    once = canonical_url("https://Careers.Acme.Example/jobs/42/?utm_medium=x&z=1&a=2#top")
    assert canonical_url(once) == once


@pytest.mark.parametrize("raw", ["/jobs/42", "mailto:hr@acme.example", "javascript:void(0)", ""])
def test_canonical_url_rejects_relative_and_non_http_urls(raw):
    with pytest.raises(ValueError):
        canonical_url(raw)


def test_fingerprint_ignores_case_punctuation_spacing_and_legal_suffixes():
    assert (
        fingerprint("Acme Robotics Pvt. Ltd.", "Software  Engineer - Intern")
        == fingerprint("ACME ROBOTICS", "software engineer intern")
        == "acme robotics|software engineer intern"
    )


def test_fingerprint_treats_ampersand_as_and_and_keeps_distinct_roles_apart():
    assert fingerprint("Johnson & Johnson", "Analyst") == fingerprint(
        "Johnson and Johnson", "Analyst"
    )
    assert fingerprint("Acme", "Data Engineer") != fingerprint("Acme", "Data Scientist")

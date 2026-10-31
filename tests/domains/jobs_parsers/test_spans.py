from ripple.domains.jobs.parsers.spans import locate_span


def test_locate_span_finds_exact_substring_with_offsets():
    text = "Eligibility: CGPA 7.5 and above."
    span = locate_span(text, "CGPA 7.5")
    assert span is not None
    assert (span.start, span.end, span.text) == (13, 21, "CGPA 7.5")
    assert text[span.start : span.end] == span.text


def test_locate_span_tolerates_line_breaks_the_model_read_as_spaces():
    text = "Minimum CGPA of\n7.5 required"
    span = locate_span(text, "Minimum CGPA of 7.5")
    assert span is not None
    assert span.text == "Minimum CGPA of\n7.5"  # the source's own characters, not the quote


def test_locate_span_falls_back_to_case_insensitive_match():
    text = "Batch: 2027 only"
    span = locate_span(text, "batch: 2027")
    assert span is not None
    assert span.text == "Batch: 2027"


def test_locate_span_returns_none_when_quote_is_absent():
    assert locate_span("CGPA 7.5", "CGPA 8.0") is None
    assert locate_span("CGPA 7.5", "   ") is None

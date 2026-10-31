from ripple.domains.jobs.parsers.envelope import strip_email_envelope

GMAIL_FORWARD = """---------- Forwarded message ---------
From: Placement Cell <tpo@college.edu>
Date: Mon, 19 Oct 2026 at 10:02
Subject: Acme Robotics - Intern hiring 2027 batch
To: <students-2027@college.edu>


Dear students,

Acme Robotics is hiring Software Engineer Interns.
Eligibility: 2027 batch, CGPA 7.5 and above.
Apply by 15 November 2026.

Regards,
Dr. A. Sharma
Training and Placement Officer
"""

OUTLOOK_REPLY = """FYI, see below.

-----Original Message-----
From: careers@acme.example
Sent: Monday, October 19, 2026 9:30 AM
To: Placement Cell
Subject: Hiring: Backend Engineer (Full-time)

> Role: Backend Engineer (Full-time), Hyderabad
> Required: Java, Spring Boot
> Last date: 20/11/2026
>
> Thanks & Regards,
> Priya
> Talent Team
>
> DISCLAIMER: This e-mail is confidential and intended solely for the addressee.
"""


def test_strip_email_envelope_removes_forwarded_headers_and_signature():
    body = strip_email_envelope(GMAIL_FORWARD)
    assert body.startswith("Dear students,")
    assert "Forwarded message" not in body
    assert "tpo@college.edu" not in body
    assert "Apply by 15 November 2026." in body
    assert "Regards" not in body and "Placement Officer" not in body


def test_strip_email_envelope_removes_quote_prefixes_and_original_message_block():
    body = strip_email_envelope(OUTLOOK_REPLY)
    assert "Original Message" not in body
    assert "careers@acme.example" not in body
    assert ">" not in body
    assert "Role: Backend Engineer (Full-time), Hyderabad" in body
    assert "Last date: 20/11/2026" in body


def test_strip_email_envelope_cuts_disclaimer_and_closing():
    body = strip_email_envelope(OUTLOOK_REPLY)
    assert "DISCLAIMER" not in body
    assert "Talent Team" not in body
    assert "Thanks" not in body


def test_strip_email_envelope_removes_on_wrote_lines_and_sent_from_lines():
    text = (
        "On Mon, 19 Oct 2026, Placement Cell <tpo@college.edu> wrote:\n"
        "JD body here.\n\nSent from my iPhone\n"
    )
    assert strip_email_envelope(text) == "JD body here."


def test_strip_email_envelope_keeps_a_thanks_line_followed_by_a_long_body():
    lines = ["Thanks,"] + [f"Requirement {n}: detail" for n in range(15)]
    body = strip_email_envelope("\n".join(lines))
    # A closing word deep above real content is not treated as a signature.
    assert "Requirement 14: detail" in body


def test_strip_email_envelope_leaves_plain_pasted_text_alone():
    plain = "Acme Robotics\nCGPA 7.5 and above\nApply by 15 November 2026"
    assert strip_email_envelope(plain) == plain


def test_strip_email_envelope_normalises_windows_line_endings_and_blank_runs():
    body = strip_email_envelope("Line one\r\n\r\n\r\n\r\nLine two\r\n")
    assert body == "Line one\n\nLine two"


def test_strip_email_envelope_keeps_a_date_line_inside_the_jd_body():
    text = "Acme Robotics is hiring.\nDate: 20 November 2026 (online test)\nVenue: Lab 3"
    assert strip_email_envelope(text) == text


def test_strip_email_envelope_keeps_a_double_dash_divider_above_long_content():
    lines = ["Acme Robotics", "--"] + [f"Requirement {n}" for n in range(15)]
    body = strip_email_envelope("\n".join(lines))
    assert "Requirement 14" in body


def test_strip_email_envelope_cuts_a_signature_followed_by_a_long_disclaimer():
    disclaimer = ["DISCLAIMER: This e-mail is confidential."] + [f"Clause {n}." for n in range(12)]
    text = "\n".join(["JD body.", "Regards,", "Priya", "Talent Team", *disclaimer])
    assert strip_email_envelope(text) == "JD body."

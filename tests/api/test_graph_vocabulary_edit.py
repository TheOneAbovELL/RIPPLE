"""Checkpoint C3 additions requested by the dashboard (WS-12) and MCP (WS-11) handovers."""

import asyncio
from datetime import timedelta

from httpx import ASGITransport, AsyncClient

from ripple.api.app import create_app
from ripple.api.contracts import jobs_vocabulary
from ripple.domains.jobs.vocabulary import Kind, ProfileAttribute
from tests.api.harness import BASE_URL, Harness, body
from tests.builders import derived, fact, link


def test_graph_returns_the_users_nodes_and_links_only():
    h = Harness.build()

    async def run():
        asha, asha_headers = await h.user("Asha")
        ravi, _ = await h.user("Ravi")
        cgpa = fact("student", "cgpa", 7.6, user_id=asha.id)
        belief = derived("eligible for Acme", user_id=asha.id)
        other = fact("student", "cgpa", 9.1, user_id=ravi.id)
        await h.seed(cgpa, belief, other, link(cgpa, belief))
        async with h.client() as c:
            return cgpa, belief, await c.get("/graph", headers=asha_headers)

    cgpa, belief, response = asyncio.run(run())
    out = body(response)
    assert {n["memory"]["id"] for n in out["nodes"]} == {cgpa.id, belief.id}
    assert len(out["links"]) == 1 and out["links"][0]["link_class"] == "depends_on"


def test_graph_needs_a_token():
    h = Harness.build()

    async def run():
        async with h.client() as c:
            return await c.get("/graph")

    assert asyncio.run(run()).status_code == 401


def test_vocabulary_lists_the_adapters_kinds_attributes_and_link_types():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.get("/vocabulary", headers=headers)

    out = body(asyncio.run(run()))
    assert out["domain"] == "jobs"
    assert Kind.CRITERIA.value in out["kinds"]
    assert ProfileAttribute.CGPA_SCALE.value in out["attributes"]
    classes = {t["name"]: t["link_class"] for t in out["link_types"]}
    assert set(classes.values()) <= {"depends_on", "snapshot_of"} and classes
    assert out["kinds"] == list(jobs_vocabulary().kinds)


def _edit(h, memory_json):
    async def run():
        user, headers = await h.user()
        exams = fact(
            "student",
            "availability",
            "exams",
            user_id=user.id,
            valid_to=h.clock.now() + timedelta(days=10),
        )
        await h.seed(exams)
        async with h.client() as c:
            return exams, await c.post(
                f"/memories/{exams.id}/edit", json=memory_json, headers=headers
            )

    return asyncio.run(run())


def test_edit_without_valid_to_keeps_the_old_end():
    h = Harness.build()
    exams, response = _edit(h, {"content": "busy with exams and labs"})
    assert response.status_code == 200, response.text
    assert exams.valid_to is not None
    returned = body(response)["memory"]["valid_to"]
    assert returned == exams.valid_to.isoformat().replace("+00:00", "Z")


def test_edit_can_move_valid_to_later():
    h = Harness.build()
    later = h.clock.now() + timedelta(days=20)
    _, moved = _edit(h, {"content": "busy until the 20th", "valid_to": later.isoformat()})
    assert moved.status_code == 200, moved.text
    assert moved.json()["memory"]["valid_to"].startswith(later.date().isoformat())


def test_edit_with_null_valid_to_makes_the_belief_permanent():
    h = Harness.build()
    _, cleared = _edit(h, {"content": "always busy", "valid_to": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["memory"]["valid_to"] is None


def test_edit_refuses_a_valid_to_in_the_past_with_422():
    h = Harness.build()
    past = h.clock.now() - timedelta(minutes=1)
    _, refused = _edit(h, {"content": "busy", "valid_to": past.isoformat()})
    assert refused.status_code == 422


def test_edit_refuses_a_timestamp_without_an_offset_with_422():
    h = Harness.build()
    naive = (h.clock.now() + timedelta(days=1)).replace(tzinfo=None)
    _, refused = _edit(h, {"content": "busy", "valid_to": naive.isoformat()})
    assert refused.status_code == 422


def test_edit_of_an_expired_belief_without_a_new_end_is_409_not_500():
    h = Harness.build()

    async def run():
        user, headers = await h.user()
        exams = fact(
            "student",
            "availability",
            "exams",
            user_id=user.id,
            valid_to=h.clock.now() + timedelta(hours=1),
        )
        await h.seed(exams)
        h.clock.advance(timedelta(hours=2))  # past its end; the nightly sweep has not run
        async with h.client() as c:
            return await c.post(
                f"/memories/{exams.id}/edit", json={"content": "exams done"}, headers=headers
            )

    response = asyncio.run(run())
    assert response.status_code == 409
    assert "expired" in body(response)["detail"]


def test_memory_and_link_ids_are_required_in_the_openapi_schema():
    schemas = Harness.build().app.openapi()["components"]["schemas"]
    assert "id" in schemas["Memory"]["required"]
    assert "id" in schemas["Link"]["required"]


def test_cors_is_off_by_default_and_limited_to_the_given_origins():
    h = Harness.build()
    dev = create_app(h.services, cors_origins=["http://localhost:3000"])

    async def preflight(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            return await c.options(
                "/memories",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

    assert "access-control-allow-origin" not in asyncio.run(preflight(h.app)).headers
    allowed = asyncio.run(preflight(dev))
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_vocabulary_publishes_the_profile_subject_and_each_profile_attributes_shape():
    h = Harness.build()

    async def run():
        _, headers = await h.user()
        async with h.client() as c:
            return await c.get("/vocabulary", headers=headers)

    out = body(asyncio.run(run()))
    assert out["profile_subject"] == "student"
    specs = {a["name"]: a for a in out["profile_attributes"]}
    assert set(specs) == {a.value for a in ProfileAttribute}
    assert specs["cgpa"] == {
        "name": "cgpa",
        "value_type": "number",
        "permanent": True,
        "multi_valued": False,
        "stated_by_user": True,
        "choices": None,
    }
    assert specs["batch"]["value_type"] == "integer"
    assert specs["looking"]["value_type"] == "bool"
    assert (specs["skill"]["multi_valued"], specs["skill"]["value_type"]) == (True, "text")
    assert specs["availability"]["permanent"] is False  # can lapse: the detector decides
    assert specs["resume"]["stated_by_user"] is False  # written by the resume review


def test_every_published_profile_attribute_shape_is_accepted_by_profile_fact():
    """The published value type (and choices) must match what the write path accepts,
    or the dashboard offers inputs the API refuses with 422."""
    from ripple.domains.jobs.profile import profile_fact

    samples = {"number": 8.1, "integer": 2027, "bool": True, "text": "Docker"}
    for spec in jobs_vocabulary().profile_attributes:
        values = spec.choices or (samples[spec.value_type],)
        for value in values:
            profile_fact(ProfileAttribute(spec.name), value)  # raises if refused


def test_cgpa_scale_is_published_as_an_integer_with_its_two_choices():
    [scale] = [a for a in jobs_vocabulary().profile_attributes if a.name == "cgpa_scale"]
    assert (scale.value_type, scale.choices) == ("integer", (4, 10))

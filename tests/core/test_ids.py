from uuid import UUID

from ripple.core.ids import new_id


def test_new_id_is_a_uuid4_string():
    parsed = UUID(new_id())
    assert parsed.version == 4


def test_new_id_is_unique_across_calls():
    assert len({new_id() for _ in range(1000)}) == 1000

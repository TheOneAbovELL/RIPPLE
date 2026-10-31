import pytest

from ripple.core.errors import ConfigurationError
from ripple.core.links import (
    ForgetBehaviour,
    LinkTypeRegistry,
    UnknownLinkTypeError,
    policy_for,
)
from ripple.core.models import LinkClass


def test_depends_on_propagates_copies_and_cascades():
    policy = policy_for(LinkClass.DEPENDS_ON)
    assert policy.propagates
    assert policy.copied_on_update
    assert policy.on_forget is ForgetBehaviour.CASCADE_DELETE


def test_snapshot_of_never_propagates_or_copies_and_keeps_dependent_on_forget():
    policy = policy_for(LinkClass.SNAPSHOT_OF)
    assert not policy.propagates
    assert not policy.copied_on_update
    assert policy.on_forget is ForgetBehaviour.REMOVE_LINK


def test_every_link_class_has_a_policy():
    for link_class in LinkClass:
        assert policy_for(link_class) is not None


def test_registry_knows_generic_types_by_default():
    registry = LinkTypeRegistry()
    assert registry.class_of("depends_on_fact") is LinkClass.DEPENDS_ON
    assert registry.class_of("depends_on_time_period") is LinkClass.DEPENDS_ON


def test_registry_rejects_unknown_type():
    with pytest.raises(UnknownLinkTypeError, match="no class mapping"):
        LinkTypeRegistry().class_of("eligibility_of")


def test_registry_accepts_domain_types():
    registry = LinkTypeRegistry({"eligibility_of": LinkClass.DEPENDS_ON})
    registry.register("sent_with_resume", LinkClass.SNAPSHOT_OF)
    assert registry.class_of("eligibility_of") is LinkClass.DEPENDS_ON
    assert registry.class_of("sent_with_resume") is LinkClass.SNAPSHOT_OF


def test_registry_refuses_to_remap_a_type_to_another_class():
    registry = LinkTypeRegistry({"eligibility_of": LinkClass.DEPENDS_ON})
    with pytest.raises(ConfigurationError, match="already mapped"):
        registry.register("eligibility_of", LinkClass.SNAPSHOT_OF)


def test_registry_allows_idempotent_registration():
    registry = LinkTypeRegistry()
    registry.register("depends_on_fact", LinkClass.DEPENDS_ON)
    assert "depends_on_fact" in registry.known_types()

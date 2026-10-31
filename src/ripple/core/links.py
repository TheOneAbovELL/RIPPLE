"""Link classes and the type → class registry (ADR-0013, docs/03-data-model.md).

Core fixes the behaviour of each class once, here. A domain adapter declares its link
types and maps each to a class; the write flow consults the registry so that core only
ever sees link_class on a Link.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ripple.core.errors import ConfigurationError
from ripple.core.models import LinkClass


class ForgetBehaviour(StrEnum):
    CASCADE_DELETE = "cascade_delete"  # the dependent is deleted with the parent (I7)
    REMOVE_LINK = "remove_link"  # only the edge goes; the dependent stays


@dataclass(frozen=True)
class LinkPolicy:
    propagates: bool
    copied_on_update: bool
    on_forget: ForgetBehaviour


LINK_POLICIES: Mapping[LinkClass, LinkPolicy] = {
    LinkClass.DEPENDS_ON: LinkPolicy(
        propagates=True, copied_on_update=True, on_forget=ForgetBehaviour.CASCADE_DELETE
    ),
    LinkClass.SNAPSHOT_OF: LinkPolicy(
        propagates=False, copied_on_update=False, on_forget=ForgetBehaviour.REMOVE_LINK
    ),
}


def policy_for(link_class: LinkClass) -> LinkPolicy:
    return LINK_POLICIES[link_class]


# Link types every domain shares (docs/03, link types table).
GENERIC_LINK_TYPES: Mapping[str, LinkClass] = {
    "depends_on_fact": LinkClass.DEPENDS_ON,
    "depends_on_time_period": LinkClass.DEPENDS_ON,
}


class UnknownLinkTypeError(ConfigurationError):
    """A link type no adapter has mapped to a class; refused at write time."""


class LinkTypeRegistry:
    def __init__(self, mapping: Mapping[str, LinkClass] | None = None) -> None:
        self._classes: dict[str, LinkClass] = dict(GENERIC_LINK_TYPES)
        if mapping:
            for link_type, link_class in mapping.items():
                self.register(link_type, link_class)

    def register(self, link_type: str, link_class: LinkClass) -> None:
        existing = self._classes.get(link_type)
        if existing is not None and existing is not link_class:
            raise ConfigurationError(
                f"link type {link_type!r} is already mapped to {existing.value}, "
                f"cannot remap to {link_class.value}"
            )
        self._classes[link_type] = link_class

    def class_of(self, link_type: str) -> LinkClass:
        try:
            return self._classes[link_type]
        except KeyError as exc:
            raise UnknownLinkTypeError(f"link type {link_type!r} has no class mapping") from exc

    def known_types(self) -> frozenset[str]:
        return frozenset(self._classes)

"""Leakage checks for a C5 pair set (docs/04 split rule, eval-auditor item 1).

A train pair leaks when it carries a test persona or a test template (a joined
template "a+b" is checked part by part), when its split disagrees with `split_for`,
when its unordered texts equal a test pair's texts, or when its text names a test
persona. The generator refuses to write a set with any problem; the named test in
tests/training/test_leakage.py runs the same checks on the checked-in file.
"""

import re
from collections.abc import Sequence

from bench.linkpairs import LabelledPair, Split, split_for

TEMPLATE_JOIN = "+"


def template_parts(pair: LabelledPair) -> list[str]:
    return pair.template.split(TEMPLATE_JOIN)


def persona_name(persona: str) -> str:
    """ "p3_esha" -> "esha", "n0_meera" -> "meera": the name a persona's text could carry.

    Every track prefixes its personas with a letter and an index (jobs p, news n,
    finance f; bench/data/*/manifest.json), so any such prefix is stripped.
    """
    return persona.split("_", 1)[1] if re.match(r"^[a-z]\d+_", persona) else persona


def held_out_cell(
    pair: LabelledPair, *, test_personas: frozenset[str], test_templates: frozenset[str]
) -> str:
    """ADR-0061's held_out for a pair: none (train), persona, template or both (the strict
    test cell, where neither the persona nor any template was seen in training)."""
    persona = pair.persona in test_personas
    template = any(t in test_templates for t in template_parts(pair))
    if persona and template:
        return "both"
    return "persona" if persona else "template" if template else "none"


def _texts(pair: LabelledPair) -> frozenset[str]:
    return frozenset({pair.parent.content, pair.dependent.content})


def leakage_problems(
    pairs: Sequence[LabelledPair], *, test_personas: frozenset[str], test_templates: frozenset[str]
) -> list[str]:
    problems: list[str] = []
    test_texts = {_texts(p) for p in pairs if p.split is Split.TEST}
    test_names = [persona_name(p) for p in sorted(test_personas)]
    for pair in pairs:
        parts = template_parts(pair)
        expected = split_for(
            pair.persona not in test_personas, all(t not in test_templates for t in parts)
        )
        if pair.split is not expected:
            problems.append(f"{pair.pair_id}: split {pair.split} but split_for says {expected}")
        if pair.split is not Split.TRAIN:
            continue
        if pair.persona in test_personas:
            problems.append(f"{pair.pair_id}: train pair of test persona {pair.persona}")
        for template in parts:
            if template in test_templates:
                problems.append(f"{pair.pair_id}: train pair of test template {template}")
        if _texts(pair) in test_texts:
            problems.append(f"{pair.pair_id}: train texts equal a test pair's texts")
        for name in test_names:
            pattern = rf"(?<![a-z0-9]){re.escape(name.lower())}(?![a-z0-9])"
            for text in (pair.parent.content, pair.dependent.content):
                if re.search(pattern, text.lower()):
                    problems.append(f"{pair.pair_id}: train text names test persona {name!r}")
    return problems

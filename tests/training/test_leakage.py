import json

from bench.linkpairs import PairMemory, Split, read_pairs
from training.jobs_pairs import SOURCE_DIR, pairs_path
from training.leakage import leakage_problems, persona_name

from tests.training.support import pair

TEST_PERSONAS = frozenset({"p3_esha", "p4_bharat"})
TEST_TEMPLATES = frozenset({"cgpa_rise", "deadline_moved"})


def test_no_test_persona_template_or_text_leaks_into_train():
    """docs/04 split rule on the checked-in jobs_v0 pair file: no train pair carries a
    test persona or template, no train pair's texts equal a test pair's, no train text
    names a test persona, and every split agrees with split_for."""
    manifest = json.loads((SOURCE_DIR / "manifest.json").read_text(encoding="utf-8"))
    pairs = list(read_pairs(pairs_path()))
    train = [p for p in pairs if p.split is Split.TRAIN]
    test = [p for p in pairs if p.split is Split.TEST]
    assert train and test
    assert (
        leakage_problems(
            pairs,
            test_personas=frozenset(manifest["personas"]["test"]),
            test_templates=frozenset(manifest["templates"]["test"]),
        )
        == []
    )
    assert {p.persona for p in train}.isdisjoint(manifest["personas"]["test"])
    train_templates = {t for p in train for t in p.template.split("+")}
    assert train_templates.isdisjoint(manifest["templates"]["test"])
    test_texts = {frozenset({p.parent.content, p.dependent.content}) for p in test}
    assert not {frozenset({p.parent.content, p.dependent.content}) for p in train} & test_texts


def test_leakage_flags_a_train_pair_of_a_test_persona_or_template():
    bad_persona = pair("a", split=Split.TRAIN, persona="p3_esha", template="exam_block")
    bad_template = pair("b", split=Split.TRAIN, persona="p0_jay", template="exam_block+cgpa_rise")
    problems = leakage_problems(
        [bad_persona, bad_template], test_personas=TEST_PERSONAS, test_templates=TEST_TEMPLATES
    )
    assert any("test persona p3_esha" in p for p in problems)
    assert any("test template cgpa_rise" in p for p in problems)
    assert any("split_for" in p for p in problems)


def test_leakage_flags_train_texts_equal_to_test_texts_in_either_order():
    test_pair = pair("t", persona="p3_esha")
    train_pair = pair(
        "r",
        split=Split.TRAIN,
        persona="p0_jay",
        template="exam_block",
        parent=test_pair.dependent,
        dependent=test_pair.parent,
        link_type=None,
    )
    problems = leakage_problems(
        [test_pair, train_pair], test_personas=TEST_PERSONAS, test_templates=TEST_TEMPLATES
    )
    assert problems == ["r: train texts equal a test pair's texts"]


def test_leakage_flags_a_train_text_naming_a_test_persona():
    named = pair(
        "n",
        split=Split.TRAIN,
        persona="p0_jay",
        template="exam_block",
        dependent=PairMemory(kind="derived", content="Esha is eligible"),
    )
    problems = leakage_problems([named], test_personas=TEST_PERSONAS, test_templates=TEST_TEMPLATES)
    assert problems == ["n: train text names test persona 'esha'"]


def test_a_clean_train_pair_passes():
    clean = pair("c", split=Split.TRAIN, persona="p0_jay", template="exam_block")
    assert (
        leakage_problems([clean], test_personas=TEST_PERSONAS, test_templates=TEST_TEMPLATES) == []
    )


def test_persona_name_strips_the_index():
    assert persona_name("p3_esha") == "esha"
    assert persona_name("custom") == "custom"
    assert persona_name("n0_meera") == "meera" and persona_name("f3_uma") == "uma"

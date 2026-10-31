import asyncio

from ripple.core.models import LinkCreator
from ripple.linking.rules import RuleLinker
from tests.builders import derived, fact


def _propose(memory, candidates):
    return asyncio.run(RuleLinker().propose(memory, candidates))


def test_rule_linker_links_new_belief_to_the_fact_it_mentions():
    cgpa = fact("student", "cgpa", 7.6)
    belief = derived("Not eligible for Acme because CGPA 7.6 is under the 7.8 cutoff")
    [proposal] = _propose(belief, [cgpa])
    assert (proposal.parent_id, proposal.dependent_id) == (cgpa.id, belief.id)
    assert proposal.link_type == "depends_on_fact"
    assert proposal.created_by is LinkCreator.RULE


def test_rule_linker_links_existing_belief_to_a_new_fact_it_mentions():
    fit = derived("Strong fit for Globex: asks for PyTorch")
    pytorch = fact("student", "skills", "PyTorch")
    [proposal] = _propose(pytorch, [fit])
    assert (proposal.parent_id, proposal.dependent_id) == (pytorch.id, fit.id)


def test_rule_linker_does_not_link_versions_of_the_same_fact():
    old = fact("student", "cgpa", 7.6)
    new = fact("student", "cgpa", 7.9, content="cgpa is now 7.9")
    assert _propose(new, [old]) == []


def test_rule_linker_matches_whole_words_only():
    fact_ml = fact("student", "skills", "ML")
    belief = derived("HTML and XML experience")
    assert _propose(belief, [fact_ml]) == []


def test_rule_linker_ignores_other_users_and_itself():
    cgpa = fact("student", "cgpa", 7.6)
    foreign = derived("mentions cgpa", user_id="someone-else")
    assert _propose(cgpa, [cgpa, foreign]) == []


def test_rule_linker_is_case_insensitive():
    cgpa = fact("student", "CGPA", 7.6)
    belief = derived("cgpa too low for Acme")
    assert len(_propose(belief, [cgpa])) == 1

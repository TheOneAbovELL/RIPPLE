"""Small C5 pair builders for the training tests."""

from bench.linkpairs import LabelledPair, PairMemory, Provenance, Split

from ripple.core.models import LinkClass, StructuredFact

CGPA = PairMemory(
    kind="fact",
    content="CGPA is 7.4",
    structured=StructuredFact(subject="student", attribute="cgpa", value=7.4),
)
ELIGIBILITY = PairMemory(kind="derived", content="not eligible for acme")


def pair(
    pair_id: str,
    *,
    parent: PairMemory = CGPA,
    dependent: PairMemory = ELIGIBILITY,
    link_type: str | None = "eligibility_of",
    provenance: Provenance = Provenance.SCENARIO,
    split: Split = Split.TEST,
    persona: str = "p3_esha",
    template: str = "cgpa_rise",
    labeller: str | None = None,
) -> LabelledPair:
    return LabelledPair(
        pair_id=pair_id,
        track="jobs_v0",
        domain="jobs",
        persona=persona,
        template=template,
        split=split,
        parent=parent,
        dependent=dependent,
        link_type=link_type,
        link_class=None if link_type is None else LinkClass.DEPENDS_ON,
        provenance=provenance,
        labeller=labeller,
    )

"""GET /vocabulary: the domain adapter's kinds, attributes and link types.

The dashboard reads these instead of hardcoding the jobs values, so the inspector stays
domain-agnostic the way core is (ADR-0013: domains map their types onto core classes).
It needs a token like every product route, though nothing in it is personal.
"""

from fastapi import APIRouter

from ripple.api.auth import CurrentServices, CurrentUser
from ripple.api.schemas import LinkTypeOut, ProfileAttributeOut, VocabularyOut

router = APIRouter(prefix="/vocabulary", tags=["me"])


@router.get("", response_model=VocabularyOut)
async def get_vocabulary(user: CurrentUser, services: CurrentServices) -> VocabularyOut:
    del user  # authenticated like every product route; the answer is not per user
    vocabulary = services.vocabulary
    return VocabularyOut(
        domain=services.domain,
        kinds=list(vocabulary.kinds),
        attributes=list(vocabulary.attributes),
        link_types=[
            LinkTypeOut(name=name, link_class=services.registry.class_of(name))
            for name in sorted(services.registry.known_types())
        ],
        profile_subject=vocabulary.profile_subject,
        profile_attributes=[
            ProfileAttributeOut.model_validate(spec, from_attributes=True)
            for spec in vocabulary.profile_attributes
        ],
    )

"""Resume upload and the confirmation flow (FR-1, ADR-0024, ADR-0043, ADR-0097, I5).

Upload: PDF bytes go to the ResumeParser; the text it read is persisted as a
ResumeUpload (so span references resolve) and what it found is stored as pending
candidates, never as memories. Confirm: the candidate becomes a Statement through the
injected CandidateStatements and goes through Intake like any other fact; the candidate
row is then claimed with a conditional update, so of two concurrent confirms exactly one
wins and the other answers 409. Reject: the candidate is kept with status rejected so
the user can see what they declined.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from ripple.api.auth import CurrentServices, CurrentUser, not_found
from ripple.api.candidates import candidate_from_fact, fact_of
from ripple.api.logging import current_trace_id
from ripple.api.schemas import CandidateOut, CandidatesOut, ConfirmOut, IntakeOut, ResumeUploadOut
from ripple.api.services import Services
from ripple.core.errors import InvariantViolationError
from ripple.storage.candidates import (
    CandidateAlreadyDecidedError,
    CandidateStatus,
    ResumeCandidate,
)
from ripple.storage.uploads import (
    MAX_RESUME_TEXT_CHARS,
    ResumeUpload,
    resume_source_ref,
    sha256_of,
)
from ripple.storage.users import User

log = logging.getLogger("ripple.api.resume")
router = APIRouter(prefix="/resume", tags=["resume"])

CandidateFilter = Literal["pending", "confirmed", "rejected", "all"]

PDF_MAGIC = b"%PDF-"
DEFAULT_FILENAME = "resume.pdf"


@router.post("", response_model=ResumeUploadOut, status_code=201)
async def upload_resume(
    user: CurrentUser,
    services: CurrentServices,
    file: Annotated[UploadFile, File(description="The resume as a PDF.")],
) -> ResumeUploadOut:
    pdf = await file.read(services.max_resume_bytes + 1)
    if len(pdf) > services.max_resume_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"resume larger than {services.max_resume_bytes} bytes",
        )
    if not pdf.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="resume must be a PDF"
        )
    upload = ResumeUpload(
        user_id=user.id,
        filename=(file.filename or DEFAULT_FILENAME)[:255],
        sha256=sha256_of(pdf),
        text="",
        uploaded_at=services.clock.now(),
    )
    parsed = await services.resume_parser.parse(pdf, source_ref=resume_source_ref(upload.id))
    if len(parsed.text) > MAX_RESUME_TEXT_CHARS:
        # Spans index into the whole text, so it is stored whole or not at all.
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"resume text longer than {MAX_RESUME_TEXT_CHARS} characters",
        )
    upload = upload.model_copy(update={"text": parsed.text})
    # The text is written before the candidates: a candidate whose upload is missing
    # would be a span pointing at nothing, the gap this table closes (ADR-0097).
    await services.upload_store.add_upload(upload)
    now = services.clock.now()
    candidates = [candidate_from_fact(user.id, upload.id, fact, now) for fact in parsed.facts]
    await services.candidate_store.add_candidates(candidates)
    return ResumeUploadOut(upload_id=upload.id, candidates=candidates)


@router.get("/candidates", response_model=CandidatesOut)
async def list_candidates(
    user: CurrentUser,
    services: CurrentServices,
    status_filter: Annotated[CandidateFilter, Query(alias="status")] = "pending",
) -> CandidatesOut:
    wanted = None if status_filter == "all" else CandidateStatus(status_filter)
    return CandidatesOut(
        candidates=await services.candidate_store.candidates_for_user(user.id, wanted)
    )


@router.post("/candidates/{candidate_id}/confirm", response_model=ConfirmOut)
async def confirm_candidate(
    candidate_id: str, user: CurrentUser, services: CurrentServices
) -> ConfirmOut:
    candidate = await _pending_candidate(services, user, candidate_id)
    # The builder appends the span (WS-2's candidate_to_statement does), so the memory's
    # source_ref reads resume:<upload id>#<start>-<end> and the inspector can show the line.
    statement = services.candidate_statements.statement_for(
        user.id, fact_of(candidate), source_ref=resume_source_ref(candidate.upload_id)
    )
    if statement.user_id != user.id:
        # The builder is injected code; a wrong user id here would cross tenants.
        log.error("statement builder changed the user id", extra={"user_id": user.id})
        raise InvariantViolationError("statement builder changed the user id")
    # Intake is idempotent for an identical structured fact (ChangeKind.UNCHANGED writes
    # nothing), so a second confirm racing this one adds no memory; the conditional
    # replace below is what decides which request owns the candidate.
    result = await services.intake.ingest(statement, trace_id=current_trace_id())
    decided = candidate.model_copy(
        update={
            "status": CandidateStatus.CONFIRMED,
            "decided_at": services.clock.now(),
            "memory_id": result.memory.id,
        }
    )
    await _claim(services, decided)
    return ConfirmOut(
        candidate=decided,
        intake=IntakeOut(
            memory=result.memory,
            change_kind=result.change_kind,
            links_written=result.links_written,
            event=result.event,
        ),
    )


@router.post("/candidates/{candidate_id}/reject", response_model=CandidateOut)
async def reject_candidate(
    candidate_id: str, user: CurrentUser, services: CurrentServices
) -> CandidateOut:
    candidate = await _pending_candidate(services, user, candidate_id)
    decided = candidate.model_copy(
        update={"status": CandidateStatus.REJECTED, "decided_at": services.clock.now()}
    )
    await _claim(services, decided)
    return CandidateOut(candidate=decided)


async def _pending_candidate(services: Services, user: User, candidate_id: str) -> ResumeCandidate:
    candidate = await services.candidate_store.get_candidate(candidate_id)
    if candidate is None or candidate.user_id != user.id:
        raise not_found("candidate")
    if candidate.status is not CandidateStatus.PENDING:
        raise _already(candidate.status)
    return candidate


async def _claim(services: Services, decided: ResumeCandidate) -> None:
    """Write the decision only if the row is still pending (ADR-0043, atomic confirm)."""
    try:
        await services.candidate_store.replace_candidate(
            decided, expected_status=CandidateStatus.PENDING
        )
    except CandidateAlreadyDecidedError as exc:
        raise _already(exc.actual) from exc


def _already(current: CandidateStatus) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=f"candidate already {current.value}"
    )

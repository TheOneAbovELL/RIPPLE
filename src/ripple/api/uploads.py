"""Resolve a memory's `source_ref` against the user's resume uploads (ADR-0097, FR-12).

A confirmed resume fact points at `resume:<upload id>#<start>-<end>`. The inspector
asks here for the quoted characters and the line they sit on; anything that is not an
upload reference, belongs to another user or falls outside the text resolves to None
rather than to a guess (I5: the quote is the stored text or nothing).
"""

from ripple.api.schemas import SourceOut
from ripple.core.models import Memory
from ripple.storage.uploads import UploadStore, parse_resume_ref, quote


async def source_for(uploads: UploadStore, memory: Memory) -> SourceOut | None:
    ref = parse_resume_ref(memory.source_ref)
    if ref is None:
        return None
    upload = await uploads.get_upload(ref.upload_id)
    if upload is None or upload.user_id != memory.user_id:
        return None
    quoted = None
    if ref.start is not None and ref.end is not None:
        quoted = quote(upload.text, ref.start, ref.end)
    return SourceOut(
        upload_id=upload.id,
        filename=upload.filename,
        uploaded_at=upload.uploaded_at,
        start=None if quoted is None else quoted.start,
        end=None if quoted is None else quoted.end,
        quote=None if quoted is None else quoted.text,
        line=None if quoted is None else quoted.line,
    )

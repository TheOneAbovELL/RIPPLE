"""Bearer-token authentication and per-user scoping (ADR-0040).

Every router depends on `current_user`; a request without a valid token never reaches
a handler. Scoping is enforced where an id is dereferenced: `owned_memory` answers 404
for another user's memory, so the API does not reveal that the id exists.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ripple.api.services import Services, services_of
from ripple.core.models import Memory
from ripple.core.store import MemoryNotFoundError, StoreReader
from ripple.storage.users import User, hash_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("missing bearer token")
    user = await services_of(request).user_store.user_for_token_hash(
        hash_token(credentials.credentials)
    )
    if user is None:
        raise _unauthorized("invalid bearer token")
    request.state.user = user  # error handlers read it to report the user's open events
    return user


CurrentUser = Annotated[User, Depends(current_user)]
CurrentServices = Annotated[Services, Depends(services_of)]


def not_found(what: str = "memory") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


async def owned_memory(store: StoreReader, user: User, memory_id: str) -> Memory:
    """The memory, if it exists and belongs to `user`; otherwise 404 either way."""
    try:
        memory = await store.get_memory(memory_id)
    except MemoryNotFoundError as exc:
        raise not_found() from exc
    if memory.user_id != user.id:
        raise not_found()
    return memory

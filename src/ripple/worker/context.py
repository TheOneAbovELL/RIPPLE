"""JobContext: everything a job function needs, injected (ADR-0017).

Jobs are plain async functions over this object so tests call them with fakes and no
Redis. The arq layer (settings.py) builds one at worker startup and hands it to every
job through arq's `ctx` dict.
"""

from dataclasses import dataclass

from ripple.core.clock import Clock
from ripple.core.ripple import RippleRunner
from ripple.core.store import Store
from ripple.core.sweep import NightlySweep
from ripple.llm.router import Router
from ripple.notify.contracts import UserDirectory
from ripple.notify.digest import DigestService
from ripple.worker.lease import Lease


@dataclass(frozen=True)
class JobContext:
    store: Store
    runner: RippleRunner
    clock: Clock
    users: UserDirectory
    sweep: NightlySweep
    digest: DigestService
    leases: Lease
    # The process's one Router (one tracer, flushed at shutdown); jobs that call a model
    # outside the runner (the Scout's JD parser) use it. None in tests that inject.
    router: Router | None = None

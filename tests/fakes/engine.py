"""ScriptedEngine: returns pre-planned waves so runner tests do not depend on the
human-owned WaveEngine. It records what the runner fed back, so a test can assert the
runner reported outcomes correctly.
"""

from collections import deque
from collections.abc import Sequence

from ripple.core.engine import DependencyGraph, Wave, WaveOutcome


class ScriptedEngine:
    def __init__(self, *waves: Sequence[str], max_depth: int = 8) -> None:
        self._waves: deque[tuple[str, ...]] = deque(tuple(w) for w in waves)
        self.max_depth = max_depth
        self.truncated = False
        self.seeds: list[str] = []
        self.outcomes: list[list[WaveOutcome]] = []
        self._number = 0

    def first_wave(self, graph: DependencyGraph, seeds: Sequence[str]) -> Wave | None:
        self.seeds = list(seeds)
        return self._emit()

    def next_wave(self, graph: DependencyGraph, outcomes: Sequence[WaveOutcome]) -> Wave | None:
        self.outcomes.append(list(outcomes))
        return self._emit()

    def _emit(self) -> Wave | None:
        if not self._waves:
            return None
        self._number += 1
        return Wave(number=self._number, memory_ids=self._waves.popleft())

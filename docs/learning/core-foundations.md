# ripple.core foundations: clock, ids, errors, boundaries
Written 2026-10-19 for src/ripple/core as it exists after Phase 0 task 0.5. Models, the
Store protocol and the ripple engine arrive in Phase 1 and will get their own page.

## 1. What it does
Three small modules give every later core component its time, its identifiers and its
exceptions, and one test keeps core free of other packages and frameworks.

## 2. Why it exists
python.md: core is pure, I/O only through injected interfaces, never `datetime.now()`
in core. ADR-0005 keeps frameworks out of core; ADR-0016 keeps the ORM out of it.
docs/02-architecture.md: core may import nothing in ripple except core. FakeClock is
what makes self-expiry (ADR-0015) testable: a test writes a fact valid until month end,
advances the clock, runs the sweep and asserts the result, in milliseconds.

## 3. How it works
- `clock.py`: `Clock` is a Protocol with `now() -> datetime` (aware, UTC).
  `SystemClock` is the only code reading the real clock. Everything else receives a
  Clock in its constructor.
- `ids.py`: `new_id()` returns a uuid4 string. Ordering comes from `recorded_at`, so no
  ULID dependency.
- `errors.py`: `RippleError` and four specific errors (ConfigurationError,
  InvariantViolationError, LLMOutputInvalidError, LLMUnavailableError). New error
  types are added when the code that raises them exists, not speculatively.
- `tests/core/test_boundaries.py` parses every core module with `ast` and allows only
  stdlib, pydantic and `ripple.core` imports (an allowlist, so a new SDK is a breach
  without being listed). A second test flags any `.now()`, `.utcnow()`, `.today()`,
  `.time()`, `.monotonic()` or `.perf_counter()` call outside clock.py, including
  aliased ones. Two more tests prove the checkers themselves catch a breach.

## 4. Trade-offs
- A Protocol instead of an abstract base class: any object with `now()` qualifies, so
  FakeClock needs no inheritance. Wrong when: you want runtime enforcement; pyright
  strict gives it at check time instead.
- uuid4 over UUIDv7: no dependency, at the cost of index locality in Postgres. Revisit
  if a user graph grows far beyond the pilot's size.
- The boundary test checks direct imports, not the full import graph. It cannot catch
  a core module importing a module that itself imports a forbidden one; since only
  stdlib, pydantic and core are allowed, that gap is small.

## 5. Failure modes and tests
| Failure | Test |
|---|---|
| Time logic untestable because something reads the system clock | test_core_never_reads_the_wall_clock_outside_clock_module |
| Core grows a dependency on llm, storage or a framework | test_core_only_imports_stdlib_pydantic_and_itself |
| Naive datetimes sneak in | test_fake_clock_rejects_naive_datetimes, test_system_clock_returns_aware_utc |
| Ids collide | test_new_id_is_unique_across_calls |

## 6. Interview questions
1. *Why inject a clock at all?* Expiry and validity windows are time logic; tests must
   move time without sleeping, and production must not be special-cased.
2. *Why is the boundary a test and not a linter plugin?* No new dependency; the test
   fails on CI like any other and is readable in a minute.
3. *What breaks if core imports SQLAlchemy?* Core's models become table-shaped, the
   in-memory store drifts from Postgres, and pyright strict gets noisier.
4. *Why UTC everywhere?* Deadlines in JDs are stated in local time but compared across
   users and servers; one zone in storage, convert at the edge.
5. *Why is `InvariantViolationError` defined before any code raises it?* It is the one
   exception named by CLAUDE.md's invariant tests; the others wait for their callers.

## 7. Exercise
Add a forbidden import to clock.py, run `uv run pytest tests/core -q`, and read the
exact breach message the boundary test prints. Then remove it.

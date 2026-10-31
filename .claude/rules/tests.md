---
paths:
  - "tests/**"
---
# Test rules
- One behaviour per test. Name: test_<unit>_<behaviour>_<condition>.
- Build objects with tests/builders, not hand-written dicts.
- Offline only: FakeLLM with scripted responses, FakeClock, in-memory store.
- Mark slow tests with @pytest.mark.slow.
- Scenario files: tests/scenarios/<name>.yaml = initial memories, events in order,
  expected memory states after each event.
- A test must fail without the change it covers. Check this when writing it.

# Test Writer

Invoke by saying: "write tests for X" or "add test coverage for X"

---

## Process:

1. **Read** the target module/function to understand its behavior
2. **Identify** the testing framework already used in the project (pytest, jest, etc.)
3. **Follow existing test patterns** — match style, directory structure, naming conventions
4. **Write tests** covering:

## Coverage priorities (in order):
1. Happy path — normal expected usage
2. Edge cases — empty inputs, boundary values, max/min
3. Error cases — invalid inputs, missing files, network failures
4. Integration — components working together correctly

## Rules:
- One assertion per test (or closely related assertions)
- Test names describe the scenario: `test_returns_empty_list_when_no_videos_found`
- No test interdependence — each test runs independently
- Mock external dependencies (filesystem, network, GPU)
- Use fixtures/factories for test data setup
- Tests must be deterministic — no random, no time-dependent assertions

## After writing:
- Run the test suite to verify tests pass
- Intentionally break the code to verify tests catch the failure

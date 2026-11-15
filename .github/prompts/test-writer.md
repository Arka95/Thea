---
title: Test Writer
description: Generate test cases following project patterns and best practices
---

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
- Group related assertions around observable behavior, not private structure.
- Test names describe the scenario: `test_returns_empty_list_when_no_videos_found`
- No test interdependence — each test runs independently
- Mock external dependencies (filesystem, network, GPU)
- Use fixtures/factories for test data setup
- Tests must be deterministic — no random, no time-dependent assertions

## After writing:
- Run the smallest relevant module unit suite using the existing pytest runner.
- Keep units in `src\<module>\tests` and real integrations in
  `src\integration_tests`; mock hardware, subprocesses, media and model calls.
- Do not run full/long integration suites or mutate production code to prove
  a test fails unless explicitly requested. Follow `AGENTS.md`.

# Evaluation Rubric (Meta E5 coding bar)

Thea scores each attempt on 5 axes. The **primary signal is TIME** — that's Arka's known gap.

| Axis | Weight | What "pass" looks like at E5 |
|---|---|---|
| **Time** ⏱️ (primary) | 40% | Single Q solved in ≤ 15–20 min; in mock, both Q attempted within 35 min. |
| **Correctness** | 25% | Passes all provided + edge test cases; handles empties, duplicates, bounds. |
| **Optimality** | 20% | Hits expected time/space complexity; no obviously wasteful passes. |
| **Approach-first** | 10% | Stated brute force → optimal → chose one, BEFORE coding (no blind coding). |
| **Communication** | 5% | Clear reasoning as comments / narration; names complexity. |

## Timing failure-mode tag (recorded every session)
Thea labels which pattern showed up so reps target it:
- `SLOW_START` — >6 min before first line of solution code.
- `Q1_OVERRUN` — spent >20 min on question 1 (mock mode).
- `DEBUG_SPIRAL` — >5 min debugging after first "done".
- `PATTERN_FREEZE` — long stall on an unfamiliar pattern.
- `CLEAN` — none of the above; paced well.

## Pacing script (the target reflex)
- **min 0–2:** clarify + state brute force
- **min 2–5:** derive optimal approach, pick data structures
- **min 6:** start coding
- **min ~15:** working solution + dry-run
- **remaining:** edge cases / test

## Scoring output (appended to session_log.md)
```
Q## <slug> | difficulty | topic
Time: <mm:ss> / target <mm:ss>   [PASS/OVER]
Correct: <x/y tests>   Optimality: <expected vs actual>
Failure tag: <TAG>
Approach-first: <yes/no>   Hints used: <n>
ONE FIX: <single concrete action for next rep>
```

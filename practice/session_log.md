# Session Log

Running record of Arka's timed coding practice. Newest entries at the top.

---
Q04 min-max-shard-load | Medium | binary-search-on-answer (partition/split-array) | 2026-07-21
Time: 20:00 / target 20:00   [OVER — no code written]
Correct: 0/5 tests (harness prints all FAIL; function body still `pass` -> returns None)
Optimality: expected O(n log S) binary-search on the answer + O(n) greedy feasibility
         (place shards left-to-right, open a new server when the running sum would exceed
         the candidate max; feasible iff servers_used <= k). Actual: none.
Failure tag: NO_ATTEMPT (session lost to a VS Code stale-buffer issue — the editor showed
         an old unsaved tab; disk had the correct new Q the whole time. Not a coding-timing
         failure; verbal reasoning below is what was assessable.)
Verbal approach (chat, ~min 0-3): (1) first idea = prefix-sum + pick k-1 partition slots via
         "best fit after an initial slot" — a greedy/DP framing, direction right but fuzzy on
         mechanism. (2) then pivoted to "the answer lies between [~max element] and [total
         sum]" — this IS the binary-search-on-answer insight, reached verbally in ~2 min.
         Search range nuance: low = max(shards) (a server must hold its largest single shard),
         high = sum(shards); he phrased it as "min k-elements sum / max k-elements sum".
Approach-first: yes (verbal, no written plan comment)   Hints used: 0
ONE FIX: Before coding, run `File -> Revert File` to confirm the editor matches disk — a
stale buffer burned the whole clock. Then translate the binary-search instinct straight to
code: lo=max(shards), hi=sum(shards); feasible(cap) = one left-to-right greedy pass counting
servers; shrink hi when feasible, raise lo when not. That's ~12 lines and O(n log S).
---
Q03 min-rollout-rounds | Medium | graph/topological-sort (level BFS) | 2026-07-21
Time: 20:00 / target 20:00   [OVER — no working solution]
Correct: 0/11 tests (harness prints all FAIL, returns 0 for every case)
Optimality: expected O(n+E) Kahn level-BFS; actual is a single static sort by initial
         indegree — wrong mechanism, cannot compute rounds; returns len(rounds)=0 always.
Failure tag: PATTERN_FREEZE (right family — indegree/topo — wrong execution) + no dry-run
Bugs: (1) `rounds` never populated: the `if indegree[service]==current` guard is always
      True by construction (current was just set to indegree[service] one line above), so
      the `else: rounds.append(round)` branch is dead code -> always returns 0.
      (2) Static `sorted(range(n), key=indegree)` can't produce levels — indegree must be
      DECREMENTED as deps clear (Kahn). A one-shot sort loses the dependency cascade.
      (3) No cycle detection -> never returns -1 (Examples 3, 5, 10 unreachable).
      (4) `outdegree[]` computed but unused; no adjacency list built, so neighbors can't
      be relaxed even if the loop were fixed.
Approach-first: no (no written plan comment)   Hints used: 0
ONE FIX: Build adjacency + indegree, seed a queue with all indegree==0 nodes, then process
LEVEL BY LEVEL (rounds += 1 per level, for each node decrement neighbors' indegree, enqueue
new zeros). Count processed nodes; if processed < n -> return -1. And press ▶ Run before
time expires — 0/11 would have shown in the first 30s, leaving 15+ min to fix.
---
Q02 cheapest-routing-hop-limit | Medium | weighted-graph/bellman-ford | 2026-07-19
Time: ~07:40 / target 20:00   [early submit — fast but unverified]
Correct: 0/3 examples (hidden tests also fail)   Optimality: right family (Bellman-Ford),
         loops range(n) not range(k+1); missing per-round snapshot
Failure tag: DEBUG_SPIRAL (submit-before-verify — never ran the ▶ harness)
Bugs: hop gate `hops[s] < k` blocks the final edge (off-by-one) so dst unreachable;
      no snapshot -> same-pass chained relax silently exceeds hop budget;
      stray debug print(dist); hops[] array is the wrong mechanism entirely.
Approach-first: no (no written plan comment)   Hints used: 0
ONE FIX: Press ▶ Run before "done" every session — 0/3 shows instantly, leaving time to
fix. For hop-limited shortest path use snapshot Bellman-Ford (iterate k+1 times, relax
from prev=dist[:]); drop the hops[] array — iteration count IS the hop count.
---
Q01 minimum-deployment-windows | Medium | intervals/greedy | 2026-07-19 (attempt)
Time: untimed (coded offline)   target 20:00
Correct: 0/7 tests   Optimality: N/A (crashes; intended model was O(n^2), fails 1e5)
Failure tag: DEBUG/CORRECTNESS (right family: interval partitioning; 4 impl bugs)
Bugs: empty-list index-assign (use append); overlaps double-index [1][1];
      lowercase false/true; return uses undefined server_ends.
Approach-first: partial (had greedy idea, no written plan)   Hints used: 0
ONE FIX: Hand-trace Example 1 before declaring done — every bug surfaces on one
manual pass. Prefer the min-heap form (heapreplace when ends[0] <= start) for O(n log n).
---
Q01 minimum-deployment-windows | Medium | intervals/greedy | 2026-07-18 (flow test)
Time: 20:00 / target 20:00   [OVER — no submission]
Correct: 0/7 tests   Optimality: expected O(n log n), actual N/A (empty `min_servers`)
Failure tag: NO_ATTEMPT (dry-run — bootstrap/flow verification only)
Approach-first: no   Hints used: 0
ONE FIX: This was a plumbing test of the flow (question→timer→10-min marker→silent
eval→log). Flow confirmed working. Next real session: write the approach comment in the
first 2 min, then code the sweep-line/heap solution by min 6.
---

<!-- template
Q## <slug> | <difficulty> | <topic> | <date>
Time: mm:ss / target mm:ss   [PASS/OVER]
Correct: x/y tests   Optimality: expected vs actual
Failure tag: TAG
Approach-first: yes/no   Hints used: n
ONE FIX: ...
-->

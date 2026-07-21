# =============================================================================
# Q04 — Minimum Max Shard Load
# =============================================================================
#
# A storage service must place an ordered list of shards onto exactly `k`
# servers. `shards` is an array of positive integers where shards[i] is the
# size of the i-th shard. The shards are laid out in a fixed order and must be
# assigned to servers as `k` CONTIGUOUS groups (you cannot reorder shards, and
# every server gets a non-empty contiguous block; all shards must be placed).
#
# A server's LOAD is the sum of the sizes of the shards assigned to it.
#
# Partition the shards into exactly `k` contiguous groups so that the MAXIMUM
# server load is as SMALL as possible. Return that minimized maximum load.
#
# Constraints:
#   - 1 <= k <= len(shards) <= 10^5
#   - 1 <= shards[i] <= 10^6
#
# Examples:
#   Example 1:
#     shards = [7, 2, 5, 10, 8], k = 2
#     -> 18        (split [7,2,5] and [10,8] -> loads 14 and 18 -> max 18)
#
#   Example 2:
#     shards = [1, 2, 3, 4, 5], k = 2
#     -> 9         (split [1,2,3] and [4,5] -> loads 6 and 9 -> max 9)
#
#   Example 3:
#     shards = [1, 4, 4], k = 3
#     -> 4         (each shard on its own server -> max 4)
#
#   Example 4:
#     shards = [2, 3, 1, 2, 4, 3], k = 3
#     -> 6         (split [2,3,1], [2,4], [3] -> loads 6, 6, 3 -> max 6)
#
#   Example 5:
#     shards = [5], k = 1
#     -> 5
#
# =============================================================================

from typing import List


def min_max_shard_load(shards: List[int], k: int) -> int:
    # ---- YOUR SOLUTION BELOW ----
    # Binary-search on the answer (the max load), O(n log S).
    # A candidate cap is feasible iff we can lay the shards left-to-right into
    # <= k contiguous groups where no group's sum exceeds cap.
    def servers_needed(cap: int) -> int:
        servers = 1
        running = 0
        for size in shards:
            if running + size > cap:      # start a new server
                servers += 1
                running = size
            else:
                running += size
        return servers

    lo = max(shards)          # a server must hold its largest single shard
    hi = sum(shards)          # everything on one server
    while lo < hi:
        mid = (lo + hi) // 2
        if servers_needed(mid) <= k:
            hi = mid          # cap works -> try smaller
        else:
            lo = mid + 1      # too tight -> raise cap
    return lo


# =============================================================================
# Run harness — press the Run button; prints got vs expected for each example.
# =============================================================================
if __name__ == "__main__":
    cases = [
        ([7, 2, 5, 10, 8], 2, 18),
        ([1, 2, 3, 4, 5], 2, 9),
        ([1, 4, 4], 3, 4),
        ([2, 3, 1, 2, 4, 3], 3, 6),
        ([5], 1, 5),
    ]
    for i, (shards, k, expected) in enumerate(cases, 1):
        got = min_max_shard_load(shards, k)
        status = "PASS" if got == expected else "FAIL"
        print(f"Example {i}: got={got} expected={expected} [{status}]")

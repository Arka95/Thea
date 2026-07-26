# Coding Interview Patterns & Practice Problems

## When to Use Each Pattern
- **Arrays & Hashing** — O(1) lookups/dedup/counting; map values to indices or frequencies.
- **Two Pointers** — Sorted arrays or pair/triplet search; converge from both ends or fast/slow.
- **Sliding Window** — Contiguous subarray/substring optima over a moving range.
- **Stack** — LIFO order, matching pairs, nested/parenthesized structures, backtrack-on-pop.
- **Queue** — FIFO order, streaming, level-by-level or first-come processing.
- **Deque** — Push/pop both ends; window min/max in O(n).
- **Monotonic Stack** — Next/previous greater-or-smaller element; span/histogram problems.
- **Binary Search** — Sorted search space or "minimize/maximize feasible value" on a monotonic predicate.
- **Linked List** — In-place pointer manipulation, cycle detection, reordering.
- **Trees** — Hierarchical recursion, DFS/BFS, BST ordering, path aggregation.
- **Tries** — Prefix/word lookups, autocomplete, dictionary matching.
- **Heap / Priority Queue** — Top-K, running median, repeatedly pick min/max.
- **Backtracking** — Enumerate combinations/permutations/subsets with pruning.
- **Graphs** — Connectivity, traversal, shortest unweighted path, topological order.
- **Advanced Graphs** — Weighted shortest paths, MST, Dijkstra/Bellman-Ford/Union-Find.
- **1-D DP** — Optimal substructure over a single sequence/index.
- **2-D DP** — Decisions over two dimensions (grids, two strings, capacity).
- **Greedy** — Locally optimal choices that yield a global optimum.
- **Intervals** — Overlap/merge/scheduling on ranges; sort by start or end.
- **Bit Manipulation** — XOR tricks, masks, bit counting, integer arithmetic.
- **Math & Geometry** — Matrix transforms, number theory, coordinate/spatial logic.
- **Prefix Sum** — Range-sum queries and subarray-sum conditions in O(1) after precompute.

## Arrays & Hashing

<table>
<tr><td><a href="https://leetcode.com/problems/two-sum/">Two Sum</a></td><td><a href="https://leetcode.com/problems/contains-duplicate/">Contains Duplicate</a></td><td><a href="https://leetcode.com/problems/group-anagrams/">Group Anagrams</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/top-k-frequent-elements/">Top K Frequent Elements</a></td><td><a href="https://leetcode.com/problems/product-of-array-except-self/">Product of Array Except Self</a></td><td><a href="https://leetcode.com/problems/valid-sudoku/">Valid Sudoku</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/longest-consecutive-sequence/">Longest Consecutive Sequence</a></td><td><a href="https://leetcode.com/problems/encode-and-decode-strings/">Encode and Decode Strings</a></td><td><a href="https://leetcode.com/problems/subarray-sum-equals-k/">Subarray Sum Equals K</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/sort-colors/">Sort Colors</a></td><td></td><td></td></tr>
</table>

## Two Pointers

<table>
<tr><td><a href="https://leetcode.com/problems/valid-palindrome/">Valid Palindrome</a></td><td><a href="https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/">Two Sum II - Input Array Is Sorted</a></td><td><a href="https://leetcode.com/problems/3sum/">3Sum</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/container-with-most-water/">Container With Most Water</a></td><td><a href="https://leetcode.com/problems/trapping-rain-water/">Trapping Rain Water</a></td><td><a href="https://leetcode.com/problems/remove-duplicates-from-sorted-array/">Remove Duplicates from Sorted Array</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/move-zeroes/">Move Zeroes</a></td><td><a href="https://leetcode.com/problems/4sum/">4Sum</a></td><td><a href="https://leetcode.com/problems/boats-to-save-people/">Boats to Save People</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/squares-of-a-sorted-array/">Squares of a Sorted Array</a></td><td></td><td></td></tr>
</table>

## Sliding Window

<table>
<tr><td><a href="https://leetcode.com/problems/best-time-to-buy-and-sell-stock/">Best Time to Buy and Sell Stock</a></td><td><a href="https://leetcode.com/problems/longest-substring-without-repeating-characters/">Longest Substring Without Repeating Characters</a></td><td><a href="https://leetcode.com/problems/longest-repeating-character-replacement/">Longest Repeating Character Replacement</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/permutation-in-string/">Permutation in String</a></td><td><a href="https://leetcode.com/problems/minimum-window-substring/">Minimum Window Substring</a></td><td><a href="https://leetcode.com/problems/sliding-window-maximum/">Sliding Window Maximum</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/fruit-into-baskets/">Fruit Into Baskets</a></td><td><a href="https://leetcode.com/problems/find-all-anagrams-in-a-string/">Find All Anagrams in a String</a></td><td><a href="https://leetcode.com/problems/max-consecutive-ones-iii/">Max Consecutive Ones III</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/longest-substring-with-at-most-k-distinct-characters/">Longest Substring with At Most K Distinct Characters</a></td><td></td><td></td></tr>
</table>

## Stack

<table>
<tr><td><a href="https://leetcode.com/problems/valid-parentheses/">Valid Parentheses</a></td><td><a href="https://leetcode.com/problems/min-stack/">Min Stack</a></td><td><a href="https://leetcode.com/problems/evaluate-reverse-polish-notation/">Evaluate Reverse Polish Notation</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/generate-parentheses/">Generate Parentheses</a></td><td><a href="https://leetcode.com/problems/decode-string/">Decode String</a></td><td><a href="https://leetcode.com/problems/simplify-path/">Simplify Path</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/backspace-string-compare/">Backspace String Compare</a></td><td><a href="https://leetcode.com/problems/remove-all-adjacent-duplicates-in-string/">Remove All Adjacent Duplicates In String</a></td><td><a href="https://leetcode.com/problems/basic-calculator/">Basic Calculator</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/baseball-game/">Baseball Game</a></td><td><a href="https://leetcode.com/problems/remove-k-digits/">Remove K Digits</a></td><td><a href="https://leetcode.com/problems/exclusive-time-of-functions/">Exclusive Time of Functions</a></td></tr>
</table>

## Queue

<table>
<tr><td><a href="https://leetcode.com/problems/implement-queue-using-stacks/">Implement Queue using Stacks</a></td><td><a href="https://leetcode.com/problems/implement-stack-using-queues/">Implement Stack using Queues</a></td><td><a href="https://leetcode.com/problems/design-circular-queue/">Design Circular Queue</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/number-of-recent-calls/">Number of Recent Calls</a></td><td><a href="https://leetcode.com/problems/moving-average-from-data-stream/">Moving Average from Data Stream</a></td><td><a href="https://leetcode.com/problems/design-hit-counter/">Design Hit Counter</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/first-unique-character-in-a-string/">First Unique Character in a String</a></td><td><a href="https://leetcode.com/problems/dota2-senate/">Dota2 Senate</a></td><td><a href="https://leetcode.com/problems/time-needed-to-buy-tickets/">Time Needed to Buy Tickets</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/reveal-cards-in-increasing-order/">Reveal Cards In Increasing Order</a></td><td></td><td></td></tr>
</table>

## Deque

<table>
<tr><td><a href="https://leetcode.com/problems/design-circular-deque/">Design Circular Deque</a></td><td><a href="https://leetcode.com/problems/design-front-middle-back-queue/">Design Front Middle Back Queue</a></td><td><a href="https://leetcode.com/problems/sliding-window-maximum/">Sliding Window Maximum</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/shortest-subarray-with-sum-at-least-k/">Shortest Subarray with Sum at Least K</a></td><td><a href="https://leetcode.com/problems/jump-game-vi/">Jump Game VI</a></td><td><a href="https://leetcode.com/problems/constrained-subsequence-sum/">Constrained Subsequence Sum</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/continuous-subarrays/">Continuous Subarrays</a></td><td><a href="https://leetcode.com/problems/sum-of-subarray-minimums/">Sum of Subarray Minimums</a></td><td><a href="https://leetcode.com/problems/shortest-path-in-binary-matrix/">Shortest Path in Binary Matrix</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/01-matrix/">01 Matrix</a></td><td></td><td></td></tr>
</table>

## Monotonic Stack

<table>
<tr><td><a href="https://leetcode.com/problems/daily-temperatures/">Daily Temperatures</a></td><td><a href="https://leetcode.com/problems/next-greater-element-i/">Next Greater Element I</a></td><td><a href="https://leetcode.com/problems/next-greater-element-ii/">Next Greater Element II</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/largest-rectangle-in-histogram/">Largest Rectangle in Histogram</a></td><td><a href="https://leetcode.com/problems/maximal-rectangle/">Maximal Rectangle</a></td><td><a href="https://leetcode.com/problems/trapping-rain-water/">Trapping Rain Water</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/car-fleet/">Car Fleet</a></td><td><a href="https://leetcode.com/problems/asteroid-collision/">Asteroid Collision</a></td><td><a href="https://leetcode.com/problems/online-stock-span/">Online Stock Span</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/remove-duplicate-letters/">Remove Duplicate Letters</a></td><td><a href="https://leetcode.com/problems/sum-of-subarray-minimums/">Sum of Subarray Minimums</a></td><td><a href="https://leetcode.com/problems/next-greater-node-in-linked-list/">Next Greater Node In Linked List</a></td></tr>
</table>

## Binary Search

<table>
<tr><td><a href="https://leetcode.com/problems/binary-search/">Binary Search</a></td><td><a href="https://leetcode.com/problems/search-a-2d-matrix/">Search a 2D Matrix</a></td><td><a href="https://leetcode.com/problems/koko-eating-bananas/">Koko Eating Bananas</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/">Find Minimum in Rotated Sorted Array</a></td><td><a href="https://leetcode.com/problems/search-in-rotated-sorted-array/">Search in Rotated Sorted Array</a></td><td><a href="https://leetcode.com/problems/time-based-key-value-store/">Time Based Key-Value Store</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/median-of-two-sorted-arrays/">Median of Two Sorted Arrays</a></td><td><a href="https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/">Find First and Last Position of Element in Sorted Array</a></td><td><a href="https://leetcode.com/problems/split-array-largest-sum/">Split Array Largest Sum</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/">Capacity To Ship Packages Within D Days</a></td><td></td><td></td></tr>
</table>

## Linked List

<table>
<tr><td><a href="https://leetcode.com/problems/reverse-linked-list/">Reverse Linked List</a></td><td><a href="https://leetcode.com/problems/merge-two-sorted-lists/">Merge Two Sorted Lists</a></td><td><a href="https://leetcode.com/problems/linked-list-cycle/">Linked List Cycle</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/reorder-list/">Reorder List</a></td><td><a href="https://leetcode.com/problems/remove-nth-node-from-end-of-list/">Remove Nth Node From End of List</a></td><td><a href="https://leetcode.com/problems/copy-list-with-random-pointer/">Copy List with Random Pointer</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/add-two-numbers/">Add Two Numbers</a></td><td><a href="https://leetcode.com/problems/find-the-duplicate-number/">Find the Duplicate Number</a></td><td><a href="https://leetcode.com/problems/lru-cache/">LRU Cache</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/merge-k-sorted-lists/">Merge k Sorted Lists</a></td><td></td><td></td></tr>
</table>

## Trees

<table>
<tr><td><a href="https://leetcode.com/problems/invert-binary-tree/">Invert Binary Tree</a></td><td><a href="https://leetcode.com/problems/maximum-depth-of-binary-tree/">Maximum Depth of Binary Tree</a></td><td><a href="https://leetcode.com/problems/diameter-of-binary-tree/">Diameter of Binary Tree</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/balanced-binary-tree/">Balanced Binary Tree</a></td><td><a href="https://leetcode.com/problems/same-tree/">Same Tree</a></td><td><a href="https://leetcode.com/problems/binary-tree-level-order-traversal/">Binary Tree Level Order Traversal</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/validate-binary-search-tree/">Validate Binary Search Tree</a></td><td><a href="https://leetcode.com/problems/kth-smallest-element-in-a-bst/">Kth Smallest Element in a BST</a></td><td><a href="https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/">Lowest Common Ancestor of a Binary Tree</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/binary-tree-maximum-path-sum/">Binary Tree Maximum Path Sum</a></td><td></td><td></td></tr>
</table>

## Tries

<table>
<tr><td><a href="https://leetcode.com/problems/implement-trie-prefix-tree/">Implement Trie (Prefix Tree)</a></td><td><a href="https://leetcode.com/problems/design-add-and-search-words-data-structure/">Design Add and Search Words Data Structure</a></td><td><a href="https://leetcode.com/problems/word-search-ii/">Word Search II</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/replace-words/">Replace Words</a></td><td><a href="https://leetcode.com/problems/map-sum-pairs/">Map Sum Pairs</a></td><td><a href="https://leetcode.com/problems/longest-word-in-dictionary/">Longest Word in Dictionary</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/search-suggestions-system/">Search Suggestions System</a></td><td><a href="https://leetcode.com/problems/maximum-xor-of-two-numbers-in-an-array/">Maximum XOR of Two Numbers in an Array</a></td><td><a href="https://leetcode.com/problems/design-search-autocomplete-system/">Design Search Autocomplete System</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/word-break/">Word Break</a></td><td></td><td></td></tr>
</table>

## Heap / Priority Queue

<table>
<tr><td><a href="https://leetcode.com/problems/kth-largest-element-in-a-stream/">Kth Largest Element in a Stream</a></td><td><a href="https://leetcode.com/problems/last-stone-weight/">Last Stone Weight</a></td><td><a href="https://leetcode.com/problems/k-closest-points-to-origin/">K Closest Points to Origin</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/kth-largest-element-in-an-array/">Kth Largest Element in an Array</a></td><td><a href="https://leetcode.com/problems/task-scheduler/">Task Scheduler</a></td><td><a href="https://leetcode.com/problems/design-twitter/">Design Twitter</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/find-median-from-data-stream/">Find Median from Data Stream</a></td><td><a href="https://leetcode.com/problems/reorganize-string/">Reorganize String</a></td><td><a href="https://leetcode.com/problems/smallest-range-covering-elements-from-k-lists/">Smallest Range Covering Elements from K Lists</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/maximum-performance-of-a-team/">Maximum Performance of a Team</a></td><td></td><td></td></tr>
</table>

## Backtracking

<table>
<tr><td><a href="https://leetcode.com/problems/subsets/">Subsets</a></td><td><a href="https://leetcode.com/problems/combination-sum/">Combination Sum</a></td><td><a href="https://leetcode.com/problems/permutations/">Permutations</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/subsets-ii/">Subsets II</a></td><td><a href="https://leetcode.com/problems/combination-sum-ii/">Combination Sum II</a></td><td><a href="https://leetcode.com/problems/word-search/">Word Search</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/palindrome-partitioning/">Palindrome Partitioning</a></td><td><a href="https://leetcode.com/problems/letter-combinations-of-a-phone-number/">Letter Combinations of a Phone Number</a></td><td><a href="https://leetcode.com/problems/n-queens/">N-Queens</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/sudoku-solver/">Sudoku Solver</a></td><td></td><td></td></tr>
</table>

## Graphs

<table>
<tr><td><a href="https://leetcode.com/problems/number-of-islands/">Number of Islands</a></td><td><a href="https://leetcode.com/problems/clone-graph/">Clone Graph</a></td><td><a href="https://leetcode.com/problems/max-area-of-island/">Max Area of Island</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/pacific-atlantic-water-flow/">Pacific Atlantic Water Flow</a></td><td><a href="https://leetcode.com/problems/surrounded-regions/">Surrounded Regions</a></td><td><a href="https://leetcode.com/problems/rotting-oranges/">Rotting Oranges</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/course-schedule/">Course Schedule</a></td><td><a href="https://leetcode.com/problems/course-schedule-ii/">Course Schedule II</a></td><td><a href="https://leetcode.com/problems/redundant-connection/">Redundant Connection</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/word-ladder/">Word Ladder</a></td><td></td><td></td></tr>
</table>

## Advanced Graphs

<table>
<tr><td><a href="https://leetcode.com/problems/network-delay-time/">Network Delay Time</a></td><td><a href="https://leetcode.com/problems/cheapest-flights-within-k-stops/">Cheapest Flights Within K Stops</a></td><td><a href="https://leetcode.com/problems/min-cost-to-connect-all-points/">Min Cost to Connect All Points</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/swim-in-rising-water/">Swim in Rising Water</a></td><td><a href="https://leetcode.com/problems/alien-dictionary/">Alien Dictionary</a></td><td><a href="https://leetcode.com/problems/reconstruct-itinerary/">Reconstruct Itinerary</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/path-with-maximum-probability/">Path with Maximum Probability</a></td><td><a href="https://leetcode.com/problems/find-the-city-with-the-smallest-number-of-neighbors-at-a-threshold-distance/">Find the City With the Smallest Number of Neighbors</a></td><td><a href="https://leetcode.com/problems/number-of-connected-components-in-an-undirected-graph/">Number of Connected Components in an Undirected Graph</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/graph-valid-tree/">Graph Valid Tree</a></td><td></td><td></td></tr>
</table>

## 1-D Dynamic Programming

<table>
<tr><td><a href="https://leetcode.com/problems/climbing-stairs/">Climbing Stairs</a></td><td><a href="https://leetcode.com/problems/min-cost-climbing-stairs/">Min Cost Climbing Stairs</a></td><td><a href="https://leetcode.com/problems/house-robber/">House Robber</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/house-robber-ii/">House Robber II</a></td><td><a href="https://leetcode.com/problems/longest-palindromic-substring/">Longest Palindromic Substring</a></td><td><a href="https://leetcode.com/problems/palindromic-substrings/">Palindromic Substrings</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/decode-ways/">Decode Ways</a></td><td><a href="https://leetcode.com/problems/coin-change/">Coin Change</a></td><td><a href="https://leetcode.com/problems/longest-increasing-subsequence/">Longest Increasing Subsequence</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/maximum-product-subarray/">Maximum Product Subarray</a></td><td></td><td></td></tr>
</table>

## 2-D Dynamic Programming

<table>
<tr><td><a href="https://leetcode.com/problems/unique-paths/">Unique Paths</a></td><td><a href="https://leetcode.com/problems/longest-common-subsequence/">Longest Common Subsequence</a></td><td><a href="https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/">Best Time to Buy and Sell Stock with Cooldown</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/coin-change-ii/">Coin Change II</a></td><td><a href="https://leetcode.com/problems/target-sum/">Target Sum</a></td><td><a href="https://leetcode.com/problems/interleaving-string/">Interleaving String</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/edit-distance/">Edit Distance</a></td><td><a href="https://leetcode.com/problems/distinct-subsequences/">Distinct Subsequences</a></td><td><a href="https://leetcode.com/problems/regular-expression-matching/">Regular Expression Matching</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/partition-equal-subset-sum/">Partition Equal Subset Sum</a></td><td></td><td></td></tr>
</table>

## Greedy

<table>
<tr><td><a href="https://leetcode.com/problems/maximum-subarray/">Maximum Subarray</a></td><td><a href="https://leetcode.com/problems/jump-game/">Jump Game</a></td><td><a href="https://leetcode.com/problems/jump-game-ii/">Jump Game II</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/gas-station/">Gas Station</a></td><td><a href="https://leetcode.com/problems/hand-of-straights/">Hand of Straights</a></td><td><a href="https://leetcode.com/problems/merge-triplets-to-form-target-triplet/">Merge Triplets to Form Target Triplet</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/partition-labels/">Partition Labels</a></td><td><a href="https://leetcode.com/problems/valid-parenthesis-string/">Valid Parenthesis String</a></td><td><a href="https://leetcode.com/problems/non-overlapping-intervals/">Non-overlapping Intervals</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/candy/">Candy</a></td><td></td><td></td></tr>
</table>

## Intervals

<table>
<tr><td><a href="https://leetcode.com/problems/insert-interval/">Insert Interval</a></td><td><a href="https://leetcode.com/problems/merge-intervals/">Merge Intervals</a></td><td><a href="https://leetcode.com/problems/non-overlapping-intervals/">Non-overlapping Intervals</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/meeting-rooms/">Meeting Rooms</a></td><td><a href="https://leetcode.com/problems/meeting-rooms-ii/">Meeting Rooms II</a></td><td><a href="https://leetcode.com/problems/minimum-interval-to-include-each-query/">Minimum Interval to Include Each Query</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/interval-list-intersections/">Interval List Intersections</a></td><td><a href="https://leetcode.com/problems/employee-free-time/">Employee Free Time</a></td><td><a href="https://leetcode.com/problems/my-calendar-i/">My Calendar I</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/car-pooling/">Car Pooling</a></td><td></td><td></td></tr>
</table>

## Bit Manipulation

<table>
<tr><td><a href="https://leetcode.com/problems/single-number/">Single Number</a></td><td><a href="https://leetcode.com/problems/number-of-1-bits/">Number of 1 Bits</a></td><td><a href="https://leetcode.com/problems/counting-bits/">Counting Bits</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/reverse-bits/">Reverse Bits</a></td><td><a href="https://leetcode.com/problems/missing-number/">Missing Number</a></td><td><a href="https://leetcode.com/problems/sum-of-two-integers/">Sum of Two Integers</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/reverse-integer/">Reverse Integer</a></td><td><a href="https://leetcode.com/problems/single-number-ii/">Single Number II</a></td><td><a href="https://leetcode.com/problems/bitwise-and-of-numbers-range/">Bitwise AND of Numbers Range</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/divide-two-integers/">Divide Two Integers</a></td><td></td><td></td></tr>
</table>

## Math & Geometry

<table>
<tr><td><a href="https://leetcode.com/problems/rotate-image/">Rotate Image</a></td><td><a href="https://leetcode.com/problems/spiral-matrix/">Spiral Matrix</a></td><td><a href="https://leetcode.com/problems/set-matrix-zeroes/">Set Matrix Zeroes</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/happy-number/">Happy Number</a></td><td><a href="https://leetcode.com/problems/plus-one/">Plus One</a></td><td><a href="https://leetcode.com/problems/powx-n/">Pow(x, n)</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/multiply-strings/">Multiply Strings</a></td><td><a href="https://leetcode.com/problems/detect-squares/">Detect Squares</a></td><td><a href="https://leetcode.com/problems/robot-bounded-in-circle/">Robot Bounded In Circle</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/roman-to-integer/">Roman to Integer</a></td><td></td><td></td></tr>
</table>

## Prefix Sum

<table>
<tr><td><a href="https://leetcode.com/problems/range-sum-query-immutable/">Range Sum Query - Immutable</a></td><td><a href="https://leetcode.com/problems/range-sum-query-2d-immutable/">Range Sum Query 2D - Immutable</a></td><td><a href="https://leetcode.com/problems/find-pivot-index/">Find Pivot Index</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/contiguous-array/">Contiguous Array</a></td><td><a href="https://leetcode.com/problems/continuous-subarray-sum/">Continuous Subarray Sum</a></td><td><a href="https://leetcode.com/problems/subarray-sums-divisible-by-k/">Subarray Sums Divisible by K</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/minimum-size-subarray-sum/">Minimum Size Subarray Sum</a></td><td><a href="https://leetcode.com/problems/binary-subarrays-with-sum/">Binary Subarrays With Sum</a></td><td><a href="https://leetcode.com/problems/count-number-of-nice-subarrays/">Count Number of Nice Subarrays</a></td></tr>
<tr><td><a href="https://leetcode.com/problems/maximum-sum-of-distinct-subarrays-with-length-k/">Maximum Sum of Distinct Subarrays With Length K</a></td><td></td><td></td></tr>
</table>


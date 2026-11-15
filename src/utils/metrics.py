"""
utils/metrics.py — Execution metrics collection and reporting.

Provides a decorator-based approach to instrument major pipeline functions with:
  - Execution time (wall clock)
  - Function name and module
  - Success/failure status
  - Structured metric records

Design:
  - Zero external dependencies (stdlib only + dataclasses)
  - Thread-safe metric accumulation
  - JSON-serializable output for metadata embedding
  - Decorator is opt-in on major functions only (not micro-functions)

Usage:
    from utils.metrics import track, MetricsCollector

    collector = MetricsCollector()

    @track(collector)
    def compute_motion_scores(video_path, config):
        ...

    # After pipeline completes:
    report = collector.report()
    print(report)
"""

import time
import threading
import functools
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable

logger = logging.getLogger("thea.metrics")


@dataclass
class MetricRecord:
    """A single function execution metric."""
    function: str
    module: str
    status: str              # "success" | "error"
    duration_sec: float
    timestamp_start: float   # time.time() epoch
    error: Optional[str] = None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration_sec"] = round(d["duration_sec"], 4)
        d["timestamp_start"] = round(d["timestamp_start"], 3)
        if d["error"] is None:
            del d["error"]
        if not d["context"]:
            del d["context"]
        return d


class MetricsCollector:
    """Thread-safe collector for execution metrics.

    Accumulates MetricRecords and provides summary reporting.
    """

    def __init__(self):
        self._records: list = []
        self._lock = threading.Lock()

    def record(self, metric: MetricRecord):
        """Add a metric record (thread-safe)."""
        with self._lock:
            self._records.append(metric)

    @property
    def records(self) -> list:
        with self._lock:
            return list(self._records)

    def clear(self):
        with self._lock:
            self._records.clear()

    def summary(self) -> dict:
        """Aggregate metrics into a summary report.

        Returns:
            {
                "total_functions": int,
                "total_duration_sec": float,
                "success_count": int,
                "error_count": int,
                "functions": {
                    "func_name": {
                        "calls": int,
                        "total_sec": float,
                        "avg_ms": float,
                        "min_ms": float,
                        "max_ms": float,
                        "errors": int
                    }
                }
            }
        """
        with self._lock:
            records = list(self._records)

        if not records:
            return {"total_functions": 0, "total_duration_sec": 0, "success_count": 0, "error_count": 0, "functions": {}}

        # Aggregate per function
        funcs = {}
        for r in records:
            name = r.function
            if name not in funcs:
                funcs[name] = {"calls": 0, "total_sec": 0.0, "durations": [], "errors": 0}
            funcs[name]["calls"] += 1
            funcs[name]["total_sec"] += r.duration_sec
            funcs[name]["durations"].append(r.duration_sec)
            if r.status == "error":
                funcs[name]["errors"] += 1

        # Build output
        func_summary = {}
        for name, data in funcs.items():
            durations = data["durations"]
            func_summary[name] = {
                "calls": data["calls"],
                "total_sec": round(data["total_sec"], 3),
                "avg_ms": round((data["total_sec"] / data["calls"]) * 1000, 2),
                "min_ms": round(min(durations) * 1000, 2),
                "max_ms": round(max(durations) * 1000, 2),
                "errors": data["errors"],
            }

        return {
            "total_functions": len(records),
            "total_duration_sec": round(sum(r.duration_sec for r in records), 3),
            "success_count": sum(1 for r in records if r.status == "success"),
            "error_count": sum(1 for r in records if r.status == "error"),
            "functions": func_summary,
        }

    def report_table(self) -> str:
        """Format summary as a readable table string."""
        s = self.summary()
        lines = [
            "EXECUTION METRICS",
            f"{'Function':<30} {'Calls':>6} {'Total(s)':>9} {'Avg(ms)':>9} {'Min(ms)':>9} {'Max(ms)':>9} {'Errors':>7}",
            "-" * 85,
        ]
        for name, data in s["functions"].items():
            lines.append(
                f"{name:<30} {data['calls']:>6} {data['total_sec']:>9.3f} "
                f"{data['avg_ms']:>9.2f} {data['min_ms']:>9.2f} {data['max_ms']:>9.2f} {data['errors']:>7}"
            )
        lines.append("-" * 85)
        lines.append(f"Total: {s['total_functions']} calls, {s['total_duration_sec']:.3f}s, "
                     f"{s['error_count']} errors")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Global default collector (used when no explicit collector is passed)
# ---------------------------------------------------------------------------

_default_collector = MetricsCollector()


def get_default_collector() -> MetricsCollector:
    """Get the global default metrics collector."""
    return _default_collector


def reset_default_collector():
    """Reset the global collector (useful in tests)."""
    _default_collector.clear()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def track(collector: MetricsCollector = None, context_fn: Callable = None):
    """Decorator to track execution time and status of a function.

    Args:
        collector: MetricsCollector instance (uses global default if None).
        context_fn: Optional callable(args, kwargs) -> dict for extra context.

    Usage:
        @track()
        def my_function(x):
            ...

        @track(collector=my_collector, context_fn=lambda a, kw: {"video": a[0]})
        def process_video(path, config):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Resolve collector lazily so reset_default_collector() works
            coll = collector if collector is not None else _default_collector
            module = func.__module__ or ""
            func_name = func.__qualname__

            # Gather context
            ctx = {}
            if context_fn:
                try:
                    ctx = context_fn(args, kwargs) or {}
                except Exception:
                    pass

            t_start = time.time()
            t_perf = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - t_perf

                metric = MetricRecord(
                    function=func_name,
                    module=module,
                    status="success",
                    duration_sec=duration,
                    timestamp_start=t_start,
                    context=ctx,
                )
                coll.record(metric)

                logger.debug(f"{func_name} completed in {duration*1000:.1f}ms")
                return result

            except Exception as e:
                duration = time.perf_counter() - t_perf

                metric = MetricRecord(
                    function=func_name,
                    module=module,
                    status="error",
                    duration_sec=duration,
                    timestamp_start=t_start,
                    error=f"{type(e).__name__}: {e}",
                    context=ctx,
                )
                coll.record(metric)

                logger.error(f"{func_name} failed after {duration*1000:.1f}ms: {type(e).__name__}: {e}")
                raise

        return wrapper
    return decorator

"""Metrics remain bounded, safe and unable to change application outcomes."""

import logging

import pytest

from utils.metrics import (
    MAX_METRIC_RECORDS,
    MetricRecord,
    MetricsCollector,
    get_default_collector,
    log_default_metrics,
    track,
)


def test_tracking_failure_does_not_mask_success_or_application_error(monkeypatch):
    collector = MetricsCollector()

    def unavailable(record):
        raise OSError("collector unavailable")

    monkeypatch.setattr(collector, "record", unavailable)

    @track(collector)
    def operation(fail=False):
        if fail:
            raise ValueError("application error")
        return "result"

    assert operation() == "result"
    with pytest.raises(ValueError, match="application error"):
        operation(True)


def test_tracking_logs_operation_outcome_and_error_type_not_exception_message(caplog):
    collector = MetricsCollector()

    @track(collector, context_fn=lambda args, kwargs: {"operation": "caption"})
    def operation():
        raise RuntimeError("sensitive endpoint response")

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        operation()
    assert collector.records[0].error == "RuntimeError"
    assert collector.records[0].duration_sec >= 0
    assert "operation=caption" in caplog.text and "outcome=error" in caplog.text
    assert "sensitive endpoint response" not in caplog.text


def test_collector_discards_oldest_records_when_bounded():
    collector = MetricsCollector()
    for index in range(MAX_METRIC_RECORDS + 2):
        collector.record(MetricRecord(str(index), "tests", "success", 0.1, 0))
    assert len(collector.records) == MAX_METRIC_RECORDS
    assert collector.records[0].function == "2"
    assert collector.records[-1].function == str(MAX_METRIC_RECORDS + 1)


def test_summary_failure_remains_best_effort(monkeypatch):
    def unavailable():
        raise OSError("collector unavailable")

    collector = get_default_collector()
    collector.record(MetricRecord("operation", "tests", "success", 0.1, 0))
    monkeypatch.setattr(collector, "report_table", unavailable)
    log_default_metrics()

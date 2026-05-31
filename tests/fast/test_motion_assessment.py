"""
tests/fast/test_motion_assessment.py — Unit tests for motion classification (no video I/O).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from motion_assessment.assessment import (
    MotionAssessment, THRESHOLD_PRESETS, get_assessment_table, _RANGES,
)


class TestMotionAssessmentEnum:
    def test_all_members_exist(self):
        expected = {"STATIC", "VERY_STABLE", "STABLE", "MODERATE", "UNSTABLE", "VERY_UNSTABLE", "CUT"}
        assert set(m.name for m in MotionAssessment) == expected

    def test_ranges_are_contiguous(self):
        members = list(MotionAssessment)
        for i in range(len(members) - 1):
            _, upper = members[i].range
            lower, _ = members[i + 1].range
            assert upper == lower

    def test_ranges_start_at_zero(self):
        assert MotionAssessment.STATIC.range[0] == 0.0

    def test_ranges_end_at_infinity(self):
        assert MotionAssessment.CUT.range[1] == float("inf")

    def test_stock_footage_grade(self):
        assert MotionAssessment.STATIC.stock_footage_grade is True
        assert MotionAssessment.STABLE.stock_footage_grade is True
        assert MotionAssessment.MODERATE.stock_footage_grade is False
        assert MotionAssessment.UNSTABLE.stock_footage_grade is False


class TestFromScore:
    def test_boundary_values(self):
        assert MotionAssessment.from_score(0.0) == MotionAssessment.STATIC
        assert MotionAssessment.from_score(0.05) == MotionAssessment.VERY_STABLE
        assert MotionAssessment.from_score(0.20) == MotionAssessment.STABLE
        assert MotionAssessment.from_score(0.50) == MotionAssessment.MODERATE
        assert MotionAssessment.from_score(1.0) == MotionAssessment.UNSTABLE
        assert MotionAssessment.from_score(2.0) == MotionAssessment.VERY_UNSTABLE
        assert MotionAssessment.from_score(5.0) == MotionAssessment.CUT

    def test_resolution_scaling(self):
        # 0.6 at 640px -> normalized 0.3 at 320px -> STABLE
        assert MotionAssessment.from_score(0.6, analysis_width=640) == MotionAssessment.STABLE

    def test_sample_video_mean(self):
        assert MotionAssessment.from_score(0.3742) == MotionAssessment.STABLE


class TestThresholdPresets:
    def test_all_presets_exist(self):
        for name in ("strict", "cinematic", "permissive", "action"):
            assert name in THRESHOLD_PRESETS

    def test_presets_ordered(self):
        assert THRESHOLD_PRESETS["strict"]["motion_threshold"] < THRESHOLD_PRESETS["cinematic"]["motion_threshold"]
        assert THRESHOLD_PRESETS["cinematic"]["motion_threshold"] < THRESHOLD_PRESETS["permissive"]["motion_threshold"]
        assert THRESHOLD_PRESETS["permissive"]["motion_threshold"] < THRESHOLD_PRESETS["action"]["motion_threshold"]


class TestGetAssessmentTable:
    def test_returns_all_categories(self):
        assert len(get_assessment_table()) == 7

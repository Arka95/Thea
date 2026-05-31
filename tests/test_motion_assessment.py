"""
test_motion_assessment.py — Tests for motion classification enum and thresholds.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from motion_assessment import (
    MotionAssessment,
    THRESHOLD_PRESETS,
    get_assessment_table,
    _RANGES,
    _DESCRIPTIONS,
)


class TestMotionAssessmentEnum:
    """Test the MotionAssessment enum values and properties."""

    def test_all_members_exist(self):
        expected = {"STATIC", "VERY_STABLE", "STABLE", "MODERATE", "UNSTABLE", "VERY_UNSTABLE", "CUT"}
        assert set(m.name for m in MotionAssessment) == expected

    def test_enum_values(self):
        assert MotionAssessment.STATIC.value == "static"
        assert MotionAssessment.STABLE.value == "stable"
        assert MotionAssessment.CUT.value == "cut"

    def test_descriptions_not_empty(self):
        for member in MotionAssessment:
            assert len(member.description) > 10

    def test_ranges_are_contiguous(self):
        """Ranges should cover 0 to infinity without gaps."""
        members = list(MotionAssessment)
        for i in range(len(members) - 1):
            _, upper = members[i].range
            lower, _ = members[i + 1].range
            assert upper == lower, f"Gap between {members[i].name} and {members[i+1].name}"

    def test_ranges_start_at_zero(self):
        assert MotionAssessment.STATIC.range[0] == 0.0

    def test_ranges_end_at_infinity(self):
        assert MotionAssessment.CUT.range[1] == float("inf")

    def test_stock_footage_grade(self):
        assert MotionAssessment.STATIC.stock_footage_grade is True
        assert MotionAssessment.VERY_STABLE.stock_footage_grade is True
        assert MotionAssessment.STABLE.stock_footage_grade is True
        assert MotionAssessment.MODERATE.stock_footage_grade is False
        assert MotionAssessment.UNSTABLE.stock_footage_grade is False
        assert MotionAssessment.CUT.stock_footage_grade is False


class TestFromScore:
    """Test score-to-assessment classification."""

    def test_static_score(self):
        assert MotionAssessment.from_score(0.0) == MotionAssessment.STATIC
        assert MotionAssessment.from_score(0.03) == MotionAssessment.STATIC

    def test_very_stable_score(self):
        assert MotionAssessment.from_score(0.05) == MotionAssessment.VERY_STABLE
        assert MotionAssessment.from_score(0.15) == MotionAssessment.VERY_STABLE

    def test_stable_score(self):
        assert MotionAssessment.from_score(0.20) == MotionAssessment.STABLE
        assert MotionAssessment.from_score(0.37) == MotionAssessment.STABLE

    def test_moderate_score(self):
        assert MotionAssessment.from_score(0.50) == MotionAssessment.MODERATE
        assert MotionAssessment.from_score(0.99) == MotionAssessment.MODERATE

    def test_unstable_score(self):
        assert MotionAssessment.from_score(1.0) == MotionAssessment.UNSTABLE
        assert MotionAssessment.from_score(1.5) == MotionAssessment.UNSTABLE

    def test_very_unstable_score(self):
        assert MotionAssessment.from_score(2.5) == MotionAssessment.VERY_UNSTABLE

    def test_cut_score(self):
        assert MotionAssessment.from_score(5.0) == MotionAssessment.CUT
        assert MotionAssessment.from_score(100.0) == MotionAssessment.CUT

    def test_resolution_scaling(self):
        """Score at 640px should be equivalent to 2x at 320px."""
        # 0.6 at 640px → normalized to 0.3 at 320px → STABLE
        assert MotionAssessment.from_score(0.6, analysis_width=640) == MotionAssessment.STABLE
        # 0.3 at 320px → STABLE
        assert MotionAssessment.from_score(0.3, analysis_width=320) == MotionAssessment.STABLE

    def test_sample_video_overall_assessment(self):
        """The sample video has mean motion 0.3742, which should be STABLE."""
        assert MotionAssessment.from_score(0.3742) == MotionAssessment.STABLE


class TestThresholdPresets:
    """Test threshold preset definitions."""

    def test_presets_exist(self):
        assert "strict" in THRESHOLD_PRESETS
        assert "cinematic" in THRESHOLD_PRESETS
        assert "permissive" in THRESHOLD_PRESETS
        assert "action" in THRESHOLD_PRESETS

    def test_presets_have_threshold(self):
        for name, preset in THRESHOLD_PRESETS.items():
            assert "motion_threshold" in preset
            assert preset["motion_threshold"] > 0

    def test_presets_are_ordered(self):
        """Strict < Cinematic < Permissive < Action."""
        assert THRESHOLD_PRESETS["strict"]["motion_threshold"] < THRESHOLD_PRESETS["cinematic"]["motion_threshold"]
        assert THRESHOLD_PRESETS["cinematic"]["motion_threshold"] < THRESHOLD_PRESETS["permissive"]["motion_threshold"]
        assert THRESHOLD_PRESETS["permissive"]["motion_threshold"] < THRESHOLD_PRESETS["action"]["motion_threshold"]

    def test_presets_have_description(self):
        for name, preset in THRESHOLD_PRESETS.items():
            assert "description" in preset
            assert len(preset["description"]) > 10


class TestGetAssessmentTable:
    """Test the assessment table helper."""

    def test_returns_all_categories(self):
        table = get_assessment_table()
        assert len(table) == 7

    def test_table_has_required_fields(self):
        table = get_assessment_table()
        for row in table:
            assert "category" in row
            assert "range_low" in row
            assert "description" in row
            assert "stock_footage_ok" in row

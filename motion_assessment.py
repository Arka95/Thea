"""
motion_assessment.py — Motion classification enum and thresholds.

Defines standardized motion categories used throughout the Thea pipeline
for classifying frame-level and segment-level motion intensity.

The threshold values are derived from:
  - OpenCV Farneback optical flow mean magnitude at 320px analysis width
  - Empirical testing on cinematic 4K footage (30fps)
  - Industry references for camera motion classification in post-production

At 320px analysis width, mean pixel displacement values map to:
  - Static shots (tripod, locked-off): 0.00 - 0.05
  - Slow dolly/slider: 0.05 - 0.20
  - Smooth pan/tilt: 0.20 - 0.50
  - Fast pan or handheld (stabilized): 0.50 - 1.00
  - Jerky handheld / whip pan: 1.00 - 2.00
  - Scene cut / extreme motion: 2.00+

These scale linearly with analysis resolution. At 640px width, multiply by ~2.
"""

from enum import Enum
from typing import Tuple


class MotionAssessment(Enum):
    """Motion intensity classification for video segments.

    Each member maps to a (lower_bound, upper_bound) range of mean motion scores
    at the reference analysis width of 320px.
    """

    STATIC = "static"
    VERY_STABLE = "very_stable"
    STABLE = "stable"
    MODERATE = "moderate"
    UNSTABLE = "unstable"
    VERY_UNSTABLE = "very_unstable"
    CUT = "cut"

    @property
    def description(self) -> str:
        return _DESCRIPTIONS[self]

    @property
    def range(self) -> Tuple[float, float]:
        """(lower_bound_inclusive, upper_bound_exclusive) at 320px analysis width."""
        return _RANGES[self]

    @property
    def stock_footage_grade(self) -> bool:
        """Whether this motion level is acceptable for stock footage extraction."""
        return self in (MotionAssessment.STATIC, MotionAssessment.VERY_STABLE, MotionAssessment.STABLE)

    @classmethod
    def from_score(cls, score: float, analysis_width: int = 320) -> "MotionAssessment":
        """Classify a motion score into an assessment category.

        Args:
            score: Mean motion magnitude (pixel displacement)
            analysis_width: Width at which flow was computed (for scaling)

        Returns:
            MotionAssessment enum value
        """
        # Normalize to reference width of 320px
        scale_factor = 320.0 / analysis_width
        normalized = score * scale_factor

        for assessment, (low, high) in _RANGES.items():
            if low <= normalized < high:
                return assessment
        return cls.CUT


# Motion score ranges at 320px reference width
_RANGES = {
    MotionAssessment.STATIC:        (0.00, 0.05),
    MotionAssessment.VERY_STABLE:   (0.05, 0.20),
    MotionAssessment.STABLE:        (0.20, 0.50),
    MotionAssessment.MODERATE:      (0.50, 1.00),
    MotionAssessment.UNSTABLE:      (1.00, 2.00),
    MotionAssessment.VERY_UNSTABLE: (2.00, 5.00),
    MotionAssessment.CUT:           (5.00, float("inf")),
}

# Human-readable descriptions
_DESCRIPTIONS = {
    MotionAssessment.STATIC:        "Tripod/locked camera, no visible motion",
    MotionAssessment.VERY_STABLE:   "Slow dolly, slider, or imperceptible drift",
    MotionAssessment.STABLE:        "Smooth pan/tilt or gentle tracking shot",
    MotionAssessment.MODERATE:      "Fast pan, stabilized handheld, or intentional camera movement",
    MotionAssessment.UNSTABLE:      "Jerky handheld, whip pan, or irregular camera motion",
    MotionAssessment.VERY_UNSTABLE: "Extreme shake, rapid direction change, or unstabilized handheld",
    MotionAssessment.CUT:           "Scene cut, flash, or abrupt transition (not real motion)",
}


# Suggested threshold mapping for config.json
# Use these as starting points for motion_threshold in window_detection
THRESHOLD_PRESETS = {
    "strict": {
        "motion_threshold": 0.20,
        "description": "Only static and very slow camera moves. Best for b-roll overlay footage.",
    },
    "cinematic": {
        "motion_threshold": 0.50,
        "description": "Smooth cinematic shots including pans/tilts. Excludes handheld/jerky. Default for stock footage.",
    },
    "permissive": {
        "motion_threshold": 1.00,
        "description": "Allows moderate motion including fast pans. Only excludes clearly unstable footage.",
    },
    "action": {
        "motion_threshold": 2.00,
        "description": "Very permissive. Allows most motion except extreme shake or scene cuts.",
    },
}


def get_assessment_table() -> list:
    """Return assessment categories as a list of dicts for display/logging."""
    rows = []
    for assessment in MotionAssessment:
        low, high = assessment.range
        rows.append({
            "category": assessment.value,
            "range_low": low,
            "range_high": high if high != float("inf") else None,
            "description": assessment.description,
            "stock_footage_ok": assessment.stock_footage_grade,
        })
    return rows

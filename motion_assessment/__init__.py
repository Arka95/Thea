"""
motion_assessment/__init__.py - Public API for motion assessment module.
"""

from motion_assessment.assessment import MotionAssessment, THRESHOLD_PRESETS, get_assessment_table
from motion_assessment.optical_flow import create_flow_calculator
from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows

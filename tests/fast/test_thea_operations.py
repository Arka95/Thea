import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from thea.operations import get_registry
from thea.pipeline import PipelineContext


def test_package_init_adds_project_root_to_sys_path():
    import thea

    expected = Path(__file__).resolve().parents[2]
    assert str(expected) in sys.path
    assert thea.__version__ == "2.0.0"


def test_registry_loads_expected_operations():
    registry = get_registry()

    assert {"downscale", "analyze", "slice", "colorgrade", "slowdown", "speedup"} <= set(registry)
    assert registry["colorgrade"].status == "stub"
    assert registry["slowdown"].status == "stub"
    assert registry["speedup"].status == "stub"


def test_downscale_operation_updates_analysis_path(tmp_path, monkeypatch):
    registry = get_registry()
    context = PipelineContext(
        source_path=tmp_path / "source.mp4",
        current_video_path=tmp_path / "source.mp4",
        data_dir=tmp_path / "Thea",
    )
    context.source_path.touch()

    expected_output = context.data_dir / "downscaled" / "source.mp4"

    calls = {}

    def fake_downscale(source_path, output_path, max_width, codec, lossless=False):
        calls.update(
            source_path=source_path,
            output_path=output_path,
            max_width=max_width,
            codec=codec,
            lossless=lossless,
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).touch()
        return {"output": output_path}

    monkeypatch.setattr("thea.operations.downscale.downscale_video", fake_downscale)

    updated = registry["downscale"].execute(
        context,
        {"analysis": {"max_width": 320}, "output": {"codec": "mp4v"}},
    )

    assert updated.analysis_video_path == expected_output
    assert calls == {
        "source_path": str(context.source_path),
        "output_path": str(expected_output),
        "max_width": 320,
        "codec": "mp4v",
        "lossless": False,
    }


def test_analyze_operation_updates_context(monkeypatch, tmp_path):
    registry = get_registry()
    analysis_path = tmp_path / "analysis.mp4"
    context = PipelineContext(
        source_path=tmp_path / "source.mp4",
        current_video_path=tmp_path / "source.mp4",
        analysis_video_path=analysis_path,
    )

    result = {
        "motion_scores": [0.1, 0.2],
        "motion_stats": {"mean": 0.15},
        "video_info": {"fps": 30.0},
    }
    windows = [{"start_sec": 0.0, "end_sec": 2.0, "duration_sec": 2.0}]

    monkeypatch.setattr("thea.operations.analyze.compute_motion_scores", lambda path, config: result)
    monkeypatch.setattr("thea.operations.analyze.detect_stable_windows", lambda scores, fps, config: windows)

    updated = registry["analyze"].execute(context, {"window_detection": {}})

    assert updated.motion_scores == result["motion_scores"]
    assert updated.motion_stats == result["motion_stats"]
    assert updated.stable_windows == windows


def test_slice_operation_uses_source_video_and_sets_clips(monkeypatch, tmp_path):
    registry = get_registry()
    context = PipelineContext(
        source_path=tmp_path / "source.mp4",
        current_video_path=tmp_path / "source.mp4",
        stable_windows=[{"start_sec": 1.0, "end_sec": 3.0, "duration_sec": 2.0}],
        data_dir=tmp_path / "Thea",
    )

    clip_path = context.data_dir / "sliced" / "source_1.mp4"

    def fake_slice(video_path, windows, config, output_dir=None):
        assert video_path == str(context.source_path)
        assert windows == context.stable_windows
        assert output_dir == str(context.data_dir / "sliced")
        return [str(clip_path)]

    monkeypatch.setattr("thea.operations.slice_op.slice_video", fake_slice)

    updated = registry["slice"].execute(context, {"output": {"codec": "mp4v"}})

    assert updated.clips == [clip_path]


@pytest.mark.parametrize("name", ["colorgrade", "slowdown", "speedup"])
def test_stub_operations_raise(name):
    operation = get_registry()[name]

    with pytest.raises(NotImplementedError, match=f"{name} is not yet implemented"):
        operation.execute(None, {})

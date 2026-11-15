"""MCP tools matching Thea's CLI operations; no media work happens at import."""

import logging
import sys
from threading import Lock
from typing import Any, Literal

_operation_lock = Lock()


def run(command, **arguments):
    """Run one operation without mixing its process-local metrics with another."""
    from mcp.server.mcpserver.exceptions import ToolError

    from main import run_command
    from utils.metrics import log_default_metrics, reset_default_collector

    with _operation_lock:
        reset_default_collector()
        try:
            return run_command(command, **arguments)
        except (ValueError, FileNotFoundError, FileExistsError) as error:
            raise ToolError(str(error)) from error
        finally:
            log_default_metrics()


def create_server():
    """Build the optional MCP v2 server without starting a transport."""
    from mcp.server import MCPServer

    server = MCPServer(
        "Thea",
        instructions=(
            "Process existing source footage using tools named after the CLI commands. "
            "Paths and output settings are local to the server. Caption requires a running "
            "image-capable endpoint and an explicit model. Pan defaults to a 9:16 crop "
            "moving left-to-right for the original video's full duration."
        ),
    )

    @server.tool()
    def presets() -> dict[str, Any]:
        """List available presets. CLI: thea presets. Does not process media."""
        return run("presets")

    @server.tool()
    def downscale(
        path: str,
        preset: str = "cinematic",
        config: str | None = None,
        output: str | None = None,
        width: int = 320,
        lossless: bool = False,
    ) -> dict[str, Any]:
        """Create analysis copies. CLI: thea downscale PATH; output is a directory."""
        return run("downscale", **locals())

    @server.tool()
    def analyze(
        path: str,
        preset: str = "cinematic",
        config: str | None = None,
        output: Literal["csv", "pkl"] = "csv",
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Assess motion. CLI: thea analyze PATH; output/output_path select batch reports."""
        return run("analyze", **locals())

    @server.tool()
    def slice(
        path: str,
        preset: str = "cinematic",
        config: str | None = None,
        output: str | None = None,
    ) -> dict[str, Any]:
        """Analyze and extract stable windows. CLI: thea slice PATH; output is a directory."""
        return run("slice", **locals())

    @server.tool()
    def pipeline(
        path: str,
        preset: str = "cinematic",
        config: str | None = None,
        output: str | None = None,
    ) -> dict[str, Any]:
        """Downscale, analyze and slice originals. CLI: thea pipeline PATH; output is a directory."""
        return run("pipeline", **locals())

    @server.tool()
    def merge(
        paths: list[str] | None = None,
        manifest: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Join compatible clips. CLI: thea merge; use paths or manifest, not both."""
        return run("merge", paths=paths or [], manifest=manifest, output_path=output_path)

    @server.tool()
    def crop(
        path: str, width: int, height: int, x: int, y: int, output_path: str | None = None
    ) -> dict[str, Any]:
        """Crop a rectangle at top-left x,y. CLI: thea crop PATH WIDTH HEIGHT X Y."""
        return run("crop", **locals())

    @server.tool()
    def centercrop(
        path: str, width: int, height: int, output_path: str | None = None
    ) -> dict[str, Any]:
        """Center a pixel-sized crop. CLI: thea centercrop PATH WIDTH HEIGHT."""
        return run("centercrop", **locals())

    @server.tool()
    def ratiocrop(
        path: str, ratiox: float, ratioy: float, output_path: str | None = None
    ) -> dict[str, Any]:
        """Center the largest exact aspect-ratio crop. CLI: thea ratiocrop PATH RATIOX RATIOY."""
        return run("ratiocrop", **locals())

    @server.tool()
    def pan(
        path: str,
        resolutionx: int | None = None,
        resolutiony: int | None = None,
        startx: int | None = None,
        starty: int | None = None,
        endx: int | None = None,
        endy: int | None = None,
        duration: float | None = None,
        ratiox: float | None = None,
        ratioy: float | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Pan a crop, default 9:16, full duration, left-to-right. CLI: thea pan PATH."""
        return run("pan", **locals())

    @server.tool()
    def caption(
        path: str,
        model: str,
        base_url: str = "http://localhost:1234/v1",
        api_key_env: str = "THEA_CAPTION_API_KEY",
        timeout_sec: int = 120,
        contact_sheet: str | None = None,
        sampling_video: str | None = None,
        sample_count: int = 12,
        frame_width: int = 176,
        frame_height: int = 144,
        columns: int = 4,
        location_in_metadata: bool = False,
        timestamp_in_metadata: bool = False,
        context: str | None = None,
    ) -> dict[str, Any]:
        """Caption a file/directory, using indexed locale, into videos.description. CLI: thea caption PATH --model MODEL."""
        return run("caption", **locals())

    @server.tool()
    def index(
        root: str = "D:\\",
        limit: int | None = None,
        probe: bool = False,
        geocode: bool = False,
        infer_loc: bool = False,
        report_path: str | None = None,
    ) -> dict[str, Any]:
        """Index metadata with scan counts and an optional audit. CLI: thea index ROOT [LIMIT] --report-path NEW.json."""
        return run("index", **locals())

    @server.tool()
    def importindex(paths: list[str]) -> dict[str, Any]:
        """Merge read-only old catalogues into the configured index. CLI: thea importindex DB [DB ...]."""
        return run("importindex", **locals())

    @server.tool()
    def search(query: str, limit: int = 20) -> dict[str, Any]:
        """Find ranked video paths using descriptions and locale/device/path metadata. CLI: thea search QUERY."""
        return run("search", **locals())

    return server


def main():
    """Serve MCP over stdio; diagnostics must never enter protocol stdout."""
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()

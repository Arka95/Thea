"""Shared FFmpeg executable discovery."""


def get_ffmpeg_exe() -> str:
    """Resolve the project's bundled FFmpeg executable."""
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise RuntimeError(
            "FFmpeg is required for video processing. Install imageio-ffmpeg."
        ) from error
    return imageio_ffmpeg.get_ffmpeg_exe()

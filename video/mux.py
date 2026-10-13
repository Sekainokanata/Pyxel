from __future__ import annotations

import subprocess
from pathlib import Path

from config import SETTINGS


def mux(frames_dir: str | Path, audio_path: str | Path, output_path: str | Path, fps: int) -> None:
    """フレーム連番PNG(frame_%06d.png)とwavをffmpegで1本のmp4に合成する。"""
    frames_dir = Path(frames_dir)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        SETTINGS.ffmpeg_path,
        "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RuntimeError(f"ffmpeg failed (exit={result.returncode}):\n{stderr}")

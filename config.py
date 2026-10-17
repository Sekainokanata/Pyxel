from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent

# ターミナル側に同名の環境変数が残っていても(VSCodeが起動時に.envを注入する等)、
# 常に.envの現在の内容を優先する。
load_dotenv(_PROJECT_ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    bpm: float
    time_signature: tuple[int, int]
    fps: int
    sample_rate: int
    bit_depth: int
    master_gain: float
    ffmpeg_path: str
    output_dir: str


def _load() -> Settings:
    num, den = os.environ.get("TIME_SIGNATURE", "4/4").split("/")
    return Settings(
        bpm=float(os.environ.get("BPM", 120.0)),
        time_signature=(int(num), int(den)),
        fps=int(os.environ.get("FPS", 30)),
        sample_rate=int(os.environ.get("SAMPLE_RATE", 44100)),
        bit_depth=int(os.environ.get("BIT_DEPTH", 16)),
        master_gain=float(os.environ.get("MASTER_GAIN", 0.8)),
        # subprocess経由でffmpegを起動する際、相対パスだとWindowsのCreateProcessが
        # 見つけられないことがあったため、プロジェクトルート基準の絶対パスにする。
        ffmpeg_path=str(_PROJECT_ROOT / os.environ.get("FFMPEG_PATH", "bin/ffmpeg.exe")),
        output_dir=os.environ.get("OUTPUT_DIR", "output"),
    )


SETTINGS = _load()

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pyxel


def render_frames(
    draw_frame: Callable[[float, int], None],
    duration_sec: float,
    fps: int,
    width: int,
    height: int,
    out_dir: str | Path,
) -> Path:
    """headlessモードでPyxelを起動し、フレームを1枚ずつ描画・PNGとして書き出す。

    `pyxel.run()`のリアルタイムループは使わず、フレーム番号を明示的に
    1つずつ進める(design/mv_plan.md §5.4)。draw_frame(t_seconds, frame_index)
    は呼び出し側が用意する描画関数で、その時刻に応じたPyxelの描画コマンド
    (cls/rect/text等)を発行する。
    """
    # pyxel.screenshot()は、呼び出し元のコンテキストによっては相対パスを
    # CWD以外の場所(呼び出し元モジュールのディレクトリ等)から解決してしまう
    # ことがある(Pyxel 2.9.9で確認)。絶対パスに変換して回避する。
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pyxel.init(width, height, fps=fps, headless=True)

    n_frames = max(1, int(round(duration_sec * fps)))
    for i in range(n_frames):
        t = i / fps
        draw_frame(t, i)
        pyxel.flip()
        pyxel.screenshot(str(out_dir / f"frame_{i:06d}.png"), scale=1)

    return out_dir

from __future__ import annotations

import numpy as np
import sounddevice as sd


def play(samples: np.ndarray, sample_rate: int, blocking: bool = False) -> None:
    """事前にレンダリング済みのwavバッファをそのまま再生する(プレビュー用)。

    ここでの再生タイミングはリアルタイムのオーディオデバイス依存だが、
    最終的な書き出し(video.mux)には一切影響しない(design/mv_plan.md §2参照)。

    blocksize/latencyを大きめに指定しているのは、pyxel.run()のフレームループが
    メインスレッドを占有している間にsounddeviceの再生スレッドがGILを取得できず、
    バッファが枯渇して「ブツブツ」というノイズが乗る問題への対処(お試し・低コスト
    案)。wav書き出し(audio/render.write_wav)は別経路でこの制約を受けない。
    """
    sd.play(samples, sample_rate, blocksize=4096, latency="high")
    if blocking:
        sd.wait()


def stop() -> None:
    sd.stop()

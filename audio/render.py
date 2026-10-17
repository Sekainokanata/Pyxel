from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import soundfile as sf

from score.notes import beats_to_seconds, duration_to_beats
from score.sequencer import Event, build_sequence_events

from . import instruments


def _event_end_beats(event: Event) -> float:
    start = float(event.start_beats or 0.0)
    return start + duration_to_beats(event.duration)


def render_track(
    events: Sequence[Event],
    bpm: float,
    sample_rate: int,
    renderer: Callable[[Event], np.ndarray],
    tail_seconds: float = 1.0,
) -> np.ndarray:
    """イベント列を1パートぶんのnp.ndarrayにレンダリングする。

    各イベントの開始サンプル位置はBPM×拍数から直接計算し、丸めはサンプル単位で
    1回だけ行う(design/mv_plan.md §5.3)。全イベントが共有する固定グリッドは
    存在しないため、テンポのズレが蓄積する余地が原理的にない。
    """
    if not events:
        return np.zeros(0, dtype=np.float32)

    total_beats = max(_event_end_beats(event) for event in events)
    total_seconds = beats_to_seconds(total_beats, bpm) + tail_seconds
    mix = np.zeros(max(1, int(round(total_seconds * sample_rate))), dtype=np.float32)

    for event in events:
        start_seconds = beats_to_seconds(float(event.start_beats or 0.0), bpm)
        start_index = int(round(start_seconds * sample_rate))
        rendered = renderer(event)
        end_index = min(len(mix), start_index + len(rendered))
        if end_index <= start_index:
            continue
        mix[start_index:end_index] += rendered[: end_index - start_index]

    return mix


def mix_tracks(tracks: Sequence[np.ndarray]) -> np.ndarray:
    if not tracks:
        return np.zeros(0, dtype=np.float32)
    max_length = max(len(track) for track in tracks)
    mix = np.zeros(max_length, dtype=np.float32)
    for track in tracks:
        mix[: len(track)] += track
    return mix


def limit_peak(samples: np.ndarray, peak: float = 0.95) -> np.ndarray:
    """ピークがpeakを超えるときだけ全体を縮めて音割れを防ぐ。peak以下の音は
    そのまま返すので、velocity/gain/master_gainで下げた音量が打ち消されない。"""
    if samples.size == 0:
        return samples
    max_abs = float(np.max(np.abs(samples)))
    if max_abs <= peak:
        return samples
    return samples * (peak / max_abs)


def write_wav(path: str | Path, samples: np.ndarray, sample_rate: int, subtype: str = "PCM_16") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples.astype(np.float32), sample_rate, subtype=subtype)


def render_song(
    track_configs: Sequence, bpm: float, sample_rate: int, master_gain: float = 1.0
) -> np.ndarray:
    """score/tracks/registry.py の TRACKS を受け取り、有効なパートをすべて
    レンダリング・ミックスして1本のnp.ndarrayを返す。

    最終的な音量は velocity × TrackConfig.gain × master_gain で決まる。
    """
    rendered_tracks: list[np.ndarray] = []
    for track in track_configs:
        if not track.enabled:
            continue
        events = build_sequence_events(track.events)

        def renderer(event: Event, _instrument: str = track.instrument) -> np.ndarray:
            return instruments.render_event(event, bpm, sample_rate, _instrument)

        track_wave = render_track(events, bpm, sample_rate, renderer)
        rendered_tracks.append(track_wave * track.gain)

    return limit_peak(mix_tracks(rendered_tracks) * master_gain)

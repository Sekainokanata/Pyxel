from __future__ import annotations

import numpy as np

from score.notes import beats_to_seconds, duration_to_beats, is_percussive, is_rest, note_to_frequency
from score.sequencer import Event

from . import oscillators

# 音色プリセット名 -> 矩形波のduty比。square以外(triangle/noise)はoscillators側の
# 波形をそのまま使うのでここには載らない。
DUTY_BY_INSTRUMENT = {
    "square": 0.5,
    "square25": 0.25,
    "square12": 0.125,
}

# 利用可能なinstrument名の一覧(README.mdの表・サンプル生成スクリプトの
# 唯一の参照元)。新しいinstrumentを追加したら、DUTY_BY_INSTRUMENTまたは
# render_note()の分岐に実装を足した上で、ここにも名前を追加すること。
INSTRUMENTS: tuple[str, ...] = (*DUTY_BY_INSTRUMENT.keys(), "triangle", "noise")


def _envelope(n: int, sample_rate: int, attack_ms: float = 2.0, release_ms: float = 2.0) -> np.ndarray:
    """
    デジタルクリック防止だけを目的とした最小限のフェード。
    ノイズを消すためだけの最小値(2ms/2ms)に短縮する。
    """
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    attack_n = min(n, max(1, int(sample_rate * attack_ms / 1000)))
    release_n = min(n - attack_n, max(1, int(sample_rate * release_ms / 1000)))
    env = np.ones(n, dtype=np.float32)
    env[:attack_n] *= np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if release_n > 0:
        env[-release_n:] *= np.linspace(1.0, 0.0, release_n, dtype=np.float32)
    return env


def render_note(
    freq: float,
    duration_sec: float,
    sample_rate: int,
    instrument: str,
    velocity: float = 1.0,
) -> np.ndarray:
    if instrument == "triangle":
        wave = oscillators.triangle_wave(freq, duration_sec, sample_rate)
    elif instrument == "noise":
        wave = oscillators.noise_wave(freq, duration_sec, sample_rate)
    else:
        duty = DUTY_BY_INSTRUMENT.get(instrument, 0.5)
        wave = oscillators.square_wave(freq, duration_sec, sample_rate, duty=duty)

    env = _envelope(len(wave), sample_rate)
    return (wave * env * velocity).astype(np.float32)


def render_percussive_hit(
    duration_sec: float,
    sample_rate: int,
    velocity: float = 1.0,
    decay_rate: float = 60.0,
    noise_freq: float = 4000.0,
) -> np.ndarray:
    """ピッチを持たない打楽器的な一打(Alto recorder Programのguitarパートの
    "X"=ミュートストロークに相当)。ノイズ波形に速い指数減衰をかけるだけで、
    トラックのinstrument設定(square/triangle等)には依存しない。
    """
    n = max(0, int(round(duration_sec * sample_rate)))
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    wave = oscillators.noise_wave(noise_freq, duration_sec, sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate
    decay_env = np.exp(-t * decay_rate).astype(np.float32)
    return (wave * decay_env * velocity).astype(np.float32)


def render_event(event: Event, bpm: float, sample_rate: int, instrument: str) -> np.ndarray:
    """1つのEventを1音分(和音ならまとめて)のnp.ndarrayにレンダリングする。"""
    duration_sec = beats_to_seconds(duration_to_beats(event.duration), bpm)
    n_silence = max(0, int(round(duration_sec * sample_rate)))

    if is_rest(event.value):
        return np.zeros(n_silence, dtype=np.float32)

    if is_percussive(event.value):
        return render_percussive_hit(duration_sec, sample_rate, event.velocity)

    values = event.value if isinstance(event.value, list) else [event.value]
    tone = event.tone or instrument

    waves = [
        render_note(note_to_frequency(v), duration_sec, sample_rate, tone, event.velocity)
        for v in values
    ]
    if not waves:
        return np.zeros(n_silence, dtype=np.float32)

    length = max(len(w) for w in waves)
    mix = np.zeros(length, dtype=np.float32)
    for w in waves:
        mix[: len(w)] += w
    return mix / len(waves)

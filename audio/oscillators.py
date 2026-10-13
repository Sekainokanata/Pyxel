from __future__ import annotations

import numpy as np

# NESのAPU(音源チップ)を参考にした基本波形。
# いずれも「周波数・長さ・サンプルレート」だけを受け取り、np.ndarray(float32)を
# 返す純粋関数。BPMや拍などの音楽的な文脈は一切知らない
# (design/mv_plan.md §5.1参照)。


def _n_samples(duration_sec: float, sample_rate: int) -> int:
    return max(0, int(round(duration_sec * sample_rate)))


def square_wave(
    freq: float,
    duration_sec: float,
    sample_rate: int,
    duty: float = 0.5,
    amplitude: float = 1.0,
) -> np.ndarray:
    """矩形波。dutyは1周期のうち+amplitude側になる割合(NESは12.5%/25%/50%が基本)。"""
    n = _n_samples(duration_sec, sample_rate)
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float64) / sample_rate
    phase = np.mod(t * freq, 1.0)
    wave = np.where(phase < duty, amplitude, -amplitude)
    return wave.astype(np.float32)


def triangle_wave(
    freq: float,
    duration_sec: float,
    sample_rate: int,
    amplitude: float = 1.0,
    quantize_levels: int = 16,
) -> np.ndarray:
    """三角波。NESの三角波チャンネルに合わせ、既定でquantize_levels(16)段階に
    量子化した階段状の波形にする(quantize_levels<=0で量子化なしの滑らかな三角波)。
    """
    n = _n_samples(duration_sec, sample_rate)
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float64) / sample_rate
    phase = np.mod(t * freq, 1.0)
    saw = 2.0 * phase - 1.0
    tri = 2.0 * np.abs(saw) - 1.0  # -1..1の三角波

    if quantize_levels and quantize_levels > 1:
        steps = quantize_levels - 1
        tri = np.round((tri + 1.0) * 0.5 * steps) / steps * 2.0 - 1.0

    return (tri * amplitude).astype(np.float32)


def _lfsr_bits(n_steps: int, seed: int = 1) -> np.ndarray:
    """NESのノイズチャンネルを簡略化した15bit LFSR。1ステップごとに+1/-1を返す。"""
    state = seed & 0x7FFF or 1
    bits = np.empty(n_steps, dtype=np.float32)
    for i in range(n_steps):
        bit0 = state & 1
        bit1 = (state >> 1) & 1
        feedback = bit0 ^ bit1
        state = (state >> 1) | (feedback << 14)
        bits[i] = 1.0 if bit0 else -1.0
    return bits


def noise_wave(
    freq: float,
    duration_sec: float,
    sample_rate: int,
    amplitude: float = 1.0,
    seed: int = 1,
) -> np.ndarray:
    """疑似ノイズ。freqはLFSRを更新する頻度(高いほど高域寄りのジリジリした音、
    低いほどザーッとした低いノイズになる)。1ステップぶんをsample_rate/freq
    サンプルぶんホールドすることでビットクラッシュ感のある質感にする。
    """
    n = _n_samples(duration_sec, sample_rate)
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    step_samples = max(1, int(round(sample_rate / freq)))
    n_steps = n // step_samples + 2
    bits = _lfsr_bits(n_steps, seed=seed)
    held = np.repeat(bits, step_samples)[:n]
    return (held * amplitude).astype(np.float32)

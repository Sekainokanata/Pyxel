from __future__ import annotations

import argparse
from pathlib import Path

import pyxel

from audio.instruments import INSTRUMENTS, render_note
from audio.preview import play as play_audio
from audio.render import render_song, write_wav
from config import SETTINGS
from score.notes import note_to_frequency
from score.tracks.registry import TRACKS
from video.capture import render_frames
from video.mux import mux

WIDTH, HEIGHT = 160, 120

INSTRUMENT_SAMPLE_DIR = "output_sample"
INSTRUMENT_SAMPLE_NOTE = "A4"
INSTRUMENT_SAMPLE_DURATION_SEC = 1.2


def draw_at(t: float) -> None:
    """時刻t(秒)に応じた1フレーム分の描画。ライブプレビューと書き出しの両方から
    同じ関数を呼ぶことで、見た目が食い違わないようにする。"""
    pyxel.cls(0)
    pyxel.text(10, 10, "Hello, Pyxel!", 7)


class App:
    def __init__(self):
        pyxel.init(WIDTH, HEIGHT, title="My Pyxel App", fps=SETTINGS.fps)
        wave = render_song(TRACKS, SETTINGS.bpm, SETTINGS.sample_rate)
        play_audio(wave, SETTINGS.sample_rate)
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

    def draw(self):
        t = pyxel.frame_count / SETTINGS.fps
        draw_at(t)


def export_instrument_samples() -> None:
    """各instrumentのA4の音を1秒以上鳴らしたサンプルwavを`output_sample/`に
    書き出す。instrumentを追加したらaudio/instruments.pyのINSTRUMENTSに
    名前を足すだけで、このコマンドが自動的に追随する。"""
    freq = note_to_frequency(INSTRUMENT_SAMPLE_NOTE)
    out_dir = Path(INSTRUMENT_SAMPLE_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    for instrument in INSTRUMENTS:
        wave = render_note(freq, INSTRUMENT_SAMPLE_DURATION_SEC, SETTINGS.sample_rate, instrument)
        path = out_dir / f"{instrument}.wav"
        write_wav(str(path), wave, SETTINGS.sample_rate)
        print(f"wrote {path}")


def export_audio_only(output_path: str) -> None:
    """映像を一切介さず、音声のwavだけを書き出す(試聴用の高速確認向け)。"""
    wave = render_song(TRACKS, SETTINGS.bpm, SETTINGS.sample_rate)
    write_wav(output_path, wave, SETTINGS.sample_rate)
    print(f"exported (audio only): {output_path}")


def export(output_path: str) -> None:
    """音声(numpyオフラインレンダリング)と映像(Pyxel headlessキャプチャ)を
    別々に生成し、最後にffmpegで1本のmp4に合成する(design/mv_plan.md §2)。

    pyxel.init()はheadlessモードで呼ぶと、呼び出し元モジュール(video/capture.py)の
    ディレクトリに現在の作業ディレクトリを変えてしまう(Pyxel 2.9.9で確認した
    未文書化の挙動)。そのため、render_frames()を呼ぶ前に必要なパスをすべて
    絶対パスへ変換しておく。
    """
    wave = render_song(TRACKS, SETTINGS.bpm, SETTINGS.sample_rate)
    wav_path = str(Path(f"{SETTINGS.output_dir}/song.wav").resolve())
    write_wav(wav_path, wave, SETTINGS.sample_rate)

    duration_sec = len(wave) / SETTINGS.sample_rate
    frames_dir = str(Path(f"{SETTINGS.output_dir}/frames").resolve())
    output_path = str(Path(output_path).resolve())
    render_frames(
        lambda t, i: draw_at(t),
        duration_sec=duration_sec,
        fps=SETTINGS.fps,
        width=WIDTH,
        height=HEIGHT,
        out_dir=frames_dir,
    )

    mux(frames_dir, wav_path, output_path, fps=SETTINGS.fps)
    print(f"exported: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", metavar="OUTPUT_MP4", help="オフラインでmp4を書き出して終了する")
    parser.add_argument("--audio-only", metavar="OUTPUT_WAV", help="映像を作らず、音声のwavだけを書き出して終了する")
    parser.add_argument(
        "--instrument-samples",
        action="store_true",
        help=f"各instrumentのA4サンプルwavを{INSTRUMENT_SAMPLE_DIR}/に書き出して終了する",
    )
    args = parser.parse_args()

    if args.export:
        export(args.export)
    elif args.audio_only:
        export_audio_only(args.audio_only)
    elif args.instrument_samples:
        export_instrument_samples()
    else:
        App()

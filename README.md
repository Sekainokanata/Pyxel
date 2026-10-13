# Pyxel MV制作プログラム

ファミコン風の音とグラフィックでMV(ミュージックビデオ)を作る個人用ツール。
設計方針の詳細は [design/mv_plan.md](design/mv_plan.md) を参照。

音声はPyxelの`Sound`を使わず、numpyによる自前のDSPレンダリング
(`audio/`)で生成する。映像はPyxelの描画機能(`video/capture.py`が
headlessモードでフレームごとにキャプチャ)を使う。最終的な動画は
両者をffmpegで合成して書き出す。

## セットアップ

```powershell
.\.pyxel\Scripts\pip.exe install numpy soundfile python-dotenv sounddevice
```

`bin/ffmpeg.exe`が同梱されているので、ffmpeg自体の別途インストールは不要。

BPM・拍子・FPS・サンプルレート等の曲全体の設定は`.env`に書く
(既定値は`.env`にコメント無しで直書きされている。詳細は
[design/mv_plan.md §5.6](design/mv_plan.md)参照)。

## 実行時のコマンド一覧

プロジェクトルートで実行する(`.pyxel`は同梱の仮想環境)。

| コマンド | 内容 |
|---|---|
| `.\.pyxel\Scripts\python.exe main.py` | ライブプレビュー。Pyxelウィンドウを開きつつ`sounddevice`でリアルタイム再生する。終了は既定のquit_key(Escキー)。 |
| `.\.pyxel\Scripts\python.exe main.py --audio-only output\song.wav` | 映像を作らず、音声のwavだけを高速に書き出す。音の確認・試聴用。 |
| `.\.pyxel\Scripts\python.exe main.py --export output\mv.mp4` | 音声・映像を両方生成し、ffmpegで1本のmp4に合成して書き出す(曲の長さぶんフレームキャプチャの時間がかかる)。 |
| `.\.pyxel\Scripts\python.exe main.py --instrument-samples` | 各instrumentのA4の音を1.2秒鳴らしたサンプルwavを`output_sample/`に書き出す。instrumentを追加したら`audio/instruments.py`の`INSTRUMENTS`に名前を足すだけで、このコマンドを実行し直せば自動的にサンプルも増える。 |

仮想環境を有効化してから`python main.py`のように短く実行したい場合は、
先に`.\.pyxel\Scripts\Activate.ps1`を実行しておけばよい。

## トラックに追加できるinstrument一覧

`score/tracks/registry.py`の`TrackConfig(instrument=...)`、または
楽譜データの各音符の`"tone"`キーで指定できる音色名(`audio/instruments.py`
のプリセット)。

| instrument名 | 波形 | 特徴 |
|---|---|---|
| `square` | 矩形波(duty比50%) | 標準的なファミコンのメロディ向けリード音。既定はこれ。 |
| `square25` | 矩形波(duty比25%) | `square`よりやや鼻にかかった、細めの音。 |
| `square12` | 矩形波(duty比12.5%) | さらに細く、キラキラした高めの倍音が強い音。 |
| `triangle` | 三角波(16段階量子化) | 丸く柔らかい音。ファミコンではベースやコード伴奏によく使われる。 |
| `noise` | 疑似ノイズ(簡易LFSR) | ドラムや効果音向けのザラついたノイズ。 |

上記以外の文字列を指定した場合は`square`(duty比50%)として扱われる
(`audio/instruments.py`の`DUTY_BY_INSTRUMENT`参照)。

## パートの追加方法

1. `score/tracks/<名前>.py`に楽譜リスト(1音=1辞書)を書く。
2. `score/tracks/registry.py`の`TRACKS`に`TrackConfig(name=..., events=..., instrument=..., gain=...)`を1行足す(importも1行足す)。

詳細は[design/mv_plan.md §5.7](design/mv_plan.md)参照。

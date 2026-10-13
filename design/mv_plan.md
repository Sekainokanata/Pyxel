# ファミコン風MV制作プログラム 方針転換 計画書

> 前身の `design/score_dsl_design.md`(Pyxelの`Sound`配列を直接組み立てる設計)は
> 削除された。本ドキュメントはその後継として、**音声をPyxelから完全に切り離し
> 独自DSP実装にする**という方針転換を扱う新規の計画書。

## 1. 背景・目的

これまでの調査・実装(§9まで進めた旧設計)を通じて、Pyxelの`Sound`/`Channel`/
`Music`/`Tone`という音源は「固定長スロットを敷き詰めるトラッカー方式」であり、
以下のような**トラッカー方式に起因する制約**が次々と表面化した。

- `Sound.notes`は0-127の整数(実質0-71程度に運用制限)でしか音高を表現できず、
  `OCTAVE_SHIFT`のような補正が必要だった。
- `Sound.speed`が1/120秒単位の**正の整数**でしか指定できないため、
  実際に出せるBPMは`7200/n`(nは整数)という離散値に限られ、BPM=190のような
  値では原理的にテンポのズレが避けられなかった(`TICKS_PER_BEAT`を
  `round(7200/BPM)`で自動算出する対症療法までは実装したが、ズレそのものは
  ゼロにできない)。
- パート数(チャンネル数)にも`MAX_CHANNELS`のような運用上の上限が必要だった。

一方、参照専用の`Alto recorder Program`はPyxelを介さずnumpyで直接
音声波形を合成しており、`start_seconds = beats_to_seconds(start_beats, bpm)`
→`round(start_seconds * sample_rate)`という**サンプル単位(1/44100秒や
1/48000秒)の丸めが1回入るだけ**の方式のため、ズレが実質発生しない
(詳細は本セッションでの調査・会話を参照)。

改めて確認された最終目標は次の通り:

> **ファミコン風の音とグラフィックで作るMV(ミュージックビデオ)制作プログラム**。
> 他人に配布・操作させることは想定しておらず、**自分がコードを直接書き換えながら
> 使う個人用ツール**として運用する。

この目標に対し、Pyxelのトラッカー方式音源はテンポ精度の観点で相性が悪いと
判断し、**音声だけをPyxelから切り離し、独自DSP実装にする**方針へ転換する。
映像(ドット絵の描画)は引き続きPyxelの強みを活かす。

## 2. 全体方針

| 領域 | 方針 |
|---|---|
| **音声** | Pyxelの`Sound`/`Channel`/`Music`/`Tone`/`play`/`playm`を**一切使わない**。`Alto recorder Program`と同じ「BPM→秒→サンプル位置」を直接計算するオフラインレンダリング方式を独自実装し、原理的にズレが蓄積しない設計にする。 |
| **映像** | 引き続きPyxelを使う。`update()`/`draw()`、パレット、画像・スプライト・タイルマップ等の描画機能はそのまま活用する。 |
| **統合(MV書き出し)** | 音声(wav)と映像(フレーム画像列)を**別々に、非リアルタイムで**生成し、最後にffmpeg等で1本の動画ファイルに合成する。これによりお互いの生成過程が干渉せず、両方とも「後からズレようがない」形で組み上がる。 |
| **プレビュー** | 作業中はPyxelウィンドウでリアルタイム再生(事前に書き出したwavを`sounddevice`等でそのまま再生)して確認できるようにする。プレビュー時の多少のズレは最終成果物に影響しない(最終書き出しは必ず上記の非リアルタイム合成パイプラインを通すため)。 |

## 3. 何が不要になるか(Pyxel音源を切り離すことによる簡素化)

音声をPyxelの`Sound`に頼らなくなることで、直近まで積み上げていた
「トラッカー方式の制約に対処するための仕組み」がまるごと不要になる。
後片付け(削除)の対象として明記しておく。

- `score/pyxel_render.py`全体(`build_sound`/`allocate_channels`/`allocate_tones`/
  `event_to_slots`など、Pyxelの`Sound`配列を組み立てる処理一式)
- `MAX_CHANNELS` / `ChannelLimitExceededError`(numpy配列の加算に上限はなく、
  必要なのは音量バランス調整だけになる)
- `MIN_NOTE_INDEX` / `MAX_NOTE_INDEX` / `NoteRangeExceededError` /
  `NoteIndexOutOfPyxelRangeError`(`Sound.notes`の0-127制約が前提の仕組みなので、
  実周波数(Hz)で直接合成する新方式では意味を失う)
- `OCTAVE_SHIFT`(Pyxel側の`base_note=36`ずれを補正するためのものだったので、
  自前で正しいオクターブ計算をすれば不要)
- `TICKS_PER_BEAT`の自動算出ロジック(`Sound.speed`の整数制約に対処するための
  ものなので、BPMを直接秒に変換する新方式では概念自体が消える)

`score/notes.py`の音名パース・拍変換ロジックや`score/tracks/*.py`の
「1音=1辞書のリスト」という楽譜の書き味自体は資産として引き続き使う
(壊れていないので流用する)。

## 4. 新モジュール構成案

```
Pyxel/
├── .env                       # BPM/FPS/サンプルレート等、曲全体の設定値(後述§5.6)
├── config.py                  # .envを読み込み、型付きのSETTINGSとして提供する薄いローダー
├── bin/
│   └── ffmpeg.exe             # デスクトップのbinからコピーして同梱(§7)
├── main.py                    # 実行エントリ。--preview / --export 等でモード分岐
├── score/
│   ├── notes.py               # 音名パース・拍変換(Pyxel依存部分を撤去し、
│   │                           # Alto方式のnote_to_frequency(Hz)ベースに戻す)
│   ├── sequencer.py           # Event, build_sequence_events(既存とほぼ同じ、
│   │                           # 元々Pyxel非依存なのでそのまま使える)
│   └── tracks/
│       ├── registry.py        # TRACKS = [TrackConfig(...), ...] (後述§5.7、
│       │                       # 「トラックを追加する」ときに触る場所はここ1箇所)
│       ├── melody.py          # 既存の楽譜データをそのまま使う
│       └── ...                # bass.py等、パートを増やすたびにファイルを追加
├── audio/
│   ├── oscillators.py         # square/triangle/noiseなど、ファミコン風の基本波形
│   │                           # (numpyベース)
│   ├── instruments.py         # Eventの tone/effect/velocity から oscillators を
│   │                           # 呼び出し、1音分のnp.ndarrayを作る(音色プリセット)
│   ├── render.py              # render_track / mix_tracks / write_wav
│   │                           # (Alto recorder Programのsequencer.py相当を移植・簡略化)
│   └── preview.py             # sounddevice等によるリアルタイム再生ヘルパ
├── video/
│   ├── capture.py             # Pyxelの描画をフレーム単位で画像として書き出す
│   │                           # (pyxel.run()を使わず、フレーム番号を明示的に回す)
│   └── mux.py                  # ffmpegを呼び出し、フレーム画像列+wavをmp4に合成
└── design/
    └── mv_plan.md              # 本ドキュメント
```

## 5. 各層の役割詳細

### 5.1 `audio/oscillators.py` — ファミコン風の基本波形

NESのAPU(音源チップ)の特徴を参考に、以下をnumpyで実装する。

| 波形 | NESでの特徴 | 実装方針 |
|---|---|---|
| Square(矩形波) | duty比 12.5% / 25% / 50% の3種 | 位相の小数部としきい値の比較で生成 |
| Triangle(三角波) | 16段階に量子化された階段状の三角波。ベースによく使われる | 三角波を生成後、16段階に量子化(`np.round`で丸める)することで質感を再現 |
| Noise(ノイズ) | 疑似乱数(LFSR)を一定間隔でホールドする、ビットクラッシュ感のあるノイズ | 単純な疑似乱数を一定サンプル数ごとにホールドして再現(簡易LFSR) |

いずれも「周波数・長さ・サンプルレート」を受け取り`np.ndarray`(float32)を
返す純粋関数として実装し、音楽的な文脈(BPM等)を一切知らないようにする。

### 5.2 `audio/instruments.py` — 音色とエンベロープ

`oscillators.py`の波形に対して、音量エンベロープ(Attack/Decay/Sustain/Release
または単純なフェード)や、Pyxelの`effects`にあった`Slide`/`Vibrato`/`FadeOut`
相当の効果を自前で実装する。`Event.tone`/`Event.effect`/`Event.velocity`を
受け取り、1音分の波形(`np.ndarray`)を返す。

### 5.3 `audio/render.py` — サンプル精度のオフラインレンダリング

`Alto recorder Program`の`sequencer.py`をほぼそのまま移植する。要点は
**「イベントごとに独立して開始サンプル位置を計算し、大きな無音バッファに
加算していく」**という一点に尽きる。

```python
def render_track(events, bpm, sample_rate, renderer) -> np.ndarray:
    total_seconds = beats_to_seconds(total_beats(events), bpm)
    mix = np.zeros(int(round(total_seconds * sample_rate)), dtype=np.float32)
    for event in events:
        start_seconds = beats_to_seconds(event.start_beats, bpm)
        start_index = int(round(start_seconds * sample_rate))  # 丸めはここ1回だけ
        rendered = renderer(event)  # instruments.pyが1音分の波形を返す
        mix[start_index:start_index + len(rendered)] += rendered
    return mix
```

丸めが「サンプル単位で1回だけ」であることが、ズレが蓄積しない理由そのもの。
複数パートは`mix_tracks()`(単純な加算)で合成する。`MAX_CHANNELS`のような
上限はここには存在せず、音量バランス(クリッピング防止の`normalize_audio`)
だけ気をつければよい。

### 5.4 `video/capture.py` — フレーム単位のオフライン描画

`pyxel.run()`によるリアルタイムループとは別に、**フレーム番号を明示的に
1つずつ進めながら`draw()`相当の処理を呼び、その都度画面を画像として
保存する**オフラインループを用意する。1フレームぶんの時刻は
`frame_index / fps`(秒)として、音楽側のイベントと同じ時間軸で扱えるように
しておく。

### 5.5 `video/mux.py` — 最終合成

`video/capture.py`が書き出したフレーム画像列(連番PNG)と、
`audio/render.py`が書き出したwavファイルを、外部コマンドの`ffmpeg`で
1本のmp4に合成する(`subprocess`経由で呼び出す)。呼び出す`ffmpeg`の実体は
`bin/ffmpeg.exe`(§7)を指す。

### 5.6 `.env` + `config.py` — 曲全体の設定を1箇所にまとめる

これまで`score/tracks/__init__.py`にBPMやFPS関連の定数を直書きしていたが、
Pythonのコードに埋もれて見つけにくい、という指摘を踏まえ、**「曲全体で1つに
決まる、スカラーな設定値」は`.env`に切り出す**。

```dotenv
# .env
BPM=190.0
TIME_SIGNATURE=4/4
FPS=30
SAMPLE_RATE=44100
BIT_DEPTH=16
MASTER_GAIN=0.8
FFMPEG_PATH=bin/ffmpeg.exe
OUTPUT_DIR=output
```

`.env`はテキストファイルなので、Pythonの構文やimport文に邪魔されずに
「今何を設定しているか」がひと目でわかる。読み込みは`config.py`が
`python-dotenv`で行い、型付きの`SETTINGS`として提供する(文字列のまま
あちこちに`os.environ[...]`が散らばるのを防ぐ)。

```python
# config.py (骨子)
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

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
        ffmpeg_path=os.environ.get("FFMPEG_PATH", "bin/ffmpeg.exe"),
        output_dir=os.environ.get("OUTPUT_DIR", "output"),
    )

SETTINGS = _load()
```

`main.py`の`pyxel.init(..., fps=SETTINGS.fps)`と、`video/mux.py`が
ffmpegに渡す`-framerate`の両方が**この同じ`SETTINGS.fps`を参照する**ことで、
「プレビューのfpsと書き出し動画のfpsがズレる」という事態がそもそも
起こり得ない構造にする(ユーザー要望である「書き出し動画はmain.pyの
FPS設定に合わせる」を、force-syncではなく単一の情報源にすることで満たす)。

一方、**曲の中身そのもの(音符データ)は`.env`に入れない**。理由は単純で、
`.env`はキー=値のフラットな文字列しか表現できず、`MELODY`のような
「1音=1辞書」の構造化されたリストを書くのに向いていないため。楽譜データは
これまで通りPythonファイル(`score/tracks/*.py`)に置く。

### 5.7 トラックレジストリ(`score/tracks/registry.py`) — パート追加を1箇所に集約

これまでは「パートを増やす」ために、(1)`score/tracks/__init__.py`に
`ENABLE_BASS`フラグを足す、(2)`main.py`に`if ENABLE_BASS:`の分岐を書く、
(3)`main.py`で使う音色(`default_tone`)を個別に指定する、という**3箇所**を
触る必要があり、わかりにくかった。これを次のように1箇所へ集約する。

```python
# score/tracks/registry.py
from dataclasses import dataclass

from .melody import MELODY
# from .bass import BASS  # パートを増やしたら、ここに1行importを足す


@dataclass(frozen=True)
class TrackConfig:
    name: str             # ログ・デバッグ表示用の名前
    events: list[dict]    # score/tracks/<name>.py で定義した楽譜リスト
    instrument: str       # "square" / "triangle" / "noise" (audio/instruments.pyのプリセット名)
    gain: float = 0.8     # このトラック単体の音量(0.0-1.0)
    enabled: bool = True  # Falseにすると書き出し・プレビュー両方でこのパートを鳴らさない


TRACKS: list[TrackConfig] = [
    TrackConfig(name="melody", events=MELODY, instrument="square", gain=0.8),
    # TrackConfig(name="bass", events=BASS, instrument="triangle", gain=0.6),
]
```

これにより、**パートを1つ追加する手順は次の2ステップだけ**になる。

1. `score/tracks/<name>.py`に楽譜リストを書く(今まで通り)。
2. `score/tracks/registry.py`の`TRACKS`に`TrackConfig(...)`を1行足す
   (importも1行足す)。どんな音色(instrument)で、どのくらいの音量(gain)で
   鳴らすかもこの1行に書かれているので、後から見ても「このパートが何の
   音で鳴っているか」が`registry.py`を見るだけでわかる。

`audio/render.py`側は`TRACKS`をループして`enabled`なものだけ
`render_track()`→`mix_tracks()`すればよく、`ENABLE_MELODY`のような
個別フラグや`main.py`側の`if`分岐は不要になる(オンオフも
`registry.py`の`enabled=False`一箇所で完結する)。

将来、トラックごとに左右定位(pan)やビブラート等の個別エフェクトを
持たせたくなった場合も、`TrackConfig`にフィールドを追加するだけで
拡張できる。

## 6. BPM・テンポ精度について

音声側は「1/120秒刻みのtick」という制約自体が消えるため、`TICKS_PER_BEAT`と
いう概念は不要になり、**BPMを好きな値に設定してもテンポのズレは(浮動小数点と
サンプルレートの丸め誤差程度まで)実質ゼロ**になる。

映像側とのタイミング同期だけは新たに考える必要があるが、これは単純で、
「何フレーム目にどのイベントの映像を出すか」を
`frame_index = round(beats_to_seconds(event.start_beats, bpm) * fps)`
で計算すればよい(音声のサンプル位置計算と全く同じ考え方)。ここで使う`bpm`と
`fps`はどちらも`config.SETTINGS`(§5.6)から取るので、BPM・FPSの値自体は
`.env`を書き換えるだけで曲ごとに変えられる。

## 7. 前提・環境について(決定事項)

- **サンプルレート/ビット深度**: Altoに合わせて44.1kHz・書き出し時16bit PCM
  とする(内部処理はfloat32のまま、`soundfile.write`時に変換)。特に異論なし。
- **映像側のfps**: `main.py`で設定しているFPSに書き出し動画も必ず合わせる。
  実装上は「main.pyとvideo/muxが別々にfpsを持って一致させる」のではなく、
  §5.6の`config.SETTINGS.fps`という単一の情報源を両方が参照する形にすることで、
  構造的にズレが起こらないようにする。
- **ffmpeg依存**: 許可。デスクトップの`bin`フォルダにある`ffmpeg.exe`をこの
  プロジェクトの`bin/ffmpeg.exe`としてコピーして同梱する(§4の構成図の通り)。
  `.env`の`FFMPEG_PATH`でパスを指定し、`video/mux.py`はそこを`subprocess`で
  呼び出す。システムPATHへの追加やwinget等でのインストールは不要。
- **リアルタイムプレビュー用ライブラリ**: 特に希望なし。提案通り
  `sounddevice`を採用する。

実装着手前に、現在の`.pyxel`仮想環境へ以下を追加インストールする必要がある
(現状は`numpy`/`soundfile`/`sounddevice`/`python-dotenv`のいずれも未導入)。

- `pip install numpy soundfile python-dotenv` (波形合成・wav書き出し・
  `.env`読み込み用。必須)
- `pip install sounddevice` (リアルタイムプレビュー再生用)

## 8. 段階的な実装ステップ

1. `config.py`(`.env`ローダー)を実装し、`SETTINGS.bpm`等が正しく読めることを
   確認する。
2. `audio/oscillators.py`を実装し、単体でwavに書き出して試聴・波形確認する
   (square/triangle/noiseがそれぞれ意図通りの音か)。
3. `score/notes.py`からPyxel依存部分(`note_to_pyxel_index`関連)を削除し、
   Alto方式の`note_to_frequency`(Hz)ベースに戻す。
4. `score/tracks/registry.py`を作り、`MELODY`だけを登録した状態で
   `audio/instruments.py`+`audio/render.py`により通しでレンダリングし、
   wavとして書き出して確認する。
5. 複数パート対応: `bass.py`等を追加し、`registry.py`に1行足すだけで
   `mix_tracks()`に合成されることを確認する。
6. `bin/ffmpeg.exe`を配置し、`video/capture.py`+`video/mux.py`で、簡単な
   描画(静止画やテスト表示)でもよいので「音と映像が合ったmp4」が1本
   出せることを確認する。
7. `main.py`を「ライブプレビュー(`pyxel.run` + `sounddevice`再生)」と
   「書き出し(オフラインレンダリング+mux)」の2モードに整理する。
8. `score/pyxel_render.py`および関連する`MAX_CHANNELS`等の定数を削除
   (または`_archive/`へ退避)し、後片付けする。

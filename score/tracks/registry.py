from __future__ import annotations

from dataclasses import dataclass

from .instrument.melody import MELODY
from .instrument.chorus import MELODY_CHORUS
from .instrument.tuneta import MELODY_TUNETA
from .instrument.bass import BASS
from .instrument.guitar import GUITAR

# パートを増やしたら、ここに1行importを足す。
# from .bass import BASS


@dataclass(frozen=True)
class TrackConfig:
    name: str
    events: list[dict]
    instrument: str
    gain: float = 0.8
    enabled: bool = True


TRACKS: list[TrackConfig] = [
    TrackConfig(name="melody", events=MELODY, instrument="square12", gain=0.05),
    TrackConfig(name="tuneta", events=MELODY_TUNETA, instrument="square25", gain=0.05),
    TrackConfig(name="chorus", events=MELODY_CHORUS, instrument="triangle", gain=0.3),
    TrackConfig(name="bass", events=BASS, instrument="triangle", gain=0.05),
    TrackConfig(name="guitar", events=GUITAR, instrument="triangle", gain=0.05),
]
from __future__ import annotations

from dataclasses import dataclass

from .instrument.melody import MELODY
from .instrument.bass import BASS

# パートを増やしたら、ここに1行importを足す。
# from .bass import BASS


@dataclass(frozen=True)
class TrackConfig:
    name: str
    events: list[dict]
    instrument: str
    gain: float = 0.1
    enabled: bool = True


TRACKS: list[TrackConfig] = [
    TrackConfig(name="melody", events=MELODY, instrument="square12", gain=0.1),
    TrackConfig(name="bass", events=BASS, instrument="square25", gain=0.07),
]
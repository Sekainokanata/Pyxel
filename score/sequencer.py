from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .notes import duration_to_beats


@dataclass(frozen=True)
class Event:
    value: str | list[str]
    duration: str | float
    start_beats: float | None = None
    velocity: float = 1.0
    tone: str | None = None
    effect: str | None = None
    tie: bool = False


def build_sequence_events(items: Sequence[dict]) -> list[Event]:
    events: list[Event] = []
    cursor = 0.0
    for item in items:
        duration_beats = duration_to_beats(item["duration"])
        start_beats = item.get("start_beats")
        if start_beats is None:
            start_beats = cursor
            cursor = start_beats + duration_beats
        events.append(
            Event(
                value=item["value"],
                duration=item["duration"],
                start_beats=float(start_beats),
                velocity=float(item.get("velocity", 1.0)),
                tone=item.get("tone"),
                effect=item.get("effect"),
                tie=bool(item.get("tie", False)),
            )
        )
    return events

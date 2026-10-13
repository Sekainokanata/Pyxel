from __future__ import annotations

import re

# Ported from Alto recorder Program's notes.py (letter/accidental/octave parsing,
# duration-to-beats conversion, and MIDI/frequency conversion). Pyxel's Sound.notes
# integer index scheme (and the NoteIndexOutOfPyxelRangeError/MAX_NOTE_INDEX/
# OCTAVE_SHIFT machinery that used to live here to work around it) has been
# removed entirely per design/mv_plan.md: audio is no longer rendered through
# Pyxel's Sound at all, so notes are converted straight to real Hz frequencies
# using standard scientific pitch notation (C4 = MIDI 60 = middle C), matching
# Alto recorder Program's own note_to_midi()/note_to_frequency().

NOTE_TO_SEMITONE = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}
NOTE_RE = re.compile(r"^([A-Ga-g])([#b♯♭]?)(-?\d+)$")

JAPANESE_TO_LETTER = {
    "ド": "C",
    "レ": "D",
    "ミ": "E",
    "ファ": "F",
    "ソ": "G",
    "ラ": "A",
    "シ": "B",
}
JAPANESE_RE = re.compile(r"^(ド|レ|ミ|ファ|ソ|ラ|シ)([#b♯♭]?)(-?\d+)$")
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def _parse_letter_and_octave(note: str) -> tuple[str, int]:
    text = note.strip()

    match = NOTE_RE.match(text)
    if match:
        letter, accidental, octave_text = match.groups()
        base = letter.upper() + accidental.replace("♯", "#").replace("♭", "b")
        return base, int(octave_text)

    text_norm = text.translate(FULLWIDTH_DIGITS)
    jap_match = JAPANESE_RE.match(text_norm)
    if jap_match:
        syllable, accidental, octave_text = jap_match.groups()
        base = JAPANESE_TO_LETTER[syllable] + accidental.replace("♯", "#").replace("♭", "b")
        return base, int(octave_text)

    raise ValueError(f"Invalid note name: {note}")


def note_to_midi(note: str) -> int:
    """標準的な科学的音名表記(C4=MIDI60=中央ハ)でMIDIノート番号を返す。"""
    base, octave = _parse_letter_and_octave(note)
    if base not in NOTE_TO_SEMITONE:
        raise ValueError(f"Unsupported note spelling: {note}")
    return 12 * (octave + 1) + NOTE_TO_SEMITONE[base]


def note_to_frequency(note: str, a4_hz: float = 440.0) -> float:
    midi = note_to_midi(note)
    return a4_hz * (2.0 ** ((midi - 69) / 12.0))


def is_rest(value: object) -> bool:
    return isinstance(value, str) and value.lower() == "mute"


def is_percussive(value: object) -> bool:
    """Alto recorder Programのguitarパートに由来する"X"(ミュートストローク等の
    打楽器的な一打)。ピッチを持たないが休符でもないので、is_rest()とは区別する。
    """
    return isinstance(value, str) and value.strip().upper() == "X"


def duration_to_beats(duration: str | float) -> float:
    if isinstance(duration, (int, float)):
        return float(duration)

    text = str(duration).strip()
    dotted = text.endswith(".")
    if dotted:
        text = text[:-1]

    if "/" in text:
        numerator_text, denominator_text = text.split("/", 1)
        beats = 4.0 * float(numerator_text) / float(denominator_text)
    else:
        beats = float(text)

    if dotted:
        beats *= 1.5
    return beats


def beats_to_seconds(beats: float, bpm: float) -> float:
    return (60.0 / bpm) * beats


def seconds_to_beats(seconds: float, bpm: float) -> float:
    return seconds / (60.0 / bpm)

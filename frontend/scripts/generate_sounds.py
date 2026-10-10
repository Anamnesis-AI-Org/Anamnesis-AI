"""Generate default UI sound assets for utils/sfx.ts.

Run from the repo root:
  .venv/Scripts/python.exe frontend/scripts/generate_sounds.py

Writes tick.wav, whoosh.wav, chime.wav, hum.wav into frontend/public/sounds/.
To use your own audio, replace any of them with a real file at the same base
name (.mp3 preferred - utils/sfx.ts tries /sounds/<name>.mp3 first and falls
back to the bundled .wav).
"""

import math
import random
import struct
import wave
from pathlib import Path

SR = 22050
OUT = Path(__file__).resolve().parent.parent / "public" / "sounds"
random.seed(7)


def _write(name, samples):
    OUT.mkdir(parents=True, exist_ok=True)
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples
    )
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames)
    print("wrote", name, (OUT / name).stat().st_size, "bytes")


def tick():
    n = int(SR * 0.07)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 60)
        s = 0.6 * math.sin(2 * math.pi * 1900 * t) * env
        s += 0.25 * (random.random() * 2 - 1) * math.exp(-t * 200)
        out.append(s * 0.8)
    return out


def whoosh():
    n = int(SR * 0.55)
    out = []
    prev = 0.0
    for i in range(n):
        frac = i / n
        env = math.sin(math.pi * frac) ** 1.5
        cutoff = 0.02 + min(0.48, 4.0 * frac * (1.0 - frac))
        noise = random.random() * 2 - 1
        prev = prev + cutoff * (noise - prev)
        out.append(max(-1.0, min(1.0, prev * env * 1.4)))
    return out


def chime():
    n = int(SR * 1.4)
    out = []
    for i in range(n):
        t = i / SR
        s = 0.45 * math.sin(2 * math.pi * 740 * t) * math.exp(-t * 3.2)
        s += 0.35 * math.sin(2 * math.pi * 1108 * t) * math.exp(-t * 4.0)
        s += 0.18 * math.sin(2 * math.pi * 1480 * t) * math.exp(-t * 5.5)
        out.append(s)
    return out


def hum():
    # All partials complete a whole number of cycles over 4 s, so the loop
    # point is phase-continuous (no click when it repeats).
    n = int(SR * 4)
    out = []
    for i in range(n):
        t = i / SR
        trem = 0.85 + 0.15 * math.sin(2 * math.pi * 0.25 * t)
        s = 0.5 * math.sin(2 * math.pi * 70 * t)
        s += 0.3 * math.sin(2 * math.pi * 140 * t)
        s += 0.1 * math.sin(2 * math.pi * 105 * t)
        out.append(s * trem * 0.5)
    return out


if __name__ == "__main__":
    _write("tick.wav", tick())
    _write("whoosh.wav", whoosh())
    _write("chime.wav", chime())
    _write("hum.wav", hum())

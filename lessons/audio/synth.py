"""Procedural sound for the lesson videos: SFX library, per-theme generative music, and a cue mixer.

    python audio/synth.py out/<lesson>/info.json out/<lesson>/audio.wav

info.json comes from the engine: {total, cues:[{t,n,g,r}], theme}. Everything is numpy/scipy, no samples.
"""
import json
import sys
import zlib

import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100
RNG = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def env_ad(n, a=0.005, d=0.2, curve=3.0):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-t / max(d, 1e-3) * curve / 3)
    return e


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR / 2 - 100)], "band", fs=SR, output="sos"), x)


def noise(d):
    return RNG.standard_normal(int(d * SR))


def sine(f, d, ph=0.0):
    return np.sin(2 * np.pi * f * t_(d) + ph)


def sweep(f0, f1, d, expo=True):
    t = t_(d)
    f = f0 * (f1 / f0) ** (t / d) if expo else f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def fade(x, a=0.003, r=0.01):
    n = len(x); na, nr = int(a * SR), int(r * SR)
    x = x.copy()
    if na: x[:na] *= np.linspace(0, 1, na)
    if nr: x[-nr:] *= np.linspace(1, 0, nr)
    return x


def addat(y, s, k):
    k = int(k)
    if k < 0 or k >= len(y):
        return
    m = min(len(s), len(y) - k)
    y[k:k + m] += s[:m]


def reverb(x, wet=0.25, d=0.35):
    out = np.concatenate([x, np.zeros(int(d * SR))])
    for dt, g in ((0.029, 0.5), (0.047, 0.38), (0.071, 0.28), (0.103, 0.2), (0.151, 0.12)):
        k = int(dt * SR); addat(out, x * g * wet * 2, k)
    return out


# ───────────────────────── SFX ─────────────────────────
def sfx_whoosh(d=0.7, lo=300, hi=3500):
    n = noise(d); N = len(n); y = np.zeros(N); blk = 512
    for i in range(0, N, blk):
        p = i / N; fc = lo + (hi - lo) * np.sin(np.pi * min(1, p * 1.0)) ** 1.5
        sos = butter(2, [max(80, fc * 0.5), min(fc * 1.6, 15000)], "band", fs=SR, output="sos")
        y[i:i + blk] = sosfilt(sos, n[i:i + blk])
    e = np.sin(np.pi * np.linspace(0, 1, N)) ** 2
    return fade(norm(y * e, 0.7))


def sfx_swish():
    return sfx_whoosh(0.28, 900, 6000) * 0.8


def sfx_pop():
    s = sweep(900, 260, 0.12) * env_ad(int(0.12 * SR), 0.001, 0.05, 6)
    c = hp(noise(0.01), 2000) * 0.5
    s[:len(c)] += c
    return norm(s, 0.7)


def sfx_ding():
    d = 1.1; t = t_(d); y = np.zeros_like(t)
    for k, (m, a) in enumerate(((1, 1.0), (2.76, 0.5), (5.4, 0.28), (8.9, 0.12))):
        y += a * np.sin(2 * np.pi * 1318 * m * t) * np.exp(-t * (3 + k * 3))
    y *= np.minimum(t / 0.003, 1)
    return norm(reverb(y, 0.2), 0.6)


def sfx_tick():
    s = bp(noise(0.03), 1800, 5000) * env_ad(int(0.03 * SR), 0.0005, 0.012, 6) * 1.5
    s += sine(1500, 0.03) * env_ad(int(0.03 * SR), 0.0005, 0.01, 6) * 0.5
    return norm(s, 0.5)


def sfx_click():
    return norm(hp(noise(0.015), 1500) * env_ad(int(0.015 * SR), 0.0003, 0.006, 6), 0.45)


def sfx_boing():
    d = 0.55; t = t_(d)
    f = 220 + 380 * np.exp(-4 * t) * (1 + 0.55 * np.cos(2 * np.pi * 11 * t))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    y += 0.3 * np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * np.exp(-t * 6)
    return fade(norm(y, 0.6))


def sfx_thud():
    d = 0.45; t = t_(d)
    y = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-6 * t) + 40) / SR) * np.exp(-t * 9)
    y += lp(noise(d), 300) * np.exp(-t * 20) * 1.2
    return norm(y, 0.85)


def sfx_boom():
    d = 3.2; t = t_(d)
    y = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-1.2 * t) + 28) / SR) * np.exp(-t * 1.3)
    y += lp(noise(d), 600) * np.exp(-t * 2.2) * 1.4
    crack = np.zeros_like(t); c = hp(noise(0.25), 500) * np.exp(-t_(0.25) * 14); crack[:len(c)] = c
    return fade(norm(y + crack * 0.6, 0.9), 0.002, 0.3)


def sfx_rumble(d=3.5):
    t = t_(d)
    y = lp(noise(d), 160, 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t + np.sin(2 * np.pi * 0.9 * t) * 3))
    y += 0.5 * np.sin(2 * np.pi * 38 * t) * (0.7 + 0.3 * np.sin(2 * np.pi * 5 * t))
    e = np.minimum(t / 0.5, 1) * np.minimum((d - t) / 0.8, 1)
    return norm(y * e, 0.9)


def sfx_sparkle():
    d = 1.0; y = np.zeros(int(d * SR))
    for k in range(9):
        t0 = int(RNG.uniform(0, 0.55) * SR); f = RNG.choice([2093, 2637, 3136, 3951, 4186])
        s = sine(f, 0.22) * np.exp(-t_(0.22) * 16)
        addat(y, s * RNG.uniform(0.3, 0.7), t0)
    return norm(reverb(y, 0.25), 0.55)


def sfx_tada():
    d = 1.4; y = np.zeros(int(d * SR))
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        t0 = int(k * 0.07 * SR); t = t_(d - k * 0.07)
        s = sum(a * np.sin(2 * np.pi * f * m * t) for m, a in ((1, 1), (2, 0.4), (3, 0.2))) * np.exp(-t * 2.6)
        s *= np.minimum(t / 0.004, 1); addat(y, s, t0)
    return norm(reverb(y, 0.25), 0.6)


def sfx_chime():
    y = np.zeros(int(1.2 * SR))
    for k, f in enumerate((880, 1174.66)):
        t = t_(1.0); s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.7 * t)) * np.exp(-t * 4.5)
        t0 = int(k * 0.13 * SR); addat(y, s, t0)
    return norm(reverb(y, 0.2), 0.5)


def sfx_blip():
    f = RNG.uniform(420, 760); d = 0.07; t = t_(d)
    y = (np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6) * np.sin(np.pi * t / d)
    return norm(lp(y, 3200), 0.4)


def sfx_splash():
    d = 0.9; n = noise(d); t = t_(d)
    y = bp(n, 400, 6000) * np.exp(-t * 5) * np.minimum(t / 0.01, 1)
    for k in range(10):
        t0 = int(RNG.uniform(0.02, 0.5) * SR); f = RNG.uniform(500, 1500)
        s = sweep(f, f * 2, 0.08) * np.exp(-t_(0.08) * 30); addat(y, s * 0.35, t0)
    return norm(y, 0.7)


def sfx_wind(d=3.0):
    n = noise(d); t = t_(d); N = len(n); y = np.zeros(N); blk = 1024
    for i in range(0, N, blk):
        fc = 400 + 500 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * i / SR))
        y[i:i + blk] = sosfilt(butter(2, [fc * 0.6, fc * 1.5], "band", fs=SR, output="sos"), n[i:i + blk])
    e = np.minimum(t / 0.6, 1) * np.minimum((d - t) / 0.8, 1) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
    return norm(y * e, 0.6)


def sfx_water(d=2.5):
    n = noise(d); t = t_(d)
    y = bp(n, 300, 2500) * (0.5 + 0.5 * np.abs(lp(noise(d), 12)) * 20)
    for k in range(40):
        t0 = int(RNG.uniform(0, d - 0.1) * SR); f = RNG.uniform(500, 1800)
        s = sweep(f, f * 1.6, 0.05) * np.exp(-t_(0.05) * 40); addat(y, s * 0.25, t0)
    return norm(y * np.minimum(t / 0.3, 1) * np.minimum((d - t) / 0.5, 1), 0.55)


def sfx_crack():
    d = 0.5; t = t_(d)
    y = hp(noise(d), 700) * np.exp(-t * 40) * 1.2 + lp(noise(d), 200) * np.exp(-t * 14)
    return norm(y, 0.85)


def sfx_drum():
    d = 0.5; t = t_(d)
    y = np.sin(2 * np.pi * np.cumsum(150 * np.exp(-12 * t) + 70) / SR) * np.exp(-t * 8)
    y += bp(noise(d), 600, 3000) * np.exp(-t * 40) * 0.5
    return norm(y, 0.8)


def sfx_sizzle(d=1.2):
    n = hp(noise(d), 4000) * (RNG.random(int(d * SR)) > 0.985) * 6
    n = lp(n, 9000)
    t = t_(d); return norm(n * np.minimum(t / 0.05, 1) * np.minimum((d - t) / 0.3, 1) + hp(noise(d), 6000) * 0.02, 0.5)


def sfx_page():
    d = 0.35; t = t_(d); y = bp(noise(d), 1500, 7000) * np.sin(np.pi * t / d) ** 2
    return norm(y, 0.5)


def sfx_magic():
    d = 1.2; t = t_(d); f = 500 * (4 ** (t / d))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 1.5
    y += 0.4 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.sin(np.pi * t / d)
    return norm(reverb(y, 0.2), 0.5)


def sfx_wrong():
    y = np.zeros(int(0.7 * SR))
    for k, f in enumerate((330, 247)):
        t = t_(0.35); s = np.sign(np.sin(2 * np.pi * f * t)) * 0.3 * np.exp(-t * 4); s = lp(s, 1500)
        t0 = int(k * 0.22 * SR); addat(y, s, t0)
    return norm(y, 0.55)


def sfx_bubble():
    f = RNG.uniform(400, 900); d = 0.12
    return norm(sweep(f, f * 2.2, d) * env_ad(int(d * SR), 0.002, 0.05, 5), 0.5)


def sfx_horn():
    d = 1.1; t = t_(d)
    y = sum(a * np.sin(2 * np.pi * 220 * m * t) for m, a in ((1, 1), (2, 0.6), (3, 0.4), (4, 0.25)))
    return fade(norm(lp(y, 1800) * np.minimum(t / 0.1, 1) * np.minimum((d - t) / 0.3, 1), 0.5), 0.01, 0.05)


def sfx_gallop(d=1.6):
    y = np.zeros(int(d * SR))
    for k in range(int(d / 0.16)):
        t0 = int(k * 0.16 * SR) + (0 if k % 3 else int(0.05 * SR)); s = sfx_thud()[: int(0.15 * SR)] * (0.5 + 0.3 * (k % 2)); s = hp(s, 120); addat(y, s[: len(y) - t0], t0)
    return norm(y, 0.6)


def sfx_clash():
    d = 0.9; t = t_(d); y = np.zeros_like(t)
    for f in (1760, 2490, 3730, 5200):
        y += np.sin(2 * np.pi * f * t) * np.exp(-t * (6 + f / 900)) * RNG.uniform(0.5, 1)
    y += hp(noise(d), 3000) * np.exp(-t * 30) * 0.8
    return norm(y, 0.6)


SFX = {k[4:]: v for k, v in list(globals().items()) if k.startswith("sfx_")}
_cache = {}


def get_sfx(name):
    if name not in _cache:
        fn = SFX.get(name) or SFX["pop"]
        _cache[name] = fn().astype(np.float32)
    return _cache[name]


def resample(x, r):
    if abs(r - 1) < 1e-3:
        return x
    n = int(len(x) / r)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


# ───────────────────────── music ─────────────────────────
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "pent": [0, 2, 4, 7, 9], "minorpent": [0, 3, 5, 7, 10], "hijaz": [0, 1, 4, 5, 7, 8, 10], "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}
THEME_MUSIC = {
    "space": dict(root=60, scale="lydian", bpm=92, chords=[(0, 4, 7), (5, 9, 12), (7, 11, 14), (2, 5, 9)], drums=0.6, lead="bell"),
    "lava": dict(root=57, scale="minorpent", bpm=100, chords=[(0, 3, 7), (-4, 0, 3), (3, 7, 10), (-2, 2, 5)], drums=1.0, lead="pluck"),
    "rock": dict(root=55, scale="minorpent", bpm=96, chords=[(0, 3, 7), (5, 8, 12), (-2, 2, 5), (3, 7, 10)], drums=0.9, lead="pluck"),
    "desert": dict(root=62, scale="hijaz", bpm=98, chords=[(0, 4, 7), (1, 5, 8), (0, 4, 7), (-2, 2, 5)], drums=1.0, lead="oud"),
    "river": dict(root=60, scale="pent", bpm=96, chords=[(0, 4, 7), (-3, 0, 4), (-5, -1, 2), (-7, -3, 0)], drums=0.5, lead="bell"),
    "sea": dict(root=65, scale="lydian", bpm=90, chords=[(0, 4, 7), (2, 6, 9), (4, 7, 11), (2, 6, 9)], drums=0.4, lead="bell"),
    "sky": dict(root=62, scale="major", bpm=100, chords=[(0, 4, 7), (5, 9, 12), (7, 11, 14), (0, 4, 7)], drums=0.7, lead="pluck"),
    "islam": dict(root=62, scale="hijaz", bpm=88, chords=[(0, 4, 7), (1, 5, 8), (0, 4, 7), (-2, 2, 5)], drums=1.0, lead="oud"),
    "night": dict(root=57, scale="hijaz", bpm=80, chords=[(0, 3, 7), (1, 5, 8), (0, 3, 7), (-2, 2, 5)], drums=0.8, lead="oud"),
    "review": dict(root=60, scale="major", bpm=104, chords=[(0, 4, 7), (-3, 0, 4), (-5, -1, 2), (-7, -3, 0)], drums=0.8, lead="pluck"),
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def ks_pluck(f, d=1.0, bright=0.5):
    N = int(SR / f); n = int(d * SR)
    x = np.zeros(n); x[:N] = RNG.uniform(-1, 1, N)
    x[:N] = lp(x[:N], 4000 * bright + 800) if N > 40 else x[:N]
    a = np.zeros(N + 2); a[0] = 1; a[N] = -0.5 * 0.996; a[N + 1] = -0.5 * 0.996
    return lfilter([1], a, x)


def tone(f, d, kind="bell"):
    t = t_(d)
    if kind == "bell":
        y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * dc) for m, a, dc in ((1, 1, 3), (2.01, 0.4, 5), (3.98, 0.15, 8), (5.4, 0.08, 11)))
        return y * np.minimum(t / 0.004, 1)
    if kind == "oud":
        return ks_pluck(f, d, 0.35) * 1.6
    return ks_pluck(f, d, 0.8) * 1.4


def pad(freqs, d):
    t = t_(d); y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            y += np.sin(2 * np.pi * f * (1 + det) * t) + 0.3 * np.sin(2 * np.pi * f * 2 * (1 + det) * t) * 0.5
    e = np.minimum(t / (d * 0.3), 1) * np.minimum((d - t) / (d * 0.35), 1)
    return lp(y, 1800) * e / (len(freqs) * 3)


def music(theme, total, seed=1):
    cfg = THEME_MUSIC.get(theme, THEME_MUSIC["space"])
    rng = np.random.default_rng(seed)
    spb = 60 / cfg["bpm"]; bar = 4 * spb
    N = int((total + 3) * SR); out = np.zeros(N, dtype=np.float32)
    scale = SCALES[cfg["scale"]]; root = cfg["root"]
    nb = int(np.ceil((total + 3) / bar)); chords = cfg["chords"]
    note_pool = [root + 12 * o + s for o in (0, 1) for s in scale]
    last = len(note_pool) // 2
    for b in range(nb):
        t0 = b * bar; i0 = int(t0 * SR); ch = chords[b % len(chords)]
        # pad
        p = pad([mtof(root - 12 + c) for c in ch], bar * 1.05) * 0.55
        addat(out, p[: N - i0], i0)
        # bass: root on beat 1 and 3
        for beat in (0, 2):
            f = mtof(root - 24 + ch[0]); s = sine(f, spb * 1.6) * np.exp(-t_(spb * 1.6) * 2.5) * 0.5
            k = i0 + int(beat * spb * SR); addat(out, s[: max(0, N - k)], k)
        # melody on 8th notes
        for e in range(8):
            if rng.random() < 0.58:
                last = int(np.clip(last + rng.choice([-2, -1, 0, 1, 2, 3], p=[0.12, 0.28, 0.1, 0.28, 0.12, 0.1]), 0, len(note_pool) - 1))
                m = note_pool[last]
                tn = tone(mtof(m + 12), spb * 1.4, cfg["lead"]) * 0.2
                k = i0 + int((e * spb / 2) * SR); addat(out, tn[: max(0, N - k)], k)
        # percussion
        if cfg["drums"] > 0:
            for beat in range(4):
                if beat % 2 == 0:
                    s = sfx_drum()[: int(0.3 * SR)] * 0.35 * cfg["drums"]
                    k = i0 + int(beat * spb * SR); addat(out, s[: max(0, N - k)], k)
                s2 = sfx_tick() * 0.25 * cfg["drums"]
                k = i0 + int((beat + 0.5) * spb * SR); addat(out, s2[: max(0, N - k)], k)
    out = out[: int(total * SR)]
    fi = int(2 * SR); fo = int(3 * SR)
    out[:fi] *= np.linspace(0, 1, fi); out[-fo:] *= np.linspace(1, 0, fo)
    return out / (np.max(np.abs(out)) + 1e-6) * 0.5


def mix(info, music_gain=0.34, sfx_gain=0.75):
    total = info["total"] + 0.5
    n = int(total * SR)
    L = np.zeros(n, dtype=np.float32); R = np.zeros(n, dtype=np.float32)
    m = music(info.get("theme", "space"), total, seed=zlib.crc32(str(info.get("id", "x")).encode()) % 1000) * music_gain
    L[: len(m)] += m; R[: len(m)] += m
    for c in info["cues"]:
        s = resample(get_sfx(c["n"]), c.get("r", 1.0)) * c.get("g", 1.0) * sfx_gain
        k = int(c["t"] * SR)
        if k >= n:
            continue
        s = s[: n - k]
        pan = RNG.uniform(-0.25, 0.25); lg, rg = 1 - max(0, pan), 1 + min(0, pan)
        addat(L, s * lg, k); addat(R, s * rg, k)
    st = np.stack([L, R], 1)
    # loudness: bring the programme to about -18 dBFS RMS, then soft-limit
    rms = np.sqrt(np.mean(st[st.any(axis=1)] ** 2)) if st.any() else 1.0
    st = st * (0.125 / max(rms, 1e-4))
    st = np.tanh(st * 1.15) / np.tanh(1.15) * 0.82
    return st


def write_wav(path, st):
    import wave
    pcm = (np.clip(st, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    info = json.load(open(sys.argv[1]))
    info["id"] = sys.argv[3] if len(sys.argv) > 3 else info.get("id", "x")
    write_wav(sys.argv[2], mix(info))
    print("wrote", sys.argv[2])

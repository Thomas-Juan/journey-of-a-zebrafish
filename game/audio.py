# -*- coding: utf-8 -*-
"""Procedural music and sound effects (numpy synthesis, no asset files).

Each world has its own 16-bar tune built from a chord progression, a motif-based
melody that lands on chord tones, an accompaniment, bass, drums and a stereo echo."""
import math
import random
import sys
import threading
import pygame

WEB = sys.platform == "emscripten"

try:
    import numpy as np
except Exception:  # pragma: no cover - audio is simply disabled without numpy
    np = None

RATE = 44100
ok = False
_sfx = {}
_tunes = {}
_lock = threading.Lock()
_cur = None
_ch = []
_chi = 0
vol_music, vol_sfx = 0.6, 0.7


def init():
    global ok, _ch, RATE
    if np is None:
        return
    try:
        pygame.mixer.quit()
        pygame.mixer.init(44100, -16, 2, 1024)
        RATE = pygame.mixer.get_init()[0]
        pygame.mixer.set_num_channels(16)
        _ch = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
        pygame.mixer.set_reserved(2)
        ok = True
        _build_sfx()
        if not WEB:
            threading.Thread(target=_precompose, daemon=True).start()
    except Exception:
        ok = False


# ------------------------------------------------------------------ synthesis
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


SAW = [(k, 1.0 / k ** 1.5) for k in range(1, 9)]
SQR = [(k, 1.0 / k ** 1.25) for k in range(1, 10, 2)]
INSTR = {
    # name: (harmonics, attack, decay, sustain, release, vibrato, bend, detune)
    "sitar": ([(k, 1.0 / k ** 1.2) for k in range(1, 10)], 0.003, 0.32, 0.04, 0.05, 0.0, 0.035, 0.004),
    "bell": ([(1, 1), (2, 0.35), (4, 0.2), (6, 0.07)], 0.002, 0.42, 0.0, 0.05, 0.0, 0.0, 0.0),
    "flute": ([(1, 1), (2, 0.22), (3, 0.07)], 0.05, 1.0, 0.8, 0.07, 0.004, 0.0, 0.0),
    "harpsi": ([(k, 1.0 / k) for k in range(1, 11)], 0.002, 0.2, 0.0, 0.03, 0.0, 0.0, 0.0),
    "synth": (SAW, 0.012, 0.3, 0.6, 0.06, 0.003, 0.0, 0.006),
    "square": (SQR, 0.006, 0.2, 0.55, 0.04, 0.003, 0.0, 0.0),
    "pluck": ([(1, 1), (2, 0.4), (3, 0.2), (4, 0.1)], 0.003, 0.24, 0.0, 0.03, 0.0, 0.0, 0.0),
    "pad": (SAW, 0.3, 1.0, 0.8, 0.3, 0.002, 0.0, 0.005),
    "bass": ([(1, 1), (2, 0.35), (3, 0.12)], 0.005, 0.4, 0.35, 0.03, 0.0, 0.0, 0.0),
}
_ncache = {}


def _voice(f, n, harm, vib, bend):
    t = np.arange(n, dtype=np.float32) / RATE
    ph = 2 * np.pi * f * t
    if vib:
        ph = ph + (f * vib / 5.5) * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1.0, t * 4)
    if bend:
        ph = ph + 2 * np.pi * f * bend * 0.05 * (np.exp(-t / 0.05) - 1)
    out = np.zeros(n, dtype=np.float32)
    for k, a in harm:
        if k * f < RATE * 0.42:
            out += a * np.sin(k * ph)
    return out


def note(inst, midi, n):
    key = (inst, midi, n)
    w = _ncache.get(key)
    if w is None:
        harm, att, dec, sus, rel, vib, bend, det = INSTR[inst]
        f = hz(midi)
        w = _voice(f, n, harm, vib, bend)
        if det:
            w = 0.5 * (w + _voice(f * (1 + det), n, harm, vib, bend))
        t = np.arange(n, dtype=np.float32) / RATE
        env = np.minimum(t / att, 1.0) * (sus + (1 - sus) * np.exp(-t / dec))
        r = min(n, max(1, int(rel * RATE)))
        env[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
        w = w * env / max(1.0, sum(a for _, a in harm) * 0.6)
        _ncache[key] = w
    return w


def _drums():
    rng = np.random.default_rng(5)

    def t(n):
        return np.arange(n, dtype=np.float32) / RATE
    n = int(0.22 * RATE)
    kick = np.sin(2 * np.pi * (45 * t(n) + (110 - 45) * 0.03 * (1 - np.exp(-t(n) / 0.03)))) * np.exp(-t(n) / 0.08)
    n = int(0.18 * RATE)
    ns = rng.standard_normal(n).astype(np.float32)
    snare = (np.diff(ns, prepend=0) * 0.5 * np.exp(-t(n) / 0.055) + 0.5 * np.sin(2 * np.pi * 190 * t(n)) * np.exp(-t(n) / 0.035))
    n = int(0.05 * RATE)
    hat = np.diff(rng.standard_normal(n).astype(np.float32), prepend=0) * 0.35 * np.exp(-t(n) / 0.012)
    n = int(0.3 * RATE)
    tlo = np.sin(2 * np.pi * (88 * t(n) + 70 * 0.06 * (1 - np.exp(-t(n) / 0.06)))) * np.exp(-t(n) / 0.13)
    n = int(0.12 * RATE)
    thi = np.sin(2 * np.pi * 400 * t(n)) * np.exp(-t(n) / 0.045) + 0.1 * rng.standard_normal(n) * np.exp(-t(n) / 0.004)
    return dict(kick=kick.astype(np.float32), snare=snare.astype(np.float32), hat=hat.astype(np.float32),
                tlo=tlo.astype(np.float32), thi=thi.astype(np.float32))


MAJ, MIN, DOR = [0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10], [0, 2, 3, 5, 7, 9, 10]
P_MAJ, P_MIN = [0, 4, 5, 3, 0, 4, 3, 4], [0, 5, 2, 6, 0, 5, 3, 4]
TUNES = {
    # key: bpm, beats/bar, root midi, mode, progression, lead, lead octave, comp style, drums
    "map": (92, 4, 55, MAJ, P_MAJ, "flute", 2, "arp", "none"),
    1: (92, 4, 50, [0, 1, 4, 5, 7, 8, 11], [0, 0, 3, 0, 0, 0, 4, 0], "sitar", 1, "drone", "tabla"),
    2: (138, 3, 53, MAJ, [0, 3, 4, 0, 5, 1, 4, 4], "bell", 2, "waltz", "none"),
    3: (108, 4, 55, MAJ, P_MAJ, "flute", 2, "arp", "soft"),
    4: (116, 4, 57, MIN, P_MIN, "harpsi", 1, "arp", "none"),
    5: (124, 4, 52, DOR, [0, 6, 5, 3, 0, 6, 3, 4], "synth", 1, "arp", "rock"),
    6: (130, 4, 48, MAJ, [0, 5, 3, 4, 0, 5, 3, 4], "square", 2, "drive", "rock"),
    7: (72, 4, 50, [0, 2, 4, 6, 7, 9, 11], [0, 1, 0, 4, 0, 1, 5, 0], "bell", 2, "pad", "none"),
    "boss": (156, 4, 52, [0, 1, 3, 5, 7, 8, 10], [0, 1, 0, 6, 0, 1, 5, 0], "synth", 1, "drive", "boss"),
}
RHY = {4: [[2, 2, 2, 2], [2, 1, 1, 2, 2], [3, 1, 2, 2], [2, 2, 1, 1, 2], [4, 2, 2], [1, 1, 2, 2, 2], [3, 1, 4], [2, 2, 4]],
       3: [[2, 2, 2], [3, 1, 2], [2, 1, 1, 2], [4, 2], [2, 2, 1, 1], [1, 1, 2, 2]]}


PROGS = {"maj": [P_MAJ, [0, 3, 4, 0, 5, 3, 1, 4], [0, 5, 3, 4, 0, 5, 1, 4], [0, 2, 3, 4, 0, 5, 3, 4], [0, 4, 3, 0, 5, 3, 4, 4]],
         "min": [P_MIN, [0, 3, 6, 2, 0, 3, 4, 4], [0, 6, 5, 6, 0, 3, 4, 0], [0, 5, 6, 0, 3, 5, 4, 4], [0, 2, 5, 4, 0, 6, 3, 4]],
         1: [[0, 0, 3, 0, 0, 0, 4, 0], [0, 3, 0, 0, 4, 0, 3, 0], [0, 0, 4, 3, 0, 0, 1, 0]],
         7: [[0, 1, 0, 4, 0, 1, 5, 0], [0, 4, 1, 0, 5, 1, 4, 0]]}
LEADS = {1: ("sitar", "flute", "sitar"), 2: ("bell", "harpsi", "flute"), 3: ("flute", "pluck", "bell"), 4: ("harpsi", "flute", "bell"),
         5: ("synth", "square", "bell"), 6: ("square", "synth", "flute"), 7: ("bell", "flute", "synth")}
LOCT = {"sitar": 1, "flute": 2, "bell": 2, "harpsi": 1, "synth": 1, "square": 2, "pluck": 2}
COMPS = {1: ("drone", "drone", "arp"), 2: ("waltz", "waltz", "arp"), 3: ("arp", "drive", "arp"), 4: ("arp", "pad", "arp"),
         5: ("arp", "drive", "pad"), 6: ("drive", "arp", "drive"), 7: ("pad", "arp", "pad")}
DRUMS = {1: ("tabla", "tabla", "none"), 2: ("none", "none", "soft"), 3: ("soft", "rock", "soft"), 4: ("none", "soft", "soft"),
         5: ("rock", "rock", "soft"), 6: ("rock", "rock", "boss"), 7: ("none", "none", "soft")}


def level_key(spec, idx):
    """Music key for a level: every level and every boss gets its own tune."""
    if spec.get("boss"):
        return ("B", spec["id"], spec["world"])
    mood = "dark" if spec.get("dark") else "chase" if spec.get("chase") else ""
    return ("L", spec["id"], spec["world"], idx, mood)


def _spec(key):
    if not isinstance(key, tuple):
        return TUNES[key] + (str(key),)
    if key[0] == "B":
        w = key[2]
        bpm, beats, root, mode, prog, lead, loct, comp, drums = TUNES["boss"]
        r = random.Random("boss" + key[1])
        mode = [mode, MIN, DOR, [0, 1, 4, 5, 7, 8, 10]][w % 4]
        prog = r.choice([prog, [0, 5, 0, 6, 0, 5, 3, 4], [0, 0, 5, 4, 0, 0, 6, 4], [0, 1, 0, 4, 0, 1, 3, 4]])
        return (bpm + w * 4, beats, root + (w * 5) % 7 - 3, mode, prog, r.choice(["synth", "square", "harpsi"]), 1, comp, drums, key[1])
    _, lid, w, idx, mood = key
    bpm, beats, root, mode, prog, lead, loct, comp, drums = TUNES[w]
    r = random.Random("lvl" + lid)
    if idx > 0:   # the first level of a world keeps the world's signature tune
        root += [0, 2, -2, 3, -3, 5, -1][idx % 7]
        bpm *= [1.0, 1.06, 0.95, 1.1, 0.92, 1.08, 1.0][idx % 7]
        fam = w if w in PROGS else ("maj" if mode[2] == 4 else "min")
        prog = PROGS[fam][idx % len(PROGS[fam])]
        lead = r.choice(LEADS[w])
        comp = r.choice(COMPS[w])
        drums = r.choice(DRUMS[w])
    if mood == "dark":
        bpm *= 0.86
        comp = "pad" if comp != "drone" else comp
        drums = "tabla" if drums == "tabla" else "none"
        if mode == MAJ:
            mode, prog = MIN, PROGS["min"][idx % 5]
    elif mood == "chase":
        bpm *= 1.2
        comp = "drive"
        drums = "boss" if beats == 4 else "soft"
    return (bpm, beats, root, mode, prog, lead, LOCT[lead], comp, drums, lid)


def _melody(rnd, beats, mode, prog):
    n, bs = len(mode), beats * 2
    motifs = rnd.sample(RHY[beats], 4)
    form = [0, 1, 0, 2, 0, 1, 3, "end"]
    lo, hi = -2, n + 3
    deg = rnd.choice([0, 2, 4])
    out = []

    def snap(c, tones):
        for off in (0, 1, -1, 2, -2, 3):
            if (c + off) % n in tones:
                return c + off
        return c
    for sec in range(2):
        for b in range(8):
            tones = {(prog[b] + i) % n for i in (0, 2, 4)}
            if form[b] == "end":
                rh = [bs] if sec else ([4, bs - 4] if bs > 4 else [bs])
            else:
                rh = motifs[form[b]]
            dirn = 1 if (b + sec) % 2 == 0 else -1
            pos = 0
            for i, d in enumerate(rh):
                strong = pos % 2 == 0 and (i == 0 or d >= 2)
                c = deg + (dirn * rnd.choice([1, 1, 2]) if rnd.random() < 0.78 else -dirn)
                if strong:
                    c = snap(c, tones)
                if form[b] == "end" and i == len(rh) - 1:
                    c = snap(c, {0} if sec else tones)
                if c > hi:
                    c, dirn = c - 2, -1
                if c < lo:
                    c, dirn = c + 2, 1
                if strong:
                    c = snap(c, tones)
                if c == deg and out and rnd.random() < 0.8:
                    c = snap(c + 2 * dirn, tones) if strong else c + dirn
                rest = (not strong) and d == 1 and rnd.random() < 0.08
                if not rest:
                    out.append((sec * 8 * bs + b * bs + pos, d, c))
                deg = c
                pos += d
    return out


def _compose(key):
    bpm, beats, root, mode, prog, lead, loct, comp, drums, seed = _spec(key)
    rnd = random.Random("zebrafish-" + seed)
    n = len(mode)
    bs = beats * 2
    step = RATE * 60.0 / bpm / 2
    total = int(round(step * bs * 16))
    buf = np.zeros(total + RATE * 2, dtype=np.float32)

    def sem(d):
        return mode[d % n] + 12 * (d // n)

    def add(inst, d, octv, start, dur, gain, sustain=True):
        ln = int(dur * step * (0.96 if sustain else 1.0))
        w = note(inst, root + sem(d) + 12 * octv, max(64, ln))
        s = int(start * step)
        buf[s:s + len(w)] += w * gain

    for st, d, deg in _melody(rnd, beats, mode, prog):
        add(lead, deg, loct, st, d, 0.42)
    dk = _drums()

    def hit(name, start, gain):
        w = dk[name]
        s = int(start * step)
        buf[s:s + len(w)] += w * gain

    for bar in range(16):
        c = prog[bar % 8]
        b0 = bar * bs
        tri = [c, c + 2, c + 4]
        if comp == "arp":
            for i, k in enumerate([0, 2, 1, 2, 0, 2, 1, 2][:bs]):
                add("pluck" if lead != "harpsi" else "harpsi", tri[k] + (n if k == 2 and i % 4 == 3 else 0), 1, b0 + i, 1, 0.16)
            add("bass", c, -1, b0, bs // 2, 0.42)
            add("bass", c + (4 if bar % 2 else 0), -1, b0 + bs // 2, bs // 2, 0.36)
        elif comp == "waltz":
            add("bass", c, -1, b0, 2, 0.5)
            for beat in (1, 2):
                for k in tri:
                    add("pluck", k, 1, b0 + beat * 2, 2, 0.11)
        elif comp == "drone":
            for k, g in ((0, 0.11), (4, 0.08), (n, 0.05)):
                add("pad", k, 0, b0, bs, g)
            add("bass", c, -1, b0, bs, 0.3)
        elif comp == "pad":
            for k in tri:
                add("pad", k, 1, b0, bs, 0.085)
            add("bass", c, -1, b0, bs, 0.34)
        else:  # drive
            for i in range(bs):
                add("bass", c + (n if i % 2 else 0), -1 if i % 2 == 0 else -2, b0 + i, 1, 0.36)
            for i in (2, 5) if drums != "boss" else (1, 3, 5, 7)[:bs // 2]:
                for k in tri:
                    add("square", k, 1, b0 + i, 1, 0.055)
        fill = bar % 8 == 7
        if drums == "tabla":
            for i, (nm, g) in enumerate([("tlo", .5), (None, 0), ("thi", .2), ("thi", .28), ("tlo", .35), ("thi", .2), ("thi", .28), ("thi", .16)][:bs]):
                if nm:
                    hit(nm, b0 + i, g)
            if fill:
                for q in (bs - 1.5, bs - 1, bs - 0.5):
                    hit("thi", b0 + q, 0.3)
        elif drums in ("soft", "rock", "boss"):
            g = 0.55 if drums == "soft" else 1.0
            for i in range(bs):
                hit("hat", b0 + i, 0.16 * g * (1.0 if i % 2 == 0 else 0.6))
                if drums == "boss":
                    hit("hat", b0 + i + 0.5, 0.08)
            kicks = (0,) if beats == 3 else ((0, 4) if drums != "boss" else (0, 2, 4, 6)) + ((5,) if drums == "rock" and bar % 2 else ())
            for q in kicks:
                hit("kick", b0 + q, 0.6 * g)
            for q in ((2, 4) if beats == 3 else (2, 6)):
                hit("snare", b0 + q, 0.34 * g)
            if fill:
                for q in (bs - 1.5, bs - 1, bs - 0.5):
                    hit("snare", b0 + q, 0.26 * g)
    # fold the tail back to the start so the loop is seamless, then add stereo echo
    buf[:RATE * 2] += buf[total:total + RATE * 2]
    dry = buf[:total]
    d1, d2 = int(step * 3), int(step * 4)
    left = dry + 0.24 * np.roll(dry, d1) + 0.10 * np.roll(dry, d1 * 2)
    right = dry + 0.24 * np.roll(dry, d2) + 0.10 * np.roll(dry, d2 + d1)
    st = np.stack([left, right], axis=1)
    st = np.tanh(st * 0.2 / max(0.02, float(np.sqrt((st ** 2).mean())))) * 0.8
    return (st * 32767).astype(np.int16)


def _tune(key):
    with _lock:
        if key not in _tunes:
            for old in [k for k in _tunes if k not in ("map", _cur)]:
                del _tunes[old]          # keep memory low: only the map tune and the current one stay loaded
            _tunes[key] = pygame.mixer.Sound(buffer=_compose(key).tobytes())
            _ncache.clear()
        return _tunes[key]


def _precompose():
    try:
        _tune("map")
    except Exception:
        pass


def prepare(key):
    """Compose a tune in the background so that starting it later does not stall the game."""
    if ok and not WEB and key not in _tunes:
        threading.Thread(target=lambda: _tune(key), daemon=True).start()


def music(key):
    global _cur, _chi
    if not ok or key == _cur:
        return
    _cur = key
    _ch[_chi].fadeout(500)
    if key is None:
        return
    _chi = 1 - _chi
    c = _ch[_chi]
    c.set_volume(vol_music * 0.75)
    c.play(_tune(key), loops=-1, fade_ms=500)


def set_volumes(m, s):
    global vol_music, vol_sfx
    vol_music, vol_sfx = m / 10.0, s / 10.0
    for c in _ch:
        c.set_volume(vol_music * 0.75)


# ------------------------------------------------------------------ sound effects
def _blip(f0, f1, dur, vol=0.5, harm=((1, 1), (2, 0.3)), noise=0.0, decay=0.25, vib=0.0):
    n = int(RATE * dur)
    t = np.arange(n, dtype=np.float32) / RATE
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / RATE
    if vib:
        ph += vib * np.sin(2 * np.pi * 30 * t)
    w = sum(a * np.sin(k * ph) for k, a in harm)
    if noise:
        rng = np.random.default_rng(int(f0))
        w = w * (1 - noise) + rng.standard_normal(n) * noise * 0.8
    env = np.minimum(t / 0.004, 1) * np.exp(-t / (dur * decay))
    r = max(1, n // 6)
    env[-r:] *= np.linspace(1, 0, r)
    return (w * env * vol).astype(np.float32)


def _snd(*parts):
    w = np.concatenate(parts)
    w = np.tanh(w * 1.2) * 0.9
    st = np.stack([w, w], axis=1)
    return pygame.mixer.Sound(buffer=(st * 32767).astype(np.int16).tobytes())


def _build_sfx():
    S, B = _sfx, _blip
    bell = ((1, 1), (2, 0.4), (3, 0.15))
    S["dash"] = _snd(B(260, 700, 0.16, 0.5, noise=0.55, decay=0.5))
    S["hurt"] = _snd(B(380, 110, 0.28, 0.6, SQR, 0.15, 0.5))
    S["food"] = _snd(B(1050, 1400, 0.07, 0.3, bell, decay=0.6))
    S["page"] = _snd(B(523, 523, 0.09, 0.4, bell, decay=0.9), B(659, 659, 0.09, 0.4, bell, decay=0.9), B(784, 784, 0.09, 0.4, bell, decay=0.9), B(1047, 1047, 0.4, 0.45, bell, decay=0.4))
    S["power"] = _snd(B(330, 660, 0.12, 0.4, bell, decay=0.9), B(660, 1320, 0.3, 0.45, bell, decay=0.5))
    S["pop"] = _snd(B(620, 160, 0.12, 0.55, noise=0.25, decay=0.4))
    S["clang"] = _snd(B(1400, 1250, 0.14, 0.4, ((1, 1), (2.76, 0.6), (5.4, 0.3)), decay=0.3))
    S["check"] = _snd(B(440, 440, 0.1, 0.4, bell, decay=0.9), B(660, 660, 0.25, 0.45, bell, decay=0.5))
    S["right"] = _snd(B(659, 659, 0.1, 0.4, bell, decay=0.9), B(880, 880, 0.1, 0.4, bell, decay=0.9), B(1319, 1319, 0.4, 0.45, bell, decay=0.4))
    S["wrong"] = _snd(B(220, 196, 0.2, 0.45, SQR, decay=0.9), B(165, 147, 0.4, 0.45, SQR, decay=0.5))
    S["blip"] = _snd(B(700, 700, 0.05, 0.25, bell, decay=0.6))
    S["splash"] = _snd(B(500, 180, 0.24, 0.4, noise=0.85, decay=0.35))
    S["die"] = _snd(B(520, 70, 0.8, 0.55, bell, 0.05, 0.6, vib=1.5))
    S["boss"] = _snd(B(160, 50, 0.45, 0.8, SQR, 0.4, 0.4))
    S["shoot"] = _snd(B(1300, 500, 0.1, 0.3, bell, decay=0.5))
    win = [B(hz(m), hz(m), 0.12, 0.42, bell, decay=0.9) for m in (72, 76, 79, 84, 79, 84, 88)]
    S["win"] = _snd(*win, B(hz(91), hz(91), 0.7, 0.45, bell, decay=0.35))


def sfx(name):
    if ok and name in _sfx:
        s = _sfx[name]
        s.set_volume(vol_sfx)
        s.play()

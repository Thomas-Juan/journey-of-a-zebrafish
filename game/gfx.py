# -*- coding: utf-8 -*-
"""All art is drawn procedurally here (no image files needed)."""
import math
import random
import pygame
import core
from core import W, H, TILE, hsurf, adopt, scaled, dr

PD = dr            # draws in points on Hi surfaces, in pixels on plain ones
A = pygame.SRCALPHA
# Sprites are drawn SS pixels per point on a work surface, then smoothly scaled down to the
# render scale core.K (anti-aliasing). set_scale() picks SS; zoom() enlarges one drawing.
SS = 3
_SS0 = 3


def set_scale(k):
    """Called once, before anything is drawn: k pixels per point for every cached image."""
    global SS, _SS0
    core.K = k
    _SS0 = SS = 3 * k if k > 1 else 4
    _cache.clear()
    core._panels.clear()


class zoom:
    """with zoom(2): ... draws the next sprite twice as large (in points), at full sharpness."""
    def __init__(self, z):
        self.z = z

    def __enter__(self):
        global SS
        SS = _SS0 * self.z

    def __exit__(self, *a):
        global SS
        SS = _SS0


def _w(w):
    return 0 if not w else max(1, int(round(w * SS)))


def _blended(fn):
    """Translucent colours are blended onto the drawing instead of punching a see-through
    hole in it (pygame.draw replaces pixels, alpha included)."""
    def draw(s, c, *a, **kw):
        if len(c) == 4 and c[3] < 255:
            t = pygame.Surface(s.get_size(), A)
            fn(t, c, *a, **kw)
            s.blit(t, (0, 0))
        else:
            fn(s, c, *a, **kw)
    return staticmethod(draw)


class D:
    """pygame.draw look-alike that scales every coordinate by SS."""
    @_blended
    def polygon(s, c, pts, width=0):
        PD.polygon(s, c, [(x * SS, y * SS) for x, y in pts], _w(width))

    @_blended
    def ellipse(s, c, r, width=0):
        PD.ellipse(s, c, [int(v * SS) for v in r], _w(width))

    @_blended
    def circle(s, c, p, r, width=0):
        PD.circle(s, c, (p[0] * SS, p[1] * SS), r * SS, _w(width))

    @_blended
    def line(s, c, a, b, width=1):
        PD.line(s, c, (a[0] * SS, a[1] * SS), (b[0] * SS, b[1] * SS), _w(width))

    @_blended
    def lines(s, c, closed, pts, width=1):
        pts = [(x * SS, y * SS) for x, y in pts]
        PD.lines(s, c, closed, pts, _w(width))
        if width > 2:
            for p in pts:
                PD.circle(s, c, p, _w(width) / 2)

    @_blended
    def rect(s, c, r, width=0, border_radius=0):
        PD.rect(s, c, [int(v * SS) for v in r], _w(width), border_radius=int(border_radius * SS))

    @_blended
    def arc(s, c, r, a0, a1, width=1):
        PD.arc(s, c, [int(v * SS) for v in r], a0, a1, _w(width))


def put(s, im, pos, size=None):
    """Draw a finished image (Hi, in points) onto a work surface, optionally resized to size points."""
    w, h = size or im.get_size()
    s.blit(pygame.transform.smoothscale(im, (max(1, round(w * SS)), max(1, round(h * SS)))), (round(pos[0] * SS), round(pos[1] * SS)))


def _grad(w, h):
    key = ("G", w, h)
    if key not in _cache:
        g = pygame.Surface((w, h))
        for y in range(h):
            v = int(255 - 62 * (y / max(1, h - 1)) ** 1.4)
            g.fill((v, v, min(255, v + 8)), (0, y, w, 1))
        _cache[key] = g
    return _cache[key]


INK = (16, 26, 44)
_RING = [(math.cos(a * math.tau / 24), math.sin(a * math.tau / 24)) for a in range(24)]


def fin(s, outline=True, shade=True, k=None):
    """Finish a work surface (SS pixels per point): soft shading, a dark outline one point
    wide, then a smooth reduction to k pixels per point. Returns a Hi surface."""
    k = core.K if k is None else k
    rw, rh = s.get_size()
    if shade:
        s.blit(_grad(rw, rh), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    if outline:
        # the outline is grown around the silhouette at full work resolution, so it comes
        # out anti-aliased instead of as a staircase of whole pixels
        p = int(round(SS))
        sil = pygame.mask.from_surface(s, 110).to_surface(setcolor=INK + (255,), unsetcolor=(0, 0, 0, 0))
        out = pygame.Surface((rw + 2 * p, rh + 2 * p), A)
        for r in (p, p * 0.6, p * 0.3):
            for cx, cy in _RING:
                out.blit(sil, (p + round(cx * r), p + round(cy * r)), special_flags=pygame.BLEND_RGBA_MAX)
        out.blit(s, (p, p))
        s, rw, rh = out, rw + 2 * p, rh + 2 * p
    w, h = max(1, round(rw * k / _SS0)), max(1, round(rh * k / _SS0))     # zoom() enlarges
    return adopt(pygame.transform.smoothscale(s, (w, h)), k)


def mirror(im, fx=True, fy=False):
    """pygame.transform.flip for Hi surfaces."""
    return adopt(pygame.transform.flip(im, fx, fy), im.k)


THEMES = {
    1: dict(wt=(84, 160, 150), wb=(18, 66, 86), sky=(250, 205, 150), g=(122, 86, 52), gt=(92, 150, 62), plant=(52, 150, 70), haz=(150, 40, 60)),
    2: dict(wt=(120, 196, 232), wb=(40, 108, 170), sky=(236, 222, 192), g=(196, 166, 118), gt=(232, 206, 156), plant=(48, 160, 96), haz=(230, 90, 40)),
    3: dict(wt=(96, 172, 190), wb=(28, 86, 118), sky=(206, 196, 168), g=(104, 106, 118), gt=(162, 164, 176), plant=(70, 150, 110), haz=(170, 80, 200)),
    4: dict(wt=(104, 182, 212), wb=(30, 88, 150), sky=(216, 226, 236), g=(88, 98, 122), gt=(142, 162, 184), plant=(60, 170, 120), haz=(200, 220, 40)),
    5: dict(wt=(34, 66, 130), wb=(8, 14, 46), sky=(10, 10, 30), g=(28, 38, 80), gt=(0, 200, 180), plant=(0, 150, 170), haz=(255, 60, 120)),
    6: dict(wt=(76, 204, 212), wb=(14, 78, 120), sky=(240, 245, 250), g=(58, 68, 90), gt=(236, 240, 248), plant=(40, 180, 150), haz=(255, 120, 40)),
    7: dict(wt=(70, 130, 210), wb=(22, 42, 112), sky=(5, 5, 18), g=(150, 155, 165), gt=(222, 224, 232), plant=(90, 200, 120), haz=(255, 200, 60)),
}

_cache = {}


def surf(w, h):
    return pygame.Surface((int(w * SS), int(h * SS)), A)


def _fish(w, h, body, belly=None, fin=None, stripe=None, n=0, f=0, eye=True, dorsal=True,
          spines=False, eyecol=(255, 255, 255), big_eye=False, sw=None):
    s = surf(w, h)
    solidc = len(body) == 3
    fin = fin or tuple(max(0, c - 40) for c in body)
    dark = tuple(max(0, c - 34) for c in body[:3])
    bw = w * 0.78
    tx = w - bw
    ty = h / 2 + (f * 2 - 1) * h * 0.09
    # forked tail
    D.polygon(s, fin, [(tx + bw * 0.1, h * 0.4), (0, ty - h * 0.44), (tx * 0.6, ty), (0, ty + h * 0.44), (tx + bw * 0.1, h * 0.6)])
    if solidc:
        for q in (-0.22, 0.22):
            D.line(s, tuple(max(0, c - 30) for c in fin[:3]), (tx + 2, h / 2), (tx * 0.2, ty + h * q), 1)
    if dorsal:
        D.polygon(s, fin, [(tx + bw * 0.3, h * 0.2), (tx + bw * 0.46, 0), (tx + bw * 0.58, h * 0.03), (tx + bw * 0.7, h * 0.2)])
        D.polygon(s, fin, [(tx + bw * 0.3, h * 0.8), (tx + bw * 0.4, h), (tx + bw * 0.6, h * 0.8)])
    if spines:
        for i in range(4):
            x = tx + bw * (0.25 + 0.15 * i)
            D.line(s, (60, 60, 60), (x, h * 0.2), (x - 3, 0), 2)
    D.ellipse(s, body, (tx, h * 0.12, bw, h * 0.76))
    if solidc:
        D.ellipse(s, dark, (tx + bw * 0.1, h * 0.13, bw * 0.78, h * 0.26))
        D.ellipse(s, body, (tx + bw * 0.06, h * 0.2, bw * 0.86, h * 0.3))
    if belly:
        D.ellipse(s, belly, (tx + bw * 0.12, h * 0.5, bw * 0.72, h * 0.34))
    if stripe:
        for i in range(n):
            sp = 0.2 if n < 4 else 0.62 / n
            y = h * (0.5 + (i - (n - 1) / 2) * sp)
            D.line(s, stripe, (tx * 0.55, y + (f * 2 - 1) * (0.6 if i % 2 else 0)), (tx + bw * (0.74 - abs(i - (n - 1) / 2) * 0.05), y), sw or max(2, h * 0.09))
    if solidc and h >= 14:
        D.arc(s, dark, (tx + bw * 0.6, h * 0.24, bw * 0.16, h * 0.52), -1.3, 1.3, 1)
        D.polygon(s, fin, [(tx + bw * 0.62, h * 0.56), (tx + bw * 0.44, h * (0.8 + 0.07 * f)), (tx + bw * 0.5, h * 0.55)])
        D.line(s, tuple(max(0, c - 90) for c in body), (tx + bw * 0.93, h * 0.58), (tx + bw * 0.99, h * 0.55), 1)
    if eye:
        r = max(2, h * (0.2 if big_eye else 0.13))
        ex, ey = tx + bw * 0.84, h * 0.42
        D.circle(s, eyecol, (ex, ey), r)
        D.circle(s, (10, 10, 20), (ex + r * 0.25, ey), max(1, r * 0.55))
        D.circle(s, (255, 255, 255), (ex + r * 0.05, ey - r * 0.3), max(0.5, r * 0.2))
    return s


def _blob(w, h, col, f=0, eyes=True, spikes=0, spcol=(255, 255, 255)):
    s = surf(w, h)
    cx, cy = w / 2, h / 2
    if spikes:
        for i in range(spikes):
            a = i * math.tau / spikes + f * 0.3
            D.line(s, spcol, (cx, cy), (cx + math.cos(a) * w * 0.5, cy + math.sin(a) * h * 0.5), 2)
    q = 0.78 if spikes else 1.0
    D.ellipse(s, col, (cx - w * q / 2 + f, cy - h * q / 2, w * q - 2 * f, h * q))
    D.ellipse(s, tuple(min(255, c + 50) for c in col), (cx - w * q * 0.3, cy - h * q * 0.34, w * q * 0.3, h * q * 0.22))
    if eyes:
        for dx in (-0.14, 0.14):
            D.circle(s, (255, 255, 255), (cx + w * dx, cy), max(2, w * 0.08))
            D.circle(s, (0, 0, 0), (cx + w * dx + 1, cy), max(1, w * 0.04))
    return s


def _make(k, f):
    if k == "nymph":
        s = surf(34, 20)
        D.ellipse(s, (96, 110, 50), (2, 6, 26, 10)); D.circle(s, (120, 130, 60), (28, 10), 6)
        D.circle(s, (20, 20, 20), (30, 8), 2)
        for i in range(3):
            x = 8 + i * 7
            D.line(s, (60, 70, 30), (x, 14), (x - 3 + f * 5, 19), 2)
        return s
    if k == "leech":
        s = surf(36, 16)
        pts = [(i * 4 + 2, 8 + math.sin(i * 0.9 + f * 3.1) * 4) for i in range(9)]
        D.lines(s, (70, 30, 40), False, pts, 6); D.circle(s, (120, 50, 60), pts[-1], 4)
        return s
    if k == "garfish":
        s = _fish(64, 12, (150, 190, 170), (220, 235, 220), (110, 150, 130), f=f, dorsal=False)
        D.line(s, (150, 190, 170), (52, 5), (63, 5), 2)
        return s
    if k == "kingfisher":
        s = surf(40, 44)
        D.ellipse(s, (30, 110, 210), (8, 2, 24, 26)); D.ellipse(s, (240, 140, 50), (12, 12, 16, 16))
        D.polygon(s, (30, 30, 30), [(16, 26), (24, 26), (20, 44)])
        D.polygon(s, (20, 80, 170), [(8, 8), (0, 2 + f * 10), (10, 18)]); D.polygon(s, (20, 80, 170), [(32, 8), (40, 2 + f * 10), (30, 18)])
        D.circle(s, (255, 255, 255), (16, 12), 3); D.circle(s, (255, 255, 255), (24, 12), 3)
        D.circle(s, (0, 0, 0), (16, 13), 1); D.circle(s, (0, 0, 0), (24, 13), 1)
        return s
    if k == "snakehead":
        s = _fish(72, 26, (86, 78, 50), (150, 140, 100), (60, 54, 36), (50, 44, 28), 1, f, eyecol=(255, 210, 60))
        D.line(s, (30, 20, 10), (58, 17), (70, 15), 2)
        return s
    if k == "knifefish":
        s = _fish(60, 26, (170, 170, 180), (215, 215, 225), (120, 120, 140), f=f, dorsal=False)
        for i in range(4):
            D.circle(s, (40, 40, 50), (16 + i * 9, 19), 3, 1)
        return s
    if k in ("net", "handnet"):
        s = surf(56, 64)
        c = (150, 120, 70) if k == "net" else (40, 150, 90)
        D.line(s, (110, 80, 40), (28, 0), (28, 22), 4)
        D.ellipse(s, c, (4, 18, 48, 16), 3)
        for i in range(6):
            D.line(s, c, (8 + i * 8, 26), (18 + i * 4, 62), 1)
        for j in range(4):
            D.line(s, c, (8 + j * 3, 34 + j * 8), (48 - j * 3, 34 + j * 8), 1)
        return s
    if k == "snail":
        s = surf(30, 24)
        D.ellipse(s, (190, 170, 110), (0, 14, 30, 10)); D.circle(s, (170, 110, 60), (13, 11), 10)
        D.circle(s, (120, 70, 40), (13, 11), 5, 2)
        D.line(s, (190, 170, 110), (26, 16), (28, 8 + f * 2), 2)
        return s
    if k == "goldfish":
        return _fish(58, 38, (250, 150, 40), (255, 200, 110), (255, 190, 90), f=f, big_eye=True)
    if k == "betta":
        s = _fish(56, 44, (150, 40, 170), (190, 80, 200), (70, 60, 210), f=f)
        D.polygon(s, (70, 60, 210), [(14, 8), (40, 0), (44, 12)]); D.polygon(s, (220, 60, 120), [(16, 36), (38, 44), (42, 32)])
        return s
    if k == "angelfish":
        s = surf(44, 60)
        D.polygon(s, (230, 230, 210), [(6, 30), (26, 0), (42, 30), (26, 60)])
        for x in (16, 26):
            D.line(s, (40, 40, 40), (x, 14), (x, 46), 3)
        D.circle(s, (255, 255, 255), (35, 28), 4); D.circle(s, (0, 0, 0), (36, 28), 2)
        D.polygon(s, (200, 200, 180), [(8, 30), (0, 22 + f * 4), (0, 38 + f * 4)])
        return s
    if k == "ich":
        return _blob(18, 18, (245, 245, 245), f, eyes=False, spikes=8)
    if k == "heater":
        s = surf(20, 48)
        D.rect(s, (60, 60, 70), (6, 0, 8, 10)); D.rect(s, (230, 230, 240), (4, 8, 12, 40), border_radius=5)
        D.rect(s, (255, 90, 40) if f else (255, 160, 60), (7, 22, 6, 22), border_radius=3)
        return s
    if k == "phage":
        s = surf(28, 40)
        D.polygon(s, (120, 220, 160), [(14, 0), (24, 7), (24, 17), (14, 24), (4, 17), (4, 7)])
        D.line(s, (90, 180, 130), (14, 24), (14, 33), 4)
        for dx in (-1, 1):
            D.lines(s, (90, 180, 130), False, [(14, 32), (14 + dx * 8, 30 + f * 2), (14 + dx * 12, 39)], 2)
        D.circle(s, (20, 60, 40), (10, 10), 2); D.circle(s, (20, 60, 40), (18, 10), 2)
        return s
    if k in ("fly", "b_fly"):
        z = 1 if k == "fly" else 3
        s = surf(30 * z, 24 * z)
        D.ellipse(s, (220, 230, 255, 170), (2 * z, (0 + f * 4) * z, 14 * z, 9 * z)); D.ellipse(s, (220, 230, 255, 170), (14 * z, (0 + f * 4) * z, 14 * z, 9 * z))
        D.ellipse(s, (150, 110, 60), (4 * z, 9 * z, 20 * z, 11 * z))
        D.circle(s, (200, 40, 40), (22 * z, 12 * z), 5 * z)
        for i in range(3):
            D.line(s, (60, 40, 20), ((9 + i * 4) * z, 9 * z), ((9 + i * 4) * z, 19 * z), z)
        if z == 3:
            D.polygon(s, (255, 215, 0), [(54, 20), (58, 6), (64, 16), (70, 4), (74, 18), (78, 8), (80, 22)])
        return s
    if k in ("mouse", "b_mouse", "mouse2"):
        z = 3 if k == "b_mouse" else 1
        s = surf(44 * z, 30 * z)
        col = (235, 235, 235) if k != "mouse2" else (150, 150, 160)
        D.lines(s, (240, 170, 180), False, [(8 * z, 20 * z), (2 * z, (14 + f * 6) * z), (0, 24 * z)], 2 * z)
        D.ellipse(s, col, (6 * z, 8 * z, 30 * z, 20 * z)); D.circle(s, col, (33 * z, 14 * z), 8 * z)
        D.circle(s, (240, 170, 180), (29 * z, 6 * z), 5 * z); D.circle(s, (240, 170, 180), (41 * z, 15 * z), 2 * z)
        D.circle(s, (200, 30, 30), (35 * z, 12 * z), 2 * z)
        D.circle(s, (150, 220, 255, 130), (34 * z, 13 * z), 11 * z, 2 * z)  # diving helmet
        D.line(s, (255, 200, 0), (30 * z, 3 * z), (30 * z, 0), 2 * z)
        if z == 3:
            D.polygon(s, (255, 215, 0), [(84, 10), (88, -2 + 6), (94, 12), (100, 2), (104, 14), (110, 6), (110, 20), (84, 20)])
        return s
    if k == "frog":
        s = surf(44, 36)
        D.ellipse(s, (120, 140, 90), (8, 8, 28, 20))
        for sy in (1, -1):
            y = 18 + sy * 9
            D.lines(s, (100, 120, 70), False, [(12, y), (2 + f * 6, y + sy * 6), (0 + f * 10, y + sy * 2)], 4)
        D.circle(s, (230, 230, 200), (32, 12), 4); D.circle(s, (230, 230, 200), (32, 24), 4)
        D.circle(s, (0, 0, 0), (33, 12), 2); D.circle(s, (0, 0, 0), (33, 24), 2)
        return s
    if k == "worm":
        s = surf(40, 14)
        pts = [(i * 4 + 2, 7 + math.sin(i * 1.1 + f * 3.1) * 4) for i in range(10)]
        D.lines(s, (240, 220, 200), False, pts, 4)
        return s
    if k in ("uvlamp", "laser"):
        s = surf(40, 18)
        D.rect(s, (70, 70, 80), (0, 0, 40, 10), border_radius=3)
        D.rect(s, (190, 120, 255) if k == "uvlamp" else (90, 255, 255), (4, 9, 32, 6 + f * 2), border_radius=2)
        return s
    if k in ("reject", "paper"):
        s = surf(34, 26)
        D.polygon(s, (250, 250, 245), [(0, 4 + f * 2), (34, 13), (0, 22 - f * 2), (8, 13)])
        D.line(s, (210, 30, 30), (6, 13), (26, 13), 3)
        return s
    if k in ("enu", "pipette"):
        hh = 70 if k == "pipette" else 30
        s = surf(22, hh)
        D.rect(s, (220, 225, 235), (6, 0, 10, hh - 16)); D.polygon(s, (240, 240, 200), [(6, hh - 16), (16, hh - 16), (12, hh), (10, hh)])
        D.rect(s, (60, 120, 220), (4, 0, 14, 6))
        if k == "enu":
            D.circle(s, (200, 230, 40), (11, hh - 4 + f * 2), 3)
        return s
    if k in ("drop", "bolt", "spine", "cheese", "maggot", "ink"):
        s = surf(16, 16)
        if k == "drop":
            D.circle(s, (200, 230, 40), (8, 9), 6); D.polygon(s, (200, 230, 40), [(8, 0), (3, 8), (13, 8)])
        elif k == "bolt":
            D.circle(s, (120, 255, 255), (8, 8), 6); D.circle(s, (255, 255, 255), (8, 8), 3)
        elif k == "spine":
            D.polygon(s, (240, 240, 220), [(0, 6), (16, 8), (0, 10)])
        elif k == "cheese":
            D.polygon(s, (255, 205, 60), [(0, 14), (16, 14), (16, 4)]); D.circle(s, (220, 160, 30), (11, 11), 2)
        elif k == "maggot":
            D.ellipse(s, (245, 240, 215), (1, 4 + f, 14, 8)); D.circle(s, (60, 40, 20), (13, 8), 1)
        else:
            D.circle(s, (200, 30, 30), (8, 8), 6)
        return s
    if k == "cyclops":
        s = _fish(52, 24, (205, 205, 190), (235, 235, 225), stripe=(60, 70, 130), n=2, f=f, eye=False)
        D.circle(s, (255, 255, 255), (46, 12), 6); D.circle(s, (200, 20, 20), (47, 12), 3)
        return s
    if k == "notail":
        s = surf(28, 22)
        D.ellipse(s, (210, 210, 195), (2, 2, 24, 18)); D.line(s, (60, 70, 130), (5, 11), (20, 11), 3)
        D.circle(s, (255, 255, 255), (21, 8), 3); D.circle(s, (0, 0, 0), (22, 8), 1)
        D.arc(s, (255, 255, 255), (0, 0, 28, 22), f * 3.0, f * 3.0 + 1.5, 1)
        return s
    if k == "medaka":
        return _fish(46, 20, (250, 190, 110), (255, 230, 180), (240, 160, 80), f=f, big_eye=True, eyecol=(180, 240, 255))
    if k == "bug":
        s = surf(28, 22)
        D.ellipse(s, (220, 40, 40), (4, 4, 20, 16)); D.line(s, (0, 0, 0), (14, 4), (14, 20), 2)
        for i in range(3):
            D.line(s, (0, 0, 0), (4, 8 + i * 5), (0, 6 + i * 6 + f * 2), 2); D.line(s, (0, 0, 0), (24, 8 + i * 5), (28, 6 + i * 6 + f * 2), 2)
        return s
    if k == "morpholino":
        s = surf(36, 14)
        D.polygon(s, (255, 120, 200), [(0, 3), (26, 3), (36, 7), (26, 11), (0, 11)])
        for i in range(4):
            D.line(s, (150, 40, 110), (4 + i * 6, 3), (4 + i * 6, 11), 2)
        D.polygon(s, (255, 220, 80), [(0, 4), (-6 + 2, 7), (0, 10)] if f else [(0, 5), (2, 7), (0, 9)])
        return s
    if k == "transposon":
        s = surf(30, 30)
        D.arc(s, (255, 200, 40), (3, 3 + f * 2, 24, 24), 0.4, 5.9, 5)
        D.circle(s, (255, 90, 90), (24, 9 + f * 2), 4); D.circle(s, (255, 90, 90), (24, 21 + f * 2), 4)
        D.circle(s, (0, 0, 0), (12, 13 + f * 2), 2); D.circle(s, (0, 0, 0), (18, 13 + f * 2), 2)
        return s
    if k in ("paralog", "paralog_s"):
        z = 40 if k == "paralog" else 24
        s = _blob(z, z, (90, 200, 255) if k == "paralog" else (160, 120, 255), f)
        return s
    if k == "repeat":
        s = surf(84, 20)
        for i in range(7):
            D.circle(s, (255, 70, 140) if i % 2 else (255, 190, 60), (8 + i * 11, 10 + math.sin(i + f * 3) * 3), 8)
        D.circle(s, (0, 0, 0), (76, 8), 2)
        return s
    if k == "vortex":
        s = surf(72, 72)
        for i in range(5):
            D.arc(s, (20, 10, 40) if i % 2 else (140, 90, 220), (i * 7, i * 7, 72 - i * 14, 72 - i * 14), f * 1.5 + i, f * 1.5 + i + 4.2, 5)
        D.circle(s, (0, 0, 0), (36, 36), 9)
        return s
    if k in ("fugu", "b_fugu"):
        z = 1 if k == "fugu" else 3
        s = _fish(40 * z, 26 * z, (190, 170, 90), (245, 240, 220), (150, 130, 60), f=f, big_eye=True)
        for i in range(4):
            D.circle(s, (60, 50, 30), ((14 + i * 5) * z, 9 * z), z)
        return s
    if k in ("fugu_puff", "b_fugu_puff"):
        z = 46 if k == "fugu_puff" else 150
        s = _blob(z, z, (200, 185, 110), f, spikes=14, spcol=(250, 245, 225))
        return s
    if k == "stickleback":
        return _fish(44, 20, (110, 150, 150), (230, 90, 70), f=f, spines=True)
    if k in ("scissors", "cut"):
        z = 1 if k == "scissors" else 2
        s = surf(34 * z, 34 * z)
        o = 5 * f
        D.line(s, (210, 220, 230), (10 * z, 10 * z), (33 * z, (20 + o) * z), 4 * z); D.line(s, (210, 220, 230), (10 * z, 24 * z), (33 * z, (14 - o) * z), 4 * z)
        D.circle(s, (230, 60, 60) if z == 1 else (40, 160, 70), (7 * z, 8 * z), 6 * z, 3 * z); D.circle(s, (230, 60, 60) if z == 1 else (40, 160, 70), (7 * z, 26 * z), 6 * z, 3 * z)
        return s
    if k == "myco":
        s = surf(26, 14)
        D.rect(s, (230, 80, 130), (1, 2 + f, 24, 9), border_radius=5); D.circle(s, (255, 180, 200), (8, 6 + f), 2)
        return s
    if k == "spore":
        return _blob(20, 20, (150, 230, 90), f, eyes=False, spikes=10, spcol=(90, 160, 50))
    if k in ("reviewer", "b_reviewer"):
        z = 1 if k == "reviewer" else 3
        s = surf(40 * z, 52 * z)
        D.ellipse(s, (50, 40, 70), (4 * z, 14 * z, 32 * z, 38 * z)); D.circle(s, (235, 200, 170), (20 * z, 14 * z), 11 * z)
        for dx in (-5, 5):
            D.circle(s, (255, 255, 255), ((20 + dx) * z, 13 * z), 4 * z); D.circle(s, (20, 20, 20), ((20 + dx) * z, 13 * z), 4 * z, z)
            D.circle(s, (0, 0, 0), ((20 + dx) * z, (13 + f) * z), z)
        D.line(s, (60, 30, 20), (15 * z, 21 * z), (25 * z, (20 - f) * z), z)
        D.line(s, (220, 30, 30), (34 * z, 26 * z), (40 * z, (40 + f * 3) * z), 3 * z)
        D.rect(s, (250, 250, 245), (6 * z, 30 * z, 14 * z, 16 * z))
        D.circle(s, (150, 220, 255, 110), (20 * z, 14 * z), 14 * z, 2 * z)
        return s
    if k == "killifish":
        return _fish(46, 22, (60, 190, 210), (250, 210, 80), (240, 80, 60), (240, 80, 60), 1, f)
    if k == "danionella":
        s = _fish(26, 10, (210, 240, 250, 120), None, (200, 230, 240, 90), f=f, dorsal=False)
        return s
    if k in ("organoid", "organoid_s"):
        z = 46 if k == "organoid" else 26
        s = surf(z, z)
        rnd = random.Random(z)
        for i in range(9):
            a = i * 0.7
            D.circle(s, (245, 170 + rnd.randint(0, 40), 190), (z / 2 + math.cos(a) * z * 0.22, z / 2 + math.sin(a) * z * 0.22 + f), z * 0.26)
        D.circle(s, (255, 255, 255), (z * 0.4, z * 0.45), z * 0.07); D.circle(s, (255, 255, 255), (z * 0.6, z * 0.45), z * 0.07)
        return s
    if k == "robot":
        s = surf(38, 40)
        D.rect(s, (170, 180, 200), (4, 8, 30, 24), border_radius=5); D.line(s, (170, 180, 200), (19, 8), (19, 1), 2)
        D.circle(s, (255, 60, 60) if f else (255, 200, 60), (19, 2), 3)
        D.rect(s, (20, 30, 50), (8, 13, 22, 10)); D.circle(s, (90, 255, 255), (14, 18), 3); D.circle(s, (90, 255, 255), (24, 18), 3)
        D.rect(s, (110, 120, 140), (10, 32, 6, 8)); D.rect(s, (110, 120, 140), (22, 32, 6, 8))
        return s
    if k == "debris":
        s = surf(30, 30)
        D.polygon(s, (170, 170, 185), [(4, 8), (16, 2 + f), (27, 10), (24, 24), (10, 28), (2, 18)])
        D.line(s, (110, 110, 125), (8, 10), (20, 20), 2)
        return s
    if k == "b_snakehead":
        s = _fish(190, 76, (86, 78, 50), (160, 150, 105), (56, 50, 32), (50, 44, 28), 2, f, eyecol=(255, 200, 40))
        D.polygon(s, (255, 255, 240), [(160, 50), (166, 60), (172, 50)]); D.polygon(s, (255, 255, 240), [(172, 50), (177, 59), (182, 49)])
        D.line(s, (30, 20, 10), (150, 50), (188, 46), 3)
        return s
    if k == "b_paw":
        s = surf(90, 300)
        D.rect(s, (235, 150, 60), (20, 0, 50, 250)); D.ellipse(s, (240, 160, 70), (5, 220, 80, 76))
        for i in range(5):
            D.line(s, (200, 110, 40), (20, i * 50 + 10), (70, i * 50 + 25), 6)
        for i in range(4):
            D.ellipse(s, (255, 190, 190), (14 + i * 17, 262, 12, 16)); D.polygon(s, (250, 250, 240), [(17 + i * 17, 290), (20 + i * 17, 300), (23 + i * 17, 290)])
        D.ellipse(s, (255, 190, 190), (30, 236, 30, 22))
        return s
    if k == "b_cat":
        s = surf(260, 150)
        D.ellipse(s, (235, 150, 60), (20, 30, 220, 150))
        D.polygon(s, (235, 150, 60), [(40, 60), (50, 0), (100, 40)]); D.polygon(s, (235, 150, 60), [(220, 60), (210, 0), (160, 40)])
        for x in (95, 165):
            D.ellipse(s, (190, 230, 90), (x - 22, 70, 44, 30)); D.ellipse(s, (10, 10, 10), (x - 5 + f * 2, 72, 10, 26))
        D.polygon(s, (255, 150, 160), [(120, 112), (140, 112), (130, 124)])
        for sy in (-8, 0, 8):
            D.line(s, (255, 255, 255), (100, 124 + sy), (40, 118 + sy * 2), 1); D.line(s, (255, 255, 255), (160, 124 + sy), (220, 118 + sy * 2), 1)
        return s
    return _blob(28, 28, (200, 80, 80), f)


def spr(k, f=0, flip=False):
    key = (k, f, flip)
    s = _cache.get(key)
    if s is None:
        s = fin(_make(k, f), k not in ("vortex", "danionella"))
        if flip:
            s = mirror(s)
        _cache[key] = s
    return s


# ---------------------------------------------------------------- player
ZF_PAL = {
    "": dict(back=(112, 104, 72), base=(228, 212, 158), stripe=(36, 56, 140), belly=(246, 244, 232),
             fin=(244, 226, 160), fstripe=(48, 70, 150), iris=(222, 180, 74)),
    "star": dict(back=(36, 140, 70), base=(160, 255, 140), stripe=(18, 128, 64), belly=(222, 255, 210),
                 fin=(190, 255, 170), fstripe=(30, 150, 76), iris=(255, 250, 140)),
    "gold": dict(back=(196, 144, 44), base=(255, 226, 120), stripe=(214, 162, 54), belly=(255, 246, 206),
                 fin=(255, 232, 150), fstripe=(206, 152, 48), iris=(255, 206, 90)),
}


def _clip(layer, mask):
    """Keep only the part of layer that lies inside mask (both work surfaces)."""
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return layer


def _zebrafish(w, h, f=0, pal=None):
    """A zebrafish facing right, w x h points: tapered body, blue stripes that follow the body
    and run on into the tail and anal fin, fin rays, gill cover and a gold-ringed eye."""
    p = ZF_PAL[""] if pal is None else pal
    s = surf(w, h)
    cy = h * 0.5
    x0, x1 = w * 0.26, w * 0.985            # caudal peduncle .. snout
    L, T = x1 - x0, h * 0.31                 # body length, greatest half-depth
    flex = (f * 2 - 1) * h * 0.06            # tail beat

    def half(u):                             # slim peduncle, deepest mid-body, rounded snout
        if u < 0.5:
            return T * (0.32 + 0.68 * math.sin(math.pi * u) ** 0.9)
        return T * math.sqrt(max(0.0, 1 - ((u - 0.5) / 0.5) ** 2.2)) ** 0.9

    us = [i / 28 for i in range(29)]
    top = [(x0 + u * L, cy - half(u) * 0.92) for u in us]
    bot = [(x0 + u * L, cy + half(u) * 1.08) for u in us]
    body = top + bot[::-1]

    def at(u, o):                            # a point on the flank: o = -1 back edge, +1 belly edge
        return x0 + u * L, cy + o * half(u) * (0.92 if o < 0 else 1.08)

    # fins first, so the body overlaps their roots
    fins = surf(w, h)
    tail = [(x0 + w * 0.03, cy - T * 0.3), (w * 0.03, cy - h * 0.40 + flex), (w * 0.07, cy - h * 0.34 + flex),
            (x0 - w * 0.11, cy + flex * 0.6), (w * 0.07, cy + h * 0.34 + flex), (w * 0.03, cy + h * 0.40 + flex),
            (x0 + w * 0.03, cy + T * 0.3)]
    ua, ub = 0.40, 0.60
    dorsal = [at(ua, -0.9), (at(ua, -1)[0] - w * 0.05, cy - h * 0.47), (at(ub, -1)[0] - w * 0.09, cy - h * 0.43), at(ub, -0.9)]
    ua, ub = 0.16, 0.50
    anal = [at(ua, 0.9), (at(ua, 1)[0] - w * 0.05, cy + h * 0.44), (at(ub, 1)[0] - w * 0.07, cy + h * 0.45), at(ub, 0.9)]
    for poly in (tail, dorsal, anal):
        D.polygon(fins, p["fin"], poly)
    rays = surf(w, h)                        # rays and stripes, kept inside the fins
    ray = tuple(max(0, c - 60) for c in p["fin"]) + (150,)
    for k in (-3, -1, 1, 3):
        D.line(rays, ray, (x0, cy + k * T * 0.07), (0, cy + k * h * 0.13 + flex), 0.3)
    for k in (-1, 1):                        # tail stripes, continuing the body stripes
        for o in (0.18, 0.42):
            D.line(rays, p["fstripe"], (x0, cy + k * o * T), (0, cy + k * (o * 2.2) * h * 0.3 + flex), 0.9)
    for o in (0.33, 0.66):                   # anal fin bands
        D.line(rays, p["fstripe"], (anal[0][0] + (anal[1][0] - anal[0][0]) * o, anal[0][1] + (anal[1][1] - anal[0][1]) * o),
               (anal[3][0] + (anal[2][0] - anal[3][0]) * o, anal[3][1] + (anal[2][1] - anal[3][1]) * o), 0.9)
    for k in range(4):
        q = ua + (ub - ua) * (k + 0.5) / 4
        D.line(rays, ray, at(q, 1), (at(q, 1)[0] - w * 0.05, cy + h * 0.45), 0.3)
    fins.blit(_clip(rays, fins.copy()), (0, 0))
    s.blit(fins, (0, 0))

    # body: gold-silver ground, olive back, blue stripes, pale belly
    D.polygon(s, p["base"], body)
    det = surf(w, h)
    D.polygon(det, p["back"] + (190,), [at(u, -1.2) for u in us] + [at(u, -0.64) for u in us[::-1]])
    for i, o in enumerate((-0.44, 0.0, 0.44)):          # bold blue stripes, gold between them
        end = 0.78 - 0.06 * abs(i - 1)
        su = [u for u in us if u <= end] + [end]
        wd = 0.14
        band = ([at(u, o - wd * (1 - 0.6 * (u / end) ** 6)) for u in su] +
                [at(u, o + wd * (1 - 0.6 * (u / end) ** 6)) for u in su[::-1]])
        D.polygon(det, p["stripe"], band)
    D.polygon(det, p["stripe"], [at(u, 0.72) for u in us if 0.12 < u < 0.62] + [at(u, 0.84) for u in us[::-1] if 0.12 < u < 0.62])
    D.polygon(det, p["belly"], [at(u, 0.86) for u in us if u > 0.3] + [at(u, 1.2) for u in us[::-1] if u > 0.3])
    D.polygon(det, (255, 255, 255, 80), [at(u, -0.86) for u in us if 0.2 < u < 0.85] + [at(u, -0.66) for u in us[::-1] if 0.2 < u < 0.85])
    gx = at(0.80, 0)[0]
    D.arc(det, tuple(max(0, c - 60) for c in p["base"]), (gx - h * 0.2, cy - T * 0.75, h * 0.3, T * 1.5), -1.25, 1.25, 0.5)
    mask = surf(w, h)
    D.polygon(mask, (255, 255, 255), body)
    s.blit(_clip(det, mask), (0, 0))

    # pectoral fin, eye, mouth
    px, py = at(0.74, 0.35)
    D.polygon(s, p["fin"] + (230,), [(px, py), (px - w * 0.11, py + h * (0.16 + 0.04 * f)), (px - w * 0.05, py - h * 0.02)])
    ex, ey = at(0.86, -0.22)
    r = max(1.3, h * 0.14)
    D.circle(s, p["iris"], (ex, ey), r)
    D.circle(s, (14, 16, 26), (ex + r * 0.12, ey), r * 0.62)
    D.circle(s, (255, 255, 255), (ex - r * 0.08, ey - r * 0.32), r * 0.24)
    D.line(s, tuple(max(0, c - 110) for c in p["base"]), at(0.95, 0.30), at(0.99, 0.12), 0.45)
    return s


def _player(variant, f):
    s = _zebrafish(40, 20, f, ZF_PAL.get(variant, ZF_PAL[""]))
    if variant == "crispr":
        D.circle(s, (90, 255, 255), (30, 4), 3)
        D.line(s, (90, 255, 255), (24, 2), (36, 6), 1)
    return s


def player(variant, f, ang, flip, z=1, upside_down=False):
    key = ("P", variant, f, ang, flip, z, upside_down)
    s = _cache.get(key)
    if s is None:
        with zoom(z):
            s = fin(_player(variant, f))
        if flip or upside_down:
            s = mirror(s, flip, upside_down)
        if ang:
            k = s.k
            s = adopt(pygame.transform.rotozoom(s, ang * 15, 1), k)     # rotozoom is smooth
        if variant == "casper":
            s.set_alpha(110)
        _cache[key] = s
    return s


def buddy(f, flip):
    key = ("B", f, flip)
    if key not in _cache:
        s = fin(_zebrafish(26, 13, f))
        _cache[key] = mirror(s) if flip else s
    return _cache[key]


# ---------------------------------------------------------------- icons
def letter(s, ch, center, size, col, bold=True):
    """Draw one character on a work surface, centred on its own ink (not on the line box),
    so narrow letters such as I sit in the middle like the others."""
    t = core.font(max(4, round(size * SS)), bold).render(ch, True, col)
    bb = t.get_bounding_rect()
    s.blit(t, (round(center[0] * SS - bb.centerx), round(center[1] * SS - bb.centery)))


def coin(ch, lit=True, d=30):
    """A D-A-N-I-O letter coin, d points across."""
    key = ("COIN", ch, lit, d)
    if key not in _cache:
        r = d / 2
        s = surf(d, d)
        face, rim, ink = ((255, 205, 60), (156, 96, 24), (96, 46, 10)) if lit else ((62, 72, 96), (40, 48, 68), (128, 142, 170))
        D.circle(s, rim, (r, r), r)
        D.circle(s, face, (r, r), r - max(1.5, d * 0.07))
        if lit:
            D.arc(s, (255, 240, 170), (r * 0.36, r * 0.36, r * 1.28, r * 1.28), 1.9, 3.0, max(1, d * 0.05))
        letter(s, ch, (r, r), d * 0.62, ink)
        _cache[key] = fin(s, False, lit)
    return _cache[key]


def _centred(s):
    """Move a drawing so its visible part sits exactly in the middle of the surface."""
    bb = s.get_bounding_rect(min_alpha=40)
    out = pygame.Surface(s.get_size(), A)
    out.blit(s, (s.get_width() // 2 - bb.centerx, s.get_height() // 2 - bb.centery))
    return out


def _heart(s, c, w, h, lit=True):
    """A shaded heart w x h points, centred on c."""
    pts = []
    for i in range(72):
        t = i / 72 * math.tau
        x, y = 16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((c[0] + x / 32 * w, c[1] - (y + 2.5) / 29.5 * h))
    base = (226, 50, 74) if lit else (62, 64, 86)
    D.polygon(s, base, pts)
    det = surf(s.get_width() / SS, s.get_height() / SS)
    top, n = c[1] - h * 0.5, 24
    for i in range(n):                          # darker towards the point
        D.rect(det, (60, 0, 20, int(150 * (i / n) ** 1.6)), (c[0] - w, top + h * i / n, w * 2, h / n + 0.2))
    if lit:
        D.ellipse(det, (255, 130, 150), (c[0] - w * 0.42, c[1] - h * 0.42, w * 0.34, h * 0.30))
        D.circle(det, (255, 228, 234), (c[0] - w * 0.27, c[1] - h * 0.27), w * 0.08)
    mask = surf(s.get_width() / SS, s.get_height() / SS)
    D.polygon(mask, (255, 255, 255), pts)
    s.blit(_clip(det, mask), (0, 0))


def _scissors(s):
    """CRISPR scissors, 24 x 24 points: steel blades, red finger rings, a pivot screw."""
    steel, edge, shine = (206, 216, 230), (112, 124, 146), (248, 250, 255)
    for sy in (-1, 1):
        tip = (23, 12 - sy * 4.2)
        piv = (11.5, 12)
        ring = (5, 12 + sy * 6)
        D.polygon(s, steel, [(piv[0] - 1, piv[1] + sy * 1.6), (piv[0] + 1.5, piv[1] - sy * 1.7), tip, (piv[0] + 3, piv[1] + sy * 0.9)])
        D.line(s, edge, (piv[0] + 1, piv[1] + sy * 0.2), tip, 0.5)
        D.line(s, shine, (piv[0] + 1.8, piv[1] - sy * 1.1), (tip[0] - 3, tip[1] + sy * 0.8), 0.45)
        D.line(s, steel, piv, (ring[0] + 2.2, ring[1] - sy * 2.2), 2.4)
        D.circle(s, (214, 54, 66), ring, 4.3, 2.0)
        D.arc(s, (255, 150, 150), (ring[0] - 3.4, ring[1] - 3.4, 6.8, 6.8), 1.6, 2.9, 0.7)
    D.circle(s, (90, 100, 120), (11.5, 12), 1.5)
    D.circle(s, (230, 236, 246), (11.2, 11.6), 0.55)


def icon(k, f=0):
    key = ("I", k, f)
    if key in _cache:
        return _cache[key]
    if k in ("heart", "heart0"):
        s = surf(22, 20)
        _heart(s, (11, 10), 22, 20, k == "heart")
    elif k == "food":
        s = surf(16, 16)
        D.ellipse(s, (255, 150, 60), (2, 4 + f, 12, 8)); D.line(s, (255, 200, 120), (3, 8 + f), (0, 3 + f), 2); D.line(s, (255, 200, 120), (13, 8 + f), (16, 3 + f), 2)
        D.circle(s, (60, 20, 0), (11, 7 + f), 1)
    elif k in ("page", "page0"):
        s = surf(26, 32)
        c = (255, 250, 225) if k == "page" else (70, 80, 100)
        D.rect(s, c, (2, 2, 22, 28), border_radius=2); D.rect(s, (40, 50, 80), (2, 2, 22, 28), 2, border_radius=2)
        if k == "page":
            for i in range(4):
                D.line(s, (90, 110, 170), (6, 9 + i * 5), (20, 9 + i * 5), 1)
            D.rect(s, (200, 60, 60), (2, 2, 5, 28))
    elif k in ("check", "check1"):
        s = surf(28, 60)
        D.line(s, (230, 230, 230), (6, 0), (6, 60), 3)
        c = (120, 120, 140) if k == "check" else (80, 230, 120)
        D.polygon(s, c, [(8, 4), (28, 12), (8, 22)])
    elif k == "goal":
        s = surf(96, 150)
        for i in range(3):
            D.ellipse(s, (255, 255, 255, 60 + 60 * i), (i * 8, i * 10 + f * 3, 96 - i * 16, 150 - i * 20 - f * 6), 4)
        D.ellipse(s, (120, 255, 220, 70), (24, 30, 48, 90))
    elif k == "bubble":
        s = surf(38, 38)
        D.circle(s, (200, 240, 255, 70), (19, 19), 18); D.circle(s, (255, 255, 255, 200), (19, 19), 18, 2)
        D.circle(s, (255, 255, 255, 220), (12, 11), 3)
    elif k.startswith("pw_"):
        s = surf(24, 24)
        n = k[3:]
        if n == "heart":
            _heart(s, (12, 12), 21, 19)
        elif n == "shoal":
            for (x, y), f in (((0, 1), 0), ((4, 12), 1)):        # two shoal-mates
                s.blit(_zebrafish(20, 10, f), (round(x * SS), round(y * SS)))
        elif n == "star":
            D.circle(s, (120, 255, 110), (12, 12), 10); D.circle(s, (220, 255, 210), (9, 9), 4)
        elif n == "casper":
            D.ellipse(s, (255, 255, 255, 170), (3, 2, 18, 20)); D.circle(s, (30, 30, 60), (9, 10), 2); D.circle(s, (30, 30, 60), (15, 10), 2)
        else:
            _scissors(s)
        s = _centred(s)
    else:
        s = surf(8, 8)
    s = fin(s, k not in ("goal", "bubble"), k not in ("goal", "bubble", "page", "page0"))
    _cache[key] = s
    return s


# ---------------------------------------------------------------- tiles & backgrounds
TS = 256


def clampc(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def sh(c, d):
    return tuple(clampc(v + d) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _kind(theme):
    return {1: "earth", 2: "gravel", 5: "circuit"}.get(theme, "panel")


def ground_tex(theme):
    """A 256x256 seamless ground texture; tiles are cut out of it."""
    key = ("GT", theme)
    if key in _cache:
        return _cache[key]
    g = THEMES[theme]["g"]
    rnd = random.Random(theme * 13 + 1)
    s = hsurf(TS, TS, False)
    s.fill(g)
    kind = _kind(theme)

    def wrap(fn, x, y):
        for dx in (-TS, 0, TS):
            for dy in (-TS, 0, TS):
                fn(x + dx, y + dy)
    if kind == "earth":
        for i in range(6):
            col = sh(g, -16 if i % 2 else 12)
            pts = [(x, i * TS / 6 + 12 + math.sin(x / TS * math.tau * 2 + i) * 6) for x in range(-8, TS + 9, 8)]
            PD.lines(s, col, False, pts, 11)
        for _ in range(700):
            x, y, d, r = rnd.randint(0, TS), rnd.randint(0, TS), rnd.randint(-28, 22), rnd.choice((1, 1, 2))
            wrap(lambda a, b: PD.circle(s, sh(g, d), (a, b), r), x, y)
        for _ in range(30):
            x, y, rx, ry = rnd.randint(0, TS), rnd.randint(0, TS), rnd.randint(4, 8), rnd.randint(3, 5)
            c = sh(g, rnd.randint(18, 40))
            wrap(lambda a, b: (PD.ellipse(s, sh(g, -45), (a - rx - 1, b - ry, rx * 2 + 2, ry * 2 + 2)),
                               PD.ellipse(s, c, (a - rx, b - ry, rx * 2, ry * 2 - 1)),
                               PD.ellipse(s, sh(c, 30), (a - rx + 2, b - ry + 1, rx, ry - 1))), x, y)
    elif kind == "gravel":
        s.fill(sh(g, -70))
        pal = [(214, 186, 140), (236, 220, 190), (184, 152, 112), (164, 124, 92), (206, 146, 104), (152, 172, 190), (226, 200, 150)]
        for _ in range(520):
            x, y, r = rnd.randint(0, TS), rnd.randint(0, TS), rnd.randint(4, 8)
            c = rnd.choice(pal)
            wrap(lambda a, b: (PD.circle(s, sh(c, -70), (a, b + 1), r + 1), PD.circle(s, c, (a, b), r),
                               PD.circle(s, sh(c, 34), (a - r // 3, b - r // 3), max(1, r // 3))), x, y)
    elif kind == "circuit":
        for _ in range(40):
            x, y = rnd.randrange(0, TS, 16), rnd.randrange(0, TS, 16)
            pts = [(x, y)]
            for i in range(rnd.randint(2, 4)):
                d = rnd.choice((32, 48, 64)) * rnd.choice((-1, 1))
                x, y = (x + d, y) if i % 2 == 0 else (x, y + d)
                pts.append((x, y))
            for dx in (-TS, 0, TS):
                for dy in (-TS, 0, TS):
                    q = [(a + dx, b + dy) for a, b in pts]
                    PD.lines(s, (0, 96, 112), False, q, 2)
                    PD.circle(s, (0, 190, 176), q[0], 3)
                    PD.circle(s, (0, 190, 176), q[-1], 3, 1)
        for _ in range(26):
            core.draw_text(s, rnd.choice("ACGT"), (rnd.randint(4, TS - 12), rnd.randint(4, TS - 12)), 11, (58, 84, 150), bold=True, shadow=False)
    else:
        for _ in range(260):
            x, y, ln = rnd.randint(0, TS), rnd.randint(0, TS), rnd.randint(8, 40)
            c = sh(g, rnd.randint(-9, 9))
            wrap(lambda a, b: PD.line(s, c, (a, b), (a + ln, b)), x, y)
        gs = 32 if theme == 3 else 64
        for q in range(0, TS, gs):
            PD.line(s, sh(g, -30), (q, 0), (q, TS), 2)
            PD.line(s, sh(g, -30), (0, q), (TS, q), 2)
            PD.line(s, sh(g, 18), (q + 2, 0), (q + 2, TS))
            PD.line(s, sh(g, 18), (0, q + 2), (TS, q + 2))
        if theme != 3:
            for x in range(0, TS, gs):
                for y in range(0, TS, gs):
                    for ox, oy in ((8, 8), (gs - 6, 8), (8, gs - 6), (gs - 6, gs - 6)):
                        PD.circle(s, sh(g, -40), (x + ox, y + oy + 1), 2)
                        PD.circle(s, sh(g, 45), (x + ox, y + oy), 2)
    _cache[key] = s
    return s


def tile(theme, tx, ty, mask):
    """Ground tile; mask bits: 1 = open above, 2 = right, 4 = below, 8 = left."""
    u, v = tx % 8, ty % 8
    key = ("TL", theme, u, v, mask)
    s = _cache.get(key)
    if s is not None:
        return s
    th = THEMES[theme]
    g, gt = th["g"], th["gt"]
    s = hsurf(TILE, TILE)
    s.blit(ground_tex(theme), (0, 0), (u * TILE, v * TILE, TILE, TILE))
    dark = sh(g, -62 if theme != 2 else -95)
    if mask & 4:
        PD.rect(s, dark, (0, 29, 32, 3))
    if mask & 2:
        PD.rect(s, dark, (29, 0, 3, 32))
    if mask & 8:
        PD.rect(s, dark, (0, 0, 3, 32))
        PD.line(s, sh(g, 22), (3, 0), (3, 31))
    if mask & 1:
        rnd = random.Random(u * 31 + v * 7 + theme)
        kind = _kind(theme)
        if kind == "earth":
            PD.rect(s, gt, (0, 0, 32, 8))
            for i in range(8):
                PD.polygon(s, gt, [(i * 4, 7), (i * 4 + 4, 7), (i * 4 + 2, 9 + rnd.randint(1, 5))])
            PD.rect(s, sh(gt, 42), (0, 0, 32, 3))
            for i in range(4):
                x = rnd.randint(1, 29)
                PD.line(s, sh(gt, -34), (x, 4), (x + 1, 8))
        elif kind == "gravel":
            hl = hsurf(32, 7)
            hl.fill((255, 250, 235, 70))
            s.blit(hl, (0, 0))
            PD.line(s, sh(gt, 15), (0, 0), (32, 0), 2)
        elif kind == "circuit":
            for i in range(9):
                gl = hsurf(32, 1)
                gl.fill(gt + (150 - i * 16,))
                s.blit(gl, (0, 3 + i))
            PD.rect(s, gt, (0, 0, 32, 3))
            PD.line(s, (220, 255, 250), (0, 0), (32, 0))
        else:
            PD.rect(s, gt, (0, 0, 32, 6))
            PD.line(s, sh(gt, 28), (0, 0), (32, 0), 2)
            PD.line(s, sh(g, -45), (0, 6), (32, 6), 2)
    if mask & 16:
        ov = hsurf(TILE, TILE)
        ov.fill((0, 0, 12, 58))
        s.blit(ov, (0, 0))
    n = pygame.Surface.get_width(s)          # rounded outer corners, cut at full resolution
    R = 6 * s.k
    for cx, cy, need in ((0, 0, 9), (n - 1, 0, 3), (0, n - 1, 12), (n - 1, n - 1, 6)):
        if mask & need == need:
            for i in range(R):
                for j in range(R):
                    if (R - i - 0.5) ** 2 + (R - j - 0.5) ** 2 > R * R:
                        pygame.Surface.set_at(s, (cx + (i if cx == 0 else -i), cy + (j if cy == 0 else -j)), (0, 0, 0, 0))
    _cache[key] = s
    return s


def crack():
    if "CRK" not in _cache:
        s = hsurf(TILE, TILE)
        s.fill((255, 240, 200, 46))
        for pts in ([(3, 5), (11, 12), (8, 19), (16, 25), (14, 30)], [(11, 12), (20, 9), (28, 14)], [(16, 25), (24, 22), (30, 27)], [(20, 9), (22, 2)]):
            PD.lines(s, (20, 14, 10, 230), False, pts, 2)
            PD.lines(s, (255, 250, 230, 120), False, [(x + 1, y + 1) for x, y in pts], 1)
        PD.rect(s, (255, 244, 190, 150), (0, 0, TILE, TILE), 1)
        _cache["CRK"] = s
    return _cache["CRK"]


def tuft(theme, v):
    key = ("TUFT", theme, v)
    if key not in _cache:
        rnd = random.Random(theme * 9 + v)
        s = hsurf(TILE, 10)
        gt = THEMES[theme]["gt"]
        if theme == 1:
            for i in range(9):
                x = rnd.randint(1, 30)
                hh = rnd.randint(3, 9)
                PD.line(s, sh(gt, rnd.randint(-30, 30)), (x, 10), (x + rnd.randint(-3, 3), 10 - hh), 2)
        else:
            for i in range(4):
                x = rnd.randint(3, 28)
                PD.circle(s, sh(THEMES[theme]["plant"], rnd.randint(-20, 30)), (x, 9), rnd.randint(2, 4))
        _cache[key] = s
    return _cache[key]


def lily(v):
    key = ("LILY", v)
    if key not in _cache:
        s = surf(34, 14)
        D.ellipse(s, (58, 150, 70), (1, 4, 32, 9))
        D.ellipse(s, (90, 180, 90), (4, 5, 22, 5))
        D.polygon(s, (0, 0, 0, 0), [(17, 9), (34, 4), (34, 9)])
        if v % 2:
            for a in range(5):
                D.ellipse(s, (255, 170, 200), (9 + a * 2.2, 1 + abs(a - 2), 6, 7))
            D.circle(s, (255, 230, 120), (16, 5), 2)
        _cache[key] = fin(s, True, False)
    return _cache[key]


def glass(mask):
    key = ("GL", mask)
    if key not in _cache:
        s = hsurf(TILE, TILE)
        s.fill((196, 236, 250, 74))
        for i in range(-32, 32, 13):
            PD.line(s, (255, 255, 255, 60), (i, 32), (i + 32, 0), 4)
        edge = (240, 252, 255, 215)
        if mask & 1:
            PD.rect(s, edge, (0, 0, 32, 4))
        if mask & 2:
            PD.rect(s, edge, (29, 0, 3, 32))
        if mask & 8:
            PD.rect(s, edge, (0, 0, 3, 32))
        if mask & 4:
            PD.rect(s, edge, (0, 29, 32, 3))
        _cache[key] = s
    return _cache[key]


def hazard(theme, f, flipped=False):
    key = ("HZ", theme, f, flipped)
    if key not in _cache:
        c = THEMES[theme]["haz"]
        s = surf(TILE, TILE)
        D.ellipse(s, sh(c, -70), (7, 24, 18, 9))
        for i in range(7):
            a = -math.pi * (i + 0.5) / 7
            ln = 22 - (i % 2) * 5 - f * 2
            mx, my = 16 + math.cos(a) * ln * 0.55 + (f * 2 - 1) * 1.5, 28 + math.sin(a) * ln * 0.55
            ex, ey = 16 + math.cos(a) * 13, 28 + math.sin(a) * ln
            D.lines(s, c, False, [(16, 28), (mx, my), (ex, ey)], 3)
            D.circle(s, (255, 244, 205), (ex, ey), 2)
        im = fin(s, True, False)
        _cache[key] = mirror(im, False, True) if flipped else im
    return _cache[key]


def background(theme):
    key = ("BG", theme)
    if key in _cache:
        return _cache[key]
    th = THEMES[theme]
    s = hsurf(W, H, False)
    for y in range(H):
        t = (y / H) ** 0.8
        s.fill(mix(th["wt"], th["wb"], t), (0, y, W, 1))
    _cache[key] = s
    return s


def parallax(theme):
    """Far silhouette layer (1920 px wide, scrolls slowly)."""
    key = ("PX", theme)
    if key in _cache:
        return _cache[key]
    th = THEMES[theme]
    PW = 1920
    s = hsurf(PW, H)
    rnd = random.Random(theme * 5 + 2)
    c1 = mix(th["wt"], th["wb"], 0.5) + (120,)
    c2 = mix(th["wt"], th["wb"], 0.8) + (150,)
    if theme == 1:
        for _ in range(16):
            x, ln = rnd.randint(40, PW - 40), rnd.randint(180, 400)
            pts = [(x + math.sin(i * 0.7 + x) * 16, i * ln / 8) for i in range(9)]
            PD.lines(s, c1, False, pts, rnd.randint(8, 16))
            PD.lines(s, c1, False, [pts[4], (pts[4][0] + rnd.choice((-50, 50)), pts[4][1] + 90)], 6)
        for _ in range(70):
            x, hh = rnd.randint(10, PW - 10), rnd.randint(80, 280)
            PD.polygon(s, c2, [(x - 5, H), (x + rnd.randint(-22, 22), H - hh), (x + 5, H)])
    elif theme == 2:
        for bx in (260, 1240):
            for dx, hh in ((0, 170), (46, 230), (104, 150)):
                PD.rect(s, c1, (bx + dx, H - hh - 50, 44, hh + 50))
                for k in range(3):
                    PD.rect(s, c1, (bx + dx + k * 17, H - hh - 62, 10, 12))
                PD.rect(s, th["wb"] + (140,), (bx + dx + 16, H - hh - 20, 12, 22), border_radius=6)
        for _ in range(26):
            x, hh = rnd.randint(20, PW - 20), rnd.randint(120, 300)
            for i in range(0, hh, 26):
                side = 1 if (i // 26) % 2 else -1
                PD.ellipse(s, c2, (x + side * 4 - (26 if side < 0 else 0), H - i - 30, 30, 15))
            PD.line(s, c2, (x, H), (x, H - hh), 4)
    elif theme == 5:
        for cy, k, amp in ((150, 5, 46), (400, 7, 34)):
            for x in range(0, PW, 6):
                a = x / PW * math.tau * k
                PD.circle(s, c1, (x, cy + math.sin(a) * amp), 5)
                PD.circle(s, c2, (x, cy - math.sin(a) * amp), 5)
                if x % 30 == 0:
                    PD.line(s, c1, (x, cy + math.sin(a) * amp), (x, cy - math.sin(a) * amp), 2)
    elif theme == 7:
        for x in range(0, PW, 96):
            PD.line(s, c1, (x, 120), (x + 96, 220), 5)
            PD.line(s, c1, (x, 220), (x + 96, 120), 5)
        PD.rect(s, c1, (0, 112, PW, 8))
        PD.rect(s, c1, (0, 220, PW, 8))
        for bx in range(120, PW, 480):
            PD.rect(s, c2, (bx, 300, 220, 120))
            for i in range(1, 6):
                PD.line(s, c1, (bx + i * 36, 300), (bx + i * 36, 420), 2)
            PD.line(s, c1, (bx, 360), (bx + 220, 360), 2)
            PD.line(s, c2, (bx + 110, 228), (bx + 110, 300), 6)
    else:
        for y in (170, 350):
            PD.rect(s, c1, (0, y, PW, 9))
        for x in range(0, PW, 240):
            PD.rect(s, c1, (x, 60, 11, H))
            for y in (40, 220, 400):
                if theme == 6:
                    for i in range(4):
                        PD.circle(s, c2, (x + 46 + i * 50, y + 96), 19, 4)
                else:
                    PD.rect(s, c2, (x + 26, y + 16, 192, 110), 4)
                    PD.line(s, c2, (x + 26, y + 40), (x + 218, y + 40), 2)
    _cache[key] = s
    return s


def rays():
    if "RAYS" not in _cache:
        rnd = random.Random(4)
        z = 2           # drawn at half the final size (it was a quarter: the edges showed steps)
        q = pygame.Surface(((W // 4 + 120) * z, H // 4 * z), A)
        for _ in range(9):
            x, wd = rnd.randint(0, W // 4 + 100), rnd.randint(6, 22)
            pts = [(x, 0), (x + wd, 0), (x + wd - 44, H // 4), (x - 66, H // 4)]
            pygame.draw.polygon(q, (255, 255, 240, rnd.randint(12, 26)), [(px * z, py * z) for px, py in pts])
        _cache["RAYS"] = scaled(q, ((W // 4 + 120) * 4, H))
    return _cache["RAYS"]


def vignette():
    """Darker screen edges, as an opaque layer to multiply with, plus the strips of the screen
    it actually darkens (its middle is plain white, so that part is never drawn)."""
    if "VIG" not in _cache:
        q = pygame.Surface((96, 54))
        clear = set()
        for y in range(54):
            for x in range(96):
                a = clampc((math.hypot((x - 47.5) / 48, (y - 26.5) / 27) - 0.72) * 210)
                q.set_at((x, y), tuple(255 - a * (255 - c) // 255 for c in (0, 8, 26)))
                if a == 0:
                    clear.add((x, y))
        best = (0, 48, 27)
        for mx in range(1, 48):
            for my in range(1, 27):
                if (96 - 2 * mx) * (54 - 2 * my) > best[0] and all(
                        (x, y) in clear for x in range(mx - 1, 97 - mx) for y in (my - 1, 54 - my)) and all(
                        (x, y) in clear for y in range(my - 1, 55 - my) for x in (mx - 1, 96 - mx)):
                    best = ((96 - 2 * mx) * (54 - 2 * my), mx, my)
        mx, my = best[1] * 10, best[2] * 10
        strips = [(0, 0, W, my), (0, H - my, W, my), (0, my, mx, H - 2 * my), (W - mx, my, mx, H - 2 * my)]
        _cache["VIG"] = (scaled(q, (W, H)), strips)
    return _cache["VIG"]


def draw_vignette(s):
    v, strips = vignette()
    for r in strips:
        s.blit(v, r[:2], r, special_flags=pygame.BLEND_RGB_MULT)


def surface_strip(f):
    key = ("WS", f)
    if key not in _cache:
        s = hsurf(TILE, 12)
        for x in range(TILE):
            y = 2 + math.sin((x / TILE + f / 4) * math.tau) * 1.5
            PD.line(s, (255, 255, 255, 60), (x, y + 2), (x, 11))
            PD.line(s, (245, 252, 255, 235), (x, y), (x, y + 1.5))
        _cache[key] = s
    return _cache[key]


SKY_H = 200
SKY_TOP = 110


def sky(theme):
    """Backdrop seen above the water. 2*W wide so it can scroll; repeats every W."""
    key = ("SKY", theme)
    if key in _cache:
        return _cache[key]
    th = THEMES[theme]
    c = th["sky"]
    SKY_H = 760 if theme == 7 else 200
    s = hsurf(W, SKY_H, False)
    rnd = random.Random(theme + 50)
    if theme == 1:
        for y in range(SKY_H):
            s.fill(mix((250, 150, 96), (255, 226, 170), y / SKY_H), (0, y, W, 1))
        for r, a in ((70, 40), (54, 70), (40, 255)):
            g = hsurf(r * 2, r * 2)
            PD.circle(g, (255, 244, 206, a), (r, r), r)
            s.blit(g, (700 - r, 74 - r))
        pts = [(x, 150 + math.sin(x / W * math.tau * 3) * 14 + math.sin(x / W * math.tau * 7) * 6) for x in range(0, W + 1, 12)]
        PD.polygon(s, (150, 120, 96), pts + [(W, SKY_H), (0, SKY_H)])
        for px in (90, 300, 420, 610, 860):
            hh = rnd.randint(60, 100)
            PD.line(s, (96, 76, 60), (px, 172), (px + 8, 172 - hh), 5)
            for a in (-2.6, -2.0, -1.2, -0.5, 0.1):
                PD.line(s, (70, 96, 60), (px + 8, 172 - hh), (px + 8 + math.cos(a) * 34, 172 - hh + math.sin(a) * 18 + 14), 4)
    elif theme == 2:
        s.fill(c)
        for x in range(0, W, 60):
            PD.rect(s, sh(c, -14), (x, 0, 30, SKY_H))
            for y in range(14, 150, 34):
                PD.polygon(s, sh(c, -40), [(x + 15, y), (x + 21, y + 8), (x + 15, y + 16), (x + 9, y + 8)])
        PD.rect(s, (120, 84, 60), (0, 150, W, 50))
        PD.rect(s, (150, 108, 76), (0, 150, W, 6))
        for fx in (200, 680):
            PD.rect(s, (110, 74, 44), (fx, 26, 150, 96))
            PD.rect(s, (150, 196, 214), (fx + 9, 35, 132, 78))
            PD.ellipse(s, (240, 150, 60), (fx + 40, 62, 44, 22))
            PD.polygon(s, (240, 150, 60), [(fx + 42, 73), (fx + 26, 62), (fx + 26, 84)])
    elif theme in (3, 4, 6):
        s.fill(c)
        for x in range(0, W, 96):
            PD.line(s, sh(c, -18), (x, 0), (x, SKY_H), 2)
        if theme == 3:
            PD.rect(s, (120, 96, 70), (0, 132, W, 8))
            for x in range(30, W, 80):
                col = rnd.choice([(150, 190, 170), (200, 170, 110), (170, 150, 200), (190, 200, 210)])
                if rnd.random() < 0.5:
                    PD.polygon(s, col, [(x - 16, 132), (x + 16, 132), (x + 5, 100), (x + 5, 84), (x - 5, 84), (x - 5, 100)])
                else:
                    PD.rect(s, col, (x - 10, 92, 20, 40), border_radius=3)
                    PD.rect(s, sh(col, -40), (x - 6, 84, 12, 8))
        elif theme == 4:
            for x in range(40, W, 320):
                g = hsurf(240, 40)
                PD.ellipse(g, (255, 255, 255, 70), (0, 0, 240, 40))
                s.blit(g, (x - 10, 14))
                PD.rect(s, (255, 255, 255), (x, 26, 220, 10), border_radius=5)
            PD.rect(s, sh(c, -50), (0, 150, W, 8))
            for x in range(0, W, 160):
                PD.rect(s, sh(c, -50), (x, 60, 8, SKY_H))
        else:
            for x in range(30, W, 240):
                for y in range(22, 120):
                    PD.line(s, mix((120, 180, 240), (200, 228, 250), (y - 22) / 98), (x, y), (x + 180, y))
                PD.rect(s, (255, 255, 255), (x - 4, 18, 188, 106), 5, border_radius=8)
                PD.line(s, (255, 255, 255), (x + 90, 20), (x + 90, 122), 4)
                PD.ellipse(s, (255, 255, 255), (x + 20, 40, 50, 16))
            PD.rect(s, sh(c, -30), (0, 150, W, 6))
    else:
        s.fill(c)
        if theme == 5:
            for x in range(0, W, 40):
                PD.line(s, (22, 30, 70), (x, 0), (x, SKY_H))
            for y in range(0, SKY_H, 40):
                PD.line(s, (22, 30, 70), (0, y), (W, y))
            for _ in range(40):
                PD.circle(s, (0, 150, 150), (rnd.randrange(0, W, 40), rnd.randrange(0, SKY_H, 40)), 3)
        else:
            for _ in range(6):
                g = hsurf(300, 160)
                PD.ellipse(g, (rnd.randint(40, 110), 40, rnd.randint(90, 160), 22), (0, 0, 300, 160))
                s.blit(g, (rnd.randint(-100, W - 200), rnd.randint(-60, 60)))
            PD.circle(s, (60, 130, 220), (480, SKY_H + 1250), 1320)
            PD.circle(s, (150, 210, 255), (480, SKY_H + 1250), 1320, 5)
        for _ in range(170 if theme == 5 else 520):
            PD.circle(s, (255, 255, 255), (rnd.randint(0, W), rnd.randint(0, SKY_H - 44)), rnd.choice((1, 1, 1, 2)))
    if theme != 7:      # 110 px of head-room above the level, for when the camera follows a leap
        tall = hsurf(W, SKY_H + SKY_TOP, False)
        tall.blit(scaled(s.subsurface((0, 0, W, 1)), (W, SKY_TOP)), (0, 0))
        tall.blit(s, (0, SKY_TOP))
        s = tall
    out = hsurf(W * 2, s.get_height(), False)
    out.blit(s, (0, 0))
    out.blit(s, (W, 0))
    _cache[key] = out
    return out


def backdrop(theme):
    """Water gradient, far silhouettes and light rays baked into one opaque, 1920-px-wide
    picture. One plain copy per frame instead of three transparent layers."""
    key = ("BACK", theme)
    if key not in _cache:
        far = parallax(theme)
        s = hsurf(far.get_width(), H, False)
        for x in range(0, far.get_width(), W):
            s.blit(background(theme), (x, 0))
        s.blit(far, (0, 0))
        for x in (-110, W - 110):
            s.blit(rays(), (x, 0))
        _cache[key] = s
    return _cache[key]


def _radial(r, alpha, rgb=(0, 0, 12)):
    """A smooth radial alpha gradient 2r points across: alpha(d) for d = distance / r."""
    n = 64
    q = pygame.Surface((n, n), A)
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5) / (n / 2)
            q.set_at((x, y), rgb + (clampc(alpha(d)),))
    return scaled(q, (r * 2, r * 2))


def dark_hole(r):
    """Darkness with a soft see-through hole, for dark levels in the browser."""
    key = ("HOLE", r)
    if key not in _cache:
        _cache[key] = _radial(r, lambda d: 255 * min(1, d) ** 2.2)
    return _cache[key]


def light_mask(r):
    key = ("L", r)
    if key not in _cache:
        _cache[key] = _radial(r, lambda d: 235 * (1 - d ** 2.2) if d < 1 else 0, (0, 0, 0))
    return _cache[key]


# ---------------------------------------------------------------- world map
MW, MH = 1920, 960
LAND = [
 [(-168, 66), (-156, 71), (-128, 70), (-110, 68), (-95, 72), (-82, 73), (-78, 63), (-64, 60), (-56, 52), (-66, 45), (-70, 42), (-76, 35), (-81, 31), (-80, 25), (-84, 30), (-90, 29), (-97, 26), (-97, 20), (-88, 21), (-87, 16), (-83, 10), (-78, 8), (-80, 7), (-85, 11), (-92, 15), (-97, 16), (-105, 20), (-110, 23), (-114, 31), (-117, 33), (-124, 40), (-124, 48), (-135, 58), (-150, 60), (-165, 55), (-158, 58), (-165, 62)],
 [(-45, 60), (-22, 70), (-20, 80), (-60, 82), (-70, 77), (-52, 68)],
 [(-78, 8), (-72, 12), (-62, 10), (-52, 5), (-50, 0), (-35, -6), (-39, -15), (-41, -22), (-48, -27), (-57, -37), (-65, -42), (-68, -52), (-72, -53), (-75, -45), (-72, -30), (-70, -18), (-76, -14), (-81, -5), (-80, 2)],
 [(-9, 37), (-9, 43), (-1, 44), (-4, 48), (3, 51), (8, 54), (8, 57), (11, 56), (13, 54), (20, 55), (24, 58), (29, 60), (23, 60), (21, 63), (25, 65), (22, 66), (18, 63), (17, 60), (12, 56), (11, 59), (6, 58), (5, 62), (14, 68), (26, 71), (40, 67), (44, 66), (60, 69), (70, 73), (90, 76), (110, 77), (130, 71), (160, 70), (180, 69), (180, 65), (172, 61), (160, 60), (163, 56), (156, 51), (156, 57), (142, 59), (135, 54), (141, 52), (140, 47), (132, 43), (127, 40), (129, 36), (126, 34), (126, 38), (121, 39), (122, 31), (120, 26), (110, 21), (106, 19), (108, 12), (105, 9), (100, 13), (103, 2), (98, 8), (94, 16), (91, 22), (86, 20), (80, 15), (80, 10), (77, 8), (73, 17), (70, 21), (67, 24), (57, 25), (56, 27), (50, 30), (48, 29), (52, 24), (56, 26), (59, 22), (55, 17), (45, 13), (43, 13), (39, 21), (35, 28), (36, 36), (28, 36), (26, 39), (29, 41), (24, 41), (23, 38), (20, 40), (19, 42), (13, 45), (18, 40), (16, 38), (12, 44), (9, 44), (3, 43), (0, 39), (-5, 36)],
 [(-6, 35), (10, 37), (11, 33), (20, 31), (32, 31), (34, 28), (37, 21), (43, 12), (51, 12), (48, 5), (40, -3), (39, -10), (35, -20), (33, -26), (27, -34), (19, -34), (15, -27), (12, -17), (13, -8), (9, -1), (9, 4), (-4, 5), (-8, 4), (-13, 8), (-17, 14), (-16, 22), (-10, 29)],
 [(114, -22), (122, -18), (130, -12), (136, -12), (137, -16), (142, -11), (146, -19), (153, -27), (150, -37), (144, -38), (138, -35), (131, -32), (124, -33), (116, -35), (114, -28)],
 [(-5, 50), (1, 51), (1, 53), (-2, 56), (-3, 58), (-6, 57), (-3, 54), (-5, 52)], [(-10, 52), (-6, 52), (-6, 55), (-9, 54)],
 [(130, 31), (132, 34), (137, 35), (141, 37), (141, 41), (145, 43), (142, 45), (140, 42), (139, 38), (136, 36), (131, 34)],
 [(44, -16), (49, -13), (50, -17), (47, -25), (44, -22)], [(95, 5), (104, -2), (106, -6), (102, -4), (97, 2)],
 [(109, 1), (117, 6), (118, 1), (114, -4), (110, -2)], [(106, -6), (114, -7), (114, -8), (106, -8)],
 [(131, -1), (141, -3), (150, -9), (141, -9), (134, -4)], [(80, 9), (82, 7), (80, 6)],
 [(173, -35), (178, -38), (174, -41), (171, -44), (167, -46), (171, -41)], [(-24, 65), (-14, 66), (-14, 64), (-22, 63)],
]


def ll(lon, lat):
    return (lon + 180) / 360 * MW, (90 - lat) / 180 * MH


def world_map():
    if "MAP" in _cache:
        return _cache["MAP"]
    s = hsurf(MW, MH, False)
    for y in range(0, MH, 6):
        t = abs(y / MH - 0.45) * 2
        s.fill((int(40 - 20 * t), int(110 - 50 * t), int(170 - 50 * t)), (0, y, MW, 6))
    for lon in range(-180, 181, 30):
        PD.line(s, (60, 130, 185), ll(lon, 90), ll(lon, -90), 1)
    for lat in range(-60, 91, 30):
        PD.line(s, (60, 130, 185), ll(-180, lat), ll(180, lat), 1)
    for poly in LAND:
        pts = [ll(*p) for p in poly]
        PD.polygon(s, (20, 70, 110), [(x + 3, y + 5) for x, y in pts])
    rndw = random.Random(8)
    for _ in range(900):
        x, y = rndw.randint(0, MW), rndw.randint(60, MH - 120)
        PD.arc(s, (70, 140, 195), (x, y, 16, 8), 0.3, 2.8, 1)
    for poly in LAND:
        pts = [ll(*p) for p in poly]
        PD.polygon(s, (52, 132, 186), pts, 22)
        for p in pts:
            PD.circle(s, (52, 132, 186), p, 11)
    for poly in LAND:
        pts = [ll(*p) for p in poly]
        PD.polygon(s, (84, 166, 206), pts, 10)
        for p in pts:
            PD.circle(s, (84, 166, 206), p, 5)
    land = hsurf(MW, MH)
    for poly in LAND:
        PD.polygon(land, (255, 255, 255), [ll(*p) for p in poly])
    tint = hsurf(MW, MH, False)
    rnd2 = random.Random(21)
    for y in range(0, MH, 4):
        lat = abs(90 - y / MH * 180)
        col = mix((96, 170, 92), (196, 186, 128), max(0, 1 - abs(lat - 24) / 9)) if lat < 40 else mix((100, 160, 96), (228, 234, 228), min(1, (lat - 40) / 34))
        tint.fill(col, (0, y, MW, 4))
    for _ in range(5000):
        x, y = rnd2.randint(0, MW - 1), rnd2.randint(0, MH - 1)
        PD.circle(tint, sh(tint.get_at((x, y)), rnd2.randint(-14, 10)), (x, y), rnd2.randint(2, 7))
    land.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    s.blit(land, (0, 0))
    for poly in LAND:
        PD.polygon(s, (236, 224, 172), [ll(*p) for p in poly], 3)
    for river in ([(78, 30.5), (80, 27.5), (83, 25.5), (87, 25), (89, 23.5), (90, 22)], [(82, 30), (90, 29.5), (95, 28), (92, 26), (90, 24)],
                  [(31, 2), (32, 15), (31, 24), (31, 31)], [(-72, -5), (-62, -3), (-52, -1.5)], [(-95, 46), (-90, 38), (-90, 30)],
                  [(8, 47.5), (7, 50), (5, 52)], [(10, 48), (17, 48), (22, 44.5), (29, 45)], [(100, 34), (110, 31), (120, 31.5)],
                  [(-123, 46), (-119, 46.5), (-117, 44)]):
        PD.lines(s, (72, 150, 205), False, [ll(*p) for p in river], 2)
    for lon, lat, rw, rh in ((35, 43.5, 8, 2.2), (51, 41.5, 2.5, 5)):
        x, y = ll(lon, lat)
        PD.ellipse(s, (40, 110, 165), (x - rw * 5.33, y - rh * 5.33, rw * 10.66, rh * 10.66))
    PD.rect(s, (235, 240, 250), (0, MH - 110, MW, 110))
    PD.rect(s, (6, 8, 26), (0, 0, MW, 112))
    rnd = random.Random(9)
    for _ in range(300):
        PD.circle(s, (255, 255, 255), (rnd.randint(0, MW), rnd.randint(0, 108)), 1)
    PD.line(s, (120, 160, 220), (0, 112), (MW, 112), 2)
    _cache["MAP"] = s
    return s

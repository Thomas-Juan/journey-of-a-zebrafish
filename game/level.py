# -*- coding: utf-8 -*-
"""Seeded procedural level generation and tile rendering."""
import math
import random
import pygame
import gfx
from core import W, H, TILE, T_WATER, T_SOLID, T_AIR, T_HAZ, T_GLASS, T_CRACK
from worlds import ETYPES

POWERS_BY_WORLD = {1: ["heart", "shoal", "shoal"], 2: ["heart", "shoal", "shoal"], 3: ["heart", "shoal", "star"],
                   4: ["heart", "shoal", "star"], 5: ["heart", "shoal", "star", "casper"],
                   6: ["heart", "shoal", "star", "casper", "crispr", "crispr"], 7: ["heart", "shoal", "star", "casper", "crispr"]}


class Level:
    def __init__(self, spec):
        self.spec = spec
        self._chunks = {}
        self.world = spec["world"]
        self.theme = spec.get("theme", self.world)
        self.style = spec["style"]
        self.zero_g = bool(spec.get("zero_g"))
        self.rng = random.Random("zf" + spec["id"])
        self.w = spec["len"]
        self.h = {"open": 26, "space": 20}.get(self.style, 17)
        self.air = {"river": 3, "tank": 3, "arena": 4}.get(self.style, 0)
        self.spawns, self.items, self.zones, self.nooks, self.arenas = [], [], [], [], []
        self.signs = spec.get("signs", [])
        self.t = [bytearray([T_AIR if y < self.air else T_WATER] * self.w) for y in range(self.h)]
        if self.style == "arena":
            self._arena()
        elif self.style == "space":
            self._space()
        else:
            self._terrain()
            self._populate()
        self.pw, self.ph = self.w * TILE, self.h * TILE
        self._decor()

    # ------------------------------------------------------------ queries
    def get(self, tx, ty):
        if tx < 0 or tx >= self.w or ty >= self.h:
            return T_SOLID
        if ty < 0:
            return T_AIR if (self.air or self.zero_g) else T_SOLID
        return self.t[ty][tx]

    def solid(self, tx, ty):
        return self.get(tx, ty) in (T_SOLID, T_GLASS, T_CRACK)

    def at(self, px, py):
        return self.get(int(px // TILE), int(py // TILE))

    def rect_hits(self, x, y, w, h):
        """True if the box centred on x,y overlaps a solid tile."""
        x0, x1 = int((x - w / 2) // TILE), int((x + w / 2 - 0.01) // TILE)
        y0, y1 = int((y - h / 2) // TILE), int((y + h / 2 - 0.01) // TILE)
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.solid(tx, ty):
                    return True
        return False

    def free(self, tx, ty, w=1, h=1):
        return all(self.get(tx + i, ty + j) == T_WATER for i in range(w) for j in range(h))

    def top_water(self, x):
        for y in range(self.h):
            if self.t[y][x] == T_WATER:
                return y
        return None

    def floor_spot(self, x):
        """Lowest water row in column x that has solid ground beneath."""
        for y in range(self.h - 1, 0, -1):
            if self.t[y][x] == T_WATER and self.solid(x, y + 1):
                return y
        return None

    def put(self, x, y, v):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.t[y][x] = v
            for c in {(x - 1) // CHUNK, x // CHUNK, (x + 1) // CHUNK}:
                self._chunks.pop(c, None)      # redraw the cached tiles around the change

    # ------------------------------------------------------------ terrain
    def _terrain(self):
        r, w, h, A = self.rng, self.w, self.h, self.air
        self.fl, self.cl = [], []
        f, c = h - 3, (0 if A else 2)
        for x in range(w):
            if x % 4 == 0 and 10 < x < w - 12:
                f = max(h - 5, min(h - 2, f + r.choice([-1, 0, 0, 1])))
                if not A:
                    c = max(1, min(3 if self.style == "cave" else 2, c + r.choice([-1, 0, 0, 1])))
            self.fl.append(f)
            self.cl.append(c)
            for y in range(f, h):
                self.t[y][x] = T_SOLID
            for y in range(c):
                self.t[y][x] = T_SOLID
        self.wall = T_GLASS if self.style == "tank" else T_SOLID
        forced = dict(self.spec.get("force", []))
        x = 13
        segs = self.spec["segs"] + (["jets"] if A else []) + ["vault", "draft"]
        while x < w - 22:
            name = r.choice(segs)
            for fx, fn in forced.items():
                if x <= fx < x + 14:
                    name, x = fn, fx
            if name in ("leap",) and not A:
                name = "pillars"
            wd = getattr(self, "_s_" + name)(x)
            x += wd + r.randint(3, 6)

    def _top(self, x):
        return self.air if self.air else self.cl[x]

    def _col(self, x, y0, y1, v=T_SOLID):
        for y in range(y0, y1):
            if 0 <= x < self.w and 0 <= y < self.h and self.t[y][x] in (T_WATER, T_AIR):
                self.t[y][x] = v

    def _s_open(self, x):
        return self.rng.randint(12, 18)

    def _s_arena(self, x):
        self.arenas.append((x, x + 20))
        return 20

    def _s_pillars(self, x):
        r = self.rng
        n = r.randint(3, 4)
        for i in range(n):
            px = x + 1 + i * 5
            top = max(self._top(q) for q in range(px - 2, px + 4))
            bot = min(self.fl[q] for q in range(px - 2, px + 4))
            gap = r.randint(3, 4)
            for dx in (0, 1):
                if i % 2 == 0:
                    self._col(px + dx, top + gap, bot)
                else:
                    self._col(px + dx, top, bot - gap)
        return n * 5 + 1

    def _s_shaft(self, x):
        for dx in (0, 1):
            px = x + 2 + dx
            self._col(px, self._top(px) - (1 if self.air else 0), min(self.fl[x:x + 6]) - 3, self.wall)
            px = x + 9 + dx
            self._col(px, max(self._top(q) for q in range(x + 7, x + 13)) + 3, self.fl[px], self.wall)
        self.nooks.append((x + 6, self._top(x + 6) + 1))
        return 13

    def _s_leap(self, x):
        up = 2 if (self.world >= 3 and self.rng.random() < 0.5) else 1
        for dx in (0, 1):
            self._col(x + 3 + dx, self.air - up, self.fl[x + 3 + dx], self.wall)
        return 8

    def _s_jets(self, x):
        """A bubble jet that launches the fish over a wall (inspired by barrel cannons)."""
        A = self.air
        for dx in (0, 1):
            self._col(x + 6 + dx, A - 2, self.fl[x + 6 + dx], self.wall)
        self.items.append(dict(kind="jet", x=(x + 1.5) * TILE, y=(A + 3.5) * TILE, dx=0.6, dy=-0.8))
        for i in range(7):
            self.items.append(dict(kind="food", x=(x + 3.5 + i * 1.3) * TILE, y=(A - 0.5 - 2.6 * math.sin(i / 6 * math.pi)) * TILE))
        return 14

    def _s_vault(self, x):
        """A sealed chamber behind cracked blocks: dash into them to break in."""
        f = min(self.fl[x + 2:x + 9])
        top = max(self._top(q) for q in range(x + 2, x + 9))
        if f - 4 - top < 3:
            return self._s_open(x)
        for px in range(x + 3, x + 8):
            self._col(px, f - 4, self.fl[px])
        for px in range(x + 4, x + 7):
            for y in (f - 3, f - 2):
                self.put(px, y, T_WATER)
        for y in (f - 3, f - 2):
            self.put(x + 3, y, T_CRACK)
        for i in range(3):
            self.items.append(dict(kind="food", x=(x + 4.5 + i) * TILE, y=(f - 1.6) * TILE))
        if self.rng.random() < 0.5:
            self.items.append(dict(kind="power", name=self.rng.choice(POWERS_BY_WORLD[self.world]), x=(x + 6.5) * TILE, y=(f - 2.5) * TILE))
        self.nooks.append((x + 5, f - 3))
        return 10

    def _s_draft(self, x):
        """A rising and a sinking column of water."""
        for dx, fy in ((2, -1.7), (8, 1.7)):
            px = x + dx
            top = max(self._top(q) for q in range(px, px + 3))
            bot = min(self.fl[px:px + 3])
            self.zones.append((pygame.Rect(px * TILE, top * TILE, 3 * TILE, (bot - top) * TILE), 0, fy))
            if fy > 0:
                for q in range(px, px + 3):
                    if self.get(q, self.fl[q] - 1) == T_WATER:
                        self.put(q, self.fl[q] - 1, T_HAZ)
            for i in range(4):
                self.items.append(dict(kind="food", x=(px + 1.5) * TILE, y=(top + 1.5 + i * 1.4) * TILE))
        return 13

    def _s_tunnel(self, x):
        r = self.rng
        wd = r.randint(12, 17)
        top = self._top(x)
        lo, hi = top + 1, min(self.fl[x:x + wd + 1]) - 4
        row = r.randint(lo, max(lo, hi))
        for i in range(1, wd):
            px = x + i
            if i % 3 == 0:
                row = max(lo, min(max(lo, hi), row + r.choice([-1, 0, 1])))
            for y in range(self._top(px), self.fl[px]):
                if not (row <= y < row + 3):
                    self._col(px, y, y + 1)
        return wd

    def _s_islands(self, x):
        r = self.rng
        wd = 18
        for i in range(r.randint(2, 3)):
            px = x + 1 + i * 6
            top, bot = self._top(px), self.fl[px]
            py = r.randint(top + 3, max(top + 3, bot - 5))
            for dx in range(r.randint(2, 4)):
                self._col(px + dx, py, py + r.randint(1, 2))
        cx = x + r.randint(4, 12)
        cy = r.randint(self._top(cx) + 4, self.fl[cx] - 4)
        if all(self.free(cx + i, cy + j) for i in range(-1, 5) for j in range(-2, 2)):
            for i in range(4):
                self.put(cx + i, cy + 1, T_SOLID)
            self.put(cx, cy, T_SOLID)
            self.put(cx + 3, cy, T_SOLID)
            self.nooks.append((cx + 1.5, cy))
        return wd

    def _s_current(self, x):
        wd = self.rng.randint(14, 20)
        fx = self.rng.choice([-1.3, -1.3, 1.5])
        self.zones.append((pygame.Rect(x * TILE, 0, wd * TILE, self.h * TILE), fx, 0))
        for px in range(x + 3, x + wd - 3):
            self._col(px, self.fl[px] - 2, self.fl[px])
        return wd

    def _s_hazard(self, x):
        r = self.rng
        wd = r.randint(12, 18)
        for i in range(1, wd - 1):
            px = x + i
            bot = self.fl[px]
            if r.random() < 0.6 and self.get(px, bot - 1) == T_WATER:
                self.put(px, bot - 1, T_HAZ)
            if i % 4 == 2:
                top = self._top(px)
                ln = r.randint(2, max(2, bot - top - 6))
                for y in range(top, top + ln):
                    if self.get(px, y) == T_WATER:
                        self.put(px, y, T_HAZ)
        return wd

    # ------------------------------------------------------------ contents
    def _free_swim(self, x0, x1, tries=30, size=2):
        r = self.rng
        for _ in range(tries):
            x = r.randint(x0, max(x0, x1 - size))
            top = self.top_water(x)
            if top is None:
                continue
            y = r.randint(top + 1, self.h - 3)
            if self.free(x, y, size, size):
                return x, y
        return None

    def _populate(self):
        r, w, sp = self.rng, self.w, self.spec
        self.start = (4 * TILE, (self._top(4) + 4) * TILE)
        self.goal_x = (w - 6) * TILE
        self.items.append(dict(kind="goal", x=self.goal_x, y=(self._top(w - 6) + (self.fl[w - 6] - self._top(w - 6)) / 2) * TILE))
        # checkpoints
        self.checks = []
        for frac in (0.34, 0.67):
            for x in range(int(w * frac), int(w * frac) + 25):
                fy = self.floor_spot(x)
                if fy is not None and self.free(x, fy - 2, 1, 3) and self.free(x - 1, fy - 1, 3, 1):
                    self.items.append(dict(kind="check", x=(x + 0.5) * TILE, y=(fy + 1) * TILE, on=False))
                    self.checks.append(x)
                    break
        # pages
        used = set()
        for i, frac in enumerate((0.2, 0.5, 0.8)):
            tx = w * frac
            best = None
            for k, (nx, ny) in enumerate(self.nooks):
                if k not in used and abs(nx - tx) < 30 and self.get(int(nx), int(ny)) == T_WATER:
                    if best is None or abs(nx - tx) < abs(self.nooks[best][0] - tx):
                        best = k
            if best is not None:
                used.add(best)
                nx, ny = self.nooks[best]
            else:
                nx = ny = None
                for dx in range(0, 30):
                    for x in (int(tx) + dx, int(tx) - dx):
                        fy = self.floor_spot(x) if 8 < x < w - 8 else None
                        if fy is not None and self.free(x, fy):
                            nx, ny = x, fy
                            break
                    if nx is not None:
                        break
            self.items.append(dict(kind="page", idx=i, x=(nx + 0.5) * TILE, y=(ny + 0.5) * TILE))
        # knowledge gate half-way through
        self.items.append(dict(kind="gate", x=(int(w * 0.5) + 4.5) * TILE, y=0))
        # D-A-N-I-O letters
        for i, frac in enumerate((0.12, 0.3, 0.47, 0.64, 0.86)):
            pos = self._free_swim(int(w * frac), int(w * frac) + 8, 40, 1)
            if pos:
                self.items.append(dict(kind="letter", idx=i, x=(pos[0] + 0.5) * TILE, y=(pos[1] + 0.5) * TILE))
        # enemies
        pool = sp["pool"]
        for x0 in range(15, w - 14, 10):
            if any(abs(x0 + 5 - c) < 6 for c in self.checks):
                continue
            d = sp["dens"] * (1.7 if any(a <= x0 < b for a, b in self.arenas) else 1.0)
            d *= 0.6 + 0.6 * x0 / w
            n = int(d) + (r.random() < d - int(d))
            for _ in range(n):
                self._spawn(r.choice(pool), x0, x0 + 10)
        # food trails
        x = 9
        while x < w - 10:
            pos = self._free_swim(x, x + 3, 12, 1)
            if pos:
                bx, by = pos
                ph = r.random() * 6
                for i in range(r.randint(5, 8)):
                    fx, fy = (bx + 0.5 + i * 0.9) * TILE, (by + 0.5 + math.sin(ph + i * 0.7) * 1.2) * TILE
                    if self.at(fx, fy) == T_WATER and not self.rect_hits(fx, fy, 18, 18):
                        self.items.append(dict(kind="food", x=fx, y=fy))
            x += r.randint(8, 13)
        # power-ups
        kinds = POWERS_BY_WORLD[self.world]
        x = r.randint(24, 34)
        while x < w - 16:
            pos = self._free_swim(x, x + 6, 20, 2)
            if pos:
                k = r.choice(kinds)
                if sp.get("buddies") and r.random() < 0.7:
                    k = "shoal"
                if sp.get("hearts") and r.random() < 0.7:
                    k = "heart"
                self.items.append(dict(kind="power", name=k, x=(pos[0] + 1) * TILE, y=(pos[1] + 1) * TILE))
            x += r.randint(34, 50) if not (sp.get("buddies") or sp.get("hearts")) else r.randint(20, 30)
        for a, b in self.arenas:
            pos = self._free_swim(a + 8, a + 12, 20, 2)
            if pos:
                self.items.append(dict(kind="power", name=r.choice(kinds), x=(pos[0] + 1) * TILE, y=(pos[1] + 1) * TILE))

    def _spawn(self, k, x0, x1):
        r = self.rng
        et = ETYPES[k]
        place, hh = et[7], et[4]
        for _ in range(12):
            x = r.randint(x0, x1 - 1)
            if not (0 < x < self.w - 1):
                continue
            if place == "swim":
                sz = 5 if k == "vortex" else 3 if et[6] else 2
                sz = max(sz, -(-et[3] // TILE), -(-et[4] // TILE))
                pos = self._free_swim(x, x + 2, 6, sz)
                if pos:
                    self.spawns.append((k, (pos[0] + sz / 2) * TILE, (pos[1] + sz / 2) * TILE))
                    return
            elif place == "floor":
                fy = self.floor_spot(x)
                if fy is not None and self.free(x - 1, fy, 3, 1) and self.free(x, fy - 1):
                    self.spawns.append((k, (x + 0.5) * TILE, (fy + 1) * TILE - hh / 2 - 1))
                    return
            else:
                top = self.top_water(x)
                if top is None or not self.free(x, top, 1, 5) or not self.free(x - 1, top, 3, 2):
                    continue
                if top > 0 and self.t[top - 1][x] == T_AIR:
                    if place == "ceil":
                        continue
                    y = top * TILE - hh / 2 - 12
                else:
                    y = top * TILE + hh / 2
                self.spawns.append((k, (x + 0.5) * TILE, y))
                return

    def _arena(self):
        w, h = self.w, self.h
        for y in range(h):
            for x in range(w):
                if x in (0, w - 1) or y >= h - 2:
                    self.t[y][x] = T_SOLID
        self.start = (5 * TILE, 10 * TILE)
        self.goal_x = 10 ** 9
        self.checks = []

    def _space(self):
        r, w, h = self.rng, self.w, self.h
        for y in range(h):
            for x in range(w):
                self.t[y][x] = T_SOLID if (y < 1 or y >= h - 1 or x == 0 or x == w - 1) else T_AIR

        def blob(cx, cy, rad):
            for y in range(int(cy - rad), int(cy + rad) + 1):
                for x in range(int(cx - rad), int(cx + rad) + 1):
                    if 0 < x < w - 1 and 0 < y < h - 1 and (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= rad * rad:
                        self.t[y][x] = T_WATER
        blob(5, h / 2, 5)
        self.start = (5 * TILE, h / 2 * TILE)
        x, self.checks, centers = 5.0, [], [(5, h / 2, 5)]
        while x < w - 22:
            rad = r.randint(3, 6)
            x += centers[-1][2] + rad + r.randint(1, 5)
            cy = r.randint(rad + 1, h - rad - 2)
            blob(x, cy, rad)
            centers.append((x, cy, rad))
        blob(w - 8, h / 2, 6)
        self.goal_x = (w - 8) * TILE
        self.items.append(dict(kind="goal", x=self.goal_x, y=h / 2 * TILE))
        n = len(centers)
        for frac in (0.34, 0.67):
            cx, cy, rad = centers[int(n * frac)]
            self.items.append(dict(kind="check", x=cx * TILE, y=(cy + 1) * TILE, on=False))
            self.checks.append(int(cx))
        self.items.append(dict(kind="gate", x=(centers[n // 2][0] + centers[n // 2][2] + 1) * TILE, y=0))
        for i, frac in enumerate((0.12, 0.3, 0.47, 0.64, 0.86)):
            cx, cy, rad = centers[int(n * frac)]
            self.items.append(dict(kind="letter", idx=i, x=cx * TILE, y=(cy - rad + 1) * TILE))
        for i, frac in enumerate((0.2, 0.5, 0.8)):
            cx, cy, rad = centers[int(n * frac)]
            py = 3 if cy > h / 2 else h - 4
            blob(cx, py + 0.5, 1.6)
            self.items.append(dict(kind="page", idx=i, x=(int(cx) + 0.5) * TILE, y=(py + 0.5) * TILE))
        for cx, cy, rad in centers[1:]:
            d = self.spec["dens"] * rad / 4
            for _ in range(int(d) + (r.random() < d - int(d))):
                k = r.choice(self.spec["pool"])
                if ETYPES[k][7] == "swim":
                    self.spawns.append((k, (cx + r.uniform(-rad, rad) * 0.5) * TILE, (cy + r.uniform(-rad, rad) * 0.5) * TILE))
            for i in range(5):
                a = i * 1.256 + cx
                self.items.append(dict(kind="food", x=(cx + math.cos(a) * rad * 0.55) * TILE, y=(cy + math.sin(a) * rad * 0.55) * TILE))
            if r.random() < 0.3:
                self.items.append(dict(kind="power", name=r.choice(POWERS_BY_WORLD[7]), x=cx * TILE, y=cy * TILE))
        for i in range(len(centers) - 1):
            (ax, ay, _), (bx, by, _) = centers[i], centers[i + 1]
            for t in (0.4, 0.5, 0.6):
                self.items.append(dict(kind="food", x=(ax + (bx - ax) * t) * TILE, y=(ay + (by - ay) * t) * TILE))

    # ------------------------------------------------------------ test helper
    def reachable(self):
        """Flood fill from start; True if the goal column can be reached."""
        if self.style == "arena":
            return True
        sx, sy = int(self.start[0] // TILE), int(self.start[1] // TILE)
        gx = int(self.goal_x // TILE)
        seen, stack = {(sx, sy)}, [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if x >= gx:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or nx < 0 or nx >= self.w or ny >= self.h or ny < -3:
                    continue
                t = self.get(nx, ny)
                if t in (T_SOLID, T_GLASS):
                    continue
                if t == T_AIR and not self.zero_g and ny < self.air - 3:
                    continue
                seen.add((nx, ny))
                stack.append((nx, ny))
        return False

    # ------------------------------------------------------------ drawing
    def _decor(self):
        """Swaying plants on the floor (purely cosmetic, separate RNG)."""
        r = random.Random("decor" + self.spec["id"])
        self.plants = []
        self.motes = [(r.randint(0, W), r.randint(0, H), r.uniform(0.3, 0.9), r.uniform(0, 6)) for _ in range(46)]
        self.lilies = []
        if self.style == "space":
            return
        if self.air and self.theme in (1, 2, 3):
            for x in range(3, self.w - 3):
                if r.random() < 0.09 and self.get(x, self.air) == T_WATER and self.get(x, self.air - 1) == T_AIR:
                    self.lilies.append(((x + r.random()) * TILE, r.randint(0, 3)))
        for x in range(1, self.w - 1):
            if r.random() < 0.34:
                fy = self.floor_spot(x)
                if fy is not None and self.free(x, fy - 1):
                    self.plants.append(((x + r.uniform(0.15, 0.85)) * TILE, (fy + 1) * TILE, r.randint(3, 8), r.uniform(0, 6), r.randint(0, 2)))

    def _chunk(self, ci):
        """Tiles are drawn once into 16-tile-wide strips and reused every frame.
        Returns (surface, hazard tiles, water-surface tiles)."""
        ch = self._chunks.get(ci)
        if ch is not None:
            return ch
        if len(self._chunks) > 7:
            del self._chunks[max(self._chunks, key=lambda k: abs(k - ci))]
        surf = pygame.Surface((CHUNK * TILE, self.h * TILE + PAD), pygame.SRCALPHA)
        sky = gfx.sky(self.theme)
        sh = sky.get_height()
        solid = self.solid
        haz, top, glass = [], [], []
        for ty in range(self.h):
            py = ty * TILE + PAD
            for tx in range(ci * CHUNK, ci * CHUNK + CHUNK):
                px = (tx - ci * CHUNK) * TILE
                t = self.get(tx, ty)
                if t == T_WATER:
                    if self.get(tx, ty - 1) == T_AIR:
                        top.append((tx * TILE, ty * TILE - 3, tx))
                elif t == T_AIR:
                    surf.blit(sky, (px, py), ((tx * TILE) % W, min(sh - TILE, ty * TILE + gfx.SKY_TOP), TILE, TILE))
                elif t == T_SOLID or t == T_GLASS or t == T_CRACK:
                    m = ((not solid(tx, ty - 1)) | (not solid(tx + 1, ty)) << 1 | (not solid(tx, ty + 1)) << 2 | (not solid(tx - 1, ty)) << 3)
                    if m == 0 and solid(tx, ty - 2) and solid(tx - 1, ty - 1) and solid(tx + 1, ty - 1):
                        m = 16
                    if tx <= 0:
                        m &= 7
                    if tx >= self.w - 1:
                        m &= 13
                    if ty >= self.h - 1:
                        m &= 11
                    if t == T_GLASS:          # see-through: drawn every frame, not baked in
                        glass.append((tx * TILE, ty * TILE, m))
                        continue
                    surf.blit(gfx.tile(self.theme, tx, ty, m), (px, py))
                    if t == T_CRACK:
                        surf.blit(gfx.crack(), (px, py))
                    elif (m & 1) and t == T_SOLID and self.theme in (1, 2) and m != 16:
                        surf.blit(gfx.tuft(self.theme, (tx * 5 + ty) % 4), (px, py - 9))
                elif t == T_HAZ:
                    hang = solid(tx, ty - 1) or (self.get(tx, ty - 1) == T_HAZ and not solid(tx, ty + 1))
                    haz.append((tx * TILE - 1, ty * TILE - 1, hang))
        # everything baked in is fully opaque or fully clear, so the strip can use a colour key,
        # which is much faster to draw than per-pixel transparency
        fast = pygame.Surface(surf.get_size())
        fast.fill(KEY)
        fast.blit(surf, (0, 0))
        fast.set_colorkey(KEY, pygame.RLEACCEL)
        ch = self._chunks[ci] = (fast, haz, top, glass)
        return ch

    def draw(self, s, cx, cy, tick):
        back = gfx.backdrop(self.theme)
        ox = -int(cx * 0.3) % back.get_width()
        s.blit(back, (ox - back.get_width(), 0))
        s.blit(back, (ox, 0))
        for mx, my, par, phs in self.motes:
            x = int((mx - cx * par + math.sin(tick * 0.01 + phs) * 14) % (W - 2))
            y = int((my - cy * par - tick * 0.12 * par) % H)
            s.set_at((x, y), (225, 245, 255))
            if par > 0.6:
                s.set_at((x + 1, y), (190, 225, 245))
        for bx, by, n, phs, kind in self.plants:
            x0 = bx - cx
            if -50 < x0 < W + 50:
                im = plant_frame(self.theme, kind, n, int((tick * 0.035 + phs) / math.tau * PLANT_FRAMES) % PLANT_FRAMES)
                s.blit(im, (x0 - im.get_width() // 2, by - cy - im.get_height()))
        if cy < 0 and (self.air or self.zero_g):       # the camera is above the level: sky only
            s.blit(gfx.sky(self.theme), (0, 0), (int(cx) % W, max(0, int(cy) + gfx.SKY_TOP), W, int(-cy) + 1))
        f = (tick // 20) % 2
        span = CHUNK * TILE
        shown = [self._chunk(ci) for ci in range(int(cx // span), int((cx + W) // span) + 1)]
        for k, ch in enumerate(shown):
            s.blit(ch[0], ((int(cx // span) + k) * span - cx, -PAD - cy))
        for surf, haz, top, glass in shown:
            for gx, gy, m in glass:
                if -TILE < gx - cx < W:
                    s.blit(gfx.glass(m), (gx - cx, gy - cy))
            for hx, hy, hang in haz:
                s.blit(gfx.hazard(self.theme, f, hang), (hx - cx, hy - cy))
            for wx, wy, tx in top:
                if -TILE < wx - cx < W:
                    s.blit(gfx.surface_strip((tick // 9 + tx) % 4), (wx - cx, wy - cy))
        if self.lilies:
            sy = self.air * TILE - cy - 7
            for lx, v in self.lilies:
                if -40 < lx - cx < W + 40:
                    s.blit(gfx.lily(v), (lx - cx - 17, sy + math.sin(tick * 0.05 + lx) * 1.5))


CHUNK = 16            # tiles per cached strip
KEY = (255, 0, 254)   # colour that means 'see-through' in a cached strip
PAD = 10              # room above row 0 for grass tufts
PLANT_FRAMES = 12
_plants = {}


def plant_frame(theme, kind, n, fr):
    """One animation frame of a swaying plant, drawn once and cached."""
    key = (theme, kind, n, fr)
    im = _plants.get(key)
    if im is None:
        pc = gfx.THEMES[theme]["plant"]
        pd = gfx.sh(pc, -55)
        w, hgt = 96, n * 13 + 12
        im = pygame.Surface((w, hgt), pygame.SRCALPHA)
        x0, y0, ph = w // 2, hgt, fr / PLANT_FRAMES * math.tau
        for blade in range(1 if kind == 0 else 3):
            seg = 13 - blade * 3
            pts = [(x0 + (blade - 1) * 5 * (kind > 0), y0)]
            for k in range(1, n - blade + 1):
                sway = math.sin(ph + k * 0.55 + blade) * k * 1.7
                pts.append((x0 + (blade - 1) * (5 + k * 1.5) * (kind > 0) + sway, y0 - k * seg))
            if len(pts) > 1:
                pygame.draw.lines(im, pd, False, pts, 6 if kind == 0 else 4)
                pygame.draw.lines(im, pc, False, pts, 3 if kind == 0 else 2)
                if kind == 0:
                    for k in range(1, len(pts) - 1, 2):
                        px, py = pts[k]
                        pygame.draw.ellipse(im, pc, (px - (11 if k % 4 == 1 else -1), py - 4, 11, 6))
                if kind == 2:
                    pygame.draw.circle(im, gfx.sh(pc, 60), pts[-1], 3)
        _plants[key] = im
    return im

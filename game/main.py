# -*- coding: utf-8 -*-
# /// script
# dependencies = [
#   "pygame-ce",
#   "numpy",
# ]
# ///
"""Journey of a Zebrafish - entry point, menus, world map, saving.

The same file runs on the desktop (python main.py) and in a browser (pygbag build)."""
import asyncio
import math
import os
import random
import sys

# the stage is drawn at twice its size and SDL scales it to the window: smoothly, not in blocks
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")
# pygame only allows fractional window scaling when a hint with this literal name is set; without
# it a window smaller than the 1920 x 1080 picture is scaled by 0 and stays black
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "1")
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
import gfx
import audio
import quiz
import certificate
from core import dr, hsurf, W, H, draw_text, draw_wrapped, panel, clamp, DIFF_NAMES
from worlds import LEVELS, INDEX, WORLDS, ENDING
from facts import FACTS, QUIZ, fact_id
from play import Play
import level as level_mod

TOTAL_PAGES = sum(len(v) for w, v in FACTS.items() if w)
UPGRADES = [
    ("heart", "Stronger heart", "+1 maximum heart", [120, 260, 450]),
    ("dash", "Mauthner reflex", "Dash recharges faster", [150, 320]),
    ("magnet", "Lateral line", "Food drifts towards you", [200]),
    ("shoal", "Shoaling instinct", "Start each level with a shoal-mate", [180, 380]),
]


def fmt_time(sec):
    sec = int(sec)
    return "%d:%02d:%02d" % (sec // 3600, sec // 60 % 60, sec % 60) if sec >= 3600 else "%d:%02d" % (sec // 60, sec % 60)


def star(s, x, y, r, col):
    pts = [(x + math.sin(i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45), y - math.cos(i * math.pi / 5) * (r if i % 2 == 0 else r * 0.45)) for i in range(10)]
    dr.polygon(s, col, pts)
    dr.polygon(s, (20, 30, 50), pts, 1)


_dims = {}


def dim(s, a=150):
    d = _dims.get(a)
    if d is None:
        d = _dims[a] = hsurf(W, H)
        d.fill((4, 10, 24, a))
    s.blit(d, (0, 0))


class Menu:
    """Vertical menu with a highlight bar. items: list of labels, or (label, hint) pairs."""
    def __init__(self, items):
        self.items = [it if isinstance(it, tuple) else (it, "") for it in items]
        self.i = 0

    def update(self, inp):
        if "up" in inp.pressed:
            self.i = (self.i - 1) % len(self.items)
            audio.sfx("blip")
        if "down" in inp.pressed:
            self.i = (self.i + 1) % len(self.items)
            audio.sfx("blip")
        if "ok" in inp.pressed:
            audio.sfx("food")
            return self.items[self.i][0]
        return None

    @property
    def hint(self):
        return self.items[self.i][1]

    def draw(self, s, x, y, size=22, gap=40, width=300):
        for k, (it, _) in enumerate(self.items):
            sel = k == self.i
            if sel:
                bar = hsurf(width, gap - 6)
                dr.rect(bar, (255, 240, 150, 46), bar.get_rect(), border_radius=8)
                dr.rect(bar, (255, 240, 150, 230), bar.get_rect(), 2, border_radius=8)
                s.blit(bar, (x, y + k * gap - 3))
                s.blit(gfx.buddy(0, False), (x + 10, y + k * gap - 3 + (gap - 6) / 2 - 7.5))
            draw_text(s, it, (x + 46, y + k * gap - 3 + (gap - 6) / 2), size, (255, 244, 170) if sel else (214, 226, 240), bold=sel, mid=True)


class Title:
    overlay = False

    def __init__(self, app):
        self.app = app
        self.has = None
        self.t = 0
        audio.music("map")

    def update(self, inp):
        self.t += 1
        audio.music("map")
        last = self.app.data["opt"].get("last")
        has = last is not None and self.app.data["slots"][last] is not None
        if has != self.has:
            self.has = has
            self.menu = Menu((["Continue"] if has else []) + ["New game / load", "Options"] + ([] if core.WEB else ["Quit"]))
        c = self.menu.update(inp)
        if c == "Continue":
            self.app.slot_i = last
            self.app.push(Map(self.app))
        elif c == "New game / load":
            self.app.push(Slots(self.app))
        elif c == "Options":
            self.app.push(Options(self.app))
        elif c == "Quit":
            self.app.running = False

    def draw(self, s):
        back = gfx.backdrop(1)
        s.blit(back, (-(self.t * 0.2) % 1920 - 1920, 0))
        s.blit(back, (-(self.t * 0.2) % 1920, 0))
        for i in range(9):
            x = (self.t * (1 + i % 3 * 0.5) + i * 140) % (W + 100) - 50
            y = 120 + i * 44 + math.sin(self.t * 0.03 + i) * 12
            s.blit(gfx.player("", (self.t // 8 + i) % 2, 0, False), (x, y))
        draw_text(s, "Journey of a Zebrafish", (W / 2, 70), 58, (255, 255, 255), center=True, bold=True)
        draw_text(s, "from the rivers of India to the frontiers of biomedical research", (W / 2, 144), 19, (200, 235, 245), center=True)
        n = len(self.menu.items)
        panel(s, (320, 222, 320, 30 + n * 44), alpha=205)
        self.menu.draw(s, 335, 240, 22, 44, 290)
        draw_text(s, "Arrows / WASD: move    SPACE / ENTER: select    ESC: back" + ("" if core.WEB else "    F11: fullscreen"), (W / 2, H - 34), 14, (200, 220, 235), center=True)


class Options:
    overlay = True

    def __init__(self, app):
        self.app, self.i = app, 0

    def rows(self):
        o = self.app.data["opt"]
        r = [("music", "Music   " + "|" * o["music"] + "." * (10 - o["music"])),
             ("sfx", "Sound   " + "|" * o["sfx"] + "." * (10 - o["sfx"])),
             ("full", "Fullscreen: " + ("on" if o["full"] else "off"))]
        if not core.WEB:
            r.append(("sharp", "Graphics: " + ("sharp" if o["sharp"] else "fast")))
        return r + [("back", "Back")]

    def update(self, inp):
        o = self.app.data["opt"]
        rows = self.rows()
        n = len(rows)
        if "up" in inp.pressed:
            self.i = (self.i - 1) % n
        if "down" in inp.pressed:
            self.i = (self.i + 1) % n
        d = ("right" in inp.pressed) - ("left" in inp.pressed)
        row = rows[self.i][0]
        if row == "music" and d:
            o["music"] = clamp(o["music"] + d, 0, 10)
        elif row == "sfx" and d:
            o["sfx"] = clamp(o["sfx"] + d, 0, 10)
            audio.sfx("food")
        elif row == "full" and (d or "ok" in inp.pressed):
            o["full"] = not o["full"]
            self.app.apply_display()
        elif row == "sharp" and (d or "ok" in inp.pressed):
            self.app.set_sharp(not o["sharp"])
        elif (row == "back" and "ok" in inp.pressed) or "back" in inp.pressed:
            self.app.save()
            self.app.pop()
        audio.set_volumes(o["music"], o["sfx"])

    def draw(self, s):
        rows = self.rows()
        dim(s, 120)
        panel(s, (280, 150, 400, 112 + len(rows) * 38))
        draw_text(s, "Options", (W / 2, 164), 28, center=True, bold=True)
        for k, (_, r) in enumerate(rows):
            draw_text(s, ("> " if k == self.i else "  ") + r, (320, 220 + k * 38), 22, (255, 240, 150) if k == self.i else (220, 230, 240))
        if not core.WEB and rows[self.i][0] == "sharp":
            draw_text(s, "Sharp draws at twice the resolution; fast suits slower computers.", (W / 2, 166 + len(rows) * 38 + 52), 13, (170, 200, 225), center=True)


class Slots:
    overlay = False

    def __init__(self, app):
        self.app, self.i, self.confirm, self.pick = app, 0, False, None
        self.dm = Menu(DIFF_NAMES)
        self.dm.i = 1

    def update(self, inp):
        app = self.app
        if self.pick is not None:
            c = self.dm.update(inp)
            if c:
                app.data["slots"][self.pick] = core.new_slot(self.dm.i)
                self.start(self.pick)
            elif "back" in inp.pressed:
                self.pick = None
            return
        if "up" in inp.pressed:
            self.i, self.confirm = (self.i - 1) % 3, False
        if "down" in inp.pressed:
            self.i, self.confirm = (self.i + 1) % 3, False
        if "back" in inp.pressed:
            app.pop()
        elif "ok" in inp.pressed:
            if app.data["slots"][self.i]:
                self.start(self.i)
            else:
                self.pick = self.i
        elif "shoot" in inp.pressed and app.data["slots"][self.i]:
            if self.confirm:
                app.data["slots"][self.i] = None
                app.save()
            self.confirm = not self.confirm

    def start(self, i):
        app = self.app
        app.slot_i = i
        app.data["opt"]["last"] = i
        app.save()
        app.pop()
        app.push(Map(app))

    def draw(self, s):
        s.blit(gfx.background(1), (0, 0))
        draw_text(s, "Choose a save slot", (W / 2, 40), 34, center=True, bold=True)
        for k in range(3):
            sl = self.app.data["slots"][k]
            sel = k == self.i
            panel(s, (180, 110 + k * 120, 600, 100), border=(255, 240, 150) if sel else (90, 130, 170))
            if sl:
                lv = LEVELS[sl["unlocked"]]
                draw_text(s, "Slot %d  -  World %d: %s" % (k + 1, lv["world"], WORLDS[lv["world"]]["name"]), (200, 122 + k * 120), 22, bold=True)
                draw_text(s, "%s   |   pages %d/%d   |   time %s   |   %s" % (
                    "COMPLETED" if sl["done"] else "next: " + lv["name"], len(sl["pages"]), TOTAL_PAGES, fmt_time(sl["time"]),
                    DIFF_NAMES[sl["diff"]].split(" ")[0]), (200, 158 + k * 120), 16, (200, 225, 240))
                if sel:
                    draw_text(s, "Press X again to DELETE this save" if self.confirm else "ENTER: continue     X: delete", (200, 184 + k * 120), 13,
                              (255, 120, 120) if self.confirm else (160, 190, 210))
            else:
                draw_text(s, "Slot %d  -  empty: start a new journey" % (k + 1), (200, 146 + k * 120), 22, (190, 210, 225))
        if self.pick is not None:
            panel(s, (280, 170, 400, 220))
            draw_text(s, "Difficulty", (W / 2, 184), 26, center=True, bold=True)
            self.dm.draw(s, 300, 236, 20, 42, 360)


class Story:
    """Travel-journal style story card (comic panel + caption box + route map)."""
    overlay = False

    def __init__(self, app, title, sub, text, world=1, music=None):
        self.app, self.title, self.sub, self.text, self.t, self.world = app, title, sub, text, 0, world
        pool = []
        for l in LEVELS:
            if l["world"] == world:
                for k in l["pool"]:
                    if k not in pool and k not in ("net", "handnet", "uvlamp", "laser", "enu", "heater", "pipette", "cut", "vortex"):
                        pool.append(k)
        self.cast = pool[:5]
        mini = core.scaled(gfx.world_map(), (240, 120))
        self.mini = mini
        if music:
            audio.music(music)

    def update(self, inp):
        self.t += 1
        if self.t > 40 and ("ok" in inp.pressed or "dash" in inp.pressed or "back" in inp.pressed):
            self.app.pop()

    def draw(self, s):
        t = self.t
        s.fill((244, 236, 214))
        pic = pygame.Rect(36, 70, 420, 300)
        s.blit(gfx.background(self.world), pic.topleft, (200, 120, pic.w, pic.h))
        s.set_clip(pic)
        for i, k in enumerate(self.cast):
            im = gfx.spr(k, (t // 10) % 2, True)
            s.blit(im, (pic.right - 70 - i * 62 + math.sin(t * 0.02 + i) * 8, pic.y + 60 + (i * 97) % 190 + math.sin(t * 0.05 + i) * 6))
        s.blit(gfx.player("", (t // 7) % 2, 0, False, z=2), (pic.x + 30 + math.sin(t * 0.03) * 10, pic.y + 140 + math.sin(t * 0.06) * 8))
        s.set_clip(None)
        dr.rect(s, (20, 20, 20), pic, 4)
        cap = "WORLD %d  -  %s" % (self.world, self.sub.upper())
        cw = core.font(15, True).size(core.pretty(cap))[0] + 20
        dr.rect(s, (255, 222, 80), (pic.x - 8, pic.y - 14, cw, 30))
        dr.rect(s, (20, 20, 20), (pic.x - 8, pic.y - 14, cw, 30), 3)
        draw_text(s, cap, (pic.x + 2, pic.y + 1), 15, (20, 20, 20), bold=True, shadow=False, mid=True)
        # route map
        mp = pygame.Rect(36, 384, 240, 120)
        s.blit(self.mini, mp.topleft)
        dr.rect(s, (20, 20, 20), mp, 3)
        pts = [(mp.x + (l["lon"] + 180) / 360 * 240, mp.y + (90 - l["lat"]) / 180 * 120) for l in LEVELS if l["world"] <= self.world]
        n = min(len(pts), 1 + t // 4)
        for i in range(1, n):
            if abs(pts[i][0] - pts[i - 1][0]) < 120:
                dr.line(s, (220, 30, 30), pts[i - 1], pts[i], 2)
        if n:
            dr.circle(s, (220, 30, 30), pts[n - 1], 4)
        draw_text(s, "The journey so far", (mp.right + 12, mp.y + 4), 14, (90, 80, 60), shadow=False)
        # narration
        draw_text(s, self.title, (486, 62), 38, (20, 20, 40), bold=True, shadow=False)
        box = pygame.Rect(486, 124, 440, 300)
        dr.rect(s, (255, 255, 250), box)
        dr.rect(s, (20, 20, 20), box, 3)
        draw_wrapped(s, self.text[:int(t * 1.6)], (box.x + 16, box.y + 14), 19, box.w - 32, (30, 30, 40), lh=29)
        if t > 40 and t % 60 < 40:
            draw_text(s, "SPACE to continue", (box.centerx, 446), 16, (170, 50, 40), center=True, shadow=False, bold=True)


class Map:
    overlay = False

    def __init__(self, app):
        self.app = app
        self.pos = [list(gfx.ll(l["lon"], l["lat"])) for l in LEVELS]
        for _ in range(80):   # nudge levels of the same world apart so their markers never overlap
            for i in range(len(LEVELS)):
                for j in range(i + 1, len(LEVELS)):
                    if LEVELS[i]["world"] != LEVELS[j]["world"]:
                        continue
                    dx, dy = self.pos[j][0] - self.pos[i][0], self.pos[j][1] - self.pos[i][1]
                    d = math.hypot(dx, dy) or 0.01
                    if d < 58:
                        k = (58 - d) / 2 / d
                        self.pos[i][0] -= dx * k; self.pos[i][1] -= dy * k
                        self.pos[j][0] += dx * k; self.pos[j][1] += dy * k
        self.fx, self.fy = self.pos[app.slot["node"]]
        self.t = 0
        self.face = 1

    def update(self, inp):
        app, slot = self.app, self.app.slot
        self.t += 1
        slot["time"] += 1 / 60.0
        audio.music("map")
        if slot["done"] and "end" not in slot["seen"]:
            slot["seen"].append("end")
            app.save()
            app.push(Ending(app))
            return
        w = LEVELS[slot["unlocked"]]["world"]
        if w not in slot["seen"]:
            slot["seen"].append(w)
            if w > 1:
                slot["node"] = slot["unlocked"]
            app.save()
            app.push(Story(app, WORLDS[w]["name"], WORLDS[w]["years"], WORLDS[w]["intro"], w))
            return
        n = slot["node"]
        if getattr(self, "prep", None) != n:
            self.prep = n
            audio.prepare(audio.level_key(LEVELS[n], app.level_index_in_world(LEVELS[n])))
        tx, ty = self.pos[n]
        dist = math.hypot(tx - self.fx, ty - self.fy)
        if dist > 3:
            sp = max(5.0, dist * 0.12)
            self.fx += (tx - self.fx) / dist * min(sp, dist)
            self.fy += (ty - self.fy) / dist * min(sp, dist)
            self.face = 1 if tx >= self.fx else -1
        else:
            d = ("right" in inp.pressed or "up" in inp.pressed) - ("left" in inp.pressed or "down" in inp.pressed)
            if d and 0 <= n + d <= slot["unlocked"]:
                slot["node"] = n + d
                audio.sfx("blip")
            elif d:
                audio.sfx("wrong")
            if "ok" in inp.pressed:
                app.save()
                app.push(Play(app, LEVELS[n]))
        if "tab" in inp.pressed:
            app.push(Pedia(app))
        elif "shop" in inp.pressed:
            app.push(Shop(app))
        elif "back" in inp.pressed:
            app.push(MapMenu(app))

    def all_pages(self, lv):
        if lv["boss"]:
            return False
        w0 = self.app.level_index_in_world(lv) * 3
        return all(fact_id(lv["world"], w0 + i) in self.app.slot["pages"] for i in range(3))

    def draw(self, s):
        slot, t = self.app.slot, self.t
        cx = clamp(self.fx - W / 2, 0, gfx.MW - W)
        cy = clamp(self.fy - H / 2 + 30, 0, gfx.MH - H)
        s.blit(gfx.world_map(), (0, 0), (cx, cy, W, H))
        n = slot["node"]
        cw = LEVELS[n]["world"]
        uw = LEVELS[slot["unlocked"]]["world"]
        last = max(i for i, l in enumerate(LEVELS) if l["world"] <= uw)
        # routes
        for i in range(last):
            a, b = self.pos[i], self.pos[i + 1]
            if abs(a[0] - b[0]) > gfx.MW / 2:
                continue
            focus = LEVELS[i]["world"] == cw or LEVELS[i + 1]["world"] == cw
            if i < slot["unlocked"]:
                d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
                for k in range(0, int(d), 12 if focus else 18):
                    dr.circle(s, (228, 44, 44) if focus else (150, 84, 84), (a[0] + (b[0] - a[0]) * k / d - cx, a[1] + (b[1] - a[1]) * k / d - cy), 3 if focus else 2)
            elif focus:
                dr.line(s, (70, 95, 120), (a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy), 2)
        # level nodes: the current world is drawn large and numbered, other worlds as small dots
        for i, lv in enumerate(LEVELS[:last + 1]):
            x, y = self.pos[i][0] - cx, self.pos[i][1] - cy
            if not (-40 < x < W + 40 and -40 < y < H + 40):
                continue
            rec = slot["levels"].get(lv["id"], {})
            done, locked = rec.get("done"), i > slot["unlocked"]
            if lv["world"] != cw:
                dr.circle(s, (20, 30, 50), (x, y), 6)
                dr.circle(s, (96, 200, 124) if done else (128, 138, 152), (x, y), 4)
                continue
            r = 15 if lv["boss"] else 13
            col = (112, 122, 138) if locked else (96, 220, 126) if done else (228, 70, 78) if lv["boss"] else (255, 226, 96)
            dr.circle(s, (20, 30, 50), (x, y + 2), r + 4)
            dr.circle(s, col, (x, y), r)
            dr.circle(s, (255, 255, 255), (x - r * 0.5, y - r * 0.5), r * 0.17)
            dr.circle(s, (20, 30, 50), (x, y), r + 1, 2)
            if self.all_pages(lv):
                dr.circle(s, (255, 215, 0), (x, y), r + 5, 3)
            draw_text(s, "B" if lv["boss"] else lv["id"][2:], (x, y), 15, (20, 30, 50), center=True, bold=True, shadow=False, mid=True)
        # "you are here": pulsing rings on the selected level and the fish in a pin above it
        x, y = self.pos[n][0] - cx, self.pos[n][1] - cy
        pr = 24 + math.sin(t * 0.12) * 4
        dr.circle(s, (20, 30, 50), (x, y), pr + 2, 5)
        dr.circle(s, (255, 255, 255), (x, y), pr, 3)
        dr.circle(s, (255, 236, 110), (x, y), pr + 8 + math.sin(t * 0.12) * 3, 2)
        fx, fy = self.fx - cx, self.fy - cy
        up = -1 if fy > 150 else 1          # near the top of the screen the pin hangs below the level instead
        by = fy + up * 64 + math.sin(t * 0.1) * 4
        dr.polygon(s, (20, 30, 50), [(fx - 13, by - up * 18), (fx + 13, by - up * 18), (fx, fy + up * 15)])
        dr.polygon(s, (255, 244, 170), [(fx - 8, by - up * 19), (fx + 8, by - up * 19), (fx, fy + up * 21)])
        dr.circle(s, (20, 30, 50), (fx, by), 29)
        dr.circle(s, (104, 188, 226), (fx, by), 26)
        dr.circle(s, (255, 244, 170), (fx, by), 26, 3)
        im = gfx.player("", (t // 7) % 2, 0, self.face < 0)
        s.blit(im, (fx - im.get_width() / 2, by - im.get_height() / 2))
        lv = LEVELS[n]
        rec = slot["levels"].get(lv["id"], {})
        tag = "%s  %s" % (lv["id"].replace("B", "Boss"), lv["name"])
        tw = core.font(15, True).size(core.pretty(tag))[0] + 20
        tx0 = clamp(x - tw / 2, 8, W - tw - 8)
        tx0 = clamp(fx - tw / 2, 8, W - tw - 8)
        ly = by - 62 if up < 0 else by + 34
        panel(s, (tx0, ly, tw, 28), fill=(20, 30, 50), border=(255, 244, 170), alpha=235, radius=8)
        draw_text(s, tag, (tx0 + 10, ly + 14), 15, (255, 250, 220), bold=True, shadow=False, mid=True)
        # header
        panel(s, (14, 10, 470, 42), alpha=220)
        draw_text(s, "World %d   %s" % (cw, WORLDS[cw]["name"]), (28, 31), 20, (255, 244, 170), bold=True, mid=True)
        draw_text(s, WORLDS[cw]["years"], (470, 31), 14, (150, 210, 250), right=True, mid=True)
        panel(s, (W - 314, 10, 300, 62), alpha=220)
        s.blit(gfx.icon("page"), (W - 304, 14))
        draw_text(s, "%d / %d" % (len(slot["pages"]), TOTAL_PAGES), (W - 272, 19), 15)
        s.blit(gfx.icon("food"), (W - 196, 21))
        draw_text(s, str(slot["food"]), (W - 174, 19), 15)
        kn = slot.get("know", 0)
        nr = quiz.next_rank(kn)
        draw_text(s, "Knowledge %d  -  %s" % (kn, quiz.rank(kn)), (W - 304, 46), 14, (255, 225, 90), bold=True)
        if nr:
            draw_text(s, "next: %d" % nr[0], (W - 22, 47), 12, (170, 190, 210), right=True)
        # bottom: level info and a strip with every level of this world
        panel(s, (14, H - 126, W - 28, 114), alpha=228)
        draw_text(s, lv["name"], (30, H - 118), 22, bold=True)
        draw_text(s, lv["when"], (30, H - 88), 14, (150, 210, 250))
        st = ("Cleared" + ("  -  best %s" % fmt_time(rec["best"] / 60) if rec.get("best") else "")) if rec.get("done") else "Not yet cleared"
        draw_text(s, st, (30, H - 68), 14, (214, 226, 240))
        ids = [i for i, l in enumerate(LEVELS) if l["world"] == cw]
        x0 = W - 30 - len(ids) * 60
        for k, i in enumerate(ids):
            l = LEVELS[i]
            r2 = slot["levels"].get(l["id"], {})
            bx, by2 = x0 + k * 60, H - 110
            locked = i > slot["unlocked"]
            fill = (44, 50, 64) if locked else (40, 110, 70) if r2.get("done") else (130, 50, 56) if l["boss"] else (120, 100, 30)
            sel = i == n
            dr.rect(s, fill, (bx, by2, 50, 50), border_radius=9)
            dr.rect(s, (255, 244, 170) if sel else (20, 30, 50), (bx, by2, 50, 50), 4 if sel else 2, border_radius=9)
            draw_text(s, "B" if l["boss"] else l["id"][2:], (bx + 25, by2 + 25), 24, (120, 130, 145) if locked else (255, 255, 255), center=True, bold=True, mid=True)
            if sel:
                dr.polygon(s, (255, 244, 170), [(bx + 17, by2 - 12), (bx + 33, by2 - 12), (bx + 25, by2 - 3)])
            marks = [r2.get("done")] if l["boss"] else [r2.get("done"), self.all_pages(l), r2.get("danio")]
            for q, on in enumerate(marks):
                star(s, bx + 25 + (q - (len(marks) - 1) / 2) * 16, by2 + 62, 7, (255, 214, 60) if on else (60, 70, 90))
        draw_text(s, "stars: cleared / all pages / D-A-N-I-O", (W - 34, H - 30), 11, (150, 170, 190), right=True)
        draw_text(s, "LEFT / RIGHT: choose level     ENTER: dive in     TAB: Fishipedia     U: upgrades     ESC: menu", (30, H - 36), 12, (170, 200, 220))


class MapMenu:
    overlay = True

    def __init__(self, app):
        self.app = app
        items = [("Back to the map", ""), ("Fishipedia", "Notebook pages and the zebrafish handbook."),
                 ("Upgrades", "Spend food on permanent upgrades."), ("Options", "Sound volume and fullscreen."),
                 ("Save and quit to title", "Your progress is saved automatically.")]
        if app.slot["done"]:
            items.insert(3, ("Certificate", "Your certificate from the Juan Lab, as a PDF."))
        self.menu = Menu(items)

    def update(self, inp):
        app = self.app
        if "back" in inp.pressed:
            app.pop()
            return
        c = self.menu.update(inp)
        if c == "Back to the map":
            app.pop()
        elif c == "Fishipedia":
            app.pop()
            app.push(Pedia(app))
        elif c == "Upgrades":
            app.pop()
            app.push(Shop(app))
        elif c == "Options":
            app.push(Options(app))
        elif c == "Certificate":
            app.pop()
            app.push(Certificate(app))
        elif c:
            app.save(True)
            del app.stack[1:]

    def draw(self, s):
        slot = self.app.slot
        dim(s)
        panel(s, (290, 110, 380, 372))
        draw_text(s, "Expedition menu", (W / 2, 124), 26, center=True, bold=True)
        draw_text(s, "pages %d/%d    time %s" % (len(slot["pages"]), TOTAL_PAGES, fmt_time(slot["time"])), (W / 2, 160), 14, (150, 210, 250), center=True)
        self.menu.draw(s, 310, 196, 20, 42, 340)
        draw_text(s, self.menu.hint or "ESC: close", (W / 2, 454), 13, (170, 200, 220), center=True)


class Pause:
    overlay = True

    def __init__(self, app, play):
        self.app, self.play = app, play
        self.menu = Menu([("Resume", ""), ("Restart from checkpoint", "Go back to the last flag with full hearts."),
                          ("Restart level", "Start this level again from the beginning."),
                          ("Options", "Sound volume and fullscreen."),
                          ("Back to the map", "Leave the level. Pages are kept; food from this run is not."),
                          ("Quit to title", "Leave the level (pages kept, food from this run lost) and save.")])

    def update(self, inp):
        app, play = self.app, self.play
        if "back" in inp.pressed:
            app.pop()
            return
        c = self.menu.update(inp)
        if c == "Resume":
            app.pop()
        elif c == "Restart from checkpoint":
            play.reset()
            app.pop()
        elif c == "Restart level":
            app.pop()
            app.pop()
            app.push(Play(app, play.spec))
        elif c == "Options":
            app.push(Options(app))
        elif c == "Back to the map":
            app.save(True)
            app.pop()
            app.pop()
        elif c:
            app.save(True)
            del app.stack[1:]

    def draw(self, s):
        play = self.play
        dim(s)
        panel(s, (280, 76, 400, 400))
        draw_text(s, "Paused", (W / 2, 88), 28, center=True, bold=True)
        draw_text(s, play.spec["id"].replace("B", "Boss") + "   " + play.spec["name"], (W / 2, 126), 15, (150, 210, 250), center=True)
        if not play.spec["boss"]:
            for i in range(3):
                s.blit(gfx.icon("page" if play.pages[i] else "page0"), (372 + i * 30, 150))
            for i in range(5):
                s.blit(gfx.coin("DANIO"[i], bool(play.letters[i]), 18), (480 + i * 20, 158))
        self.menu.draw(s, 300, 196, 19, 40, 360)
        draw_text(s, self.menu.hint or "ESC: resume", (W / 2, 446), 13, (170, 200, 220), center=True)


class Result:
    overlay = False

    def __init__(self, app, play, first, new_pages):
        self.app, self.spec, self.first = app, play.spec, first
        self.time, self.food, self.pages = play.time, play.food, sum(play.pages)
        self.new_pages = new_pages  # boss: list of fact tuples
        self.t, self.sel, self.answer, self.page_i = 0, 0, None, 0
        idx = INDEX[self.spec["id"]]
        nxt = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
        self.next = nxt if (nxt and nxt["world"] in app.slot["seen"] and self.spec["id"] != "6-B") else None
        self.choices = (["Next level"] if self.next else []) + ["Back to the map", "Replay"]
        self.ci = 0
        self.q = None
        if not self.spec["boss"]:
            qq = quiz.pick(app.slot, self.spec["world"], random, getattr(play, "asked", ()), use_cloze=False)
            self.q, self.opts, self.correct, self.why = qq["q"], qq["opts"], qq["correct"], qq["why"]
        audio.music("map")

    def update(self, inp):
        self.t += 1
        app, slot = self.app, self.app.slot
        if self.t < 30:
            return
        if self.q and self.answer is None:
            if "up" in inp.pressed:
                self.sel = (self.sel - 1) % 3
            if "down" in inp.pressed:
                self.sel = (self.sel + 1) % 3
            if "ok" in inp.pressed:
                self.answer = self.opts[self.sel]
                right = self.answer == self.correct
                if self.first:
                    quiz.score(slot, right)
                    slot["food"] = slot["food"] + 25 if right else max(0, slot["food"] - 15)
                audio.sfx("right" if right else "wrong")
                app.save()
                self.t = 30
            return
        if "ok" in inp.pressed and self.t > 55:
            if self.spec["boss"] and self.page_i < len(self.new_pages) - 1:
                self.page_i += 1
                self.t = 30
                audio.sfx("page")
                return
            c = self.choices[self.ci]
            if self.first or c == "Next level":
                slot["node"] = min(INDEX[self.spec["id"]] + 1, slot["unlocked"])
            if c == "Replay":
                slot["node"] = INDEX[self.spec["id"]]
            app.save()
            app.pop()
            if c == "Next level":
                app.push(Play(app, self.next))
            elif c == "Replay":
                app.push(Play(app, self.spec))
            return
        if self.t > 55 and not (self.spec["boss"] and self.page_i < len(self.new_pages) - 1):
            d = ("right" in inp.pressed) - ("left" in inp.pressed)
            if d:
                self.ci = (self.ci + d) % len(self.choices)
                audio.sfx("blip")

    def draw(self, s):
        s.blit(gfx.background(self.spec["world"]), (0, 0))
        panel(s, (110, 30, 740, 480))
        draw_text(s, ("Boss defeated!" if self.spec["boss"] else "Level complete!"), (W / 2, 44), 34, (255, 240, 150), center=True, bold=True)
        draw_text(s, "%s      time %s      food +%d%s" % (self.spec["name"], fmt_time(self.time / 60), self.food,
                  "" if self.spec["boss"] else "      pages %d/3" % self.pages), (W / 2, 96), 17, (210, 230, 245), center=True)
        if self.q:
            draw_text(s, "Final question   right: +25 food, +10 knowledge     wrong: -15 food, -5 knowledge" if self.first else
                      "Practice question (this level was already cleared, so it is not scored)", (W / 2, 138), 14, (150, 210, 250), center=True)
            y = draw_wrapped(s, self.q, (W / 2, 164), 21 if len(self.q) < 70 else 18, 680, center=True, bold=True, lh=28)
            for k, o in enumerate(self.opts):
                col = (220, 230, 240)
                if self.answer is not None:
                    col = (110, 240, 130) if o == self.correct else (240, 110, 110) if o == self.answer else (130, 140, 150)
                elif k == self.sel:
                    col = (255, 240, 150)
                panel(s, (170, y + 10 + k * 48, 620, 40), border=col, alpha=200)
                draw_text(s, o, (W / 2, y + 30 + k * 48), 17, col, center=True, mid=True)
            if self.answer is not None:
                ok = self.answer == self.correct
                draw_text(s, ("Correct!" if ok else "Wrong. The answer is in green.") if not self.first else
                          "Correct!  +25 food, +10 knowledge" if ok else "Wrong: -15 food, -5 knowledge. The answer is in green.",
                          (W / 2, y + 160), 16, (150, 255, 170) if ok else (255, 150, 150), center=True, bold=True)
                if self.why:
                    draw_wrapped(s, self.why, (W / 2, y + 184), 14, 680, (220, 230, 245), center=True, lh=19)
        elif self.new_pages:
            when, title, text = self.new_pages[self.page_i]
            draw_text(s, "New notebook page %d of %d" % (self.page_i + 1, len(self.new_pages)), (W / 2, 142), 15, (150, 210, 250), center=True)
            draw_text(s, title, (W / 2, 180), 28, center=True, bold=True)
            draw_text(s, when, (W / 2, 220), 16, (150, 210, 250), center=True)
            draw_wrapped(s, text, (W / 2, 262), 20, 640, (235, 240, 250), center=True, lh=32)
        if (not self.q or self.answer is not None) and self.t > 55:
            if self.spec["boss"] and self.page_i < len(self.new_pages) - 1:
                if self.t % 60 < 40:
                    draw_text(s, "SPACE: next page", (W / 2, 474), 15, (255, 240, 150), center=True)
            else:
                n = len(self.choices)
                x0 = W / 2 - (n * 200 - 20) / 2
                for k, c in enumerate(self.choices):
                    sel = k == self.ci
                    panel(s, (x0 + k * 200, 462, 180, 36), fill=(60, 54, 20) if sel else (18, 30, 52),
                          border=(255, 240, 150) if sel else (90, 130, 170), alpha=240)
                    draw_text(s, c, (x0 + k * 200 + 90, 480), 16, (255, 244, 170) if sel else (200, 215, 230), center=True, bold=sel, mid=True)


class Pedia:
    overlay = False

    def __init__(self, app):
        self.app, self.w, self.i = app, LEVELS[app.slot["node"]]["world"], 0

    def update(self, inp):
        if "back" in inp.pressed or "tab" in inp.pressed:
            self.app.pop()
        d = ("right" in inp.pressed) - ("left" in inp.pressed)
        if d:
            self.w = (self.w + d) % 8
            self.i = 0
        n = len(FACTS[self.w])
        self.i = (self.i + ("down" in inp.pressed) - ("up" in inp.pressed)) % n

    def draw(self, s):
        slot = self.app.slot
        s.fill((10, 20, 40))
        draw_text(s, "Fishipedia", (30, 14), 32, bold=True)
        draw_text(s, "%d / %d pages    quiz %d/%d    %s    LEFT/RIGHT: world   UP/DOWN: page   ESC: back" % (
            len(slot["pages"]), TOTAL_PAGES, slot["quiz"][0], slot["quiz"][1], quiz.rank(slot.get("know", 0))), (W - 24, 26), 13, (160, 190, 215), right=True)
        have = [self.w == 0 or fact_id(self.w, k) in slot["pages"] for k in range(len(FACTS[self.w]))]
        draw_text(s, ("< %s  (%s)   %d entries >" % (WORLDS[0]["name"], WORLDS[0]["years"], len(have))) if self.w == 0 else
                  "< World %d: %s  (%s)   %d/%d >" % (self.w, WORLDS[self.w]["name"], WORLDS[self.w]["years"], sum(have), len(have)),
                  (30, 62), 20, (255, 240, 150), bold=True)
        top = clamp(self.i - 7, 0, max(0, len(have) - 15))
        for row, k in enumerate(range(top, min(len(have), top + 15))):
            when, title, _ = FACTS[self.w][k]
            sel = k == self.i
            col = (255, 240, 150) if sel else (215, 225, 240) if have[k] else (95, 105, 125)
            s.blit(gfx.icon("page" if have[k] else "page0"), (30, 98 + row * 28 - 4)) if sel else None
            draw_text(s, (title if have[k] else "? ? ?"), (64, 98 + row * 28), 17, col, bold=sel)
        when, title, text = FACTS[self.w][self.i]
        panel(s, (400, 100, 536, 400), fill=(250, 246, 225), border=(170, 60, 60), alpha=255)
        if have[self.i]:
            draw_text(s, when, (916, 114), 15, (90, 100, 140), shadow=False, right=True)
            y = draw_wrapped(s, title, (420, 140), 25, 490, (30, 40, 80), bold=True)
            draw_wrapped(s, text, (420, y + 16), 19, 490, (40, 40, 60), lh=29)
        else:
            lvl = self.i // 3 + 1
            hint = "Defeat the boss of this world." if (self.i >= 18) else "Hidden in level %d-%d." % (self.w, lvl)
            draw_text(s, "Page not found yet", (668, 250), 24, (150, 120, 120), center=True, shadow=False, bold=True)
            draw_text(s, hint, (668, 290), 17, (120, 110, 110), center=True, shadow=False)


class Shop:
    overlay = True

    def __init__(self, app):
        self.app, self.i, self.msg = app, 0, ""

    def update(self, inp):
        slot = self.app.slot
        if "back" in inp.pressed or "shop" in inp.pressed:
            self.app.pop()
        self.i = (self.i + ("down" in inp.pressed) - ("up" in inp.pressed)) % len(UPGRADES)
        if "ok" in inp.pressed:
            key, name, desc, costs = UPGRADES[self.i]
            lv = slot["up"][key]
            if lv >= len(costs):
                self.msg = "Already at maximum."
            elif slot["food"] < costs[lv]:
                self.msg = "Not enough food - collect more in the levels."
                audio.sfx("wrong")
            else:
                slot["food"] -= costs[lv]
                slot["up"][key] += 1
                self.msg = name + " upgraded!"
                audio.sfx("power")
                self.app.save()

    def draw(self, s):
        slot = self.app.slot
        dim(s)
        panel(s, (150, 70, 660, 400))
        draw_text(s, "Upgrades", (W / 2, 84), 30, center=True, bold=True)
        s.blit(gfx.icon("food"), (W / 2 - 40, 130))
        draw_text(s, str(slot["food"]), (W / 2 - 16, 124), 20)
        for k, (key, name, desc, costs) in enumerate(UPGRADES):
            lv = slot["up"][key]
            sel = k == self.i
            panel(s, (180, 166 + k * 62, 600, 54), border=(255, 240, 150) if sel else (80, 110, 150), alpha=180)
            draw_text(s, "%s  %s" % (name, "*" * lv + "-" * (len(costs) - lv)), (196, 172 + k * 62), 19, bold=sel)
            draw_text(s, desc, (196, 196 + k * 62), 14, (180, 205, 225))
            draw_text(s, "MAX" if lv >= len(costs) else "%d food" % costs[lv], (764, 180 + k * 62), 18, (255, 200, 120), right=True)
        draw_text(s, self.msg or "ENTER: buy    ESC: back", (W / 2, 430), 16, (255, 240, 150), center=True)


class Ending:
    overlay = False

    def __init__(self, app):
        self.app, self.t = app, 0
        audio.music(6)

    def update(self, inp):
        self.t += 1
        if self.t > 240 and ("ok" in inp.pressed or "back" in inp.pressed):
            self.app.pop()
            self.app.push(Certificate(self.app))

    def draw(self, s):
        slot = self.app.slot
        s.blit(gfx.background(6), (0, 0))
        for i in range(14):
            x = (self.t * (1 + i % 3 * 0.4) + i * 90) % (W + 100) - 50
            s.blit(gfx.player("star" if i % 4 == 0 else "", (self.t // 8 + i) % 2, 0, False), (x, 60 + i * 30 + math.sin(self.t * 0.03 + i) * 10))
        panel(s, (110, 50, 740, 440), alpha=225)
        draw_text(s, "A Leading Model", (W / 2, 66), 40, (255, 240, 150), center=True, bold=True)
        y = draw_wrapped(s, ENDING[:int(self.t * 2)], (150, 130), 19, 660, (235, 240, 250), lh=28)
        draw_text(s, "Pages %d/%d    Quiz %d/%d    Retries %d    Time %s" % (len(slot["pages"]), TOTAL_PAGES, slot["quiz"][0], slot["quiz"][1],
                  slot["deaths"], fmt_time(slot["time"])), (W / 2, 404), 17, (150, 210, 250), center=True)
        draw_text(s, "Academic rank: %s  (knowledge %d)" % (quiz.rank(slot.get("know", 0)), slot.get("know", 0)), (W / 2, 430), 17, (255, 225, 90), center=True, bold=True)
        if self.t > 240:
            draw_text(s, "SPACE: receive your certificate   (a bonus world has opened in orbit)", (W / 2, 454), 15, (255, 240, 150), center=True)


class Certificate:
    """Shows the certificate earned so far, lets the player type a name and save it as a PDF."""
    overlay = False

    def __init__(self, app):
        self.app, self.t, self.msg = app, 0, ""
        self.st = certificate.stats(app.slot)
        self.name = app.slot.get("name", "")
        self.menu = Menu(["Edit name", "Save as PDF", "Back"])
        self.editing = not self.name
        if self.editing:
            self._start_edit()
        self._render()

    def _start_edit(self):
        self.editing = True
        try:
            pygame.key.start_text_input()
        except Exception:
            pass

    def _render(self):
        self.preview = core.scaled(certificate.render(self.name, self.st), (636, 450))

    def set_name(self, name):
        self.name = name.strip()[:44]
        self.editing = False
        self.app.slot["name"] = self.name
        self.app.save()
        self._render()

    def update(self, inp):
        self.t += 1
        if self.editing:
            typed = "".join(e.text for e in self.app.events if e.type == pygame.TEXTINPUT)
            if typed:
                self.app.saw_text = True
            elif core.WEB and not getattr(self.app, "saw_text", False):   # browsers that send no text events
                typed = "".join(e.unicode for e in self.app.events if e.type == pygame.KEYDOWN and e.unicode and e.unicode.isprintable())
            self.name = (self.name + typed)[:44]
            for e in self.app.events:
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_BACKSPACE:
                        self.name = self.name[:-1]
                    elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                        self.set_name(self.name)
            return
        if "back" in inp.pressed:
            self.app.pop()
            return
        c = self.menu.update(inp)
        if c == "Edit name":
            self._start_edit()
        elif c == "Save as PDF":
            try:
                if core.WEB:
                    self.msg = "Downloaded: " + certificate.download(self.name, self.st)
                else:
                    path = certificate.save(self.name, self.st)
                    self.msg = "Saved: " + path
                    if not self.app.headless:
                        certificate.open_file(path)
            except Exception as err:
                self.msg = "Could not save the PDF: %s" % err
        elif c == "Back":
            self.app.pop()

    def draw(self, s):
        st = self.st
        s.fill((10, 18, 36))
        draw_text(s, "Your certificate", (16, 8), 24, (255, 244, 170), bold=True)
        dr.rect(s, (255, 244, 170), (13, 43, 638, 452), 1)
        s.blit(self.preview, (14, 44))
        x, y = 664, 44
        for i, (title, _, col, how) in enumerate(certificate.TIERS):
            got = i <= st["tier"]
            star(s, x + 8, y + 9, 8, (255, 214, 60) if got else (60, 70, 90))
            draw_text(s, title.replace("Certificate of ", ""), (x + 22, y - 2), 15, (255, 255, 255) if got else (140, 150, 165), bold=True)
            y += 20
            for text, ok in st["reqs"][i]:
                dr.circle(s, (110, 230, 130) if ok else (230, 110, 110), (x + 27, y + 8), 3)
                draw_text(s, text, (x + 36, y), 12, (200, 215, 230) if ok else (230, 170, 170), shadow=False)
                y += 16
            y += 6
        y = max(y + 4, 318)
        draw_text(s, "Name on the certificate", (x, y), 12, (150, 210, 250))
        dr.rect(s, (255, 244, 170) if self.editing else (90, 130, 170), (x, y + 18, 282, 30), 2, border_radius=6)
        shown = self.name + ("|" if self.editing and self.t % 40 < 20 else "")
        draw_text(s, shown[-30:], (x + 8, y + 23), 15, shadow=False)
        if self.editing:
            draw_wrapped(s, "Type your name, then press ENTER.", (x, y + 56), 13, 280, (255, 244, 170))
        else:
            self.menu.draw(s, x - 4, y + 58, 16, 34, 286)
            draw_wrapped(s, self.msg or ("The PDF is downloaded by your browser." if core.WEB else "The PDF is saved in your Documents folder, under 'Journey of a Zebrafish'."), (16, 502), 12, 920, (170, 200, 220), lh=16)


class App:
    def __init__(self, headless=False):
        pygame.init()
        self.headless = headless
        self.data = core.load_all()
        self.data["opt"]["full"] = False   # always start in a window; F11 or Options switches to fullscreen
        self.data["opt"].setdefault("sharp", True)
        # pixels per point: 2 ("sharp") on the desktop; the browser stays at 1 for speed
        gfx.set_scale(1 if core.WEB or not self.data["opt"]["sharp"] else int(os.environ.get("ZF_SCALE", 2)))
        self.slot_i = 0
        self.screen = self.display = None
        self.apply_display()
        if not headless:
            audio.init()
            audio.set_volumes(self.data["opt"]["music"], self.data["opt"]["sfx"])
        self.inp = core.Input()
        self.clock = pygame.time.Clock()
        self.running = True
        self.saved_t = 0
        self.events = []
        self.show_fps = False
        self.work_ms = 0.0
        self.slow = 0
        self.stack = [Title(self)]

    @property
    def slot(self):
        return self.data["slots"][self.slot_i]

    def set_sharp(self, sharp):
        """Switch between sharp (2 pixels per point) and fast (1) graphics while running."""
        self.data["opt"]["sharp"] = sharp
        k = 2 if sharp else 1
        if core.WEB or k == core.K:
            return
        gfx.set_scale(k)
        _dims.clear()
        level_mod._plants.clear()
        for sc in self.stack:
            lv = getattr(sc, "level", None)
            if lv is not None:
                lv._chunks.clear()
            if isinstance(sc, Story):
                sc.mini = core.scaled(gfx.world_map(), (240, 120))
            if isinstance(sc, Certificate):
                sc._render()
        self.apply_display()

    def apply_display(self):
        """The game draws on self.screen, addressed in points (960 x 540). On the desktop the window
        surface has core.K pixels per point and SDL scales it smoothly to the window or monitor."""
        if core.WEB:                      # the browser page scales the canvas itself
            self.screen = self.display = pygame.display.set_mode((W, H))
            return
        k = core.K
        full = self.data["opt"]["full"] and not self.headless
        if self.display is not None:
            # pygame can crash when a SCALED window changes mode in place (fullscreen, or a new
            # resolution), so the window is closed and opened afresh, where it was
            if not self.headless and not getattr(self, "_full", False):
                try:
                    win = pygame.Window.from_display_module()
                    self._geom = (win.size, win.position)
                except Exception:
                    pass
            pygame.display.quit()
            pygame.display.init()
        self._full = full
        flags = pygame.SCALED | pygame.RESIZABLE | (pygame.FULLSCREEN if full else 0)
        try:
            self.display = pygame.display.set_mode((W * k, H * k), flags, vsync=1)
        except pygame.error:
            self.display = pygame.display.set_mode((W * k, H * k))
        if not full and not self.headless:
            self._fit_window(getattr(self, "_geom", None))
        self.screen = self.display if k == 1 else core.Canvas(self.display, k)
        pygame.display.set_caption(core.TITLE)
        try:
            pygame.display.set_icon(pygame.transform.smoothscale(gfx.player("", 0, 0, False), (64, 32)))
        except Exception:
            pass

    def _fit_window(self, geom=None):
        """Open the window as large as fits comfortably on the monitor (or as it was)."""
        try:
            win = pygame.Window.from_display_module()
            win.minimum_size = (W // 2, H // 2)      # SCALED would otherwise forbid anything below 1920 x 1080
            if geom:
                win.size, win.position = geom
                return
            dw, dh = pygame.display.get_desktop_sizes()[0]
            m = max([z for z in (1, 1.25, 1.5, 2, 2.5, 3) if W * z <= dw * 0.92 and H * z <= dh * 0.86] or [1])
            win.size = (int(W * m), int(H * m))
            win.position = pygame.WINDOWPOS_CENTERED
        except Exception:
            pass

    def present(self):
        pygame.display.flip()

    def push(self, sc):
        self.stack.append(sc)

    def pop(self):
        self.stack.pop()
        if not self.stack:
            self.running = False

    def pause(self, play):
        self.push(Pause(self, play))

    def save(self, show=False):
        if core.save_all(self.data) and show:
            self.saved_t = 120

    def level_index_in_world(self, spec):
        return sum(1 for l in LEVELS[:INDEX[spec["id"]]] if l["world"] == spec["world"] and not l["boss"])

    def give_page(self, world, idx):
        fid = fact_id(world, idx)
        if fid not in self.slot["pages"]:
            self.slot["pages"].append(fid)
            self.save()
            return True
        return False

    def finish_level(self, play):
        spec, slot = play.spec, self.slot
        rec = slot["levels"].setdefault(spec["id"], {})
        first = not rec.get("done")
        rec["done"] = 1
        rec["pages"] = list(play.pages)
        rec["danio"] = int(rec.get("danio", 0) or all(getattr(play, "letters", [0])))
        rec["best"] = min(rec.get("best") or 10 ** 9, play.time)
        slot["food"] += play.food
        idx = INDEX[spec["id"]]
        slot["unlocked"] = max(slot["unlocked"], min(idx + 1, len(LEVELS) - 1))
        new = []
        if spec["boss"]:
            for k in (18, 19, 20):
                self.give_page(spec["world"], k)
                new.append(FACTS[spec["world"]][k])
            if spec["id"] == "6-B":
                slot["done"] = True
        self.save(True)
        self.stack.pop()
        self.push(Result(self, play, first, new))

    def frame(self, events, steps=1):
        """One drawn frame. steps > 1 runs extra game updates first, so a slow browser
        shows fewer frames instead of running the game in slow motion."""
        t0 = pygame.time.get_ticks()
        self.events = events
        self.inp.update(events)
        self.stack[-1].update(self.inp)
        for _ in range(steps - 1):
            if not self.stack:
                break
            self.events = []
            self.inp.update([])
            self.stack[-1].update(self.inp)
        if not self.stack:
            return
        k = len(self.stack) - 1
        while k > 0 and self.stack[k].overlay:
            k -= 1
        for sc in self.stack[k:]:
            sc.draw(self.screen)
        if self.saved_t > 0:
            self.saved_t -= 1
            draw_text(self.screen, "Game saved", (W - 16, H - 24), 14, (160, 255, 180), right=True)
        self.work_ms = self.work_ms * 0.95 + (pygame.time.get_ticks() - t0) * 0.05
        top = self.stack[-1]
        if core.K > 1 and isinstance(top, Play) and top.state == "play" and not self.headless:
            # a computer that cannot draw the sharp picture in time gets the fast one
            self.slow = self.slow + 1 if self.work_ms > 12 else max(0, self.slow - 3)
            if self.slow > 240:
                self.slow = 0
                self.set_sharp(False)
                self.save()
                top.toast = ["Graphics set to fast for smoother play (Options to change)", 240]
        if self.show_fps and core.WEB and pygame.time.get_ticks() - getattr(self, "_rep", 0) > 1000:
            self._rep = pygame.time.get_ticks()
            try:
                import platform
                platform.window.document.title = "ZF %d fps %.1f ms sound=%s scene=%s" % (
                    self.clock.get_fps(), self.work_ms, audio.ok, type(self.stack[-1]).__name__)
            except Exception:
                pass
        if self.show_fps:      # F3: diagnostics
            draw_text(self.screen, "%d fps   %.1f ms/frame   sound %s" % (self.clock.get_fps(), self.work_ms, "on" if audio.ok else "OFF"),
                      (W / 2, H - 20), 14, (255, 255, 0), center=True, bold=True)

    async def run(self):
        dt = 16
        while self.running and self.stack:
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key in (pygame.K_F3, pygame.K_BACKQUOTE):
                    self.show_fps = not self.show_fps
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self.data["opt"]["full"] = not self.data["opt"]["full"]
                    self.apply_display()
            self.frame(events, 1 if dt < 25 else 2 if dt < 42 else 3)
            self.present()
            dt = self.clock.tick(core.FPS)
            await asyncio.sleep(0)        # lets the browser draw; harmless on the desktop
        if self.slot_i is not None:
            self.save()
        pygame.quit()


async def main():
    await App().run()


if __name__ == "__main__":
    asyncio.run(main())

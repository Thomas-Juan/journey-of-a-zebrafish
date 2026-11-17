# -*- coding: utf-8 -*-
"""The player fish and the in-level scene."""
import math
import random
from collections import deque
import pygame
import gfx
import audio
import quiz
from core import (W, H, TILE, T_WATER, T_AIR, T_HAZ, T_CRACK, DIFF_HEARTS, DIFF_SPEED, draw_text, draw_wrapped,
                  panel, clamp)
from level import Level
from enemies import Enemy, Shot, BOSSES
from facts import FACTS, fact_id

rnd = random.Random(3)
POWER_NAMES = {"heart": "Regeneration: +1 heart", "shoal": "A shoal-mate joins you (absorbs one hit)",
               "star": "GFP glow: invincible!", "casper": "Casper: transparent - enemies can't see you",
               "crispr": "CRISPR: press X to cut"}


class Player:
    w, h = 26, 14

    def __init__(self, g, x, y):
        self.x, self.y, self.vx, self.vy = float(x), float(y), 0.0, 0.0
        self.face = 1
        self.hearts = g.maxhearts
        self.inv = self.dash_t = self.dash_cd = self.star = self.casper = self.shoot_cd = 0
        self.crispr, self.shoal = False, g.app.slot["up"]["shoal"]
        self.dead, self.dead_t, self.air, self.leap = False, 0, False, False
        self.air_dashed = False
        self.trail = deque([(x, y)] * 60, maxlen=60)

    def rect(self):
        return pygame.Rect(self.x - 13, self.y - 7, 26, 14)

    def push(self, g, dx, dy):
        lv = g.level
        n = max(1, int(max(abs(dx), abs(dy)) // 6) + 1)
        hx = hy = False
        for _ in range(n):
            if dx and not hx:
                if lv.rect_hits(self.x + dx / n, self.y, self.w, self.h):
                    hx = True
                else:
                    self.x += dx / n
            if dy and not hy:
                if lv.rect_hits(self.x, self.y + dy / n, self.w, self.h):
                    hy = True
                else:
                    self.y += dy / n
        return hx, hy

    def update(self, g, inp):
        lv = g.level
        if self.dead:
            self.dead_t -= 1
            self.y -= 0.6
            return
        ix, iy = inp.axis()
        if ix:
            self.face = ix
        was_air = self.air
        self.air = lv.at(self.x, self.y) == T_AIR
        if not self.air:
            self.air_dashed = False
        if "dash" in inp.pressed and self.dash_cd == 0 and not (self.air and not lv.zero_g and self.air_dashed):
            if self.air:
                self.air_dashed = True      # a single dash per flight: no flying over the level
            dx, dy = (ix, iy) if (ix or iy) else (self.face, 0)
            d = math.hypot(dx, dy)
            self.vx, self.vy = dx / d * 9.5, dy / d * 9.5
            self.dash_t, self.dash_cd = 12, g.dash_cd
            audio.sfx("dash")
            g.burst(self.x, self.y, (220, 240, 255), 5)
        if self.air:
            if lv.zero_g:
                self.vx = clamp(self.vx + ix * 0.12, -6, 6)
                self.vy = clamp(self.vy + iy * 0.12, -6, 6)
            else:
                self.vy = min(11, self.vy + 0.45)
                self.vx = clamp((self.vx + ix * 0.18) * 0.99, -7.5, 7.5) if self.dash_t == 0 else self.vx
            if self.dash_t or self.leap:
                self.leap = True
        else:
            self.leap = False
            if self.dash_t == 0:
                self.vx = (self.vx + ix * 0.42) * 0.9
                self.vy = (self.vy + iy * 0.42) * 0.9
            for zr, fx, fy in lv.zones:
                if zr.collidepoint(self.x, self.y):
                    self.push(g, fx, fy)
        if was_air != self.air:
            audio.sfx("splash")
            g.burst(self.x, self.y, (235, 250, 255), 8)
            if not self.air:
                self.vy *= 0.6
        for a in ("dash_t", "dash_cd", "inv", "star", "casper", "shoot_cd"):
            v = getattr(self, a)
            if v > 0:
                setattr(self, a, v - 1)
        hx, hy = self.push(g, self.vx, self.vy)
        if self.dash_t > 0:
            if g.tick % 2 == 0:
                g.parts.append([self.x - self.vx, self.y + rnd.randint(-5, 5), 0, -0.4, 22, (205, 235, 255)])
            if hx or hy:
                r = self.rect().inflate(16, 16)
                for btx in range(r.left // TILE, r.right // TILE + 1):
                    for bty in range(r.top // TILE, r.bottom // TILE + 1):
                        if lv.get(btx, bty) == T_CRACK:
                            g.break_block(btx, bty)
        if hx:
            self.vx = 0 if not (self.air and lv.zero_g) else -self.vx * 0.5
        if hy:
            if self.air and not lv.zero_g and self.vy > 0:   # stranded on a ledge: flop
                self.vy = -4.8
                self.vx = (ix or self.face) * 2.8
                self.leap = False
            elif self.air and lv.zero_g:
                self.vy = -self.vy * 0.5
            else:
                self.vy = 0
        self.x = max(14, self.x)
        if lv.at(self.x, self.y) == T_HAZ:
            self.damage(g)
        if self.crispr and "shoot" in inp.pressed and self.shoot_cd == 0:
            g.shots.append(Shot(self.x + self.face * 16, self.y, self.face * 8.5, 0, "scissors", True, life=55))
            self.shoot_cd = 16
            audio.sfx("shoot")
        self.trail.append((self.x, self.y))

    def damage(self, g, kill=False):
        if self.dead or (not kill and (self.inv > 0 or self.star > 0)):
            return
        audio.sfx("hurt")
        g.shake = 8
        if kill:
            self.hearts = 0
        elif self.shoal > 0:
            self.shoal -= 1
            g.burst(self.x, self.y, (230, 225, 200), 10)
        elif self.crispr:
            self.crispr = False
        else:
            self.hearts -= 1
        self.inv = 100 if g.diff else 130
        self.vx, self.vy, self.dash_t = -self.face * 4.0, -1.0, 0
        if self.hearts <= 0:
            self.dead, self.dead_t = True, 70
            audio.sfx("die")
            g.burst(self.x, self.y, (255, 120, 120), 20)

    def draw(self, s, cx, cy, tick):
        if self.dead:
            im = pygame.transform.flip(gfx.player("", 0, 0, self.face < 0), False, True)
            s.blit(im, (self.x - cx - 20, self.y - cy - 10))
            return
        fl = self.face < 0
        for i in range(self.shoal):
            bx, by = self.trail[-9 * (i + 1) - 1]
            s.blit(gfx.buddy((tick // 7 + i) % 2, fl), (bx - cx - 13 - self.face * 8, by - cy - 6 + (8 if i % 2 else -8)))
        if self.inv and tick % 6 < 3:
            return
        var = "star" if self.star else "casper" if self.casper else "crispr" if self.crispr else ""
        if self.star and self.star < 90 and tick % 10 < 5:
            var = ""
        moving = abs(self.vx) + abs(self.vy) > 0.6
        ang = int(round(math.degrees(math.atan2(-self.vy, abs(self.vx) + 1.5)) / 15))
        ang = clamp(ang, -5, 5) * (-1 if fl else 1)
        im = gfx.player(var, (tick // (5 if moving else 14)) % 2, ang, fl)
        s.blit(im, (self.x - cx - im.get_width() / 2, self.y - cy - im.get_height() / 2))
        if self.dash_t:
            pygame.draw.circle(s, (255, 255, 255), (self.x - cx - self.vx * 2, self.y - cy - self.vy * 2), 5, 1)


class Play:
    overlay = False

    def __init__(self, app, spec):
        self.app, self.spec = app, spec
        slot = app.slot
        self.diff = slot["diff"]
        self.espeed = DIFF_SPEED[self.diff]
        self.level = Level(spec)
        self.world = spec["world"]
        up = slot["up"]
        self.maxhearts = DIFF_HEARTS[self.diff] + up["heart"]
        self.dash_cd = (40, 32, 26)[up["dash"]]
        self.magnet = 110 if up["magnet"] else 0
        wi0 = app.level_index_in_world(spec) * 3
        self.pages = [0, 0, 0] if spec["boss"] else [int(fact_id(self.world, wi0 + i) in slot["pages"]) for i in range(3)]
        self.letters = [0] * 5
        self.respawn = self.level.start
        self.food, self.time, self.tick = 0, 0, 0
        self.state, self.lock = "intro", 20
        self.popup = None
        self.toast = ["", 0]
        self.speech = ["", 0]
        self.cx = self.cy = 0.0
        self.shake = 0
        self.freeze = 0
        self.asked = set()
        self.quiz = None
        self.exam_left = self.exam_wrong = 0
        self.exam_done = False
        self.exam_hearts, self.exam_bonus = None, False
        self.buf = set()
        self._dark = None
        self.end_t = 0
        self.parts = []
        self.reset()
        audio.music(audio.level_key(spec, app.level_index_in_world(spec)))

    def reset(self):
        lv = self.level
        self.p = Player(self, *self.respawn)
        self.enemies = [Enemy(self, k, x, y) for k, x, y in lv.spawns]
        self.boss = None
        if self.spec["boss"]:
            self.boss = BOSSES[self.spec["boss"]](self)
            self.enemies.append(self.boss)
        if self.boss and self.exam_hearts is not None:
            self.p.hearts = self.exam_hearts
            if self.exam_bonus:
                self.p.shoal = min(3, self.p.shoal + 1)
        self.shots = []
        self.chase_x = self.respawn[0] - 520
        self.cx = clamp(self.p.x - W / 2, 0, max(0, lv.pw - W))

    # ---------------------------------------------------------- helpers
    def burst(self, x, y, col, n):
        for _ in range(n):
            a = rnd.uniform(0, math.tau)
            sp = rnd.uniform(0.5, 3)
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp, rnd.randint(14, 30), col])

    def drop_food(self, x, y):
        self.level.items.append(dict(kind="food", x=x, y=y))

    def break_block(self, tx, ty):
        self.level.put(tx, ty, T_WATER)
        self.burst((tx + 0.5) * TILE, (ty + 0.5) * TILE, gfx.THEMES[self.level.theme]["g"], 14)
        self.burst((tx + 0.5) * TILE, (ty + 0.5) * TILE, (255, 240, 200), 6)
        audio.sfx("pop")
        self.shake = max(self.shake, 5)

    def ask(self, kind):
        self.quiz = quiz.pick(self.app.slot, self.world, rnd, self.asked)
        self.quiz["kind"] = kind
        rec = self.app.slot["levels"].get(self.spec["id"], {})
        self.quiz["scored"] = rec.get("gateq", 0) < 1 if kind == "gate" else rec.get("examq", 0) < 3
        self.asked.add(self.quiz["q"])
        if kind == "exam":
            self.exam_left -= 1
        self.state, self.lock = "quiz", 25

    def _quiz_update(self, inp):
        q, p = self.quiz, self.p
        if q["answer"] is None:
            d = ("down" in inp.pressed) - ("up" in inp.pressed)
            if d:
                q["sel"] = (q["sel"] + d) % len(q["opts"])
                audio.sfx("blip")
            if self.lock == 0 and "ok" in inp.pressed:
                q["answer"] = q["opts"][q["sel"]]
                right = q["answer"] == q["correct"]
                if q["scored"]:
                    rec = self.app.slot["levels"].setdefault(self.spec["id"], {})
                    key = "gateq" if q["kind"] == "gate" else "examq"
                    rec[key] = rec.get(key, 0) + 1
                    quiz.score(self.app.slot, right)
                audio.sfx("right" if right else "wrong")
                if q["kind"] == "gate":
                    if right:
                        self.food += 30
                        p.hearts = min(self.maxhearts, p.hearts + 1)
                    else:
                        p.hearts = max(1, p.hearts - 1)
                        self.food = max(0, self.food - 15)
                        self.shake = 8
                elif not right:
                    self.exam_wrong += 1
                self.lock = 30
        elif self.lock == 0 and ("ok" in inp.pressed or "dash" in inp.pressed):
            if q["kind"] == "exam" and self.exam_left > 0:
                self.ask("exam")
                return
            if q["kind"] == "exam":
                p.hearts = self.exam_hearts = max(2, self.maxhearts - self.exam_wrong)
                self.exam_bonus = self.exam_wrong == 0
                if self.exam_bonus:
                    p.shoal = min(3, p.shoal + 1)
                    self.toast = ["Perfect exam! A shoal-mate joins you.", 180]
                else:
                    self.toast = ["%d wrong answer%s: you start with %d heart%s." % (
                        self.exam_wrong, "" if self.exam_wrong == 1 else "s", p.hearts, "" if p.hearts == 1 else "s"), 200]
            self.state = "play"
            self.app.save()

    def say(self, text):
        self.speech = [text, 170]

    # ---------------------------------------------------------- update
    def update(self, inp):
        self.tick += 1
        if self.lock > 0:
            self.lock -= 1
        if self.state == "intro":
            if self.lock == 0 and ("ok" in inp.pressed or "dash" in inp.pressed):
                self.state = "play"
                if self.boss and not self.exam_done:
                    self.exam_done, self.exam_left = True, 3
                    self.ask("exam")
            elif "back" in inp.pressed:
                self.app.pop()
            return
        if self.state == "popup":
            if self.lock == 0 and ("ok" in inp.pressed or "dash" in inp.pressed):
                self.state = "play"
            return
        if self.state == "quiz":
            self._quiz_update(inp)
            return
        if "back" in inp.pressed:
            self.app.pause(self)
            return
        if self.freeze > 0:
            self.freeze -= 1
            self.buf |= inp.pressed & {"dash", "shoot"}
            return
        inp.pressed |= self.buf
        self.buf = set()
        self.time += 1
        self.app.slot["time"] += 1 / 60.0
        p, lv = self.p, self.level
        p.update(self, inp)
        if p.dead:
            if p.dead_t <= 0:
                self.app.slot["deaths"] += 1
                self.reset()
            self._parts()
            return
        for e in self.enemies:
            if (e.boss and not e.dead) or (not e.boss and abs(e.x - p.x) < 780):
                e.update(self)
        self._contacts()
        self.enemies = [e for e in self.enemies if not e.dead or e.boss]
        for sh in self.shots:
            sh.update(self)
            if sh.friendly:
                for e in self.enemies:
                    if not e.dead and e.rect().inflate(10, 10).collidepoint(sh.x, sh.y):
                        if e.boss or not e.inv:
                            e.hit(self)
                        sh.dead = True
                        break
            elif abs(sh.x - p.x) < 17 and abs(sh.y - p.y) < 12:
                sh.dead = True
                if not p.star:
                    p.damage(self)
        self.shots = [s for s in self.shots if not s.dead]
        self._items()
        self._parts()
        ch = self.spec.get("chase")
        if ch and self.state == "play":
            self.chase_x += ch * self.espeed
            if p.x < self.chase_x:
                p.damage(self, kill=True)
        if self.boss and not self.boss.dead and self.tick % 1300 == 1299 and not any(i["kind"] == "power" for i in lv.items):
            lv.items.append(dict(kind="power", name="heart", x=rnd.randint(150, 800), y=rnd.randint(200, 420)))
        if self.boss and self.boss.dead:
            self.shots = []
            self.enemies = [e for e in self.enemies if e.boss]
            p.inv = max(p.inv, 30)
            self.end_t += 1
            if self.end_t % 8 == 0:
                self.burst(self.boss.x + rnd.randint(-50, 50), self.boss.y + rnd.randint(-40, 40), (255, 230, 120), 8)
                audio.sfx("pop")
            if self.end_t > 110:
                self._clear()
        # camera
        tx = clamp(p.x - W / 2 + p.face * 70, 0, max(0, lv.pw - W))
        self.cx += (tx - self.cx) * 0.1
        ymin = -110 if (lv.air or lv.zero_g) else 0
        ty = clamp(p.y - H / 2, ymin, max(ymin, lv.ph - H))
        if lv.ph - H < 40 and p.y > 150:
            ty = lv.ph - H
        self.cy += (ty - self.cy) * 0.12

    def _contacts(self):
        p = self.p
        pr = p.rect()
        attack = p.dash_t > 0 or p.leap
        for e in self.enemies:
            if e.dead or (not e.boss and (e.ai in ("beam", "emit") or abs(e.x - p.x) > 240)):
                continue
            if not pr.colliderect(e.rect()):
                continue
            if e.boss:
                if e.hurt:
                    continue
                if p.star or attack:
                    landed = e.hit(self)
                    if not landed and e.spiky and not p.star:
                        p.damage(self)
                    elif not p.star:
                        self._bounce(45 if landed else 8)
                else:
                    p.damage(self)
            elif p.star:
                e.hit(self, 3)
            elif attack:
                if e.spiky:
                    p.damage(self)
                elif e.dash:
                    if e.hit(self):
                        self._bounce(14)
                        p.dash_cd = min(p.dash_cd, 12)
                else:
                    if p.inv == 0:
                        audio.sfx("clang")
                    self._bounce(25)
            elif p.casper and e.ai != "vortex":
                continue
            else:
                p.damage(self)

    def _bounce(self, inv):
        p = self.p
        p.vx, p.vy, p.dash_t = -p.vx * 0.5, -p.vy * 0.5, 0
        p.inv = max(p.inv, inv)

    def _items(self):
        p, lv, slot = self.p, self.level, self.app.slot
        for it in lv.items:
            dx, dy = it["x"] - p.x, it["y"] - p.y
            k = it["kind"]
            if k == "goal":
                if p.x > it["x"] - 30:
                    self._clear()
                    return
                continue
            if k == "gate":
                if p.x > it["x"] and self.state == "play":
                    it["dead"] = True
                    self.ask("gate")
                continue
            if abs(dx) > 140:
                continue
            d = math.hypot(dx, dy)
            if k == "food":
                if self.magnet and d < self.magnet:
                    it["x"] -= dx / (d + 1) * 5
                    it["y"] -= dy / (d + 1) * 5
                if d < 24:
                    it["dead"] = True
                    self.food += 1
                    audio.sfx("food")
            elif k == "page":
                if d < 30:
                    it["dead"] = True
                    new = not self.pages[it["idx"]]
                    self.pages[it["idx"]] = 1
                    wi = self.app.level_index_in_world(self.spec) * 3 + it["idx"]
                    self.app.give_page(self.world, wi)
                    self.popup = FACTS[self.world][wi] + (new,)
                    self.state, self.lock = "popup", 35
                    audio.sfx("page")
            elif k == "power":
                if d < 32:
                    it["dead"] = True
                    n = it["name"]
                    audio.sfx("power")
                    if n == "heart":
                        p.hearts = min(self.maxhearts, p.hearts + 1)
                    elif n == "shoal":
                        p.shoal = min(3, p.shoal + 1)
                    elif n == "star":
                        p.star = 480
                    elif n == "casper":
                        p.casper = 600
                    else:
                        p.crispr = True
                    self.toast = [POWER_NAMES[n], 150]
            elif k == "letter":
                if d < 30:
                    it["dead"] = True
                    self.letters[it["idx"]] = 1
                    audio.sfx("check")
                    if all(self.letters):
                        self.food += 50
                        p.hearts = self.maxhearts
                        p.shoal = min(3, p.shoal + 1)
                        audio.sfx("right")
                        self.toast = ["D-A-N-I-O!  +50 food, full hearts and a shoal-mate", 200]
            elif k == "jet":
                if d < 30 and p.dash_t == 0:
                    p.x, p.y = it["x"], it["y"]
                    p.vx, p.vy, p.dash_t = it["dx"] * 13, it["dy"] * 13, 18
                    audio.sfx("power")
                    self.burst(p.x, p.y, (255, 255, 255), 14)
            elif k == "check":
                if not it["on"] and abs(dx) < 30:
                    it["on"] = True
                    self.respawn = (it["x"], it["y"] - 48)
                    p.hearts = min(self.maxhearts, p.hearts + 1)
                    audio.sfx("check")
                    self.toast = ["Checkpoint! (+1 heart)", 110]
        lv.items = [it for it in lv.items if not it.get("dead")]

    def _parts(self):
        for q in self.parts:
            q[0] += q[2]
            q[1] += q[3]
            q[4] -= 1
        self.parts = [q for q in self.parts if q[4] > 0]
        if self.toast[1] > 0:
            self.toast[1] -= 1
        if self.speech[1] > 0:
            self.speech[1] -= 1
        if self.shake > 0:
            self.shake -= 1

    def _clear(self):
        audio.sfx("win")
        self.app.finish_level(self)

    # ---------------------------------------------------------- draw
    def draw(self, s):
        lv, p, tick = self.level, self.p, self.tick
        shaking = self.shake and self.state == "play" and self.app.stack[-1] is self
        cx = int(self.cx + (rnd.randint(-4, 4) if shaking else 0))
        cy = int(self.cy + (rnd.randint(-4, 4) if shaking else 0))
        lv.draw(s, cx, cy, tick)
        for zr, fx, fy in lv.zones:
            if zr.right - cx < -20 or zr.x - cx > W + 20:
                continue
            for i in range(26 if fx else 12):
                if fx:
                    yy = (i * 53) % zr.h
                    xx = zr.x + ((i * 197 + tick * fx * 4) % zr.w)
                    pygame.draw.line(s, (255, 255, 255), (xx - cx, yy - cy), (xx - cx - fx * 14, yy - cy), 1)
                else:
                    xx = zr.x + (i * 37) % zr.w
                    yy = zr.y + ((i * 97 + tick * fy * 3) % zr.h)
                    pygame.draw.circle(s, (225, 245, 255), (xx - cx, yy - cy), 2 + i % 3, 1)
                    if i % 4 == 0:
                        pygame.draw.line(s, (255, 255, 255), (xx - cx, yy - cy + 8), (xx - cx, yy - cy + 8 + fy * 10), 1)
        for sx, text in lv.signs:
            x = sx * TILE - cx
            if -420 < x < W:
                wd = min(400, 20 + len(text) * 9)
                panel(s, (x, (lv.air + 0.4) * TILE - cy, wd, 30), alpha=170)
                draw_text(s, text, (x + 10, (lv.air + 0.4) * TILE - cy + 5), 15, (255, 255, 220), shadow=False)
        for it in lv.items:
            x, y = it["x"] - cx, it["y"] - cy
            if x < -100 or x > W + 100:
                continue
            k = it["kind"]
            if k == "food":
                s.blit(gfx.icon("food", (tick // 12) % 2), (x - 8, y - 8))
            elif k == "page":
                im = gfx.icon("page")
                if self.pages[it["idx"]] and tick % 20 < 10:
                    im = gfx.icon("page0")
                s.blit(im, (x - 13, y - 16 + math.sin(tick * 0.08) * 3))
            elif k == "power":
                s.blit(gfx.icon("bubble"), (x - 19, y - 19 + math.sin(tick * 0.06 + it["x"]) * 3))
                s.blit(gfx.icon("pw_" + it["name"]), (x - 12, y - 12 + math.sin(tick * 0.06 + it["x"]) * 3))
            elif k == "letter":
                yy = y + math.sin(tick * 0.07 + it["idx"]) * 4
                pygame.draw.circle(s, (255, 205, 60), (x, yy), 15)
                pygame.draw.circle(s, (150, 90, 20), (x, yy), 15, 2)
                draw_text(s, "DANIO"[it["idx"]], (x, yy - 13), 20, (90, 40, 10), center=True, bold=True, shadow=False)
            elif k == "jet":
                r = 20 + (tick // 6) % 3 * 2
                pygame.draw.circle(s, (255, 255, 255), (x, y), r, 3)
                pygame.draw.circle(s, (140, 220, 255), (x, y), 14)
                pygame.draw.line(s, (255, 255, 255), (x, y), (x + it["dx"] * 26, y + it["dy"] * 26), 4)
            elif k == "gate":
                band = pygame.Surface((26, H), pygame.SRCALPHA)
                band.fill((255, 225, 90, 70 + int(math.sin(tick * 0.1) * 25)))
                s.blit(band, (x - 13, 0))
                pygame.draw.line(s, (255, 244, 170), (x - 13, 0), (x - 13, H), 2)
                pygame.draw.line(s, (255, 244, 170), (x + 13, 0), (x + 13, H), 2)
                for q in range(4):
                    draw_text(s, "?", (x, (q * 140 + tick) % H - 14), 22, (120, 70, 0), center=True, bold=True, shadow=False)
            elif k == "check":
                if not it["on"]:
                    beam = pygame.Surface((8, H), pygame.SRCALPHA)
                    beam.fill((255, 255, 255, 26))
                    s.blit(beam, (x - 4, 0))
                s.blit(gfx.icon("check1" if it["on"] else "check"), (x - 6, y - 60))
            elif k == "goal":
                s.blit(gfx.icon("goal", (tick // 10) % 2), (x - 48, y - 75))
                draw_text(s, "GOAL", (x, y - 100), 16, (255, 255, 255), center=True, bold=True)
        for e in self.enemies:
            if not e.dead and (e.boss or -160 < e.x - cx < W + 160):
                e.draw(s, cx, cy, tick)
        for sh in self.shots:
            sh.draw(s, cx, cy, tick)
        p.draw(s, cx, cy, tick)
        for q in self.parts:
            pygame.draw.circle(s, q[5], (q[0] - cx, q[1] - cy), max(1, q[4] // 8))
        if self.spec.get("chase"):
            wx = self.chase_x - cx
            if wx > -40:
                wave = pygame.Surface((max(1, int(wx) + 40), H), pygame.SRCALPHA)
                wave.fill((120, 90, 60, 150) if self.world == 1 else (200, 40, 40, 110))
                s.blit(wave, (0, 0))
                for y in range(0, H, 24):
                    pygame.draw.circle(s, (255, 255, 255), (wx + 34 + math.sin(tick * 0.2 + y) * 8, y + 12), 12)
        if self.spec.get("dark"):
            if self._dark is None:
                self._dark = pygame.Surface((W, H), pygame.SRCALPHA)
            d = self._dark
            d.fill((0, 0, 12, 232))
            lights = [(p.x, p.y, 250 if p.star else 170)]
            for it in lv.items:
                if it["kind"] in ("page", "power", "check", "goal") and -80 < it["x"] - cx < W + 80:
                    lights.append((it["x"], it["y"] - (30 if it["kind"] == "check" else 0), 120 if it["kind"] == "goal" else 56))
            for e in self.enemies:
                if not e.boss and e.ai == "beam" and e.on:
                    lights.append((e.brect.centerx, e.brect.centery, 110))
            for lx, ly, r in lights:
                m = gfx.light_mask(r)
                d.blit(m, (lx - cx - r, ly - cy - r), special_flags=pygame.BLEND_RGBA_SUB)
            s.blit(d, (0, 0))
        s.blit(gfx.vignette(), (0, 0))
        self._hud(s)
        if self.state == "intro":
            self._card(s)
        elif self.state == "popup":
            self._popup(s)
        elif self.state == "quiz":
            self._quiz_draw(s)

    def _hud(self, s):
        p, slot = self.p, self.app.slot
        for i in range(self.maxhearts):
            s.blit(gfx.icon("heart" if i < p.hearts else "heart0"), (12 + i * 26, 10))
        s.blit(gfx.icon("food"), (14, 38))
        draw_text(s, str(slot["food"] + self.food), (36, 34), 18, bold=True)
        if not self.boss:
            for i in range(3):
                s.blit(gfx.icon("page" if self.pages[i] else "page0"), (W - 100 + i * 30, 8))
        for i in range(0 if self.boss else 5):
            draw_text(s, "DANIO"[i], (W - 104 + i * 19, 44), 17, (255, 205, 60) if self.letters[i] else (70, 80, 100), bold=True)
        x = 100
        for cond, ic, val in ((p.star, "pw_star", p.star / 480), (p.casper, "pw_casper", p.casper / 600), (p.crispr, "pw_crispr", 1)):
            if cond:
                s.blit(gfx.icon(ic), (x, 34))
                pygame.draw.rect(s, (255, 255, 255), (x, 60, 24 * val, 3))
                x += 32
        if p.dash_cd:
            pygame.draw.rect(s, (120, 200, 255), (12, 64, 60 * (1 - p.dash_cd / self.dash_cd), 4))
        else:
            pygame.draw.rect(s, (255, 255, 255), (12, 64, 60, 4))
        draw_text(s, self.spec["id"].replace("B", "Boss") + "  " + self.spec["name"], (W / 2, 8), 15, (220, 240, 255), center=True)
        if self.boss and not self.boss.dead:
            b = self.boss
            panel(s, (W / 2 - 202, H - 34, 404, 22), alpha=200)
            pygame.draw.rect(s, (230, 60, 70), (W / 2 - 198, H - 30, 396 * b.hp / b.maxhp, 14))
            draw_text(s, b.name, (W / 2, H - 56), 16, center=True, bold=True)
        draw_text(s, "ESC: menu", (W - 10, H - 20), 12, (200, 225, 240), right=True)
        if self.toast[1] > 0:
            draw_text(s, self.toast[0], (W / 2, 70), 18, (255, 255, 160), center=True, bold=True)
        if self.speech[1] > 0:
            wd = 40 + len(self.speech[0]) * 10
            panel(s, (W / 2 - wd / 2, 96, wd, 36), fill=(250, 250, 240), border=(60, 40, 40), alpha=240)
            draw_text(s, self.speech[0], (W / 2, 103), 17, (40, 20, 20), center=True, shadow=False)

    def _card(self, s):
        sp = self.spec
        panel(s, (140, 130, 680, 280))
        draw_text(s, "World %d  -  %s" % (self.world, sp["when"]), (W / 2, 148), 17, (150, 210, 250), center=True)
        draw_text(s, sp["name"], (W / 2, 176), 34, (255, 255, 255), center=True, bold=True)
        draw_wrapped(s, sp["blurb"], (W / 2, 240), 19, 600, (230, 240, 250), center=True)
        if self.tick % 60 < 40:
            draw_text(s, "SPACE: dive in", (W / 2, 362), 17, (255, 240, 150), center=True)
        draw_text(s, "ESC: back to the map", (W / 2, 388), 13, (170, 200, 220), center=True)

    def _quiz_draw(self, s):
        q = self.quiz
        gate = q["kind"] == "gate"
        panel(s, (110, 40, 740, 460), fill=(20, 26, 48), border=(255, 225, 90), alpha=246)
        draw_text(s, "PEER-REVIEW GATE" if gate else "QUALIFYING EXAM   question %d of 3" % (3 - self.exam_left), (W / 2, 52), 20, (255, 225, 90), center=True, bold=True)
        draw_text(s, "Right: +1 heart, +30 food, +%d knowledge.   Wrong: -1 heart, -15 food, -%d knowledge." % (quiz.GAIN, quiz.LOSS) if gate else
                  "Each wrong answer costs one heart for the boss fight. All three right: a shoal-mate.", (W / 2, 82), 13, (170, 200, 225), center=True)
        if not q.get("scored", True):
            draw_text(s, "Practice: you have already been examined here, so knowledge is not counted this time.", (W / 2, 98), 12, (255, 200, 140), center=True)
        y = draw_wrapped(s, q["q"], (150, 118), 18, 660, (240, 244, 252), lh=25)
        y = max(y + 10, 250)
        for k, o in enumerate(q["opts"]):
            col = (214, 226, 240)
            if q["answer"] is not None:
                col = (110, 240, 130) if o == q["correct"] else (240, 110, 110) if o == q["answer"] else (120, 130, 145)
            elif k == q["sel"]:
                col = (255, 240, 150)
            panel(s, (190, y + k * 50, 580, 42), border=col, alpha=210)
            draw_text(s, o, (W / 2, y + 8 + k * 50), 18, col, center=True)
        if q["answer"] is not None:
            ok = q["answer"] == q["correct"]
            draw_text(s, ("Correct!" if ok else "Wrong - the right answer is in green.") + ("   SPACE to continue" if self.lock == 0 else ""),
                      (W / 2, y + 156), 16, (150, 255, 170) if ok else (255, 150, 150), center=True, bold=True)
            if q.get("why"):
                draw_wrapped(s, q["why"], (W / 2, y + 182), 14, 660, (220, 230, 245), center=True, lh=19)

    def _popup(self, s):
        when, title, text, new = self.popup
        panel(s, (130, 110, 700, 320), fill=(250, 246, 225), border=(170, 60, 60), alpha=250)
        pygame.draw.rect(s, (200, 70, 70), (130, 110, 26, 320), border_top_left_radius=10, border_bottom_left_radius=10)
        draw_text(s, "LAB NOTEBOOK" + ("  -  new page!" if new else ""), (176, 124), 14, (150, 60, 60), shadow=False, bold=True)
        draw_text(s, when, (810, 124), 15, (90, 100, 140), shadow=False, right=True)
        draw_text(s, title, (176, 152), 28, (30, 40, 80), shadow=False, bold=True)
        for i in range(9):
            pygame.draw.line(s, (200, 210, 235), (176, 222 + i * 30, ), (806, 222 + i * 30), 1)
        draw_wrapped(s, text, (176, 198), 20, 630, (40, 40, 60), lh=30)
        if self.lock == 0 and self.tick % 60 < 40:
            draw_text(s, "SPACE to continue", (W / 2, 400), 15, (150, 60, 60), center=True, shadow=False)

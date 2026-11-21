# -*- coding: utf-8 -*-
"""Enemies, projectiles and bosses."""
import math
import random
import pygame
import gfx
import audio
from core import dr, hsurf, TILE, T_WATER, T_AIR, draw_text
from worlds import ETYPES, SPLIT_INTO, BEAM

rnd = random.Random(7)


def sign(v):
    return (v > 0) - (v < 0)


class Shot:
    def __init__(self, x, y, vx, vy, skin, friendly=False, grav=0.0, life=400):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.skin, self.friendly, self.grav, self.life = skin, friendly, grav, life
        self.dead = False

    def update(self, g):
        self.vy += self.grav
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        tx, ty = int(self.x // TILE), int(self.y // TILE)
        if self.friendly and g.level.get(tx, ty) == 5:
            g.break_block(tx, ty)
            self.dead = True
        if self.life <= 0 or g.level.solid(tx, ty):
            self.dead = True

    def draw(self, s, cx, cy, tick):
        im = gfx.spr(self.skin, (tick // 8) % 2, self.vx < 0)
        s.blit(im, (self.x - cx - im.get_width() / 2, self.y - cy - im.get_height() / 2))


class Enemy:
    boss = False

    def __init__(self, g, k, x, y):
        self.k = k
        self.ai, self.hp, self.spd, self.w, self.h, self.dash, self.spiky, self.place, self.label = ETYPES[k]
        self.spd *= g.espeed
        self.x, self.y, self.hx, self.hy = x, y, x, y
        self.dir = -1
        self.vx = self.vy = 0.0
        self.t = rnd.randint(0, 200)
        self.state, self.timer = "idle", 0
        self.dead, self.hurt, self.skin = False, 0, k
        self.inv = self.hp >= 99
        if self.ai == "bounce":
            self.vx, self.vy = self.spd * rnd.choice((-0.7, 0.7)), self.spd * rnd.choice((-0.7, 0.7))
        if self.ai == "beam":
            d, self.bcol, self.period, self.ontime = BEAM[k]
            lv = g.level
            tx, ty = int(x // TILE), int(y // TILE)
            step = 1 if d == "down" else -1
            n = 0
            while n < 12 and lv.get(tx, ty + step * (n + 1)) in (T_WATER, 3):
                n += 1
            y0 = y + (self.h / 2 if step > 0 else -self.h / 2)
            y1 = y0 + step * n * TILE
            self.brect = pygame.Rect(x - 13, min(y0, y1), 26, abs(y1 - y0))
            self.t = (int(x) // 260 * 37) % self.period
            self.on = self.warn = False

    def rect(self):
        return pygame.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)

    # ---- movement helpers
    def ok(self, g, x, y):
        lv = g.level
        if lv.rect_hits(x, y, self.w, self.h):
            return False
        return lv.at(x, y) == T_WATER

    def move(self, g, dx, dy):
        hx = hy = False
        if dx:
            if self.ok(g, self.x + dx, self.y):
                self.x += dx
            else:
                hx = True
        if dy:
            if self.ok(g, self.x, self.y + dy):
                self.y += dy
            else:
                hy = True
        return hx, hy

    def toward(self, tx, ty, spd):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1
        return dx / d * spd, dy / d * spd, d

    def sees(self, g, r):
        p = g.p
        return p.casper <= 0 and not p.dead and abs(p.x - self.x) < r and abs(p.y - self.y) < r * 0.8

    # ---- AI
    def update(self, g):
        self.t += 1
        if self.hurt:
            self.hurt -= 1
        if self.timer > 0:
            self.timer -= 1
        getattr(self, "ai_" + self.ai)(g)

    def ai_patrol(self, g, k=1.0):
        hx, _ = self.move(g, self.dir * self.spd * k, math.sin(self.t * 0.05) * 0.4)
        if hx or abs(self.x - self.hx) > 190:
            self.dir = -self.dir if hx else -sign(self.x - self.hx)

    ai_split = ai_patrol

    def ai_crawl(self, g):
        lv = g.level
        nx = self.x + self.dir * (self.w / 2 + 2)
        ahead = lv.solid(int(nx // TILE), int(self.y // TILE))
        ground = lv.solid(int(nx // TILE), int((self.y + self.h / 2 + 6) // TILE))
        if ahead or not ground or lv.at(nx, self.y) != T_WATER:
            self.dir = -self.dir
        else:
            self.x += self.dir * self.spd

    def ai_float(self, g):
        self.y = self.hy + math.sin(self.t * 0.04) * 26
        self.x = self.hx + math.sin(self.t * 0.017) * 18

    def ai_circle(self, g):
        self.x = self.hx + math.cos(self.t * 0.04 * self.spd) * 44
        self.y = self.hy + math.sin(self.t * 0.04 * self.spd) * 44
        self.dir = 1 if math.sin(self.t * 0.04 * self.spd) < 0 else -1

    def ai_bob(self, g):
        _, hy = self.move(g, 0, self.dir * self.spd)
        if hy or abs(self.y - self.hy) > 100:
            self.dir = -self.dir if hy else -sign(self.y - self.hy)

    def ai_chase(self, g):
        if self.sees(g, 270):
            vx, vy, d = self.toward(g.p.x, g.p.y, self.spd)
            self.move(g, vx, vy)
            self.dir = sign(vx) or self.dir
        else:
            self.ai_patrol(g, 0.5)

    def ai_homing(self, g):
        if self.sees(g, 430):
            vx, vy, d = self.toward(g.p.x, g.p.y, 0.09)
            self.vx = (self.vx + vx) * 0.985
            self.vy = (self.vy + vy) * 0.985
            sp = math.hypot(self.vx, self.vy)
            if sp > self.spd:
                self.vx, self.vy = self.vx / sp * self.spd, self.vy / sp * self.spd
            hx, hy = self.move(g, self.vx, self.vy)
            if hx or hy:
                self.kill(g)
            self.dir = sign(self.vx) or self.dir
        else:
            self.vx *= 0.9
            self.vy *= 0.9

    def ai_lunge(self, g):
        p = g.p
        if self.state == "idle":
            if self.sees(g, 240) and abs(p.y - self.y) < 110:
                self.state, self.timer = "tele", 34
                self.dir = sign(p.x - self.x) or 1
        elif self.state == "tele":
            if self.timer == 0:
                self.vx, self.vy, _ = self.toward(p.x, p.y, self.spd)
                self.state, self.timer = "go", 30
        elif self.state == "go":
            hx, hy = self.move(g, self.vx, self.vy)
            if self.timer == 0 or hx:
                self.state, self.timer = "rest", 70
        elif self.state == "rest":
            if self.timer == 0:
                self.state = "back"
        else:
            vx, vy, d = self.toward(self.hx, self.hy, 1.3)
            self.x += vx
            self.y += vy
            self.dir = sign(vx) or self.dir
            if d < 4:
                self.state = "idle"

    def ai_dive(self, g):
        p = g.p
        if self.state == "idle":
            if self.k in ("kingfisher", "fly") and abs(p.x - self.hx) < 170:
                self.x += max(-0.9, min(0.9, p.x - self.x))
            self.y = self.hy + math.sin(self.t * 0.1) * 3
            if self.timer == 0 and p.casper <= 0 and abs(p.x - self.x) < 46 and 0 < p.y - self.y < 340:
                self.state, self.timer = "tele", 30
        elif self.state == "tele":
            if self.timer == 0:
                self.state = "down"
        elif self.state == "down":
            ny = self.y + self.spd
            if ny > self.hy + 330 or g.level.solid(int(self.x // TILE), int((ny + self.h / 2) // TILE)):
                self.state, self.timer = "pause", 26
            else:
                self.y = ny
        elif self.state == "pause":
            if self.timer == 0:
                self.state = "up"
        else:
            self.y -= self.spd * 0.4
            if self.y <= self.hy:
                self.y, self.state, self.timer = self.hy, "idle", 50

    def ai_hop(self, g):
        lv = g.level
        self.vy += 0.22
        hx, hy = self.move(g, self.vx, self.vy)
        if hx:
            self.vx = -self.vx
        if hy:
            ground = self.vy > 0
            self.vy = 0
            if ground:
                self.vx *= 0.7
                if self.timer == 0:
                    d = sign(g.p.x - self.x) if self.sees(g, 330) else rnd.choice((-1, 1))
                    self.vx, self.vy = d * self.spd * 0.55, -self.spd * 1.25
                    self.dir = d
                    self.timer = rnd.randint(45, 80)

    def ai_kick(self, g):
        if self.timer == 0:
            if self.sees(g, 300):
                self.vx, self.vy, _ = self.toward(g.p.x, g.p.y, self.spd)
            else:
                a = rnd.uniform(0, math.tau)
                self.vx, self.vy = math.cos(a) * self.spd * 0.5, math.sin(a) * self.spd * 0.5
            self.dir = sign(self.vx) or self.dir
            self.timer = 58
        self.vx *= 0.955
        self.vy *= 0.955
        self.move(g, self.vx, self.vy)

    def ai_bounce(self, g):
        hx, hy = self.move(g, self.vx, self.vy)
        if hx:
            self.vx = -self.vx
        if hy:
            self.vy = -self.vy
        self.dir = sign(self.vx) or 1

    def ai_puff(self, g):
        if self.state == "idle":
            self.ai_patrol(g)
            if self.timer == 0 and self.sees(g, 140):
                self.state, self.timer = "puff", 120
                self.skin, self.spiky, self.dash, self.w, self.h = "fugu_puff", True, False, 40, 40
        elif self.timer == 0:
            self.state, self.timer = "idle", 90
            self.skin, self.spiky, self.dash, self.w, self.h = self.k, False, True, 34, 22

    def ai_vortex(self, g):
        p = g.p
        dx, dy = self.x - p.x, self.y - p.y
        d = math.hypot(dx, dy) or 1
        if d < 180 and not p.dead:
            f = 1.7 * (1 - d / 180)
            p.push(g, dx / d * f, dy / d * f)

    def ai_shoot(self, g):
        self.y = self.hy + math.sin(self.t * 0.03) * 30
        self.dir = sign(g.p.x - self.x) or 1
        if self.t % 120 == 0 and self.sees(g, 400):
            vx, vy, _ = self.toward(g.p.x, g.p.y, 3.0 * g.espeed)
            g.shots.append(Shot(self.x, self.y, vx, vy, "paper" if self.k == "reviewer" else "bolt"))

    def ai_emit(self, g):
        if self.t % 105 == 0 and abs(g.p.x - self.x) < 620:
            g.shots.append(Shot(self.x, self.y + 14, 0, 2.4, "drop"))

    def ai_beam(self, g):
        ph = self.t % self.period
        self.on = ph < self.ontime
        self.warn = ph > self.period - 34
        if self.on and not g.p.dead and self.brect.colliderect(g.p.rect()):
            g.p.damage(g)

    # ---- damage
    def hit(self, g, dmg=1):
        if self.inv or self.hurt:
            return False
        self.hp -= dmg
        self.hurt = 14
        if self.hp <= 0:
            self.kill(g)
        else:
            audio.sfx("clang")
        return True

    def kill(self, g):
        self.dead = True
        audio.sfx("pop")
        g.freeze = 3
        g.burst(self.x, self.y, (255, 255, 255), 10)
        g.burst(self.x, self.y, (255, 220, 120), 6)
        if self.k in SPLIT_INTO:
            for dx in (-16, 16):
                e = Enemy(g, SPLIT_INTO[self.k], self.x + dx, self.y)
                if not e.ok(g, e.x, e.y):          # would start inside a wall: use the parent's spot
                    e.x = e.hx = self.x
                e.hurt = 20
                g.enemies.append(e)
        elif rnd.random() < 0.35:
            g.drop_food(self.x, self.y)

    def draw(self, s, cx, cy, tick):
        if self.ai == "beam":
            r = self.brect.move(-cx, -cy)
            if self.on:
                b = hsurf(*r.size)
                b.fill(self.bcol + (120 + (tick % 6) * 12,))
                s.blit(b, r.topleft)
                dr.rect(s, (255, 255, 255), (r.centerx - 3, r.y, 6, r.h))
            elif self.warn and tick % 8 < 4:
                dr.line(s, self.bcol, (r.centerx, r.y), (r.centerx, r.bottom), 2)
        im = gfx.spr(self.skin, (tick // 10) % 2, self.dir < 0 and self.ai not in ("dive", "beam", "emit", "vortex"))
        x, y = self.x - cx - im.get_width() / 2, self.y - cy - im.get_height() / 2
        if self.state == "tele":
            x += (tick % 4) - 2
            draw_text(s, "!", (self.x - cx, self.y - cy - self.h / 2 - 26), 22, (255, 230, 60), center=True, bold=True)
        if self.hurt and tick % 4 < 2:
            return
        s.blit(im, (x, y))


# ====================================================================== bosses
class Boss:
    boss = True
    inv = False
    spiky = False
    name, maxhp, skin, w, h = "Boss", 5, "b_snakehead", 100, 60

    def __init__(self, g):
        self.hp = self.maxhp = max(3, self.maxhp - (1 if g.diff == 0 else 0))
        self.x, self.y, self.dir = 800.0, 300.0, -1
        self.state, self.timer, self.t, self.hurt = "start", 60, 0, 0
        self.vuln, self.dead, self.count = False, False, 0
        self.L, self.R, self.TOP, self.BOT = 32, g.level.pw - 32, g.level.air * TILE, (g.level.h - 2) * TILE

    def rect(self):
        return pygame.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)

    def phase(self):
        return 2 - min(2, int(3 * self.hp / (self.maxhp + 0.01)))

    def update(self, g):
        self.t += 1
        if self.hurt:
            self.hurt -= 1
        if self.timer > 0:
            self.timer -= 1
        self.think(g)

    def hit(self, g, dmg=1):
        if self.hurt or not self.vuln:
            return False
        self.hp -= 1
        self.hurt = 70
        g.shake = 14
        g.freeze = 7
        audio.sfx("boss")
        g.burst(self.x, self.y, (255, 220, 80), 24)
        if self.hp <= 0:
            self.dead = True
        else:
            self.on_hit(g)
        return True

    def on_hit(self, g):
        pass

    def aim(self, g, spd):
        dx, dy = g.p.x - self.x, g.p.y - self.y
        d = math.hypot(dx, dy) or 1
        return dx / d * spd, dy / d * spd

    def draw(self, s, cx, cy, tick):
        if self.hurt and tick % 6 < 3:
            return
        im = gfx.spr(self.skin, (tick // 10) % 2, self.dir < 0)
        ox = rnd.randint(-2, 2) if self.vuln else 0
        s.blit(im, (self.x - cx - im.get_width() / 2 + ox, self.y - cy - im.get_height() / 2))
        if self.vuln:
            for i in range(3):
                a = tick * 0.15 + i * 2.1
                draw_text(s, "*", (self.x - cx + math.cos(a) * 34, self.y - cy - self.h / 2 - 22 + math.sin(a) * 8), 26, (255, 240, 90), center=True, bold=True)


class Snakehead(Boss):
    name, maxhp, skin, w, h = "The Great Snakehead", 5, "b_snakehead", 160, 56

    def think(self, g):
        ph = self.phase()
        if self.state in ("start", "aim"):
            self.vuln = False
            self.y += max(-2.2, min(2.2, g.p.y - self.y))
            self.y = max(self.TOP + 40, min(self.BOT - 40, self.y))
            if self.timer == 0:
                self.state = "charge"
                audio.sfx("dash")
        elif self.state == "charge":
            self.x += self.dir * (7.5 + 2 * ph) * g.espeed
            if self.x < self.L + self.w / 2 or self.x > self.R - self.w / 2:
                self.x = max(self.L + self.w / 2, min(self.R - self.w / 2, self.x))
                self.dir = -self.dir
                g.shake = 10
                self.count += 1
                if ph == 2 and self.count % 2 == 1:
                    self.state, self.timer = "aim", 24
                else:
                    self.state, self.timer, self.vuln = "stun", 150 - 20 * ph, True
        elif self.timer == 0:
            self.state, self.timer = "aim", 80 - 18 * ph

    def on_hit(self, g):
        self.state, self.timer, self.vuln = "aim", 70, False


class Cat(Boss):
    name, maxhp, skin, w, h = "The House Cat", 5, "b_paw", 66, 290

    def __init__(self, g):
        Boss.__init__(self, g)
        self.tip = self.TOP - 20
        self.x = 480

    def rect(self):
        return pygame.Rect(self.x - 33, self.tip - 290, 66, 290)

    def think(self, g):
        ph = self.phase()
        self.y = self.tip - 40
        if self.state in ("start", "watch"):
            self.vuln = False
            self.x += max(-5, min(5, g.p.x - self.x))
            self.x = max(self.L + 45, min(self.R - 45, self.x))
            if self.timer == 0:
                self.state, self.timer = "tele", 30 - 6 * ph
        elif self.state == "tele":
            if self.timer == 0:
                self.state = "strike"
        elif self.state == "strike":
            self.tip += 17 * g.espeed
            if self.tip >= self.BOT:
                self.tip = self.BOT
                g.shake = 12
                audio.sfx("boss")
                self.count += 1
                quick = ph == 2 and self.count % 2 == 1
                self.state, self.timer, self.vuln = "stuck", (34 if quick else 115 - 15 * ph), True
        elif self.state == "stuck":
            if self.timer == 0:
                self.state, self.vuln = "up", False
        elif self.state == "up":
            self.tip -= 7
            if self.tip <= self.TOP - 20:
                self.state, self.timer = "watch", 26 if (ph == 2 and self.count % 2 == 1) else 70 - 14 * ph

    def on_hit(self, g):
        self.state, self.vuln = "up", False

    def draw(self, s, cx, cy, tick):
        face = gfx.spr("b_cat", (tick // 30) % 2)
        s.blit(face, (max(0, min(700, self.x - 130)) - cx, -34 - cy))
        if self.state == "tele":
            dr.line(s, (255, 60, 60), (self.x - cx, self.TOP - cy), (self.x - cx, self.BOT - cy), 2)
        if self.hurt and tick % 6 < 3:
            return
        im = gfx.spr("b_paw")
        s.blit(im, (self.x - cx - 45 + (rnd.randint(-2, 2) if self.vuln else 0), self.tip - 300 - cy))


class MusRex(Boss):
    name, maxhp, skin, w, h = "Mus Rex", 6, "b_mouse", 104, 64

    def think(self, g):
        ph = self.phase()
        if self.state in ("start", "swim"):
            if self.state == "start":
                self.state, self.timer = "swim", 300
            self.vuln = False
            tx = 480 + math.cos(self.t * 0.010) * 330
            ty = 310 + math.sin(self.t * 0.031) * 105
            self.dir = sign(tx - self.x) or self.dir
            self.x += (tx - self.x) * 0.05
            self.y += (ty - self.y) * 0.05
            if self.t % (72 - 12 * ph) == 0:
                vx, vy = self.aim(g, (3.0 + 0.5 * ph) * g.espeed)
                g.shots.append(Shot(self.x, self.y, vx, vy, "cheese"))
            if self.timer == 0:
                self.state = "rise"
        elif self.state == "rise":
            self.y -= 3
            if self.y <= self.TOP + 26:
                self.state, self.timer, self.vuln = "gasp", 140 - 15 * ph, True
        elif self.state == "gasp":
            if self.t % 6 == 0:
                g.burst(self.x + 30 * self.dir, self.y - 20, (220, 240, 255), 1)
            if self.timer == 0:
                self.next(g)

    def next(self, g):
        self.state, self.timer, self.vuln = "swim", 300 - 40 * self.phase(), False
        if self.phase() >= 1 and sum(1 for e in g.enemies if not e.boss) < 2:
            g.enemies.append(Enemy(g, "mouse", self.x, self.y + 40))

    def on_hit(self, g):
        self.next(g)


class FlyQueen(Boss):
    name, maxhp, skin, w, h = "Queen Drosophila", 7, "b_fly", 74, 50

    def __init__(self, g):
        Boss.__init__(self, g)
        self.y, self.vuln, self.timer = 56.0, True, 300

    def think(self, g):
        ph = self.phase()
        self.vuln = self.count == 0
        if self.count > 0:
            self.count -= 1
            if self.count % 28 == 0:
                g.shots.append(Shot(self.x, self.y + 20, 0, 1.0, "maggot", grav=0.03, life=260))
        if self.state in ("start", "fly"):
            self.state = "fly"
            self.x += self.dir * (2.0 + 0.7 * ph + (2 if self.count else 0)) * g.espeed
            if self.x < self.L + 60:
                self.dir = 1
            elif self.x > self.R - 60:
                self.dir = -1
            self.y += (58 + math.sin(self.t * 0.07) * 16 - self.y) * 0.08
            if self.t % (84 - 16 * ph) == 0:
                g.shots.append(Shot(self.x, self.y + 20, 0, 1.0, "maggot", grav=0.03, life=260))
            if self.timer == 0:
                self.state, self.timer = "swoop", 110
        elif self.state == "swoop":
            self.x += max(-3.2, min(3.2, g.p.x - self.x))
            self.x = max(self.L + 60, min(self.R - 60, self.x))
            self.y += (self.TOP + 34 - self.y) * 0.07
            if self.timer == 0:
                self.state, self.timer = "fly", 330 - 50 * ph

    def on_hit(self, g):
        self.state, self.timer, self.count = "fly", 300, 150


class Fugu(Boss):
    name, maxhp, skin, w, h = "Fugu, the Compact Genome", 6, "b_fugu", 100, 62

    def think(self, g):
        ph = self.phase()
        if self.state in ("start", "drift"):
            if self.state == "start":
                self.state, self.timer = "drift", 200
            self.vuln, self.spiky, self.skin, self.w, self.h = True, False, "b_fugu", 100, 62
            vx, vy = self.aim(g, (1.0 + 0.35 * ph) * g.espeed)
            self.x += vx
            self.y += vy
            self.dir = sign(vx) or self.dir
            if self.timer == 0:
                self.puff()
        elif self.state == "puff":
            self.vuln, self.spiky, self.skin, self.w, self.h = False, True, "b_fugu_puff", 124, 124
            self.x += (480 - self.x) * 0.01 + math.cos(self.t * 0.05) * 1.5
            self.y += (300 - self.y) * 0.01 + math.sin(self.t * 0.07) * 1.5
            if self.timer % 46 == 20:
                n = 8 + 3 * ph
                off = rnd.uniform(0, 1)
                for i in range(n):
                    a = (i + off) * math.tau / n
                    g.shots.append(Shot(self.x, self.y, math.cos(a) * 3 * g.espeed, math.sin(a) * 3 * g.espeed, "spine", life=200))
                audio.sfx("shoot")
            if self.timer == 0:
                self.state, self.timer = "drift", 210 - 30 * ph

    def puff(self):
        self.state, self.timer = "puff", 150 + 40 * self.phase()

    def on_hit(self, g):
        self.puff()


QUOTES = ["Have the authors considered using mice?", "This should be repeated in a second species.",
          "Reviewer 1 was far too kind.", "Please add fifteen further experiments.",
          "The novelty is unclear to me.", "Cite these seven papers (all mine).",
          "Is a fish even a vertebrate model?", "The n is too low. It is always too low."]


class Reviewer2(Boss):
    name, maxhp, skin, w, h = "Reviewer #2", 8, "b_reviewer", 84, 130

    def __init__(self, g):
        Boss.__init__(self, g)
        self.beams, self.side, self.seq = [], 1, 0

    def think(self, g):
        ph = self.phase()
        hx = 790 if self.side > 0 else 170
        self.x += (hx - self.x) * 0.06
        self.y += (300 + math.sin(self.t * 0.025) * 105 - self.y) * 0.05
        self.dir = -self.side
        for b in self.beams:
            b[1] -= 1
            if b[1] < 40 and not g.p.dead and abs(g.p.y - b[0]) < 13:
                g.p.damage(g)
        self.beams = [b for b in self.beams if b[1] > 0]
        if self.state == "start":
            if self.timer == 0:
                self.pick(g)
        elif self.state == "papers":
            if self.timer % 24 == 0 and self.timer > 0:
                vx, vy = self.aim(g, (3.3 + 0.4 * ph) * g.espeed)
                g.shots.append(Shot(self.x, self.y - 20, vx, vy, "paper"))
                audio.sfx("shoot")
            if self.timer == 0:
                self.pick(g)
        elif self.state == "beam":
            if self.timer in (140, 95, 50)[:1 + ph]:
                self.beams.append([g.p.y, 90])
            if self.timer == 0:
                self.pick(g)
        elif self.state == "minions":
            if self.timer == 0:
                self.pick(g)
        elif self.state == "read":
            if self.timer == 0:
                self.vuln = False
                self.pick(g)

    def pick(self, g):
        ph = self.phase()
        self.seq += 1
        order = ["papers", "beam", "read", "minions", "papers", "beam", "read"]
        st = order[self.seq % len(order)]
        self.vuln = False
        if st == "papers":
            self.state, self.timer = st, 24 * (4 + 2 * ph) + 20
            g.say(rnd.choice(QUOTES))
        elif st == "beam":
            self.state, self.timer = st, 150
            g.say("I have some comments in red.")
        elif st == "minions":
            self.state, self.timer = st, 90
            g.say("Additional experiments are required.")
            if sum(1 for e in g.enemies if not e.boss) < 3:
                for i in range(1 + (ph > 0)):
                    g.enemies.append(Enemy(g, rnd.choice(["mouse", "medaka", "scissors", "killifish"]), 480 + i * 60, 440))
        else:
            self.state, self.timer, self.vuln = "read", 175 - 15 * ph, True
            g.say("Hmm... let me read this rebuttal...")

    def on_hit(self, g):
        self.side = -self.side
        self.vuln = False
        self.state, self.timer = "start", 50
        g.say("Major revision!" if self.hp > 3 else "...Minor revision?")

    def draw(self, s, cx, cy, tick):
        for y, t in self.beams:
            if t >= 40:
                if tick % 8 < 4:
                    dr.line(s, (255, 90, 90), (0, y - cy), (960, y - cy), 1)
            else:
                dr.rect(s, (255, 40, 40), (0, y - cy - 9, 960, 18))
                dr.rect(s, (255, 220, 220), (0, y - cy - 3, 960, 6))
        Boss.draw(self, s, cx, cy, tick)


BOSSES = {"b_snakehead": Snakehead, "b_cat": Cat, "b_mouse": MusRex, "b_fly": FlyQueen, "b_fugu": Fugu,
          "b_reviewer": Reviewer2}

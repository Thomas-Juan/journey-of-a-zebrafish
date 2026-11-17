# -*- coding: utf-8 -*-
"""Shared constants, input, text and save helpers."""
import json
import os
import pygame

W, H = 960, 540
TILE = 32
FPS = 60
TITLE = "Journey of a Zebrafish"

T_WATER, T_SOLID, T_AIR, T_HAZ, T_GLASS, T_CRACK = 0, 1, 2, 3, 4, 5

DIFF_NAMES = ["Larva (relaxed)", "Juvenile (standard)", "Adult (demanding)"]
DIFF_HEARTS = [5, 4, 3]
DIFF_SPEED = [0.85, 1.0, 1.15]

KEYMAP = {
    "left": (pygame.K_LEFT, pygame.K_a), "right": (pygame.K_RIGHT, pygame.K_d),
    "up": (pygame.K_UP, pygame.K_w), "down": (pygame.K_DOWN, pygame.K_s),
    "dash": (pygame.K_SPACE, pygame.K_z, pygame.K_j),
    "shoot": (pygame.K_x, pygame.K_k, pygame.K_LCTRL),
    "ok": (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER),
    "back": (pygame.K_ESCAPE, pygame.K_BACKSPACE),
    "tab": (pygame.K_TAB,), "shop": (pygame.K_u,),
}


class Input:
    def __init__(self):
        self.held = set()
        self.pressed = set()
        self.bot = None  # test hook: callable returning set of held actions

    def update(self, events):
        prev = self.held
        if self.bot is not None:
            self.held = set(self.bot())
        else:
            keys = pygame.key.get_pressed()
            self.held = {a for a, ks in KEYMAP.items() if any(keys[k] for k in ks)}
        self.pressed = set()
        if self.bot is not None:
            self.pressed = self.held - prev
        else:
            for e in events:
                if e.type == pygame.KEYDOWN:
                    for a, ks in KEYMAP.items():
                        if e.key in ks:
                            self.pressed.add(a)

    def axis(self):
        x = ("right" in self.held) - ("left" in self.held)
        y = ("down" in self.held) - ("up" in self.held)
        return x, y


_fonts = {}
_NAMES = ["segoeui", "verdana", "helveticaneue", "helvetica", "tahoma", "arial", "dejavusans"]


def font(size, bold=False):
    k = (size, bold)
    if k not in _fonts:
        f = None
        try:
            path = pygame.font.match_font(_NAMES, bold=bold)
            if path:
                f = pygame.font.Font(path, size)
        except Exception:
            f = None
        if f is None:
            f = pygame.font.Font(None, int(size * 1.25))
        _fonts[k] = f
    return _fonts[k]


_PRETTY = [("Tubingen", "Tübingen"), ("Nusslein", "Nüsslein"), (" C ", " °C "), (" C.", " °C."),
           (" - ", " – ")]


def pretty(t):
    for a, b in _PRETTY:
        t = t.replace(a, b)
    return t


_tcache = {}


def text_surf(t, size, color, bold=False):
    k = (t, size, color, bold)
    s = _tcache.get(k)
    if s is None:
        if len(_tcache) > 600:
            _tcache.clear()
        s = font(size, bold).render(t, True, color)
        _tcache[k] = s
    return s


def draw_text(surf, t, pos, size=18, color=(255, 255, 255), center=False, bold=False,
              shadow=True, right=False):
    t = pretty(str(t))
    s = text_surf(t, size, color, bold)
    x, y = pos
    if center:
        x -= s.get_width() // 2
    elif right:
        x -= s.get_width()
    if shadow:
        surf.blit(text_surf(t, size, (0, 0, 0), bold), (x + 1, y + 2))
    surf.blit(s, (x, y))
    return s.get_width()


def wrap(t, size, width, bold=False):
    f = font(size, bold)
    out = []
    for para in pretty(t).split("\n"):
        line = ""
        for word in para.split(" "):
            test = (line + " " + word) if line else word
            if f.size(test)[0] <= width:
                line = test
            else:
                if line:
                    out.append(line)
                line = word
        out.append(line)
    return out


def draw_wrapped(surf, t, pos, size, width, color=(255, 255, 255), bold=False, lh=None,
                 shadow=False, center=False):
    lh = lh or int(size * 1.4)
    x, y = pos
    for ln in wrap(t, size, width, bold):
        draw_text(surf, ln, (x, y), size, color, bold=bold, shadow=shadow, center=center)
        y += lh
    return y


_panels = {}


def panel(surf, rect, fill=(18, 30, 52), border=(120, 190, 230), alpha=235, radius=10):
    r = pygame.Rect(rect)
    key = (r.size, fill, border, alpha, radius)
    s = _panels.get(key)
    if s is None:
        if len(_panels) > 200:
            _panels.clear()
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, fill + (alpha,), s.get_rect(), border_radius=radius)
        pygame.draw.rect(s, border + (255,), s.get_rect(), 2, border_radius=radius)
        _panels[key] = s
    surf.blit(s, r.topleft)


def clamp(v, a, b):
    return a if v < a else b if v > b else v


# ---------------------------------------------------------------- saving
def save_dir():
    import sys
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or home
    d = os.path.join(base, "JourneyOfAZebrafish")
    os.makedirs(d, exist_ok=True)
    return d


SAVE_FILE = None


def _path():
    return SAVE_FILE or os.path.join(save_dir(), "save.json")


def new_slot(diff=1):
    return {"diff": diff, "node": 0, "unlocked": 0, "levels": {}, "pages": [], "food": 0,
            "up": {"heart": 0, "dash": 0, "magnet": 0, "shoal": 0}, "deaths": 0, "time": 0.0,
            "quiz": [0, 0], "seen": [], "done": False, "know": 0}


def load_all():
    data = {"slots": [None, None, None], "opt": {"music": 6, "sfx": 7, "full": False}}
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d.get("slots"), list) and len(d["slots"]) == 3:
            for i, s in enumerate(d["slots"]):
                if s:
                    base = new_slot()
                    base.update(s)
                    for k, v in new_slot()["up"].items():
                        base["up"].setdefault(k, v)
                    data["slots"][i] = base
        data["opt"].update(d.get("opt", {}))
    except Exception:
        pass
    return data


def save_all(data):
    try:
        p = _path()
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, p)
        return True
    except Exception:
        return False

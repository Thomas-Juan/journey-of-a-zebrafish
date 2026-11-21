# -*- coding: utf-8 -*-
"""Shared constants, input, text and save helpers."""
import json
import math
import os
import sys
import pygame

WEB = sys.platform == "emscripten"      # running in a browser (pygbag build)
WEB_KEY = "juanlab-journey-of-a-zebrafish-save"

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


# ---------------------------------------------------------------- render scale
# Every position in the game is in points on a 960 x 540 stage. The picture itself is drawn
# with K pixels per point (2 on the desktop, 1 in the browser), so sprites and text stay sharp
# when the window is enlarged. Hi is a surface addressed in points; dr draws on it.
K = 1
PD = pygame.draw


def _px(n, k):
    return n // k if n % k == 0 else n / k


class Hi(pygame.Surface):
    """A surface addressed in points; it holds k pixels per point."""

    def __init__(self, size, flags=0, k=None, real=False):
        k = K if k is None else k
        if not real:
            size = (max(1, int(math.ceil(size[0] * k - 1e-6))), max(1, int(math.ceil(size[1] * k - 1e-6))))
        pygame.Surface.__init__(self, size, flags)
        self.k = k

    def get_width(self):
        return _px(pygame.Surface.get_width(self), self.k)

    def get_height(self):
        return _px(pygame.Surface.get_height(self), self.k)

    def get_size(self):
        return self.get_width(), self.get_height()

    def get_rect(self, **kw):
        r = pygame.Rect((0, 0), self.get_size())
        for a, v in kw.items():
            setattr(r, a, v)
        return r

    def real_size(self):
        return pygame.Surface.get_size(self)

    def blit(self, src, dest, area=None, special_flags=0):
        k = self.k
        sk = getattr(src, "k", None)
        if sk != k:
            src = rescale(src, sk or 1, k)
        if area is not None:
            area = (round(area[0] * k), round(area[1] * k), round(area[2] * k), round(area[3] * k))
        return pygame.Surface.blit(self, src, (round(dest[0] * k), round(dest[1] * k)), area, special_flags)

    def fill(self, color, rect=None, special_flags=0):
        if rect is not None:
            k = self.k
            x, y = rect[0] * k, rect[1] * k
            rect = (round(x), round(y), round(x + rect[2] * k) - round(x), round(y + rect[3] * k) - round(y))
        return pygame.Surface.fill(self, color, rect, special_flags)

    def set_at(self, pos, color):
        k = self.k
        pygame.Surface.fill(self, color, (int(pos[0] * k), int(pos[1] * k), int(k), int(k)))

    def get_at(self, pos):
        return pygame.Surface.get_at(self, (int(pos[0] * self.k), int(pos[1] * self.k)))

    def set_clip(self, rect=None):
        pygame.Surface.set_clip(self, None if rect is None else _rk(rect, self.k))

    def subsurface(self, rect):
        k = self.k
        s = pygame.Surface.subsurface(self, (round(rect[0] * k), round(rect[1] * k), round(rect[2] * k), round(rect[3] * k)))
        s.k = k
        return s

    def copy(self):
        s = pygame.Surface.copy(self)
        s.k = self.k
        return s


Hi.upscaled = 0     # how many plain surfaces had to be enlarged on the fly (should stay small)


class Canvas:
    """The window surface addressed in points, so the game draws straight onto it (no copy)."""

    def __init__(self, surf, k):
        self.surf, self.k = surf, k

    def get_width(self):
        return _px(self.surf.get_width(), self.k)

    def get_height(self):
        return _px(self.surf.get_height(), self.k)

    def get_size(self):
        return self.get_width(), self.get_height()

    def get_rect(self, **kw):
        return Hi.get_rect(self, **kw)

    def blit(self, src, dest, area=None, special_flags=0):
        k = self.k
        if getattr(src, "k", None) != k:
            src = rescale(src, getattr(src, "k", 1), k)
        if area is not None:
            area = (round(area[0] * k), round(area[1] * k), round(area[2] * k), round(area[3] * k))
        return self.surf.blit(src, (round(dest[0] * k), round(dest[1] * k)), area, special_flags)

    def fill(self, color, rect=None, special_flags=0):
        if rect is not None:
            rect = _rk(rect, self.k)
        return self.surf.fill(color, rect, special_flags)

    def set_at(self, pos, color):
        k = self.k
        self.surf.fill(color, (int(pos[0] * k), int(pos[1] * k), int(k), int(k)))

    def get_at(self, pos):
        return self.surf.get_at((int(pos[0] * self.k), int(pos[1] * self.k)))

    def set_clip(self, rect=None):
        self.surf.set_clip(None if rect is None else _rk(rect, self.k))


def rescale(src, sk, k):
    """Return src (sk pixels per point) as a surface with k pixels per point."""
    Hi.upscaled += 1
    w, h = pygame.Surface.get_size(src)
    size = (max(1, round(w * k / sk)), max(1, round(h * k / sk)))
    if src.get_bitsize() not in (24, 32):
        src = src.convert_alpha() if src.get_flags() & pygame.SRCALPHA else src.convert()
    out = pygame.transform.smoothscale(src, size)
    if k != 1:
        out = adopt(out, k)
    return out


def adopt(surf, k=None):
    """Wrap a plain surface whose pixels are already at k per point as a Hi surface."""
    k = K if k is None else k
    alpha = surf.get_flags() & pygame.SRCALPHA
    h = Hi(pygame.Surface.get_size(surf), pygame.SRCALPHA if alpha else 0, k, real=True)
    if alpha:
        pygame.Surface.blit(h, surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    else:
        pygame.Surface.blit(h, surf, (0, 0))
    return h


def hsurf(w, h, alpha=True):
    """A new blank surface of w x h points at the current render scale."""
    return Hi((w, h), pygame.SRCALPHA if alpha else 0)


def scaled(src, size):
    """src (plain or Hi) smoothly resized to size points, as a Hi surface."""
    out = pygame.transform.smoothscale(src, (max(1, round(size[0] * K)), max(1, round(size[1] * K))))
    return adopt(out)


def _wd(w, k):
    return 0 if not w else max(1, int(round(w * k)))


def _pts(pts, k):
    return [(x * k, y * k) for x, y in pts]


def _rk(r, k):
    x, y = r[0] * k, r[1] * k
    return (round(x), round(y), round(x + r[2] * k) - round(x), round(y + r[3] * k) - round(y))


class dr:
    """pygame.draw for surfaces addressed in points (plain surfaces pass straight through)."""
    @staticmethod
    def circle(s, c, p, r, width=0, **kw):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        if k == 1:
            return PD.circle(s, c, p, r, width, **kw)
        return PD.circle(s, c, (p[0] * k, p[1] * k), r * k, _wd(width, k), **kw)

    @staticmethod
    def ellipse(s, c, r, width=0):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        return PD.ellipse(s, c, r if k == 1 else _rk(r, k), _wd(width, k))

    @staticmethod
    def rect(s, c, r, width=0, border_radius=0, **kw):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        if k == 1:
            return PD.rect(s, c, r, width, border_radius, **kw)
        kw = {a: int(round(v * k)) for a, v in kw.items()}
        return PD.rect(s, c, _rk(r, k), _wd(width, k), int(round(border_radius * k)), **kw)

    @staticmethod
    def line(s, c, a, b, width=1):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        if k == 1:
            return PD.line(s, c, a, b, width)
        return PD.line(s, c, (a[0] * k, a[1] * k), (b[0] * k, b[1] * k), _wd(width, k))

    @staticmethod
    def lines(s, c, closed, pts, width=1):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        return PD.lines(s, c, closed, pts if k == 1 else _pts(pts, k), _wd(width, k))

    @staticmethod
    def polygon(s, c, pts, width=0):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        return PD.polygon(s, c, pts if k == 1 else _pts(pts, k), _wd(width, k))

    @staticmethod
    def arc(s, c, r, a0, a1, width=1):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        return PD.arc(s, c, r if k == 1 else _rk(r, k), a0, a1, _wd(width, k))

    @staticmethod
    def aaline(s, c, a, b):
        k = getattr(s, "k", 1)
        s = getattr(s, "surf", s)
        if k == 1:
            return PD.aaline(s, c, a, b)
        return PD.line(s, c, (a[0] * k, a[1] * k), (b[0] * k, b[1] * k), _wd(1, k))


# ---------------------------------------------------------------- text
_fonts = {}
_fontdata = {}
_capmid = {}      # top of a rendered line to the middle of its capitals, in pixels


_SIZE = (0.93, 0.97)      # Inter runs wider than the Segoe UI the layouts were made with


def font(size, bold=False):
    """Inter (bundled), so text looks the same on Windows, macOS and in the browser.
    size is the nominal size the layouts were designed for."""
    k = (size, bold)
    if k not in _fonts:
        import io
        if bold not in _fontdata:
            import base64
            import fontdata
            _fontdata[bold] = base64.b64decode("".join(fontdata.BOLD if bold else fontdata.REGULAR))
        px = max(4, int(round(size * _SIZE[bool(bold)])))
        try:
            try:
                f = pygame.font.Font(io.BytesIO(_fontdata[bold]), px)
            except Exception:
                # the browser build cannot read a font from memory: give it a file instead
                import tempfile
                path = os.path.join(tempfile.gettempdir(), "zebrafish-inter-%d.ttf" % bool(bold))
                if not os.path.exists(path) or os.path.getsize(path) != len(_fontdata[bold]):
                    with open(path, "wb") as fh:
                        fh.write(_fontdata[bold])
                f = pygame.font.Font(path, px)
            _capmid[k] = f.get_ascent() - px * 0.364         # Inter's capitals are 0.727 em tall
        except Exception as e:
            print("font: falling back to the default font:", e)
            f = pygame.font.Font(None, int(size * 1.25))
            _capmid[k] = f.get_ascent() * 0.6
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
        if color == (0, 0, 0):
            s.set_alpha(130)          # shadows: soft, so letters never look doubled
        _tcache[k] = s
    return s


def draw_text(surf, t, pos, size=18, color=(255, 255, 255), center=False, bold=False,
              shadow=True, right=False, mid=False):
    """Draw one line. pos is the top-left (or top-centre / top-right) of the line as the
    layouts were designed; with mid=True, pos[1] is where the middle of the capitals goes,
    which is the way to centre a label on a shape. Returns the width in points."""
    t = pretty(str(t))
    k = getattr(surf, "k", 1)
    s = text_surf(t, size * k, color, bold)
    x, y = pos[0] * k, pos[1] * k
    w = s.get_width()
    if center:
        x -= w / 2
    elif right:
        x -= w
    y -= _capmid[(size * k, bold)]
    if not mid:
        y += 0.75 * size * k                  # where the capitals sat in the original layouts
    x, y = round(x), round(y)
    real = getattr(surf, "surf", surf)
    if shadow:
        pygame.Surface.blit(real, text_surf(t, size * k, (0, 0, 0), bold), (x + k, y + 2 * k))
    pygame.Surface.blit(real, s, (x, y))
    return w / k


def text_width(t, size, bold=False):
    return font(size, bold).size(pretty(str(t)))[0]


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
        s = hsurf(*r.size)
        dr.rect(s, fill + (alpha,), s.get_rect(), border_radius=radius)
        dr.rect(s, border + (255,), s.get_rect(), 2, border_radius=radius)
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


def _read_save():
    if WEB:
        import platform
        raw = platform.window.localStorage.getItem(WEB_KEY)
        if not raw:
            raise IOError("no save yet")
        return str(raw)
    with open(_path(), "r", encoding="utf-8") as f:
        return f.read()


def load_all():
    data = {"slots": [None, None, None], "opt": {"music": 6, "sfx": 7, "full": False}}
    try:
        d = json.loads(_read_save())
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
    if WEB:
        try:
            import platform
            platform.window.localStorage.setItem(WEB_KEY, json.dumps(data))
            return True
        except Exception:
            return False
    try:
        p = _path()
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, p)
        return True
    except Exception:
        return False

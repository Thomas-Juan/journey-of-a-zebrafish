# -*- coding: utf-8 -*-
"""End-of-game certificates: four tiers, drawn at print resolution and saved as a PDF.

The wording, laboratory name and signatory are plain constants below - edit them freely."""
import hashlib
import math
import os
import sys
import time
import zlib
import pygame
import gfx
from worlds import LEVELS
from facts import FACTS
import quiz

LAB_NAME = "THE JUAN LAB"
LAB_SEAL = "the Juan Lab"
SIGN_NAME = "Thomas Juan"
SIGN_TITLE = "Principal Investigator, The Juan Lab"
COURSE = "JOURNEY OF A ZEBRAFISH"
DISCLAIMER = ("This certificate recognises achievement in the educational game Journey of a Zebrafish. "
              "It confers no academic credit or professional qualification.")

CW, CH = 2339, 1654            # A4 landscape at 200 dpi
NAVY, GOLD, INK, GREY = (22, 38, 82), (170, 134, 52), (30, 30, 40), (104, 104, 116)
TIERS = [
    ("Certificate of Completion", "OF COMPLETION", (168, 108, 62), "Defeat Reviewer #2 (finish world 6)."),
    ("Certificate of Merit", "WITH MERIT", (146, 152, 166), "Also: at least 90 notebook pages and 60 % of examination questions correct."),
    ("Certificate of Distinction", "WITH DISTINCTION", (190, 152, 56), "Also: all 45 levels, all 135 notebook pages and 75 % correct."),
    ("Certificate of Excellence", "WITH HIGHEST DISTINCTION  -  SUMMA CUM LAUDE", (40, 70, 150),
     "Also: D-A-N-I-O in all 39 levels and 90 % correct."),
]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def stats(slot):
    total_pages = sum(len(v) for w, v in FACTS.items() if w)
    plain = [l for l in LEVELS if not l["boss"]]
    lv = slot["levels"]
    st = dict(
        levels=sum(1 for l in LEVELS if lv.get(l["id"], {}).get("done")), levels_total=len(LEVELS),
        pages=len(slot["pages"]), pages_total=total_pages,
        danio=sum(1 for l in plain if lv.get(l["id"], {}).get("danio")), danio_total=len(plain),
        right=slot["quiz"][0], asked=slot["quiz"][1], know=slot.get("know", 0), done=bool(slot.get("done")),
    )
    st["acc"] = st["right"] / st["asked"] if st["asked"] else 0.0
    st["rank"] = quiz.rank(st["know"])
    reqs = [
        [("Final examiner (Reviewer #2) defeated", st["done"])],
        [("90 notebook pages (%d)" % st["pages"], st["pages"] >= 90), ("60 %% of questions correct (%d %%)" % round(st["acc"] * 100), st["acc"] >= 0.6)],
        [("All %d levels (%d)" % (st["levels_total"], st["levels"]), st["levels"] >= st["levels_total"]),
         ("All %d notebook pages (%d)" % (total_pages, st["pages"]), st["pages"] >= total_pages),
         ("75 %% of questions correct (%d %%)" % round(st["acc"] * 100), st["acc"] >= 0.75)],
        [("D-A-N-I-O in all %d levels (%d)" % (st["danio_total"], st["danio"]), st["danio"] >= st["danio_total"]),
         ("90 %% of questions correct (%d %%)" % round(st["acc"] * 100), st["acc"] >= 0.9)],
    ]
    tier = -1
    for i, group in enumerate(reqs):
        if all(ok for _, ok in group):
            tier = i
        else:
            break
    st["tier"], st["reqs"] = tier, reqs
    return st


def number(name, st):
    h = hashlib.sha1(("%s|%d|%d|%d|%d" % (name, st["tier"], st["pages"], st["danio"], st["right"])).encode("utf-8")).hexdigest()
    return "JL-ZF-%d-%s" % (time.localtime().tm_year, h[:6].upper())


_fonts = {}


def _font(size, bold=False, italic=False):
    k = (size, bold, italic)
    if k not in _fonts:
        f = None
        try:
            p = pygame.font.match_font(["georgia", "timesnewroman", "times", "cambria", "palatino", "dejavuserif", "liberationserif"], bold=bold, italic=italic)
            if p:
                f = pygame.font.Font(p, size)
        except Exception:
            f = None
        _fonts[k] = f or pygame.font.Font(None, int(size * 1.2))
    return _fonts[k]


def _text(s, t, y, size, col=INK, bold=False, italic=False, x=CW // 2, spacing=0, maxw=None):
    """Draw text centred on x; spacing > 0 letterspaces it; maxw shrinks the font to fit."""
    f = _font(size, bold, italic)
    if maxw:
        while size > 20 and f.size(t)[0] + spacing * len(t) > maxw:
            size -= 4
            f = _font(size, bold, italic)
    if not spacing:
        im = f.render(t, True, col)
        s.blit(im, (x - im.get_width() // 2, y))
        return im.get_width()
    glyphs = [f.render(ch, True, col) for ch in t]
    w = sum(g.get_width() for g in glyphs) + spacing * (len(t) - 1)
    cx = x - w // 2
    for g in glyphs:
        s.blit(g, (cx, y))
        cx += g.get_width() + spacing
    return w


def _rule(s, y, half, col=GOLD):
    cx = CW // 2
    pygame.draw.line(s, col, (cx - half, y), (cx - 26, y), 3)
    pygame.draw.line(s, col, (cx + 26, y), (cx + half, y), 3)
    pygame.draw.polygon(s, col, [(cx, y - 12), (cx + 14, y), (cx, y + 12), (cx - 14, y)])


def _seal(s, cx, cy, tier, k=0.72):
    col = TIERS[tier][2]
    light = tuple(min(255, c + 70) for c in col)
    dark = tuple(max(0, c - 50) for c in col)
    for dx, tilt in ((-40, -0.2), (40, 0.2)):      # ribbons
        top, bot = cy + 40, cy + 130
        pts = [(cx + dx - 32, top), (cx + dx + 32, top), (cx + dx + 32 + tilt * 110, bot), (cx + dx + tilt * 100, bot - 26), (cx + dx - 32 + tilt * 110, bot)]
        pygame.draw.polygon(s, NAVY, pts)
        pygame.draw.polygon(s, GOLD, pts, 3)
    n = 40
    ro, ri = 150 * k, 132 * k
    pts = [(cx + math.cos(i * math.pi / n) * (ro if i % 2 == 0 else ri), cy + math.sin(i * math.pi / n) * (ro if i % 2 == 0 else ri)) for i in range(n * 2)]
    pygame.draw.polygon(s, col, pts)
    pygame.draw.polygon(s, dark, pts, 3)
    pygame.draw.circle(s, light, (cx, cy), int(116 * k))
    pygame.draw.circle(s, dark, (cx, cy), int(116 * k), 4)
    pygame.draw.circle(s, dark, (cx, cy), int(102 * k), 2)
    body = gfx.fin(gfx._fish(58, 29, (236, 230, 204), (250, 248, 235), (240, 205, 95), (38, 52, 130), 4, 0, sw=2.2))
    body = pygame.transform.smoothscale(body, (int(body.get_width() * 2.2), int(body.get_height() * 2.2)))
    s.blit(body, (cx - body.get_width() // 2, cy - body.get_height() // 2 - 12))
    for i in range(tier + 1):
        sx = cx + (i - tier / 2) * 27
        sp = [(sx + math.sin(q * math.pi / 5) * (11 if q % 2 == 0 else 4.8), cy + 48 - math.cos(q * math.pi / 5) * (11 if q % 2 == 0 else 4.8)) for q in range(10)]
        pygame.draw.polygon(s, dark, sp)


def render(name, st, when=None):
    """Return the certificate as a 2339 x 1654 surface."""
    tier = max(0, st["tier"])
    title, phrase, col, _ = TIERS[tier]
    t = when or time.localtime()
    s = pygame.Surface((CW, CH))
    s.fill((252, 248, 236))
    for k in range(60):                                # faint guilloche lines
        pts = [(x, 110 + k * 24 + math.sin(x / 150.0 + k * 0.55) * 20) for x in range(0, CW + 30, 30)]
        pygame.draw.lines(s, (244, 237, 219), False, pts, 2)
    pygame.draw.rect(s, NAVY, (48, 48, CW - 96, CH - 96), 16)
    pygame.draw.rect(s, GOLD, (78, 78, CW - 156, CH - 156), 5)
    pygame.draw.rect(s, NAVY, (92, 92, CW - 184, CH - 184), 2)
    for cx, cy in ((92, 92), (CW - 92, 92), (92, CH - 92), (CW - 92, CH - 92)):
        pygame.draw.polygon(s, GOLD, [(cx, cy - 34), (cx + 34, cy), (cx, cy + 34), (cx - 34, cy)])
        pygame.draw.polygon(s, NAVY, [(cx, cy - 18), (cx + 18, cy), (cx, cy + 18), (cx - 18, cy)])

    _text(s, LAB_NAME, 138, 60, NAVY, bold=True, spacing=16)
    _rule(s, 232, 430)
    _text(s, "Programme in the History of a Model Organism", 254, 36, GREY, italic=True)
    _text(s, title, 318, 150, NAVY, bold=True, italic=True)
    _text(s, "This is to certify that", 512, 44, INK, italic=True)
    shown = name.strip() or "________________________"
    w = _text(s, shown, 578, 112, INK, bold=True, maxw=1750)
    pygame.draw.line(s, GOLD, (CW // 2 - max(w, 700) // 2 - 40, 716), (CW // 2 + max(w, 700) // 2 + 40, 716), 3)
    _text(s, "has successfully completed the full course of instruction", 748, 42)
    _text(s, COURSE, 812, 50, NAVY, bold=True, spacing=10)
    _text(s, "a history of Danio rerio as a model organism, from the rivers of Bengal (1822) to the present day,", 884, 37, INK, italic=True)
    _text(s, "and, having been duly examined and found proficient, is hereby awarded this certificate", 940, 42)
    _text(s, phrase, 1010, 56, tuple(max(0, c - 40) for c in col), bold=True, spacing=8, maxw=1900)

    rec = [("LEVELS COMPLETED", "%d / %d" % (st["levels"], st["levels_total"])),
           ("NOTEBOOK PAGES", "%d / %d" % (st["pages"], st["pages_total"])),
           ("D-A-N-I-O SETS", "%d / %d" % (st["danio"], st["danio_total"])),
           ("EXAMINATION", "%d %%  (%d of %d)" % (round(st["acc"] * 100), st["right"], st["asked"])),
           ("RANK ATTAINED", st["rank"])]
    bw = 396
    x0 = CW // 2 - (len(rec) * bw) // 2
    pygame.draw.line(s, GOLD, (x0, 1108), (x0 + len(rec) * bw, 1108), 2)
    pygame.draw.line(s, GOLD, (x0, 1236), (x0 + len(rec) * bw, 1236), 2)
    for i, (lab, val) in enumerate(rec):
        cx = x0 + i * bw + bw // 2
        _text(s, lab, 1124, 24, GREY, bold=True, x=cx, spacing=3)
        _text(s, val, 1160, 44, NAVY, bold=True, x=cx, maxw=bw - 30)
        if i:
            pygame.draw.line(s, (214, 200, 160), (x0 + i * bw, 1122), (x0 + i * bw, 1222), 2)
    _text(s, "Given under the seal of %s on %d %s %d." % (LAB_SEAL, t.tm_mday, MONTHS[t.tm_mon - 1], t.tm_year), 1248, 36, INK, italic=True)

    _seal(s, CW // 2, 1400, tier)
    lx, rx = 520, CW - 520
    pygame.draw.line(s, INK, (lx - 300, 1452), (lx + 300, 1452), 2)
    _text(s, SIGN_NAME, 1462, 38, INK, bold=True, x=lx)
    _text(s, SIGN_TITLE, 1510, 29, GREY, italic=True, x=lx)
    _text(s, number(name, st), 1398, 38, INK, bold=True, x=rx)
    pygame.draw.line(s, INK, (rx - 300, 1452), (rx + 300, 1452), 2)
    _text(s, "Certificate number", 1462, 29, GREY, italic=True, x=rx)
    _text(s, "Awarded %d %s %d" % (t.tm_mday, MONTHS[t.tm_mon - 1], t.tm_year), 1500, 29, GREY, italic=True, x=rx)
    _text(s, DISCLAIMER, 1540, 19, (140, 136, 126))
    return s


def pdf_bytes(surf, title="Certificate"):
    """The surface as a one-page A4 landscape PDF (no external libraries needed)."""
    w, h = surf.get_size()
    img = zlib.compress(pygame.image.tobytes(surf, "RGB"), 6)
    pw, ph = 841.89, 595.28
    content = ("q %.2f 0 0 %.2f 0 0 cm /Im0 Do Q" % (pw, ph)).encode("ascii")

    def esc(t):
        return t.encode("ascii", "replace").decode("ascii").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>" % (pw, ph)).encode("ascii"),
        ("<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n"
         % (w, h, len(img))).encode("ascii") + img + b"\nendstream",
        ("<< /Length %d >>\nstream\n" % len(content)).encode("ascii") + content + b"\nendstream",
        ("<< /Title (%s) /Author (%s) /Creator (Journey of a Zebrafish) >>" % (esc(title), esc(LAB_NAME.title()))).encode("ascii"),
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs):
        offs.append(len(out))
        out += ("%d 0 obj\n" % (i + 1)).encode("ascii") + o + b"\nendobj\n"
    xref = len(out)
    out += ("xref\n0 %d\n" % (len(objs) + 1)).encode("ascii") + b"0000000000 65535 f \n"
    for o in offs:
        out += ("%010d 00000 n \n" % o).encode("ascii")
    out += ("trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode("ascii")
    return bytes(out)


def write_pdf(path, surf, title="Certificate"):
    with open(path, "wb") as f:
        f.write(pdf_bytes(surf, title))


def file_name(name, st):
    tier = max(0, st["tier"])
    safe = "".join(ch for ch in name.strip() if ch.isalnum() or ch in " -_.").strip() or "Certificate"
    return "%s - %s.pdf" % (TIERS[tier][0], safe)


def download(name, st):
    """Browser build: hand the PDF to the browser as a download."""
    import base64
    import platform
    tier = max(0, st["tier"])
    fn = file_name(name, st)
    b64 = base64.b64encode(pdf_bytes(render(name, st), TIERS[tier][0] + " - " + name)).decode("ascii")
    js = ("(function(){var a=document.createElement('a');a.href='data:application/pdf;base64,%s';"
          "a.download=%r;document.body.appendChild(a);a.click();a.remove();})()") % (b64, fn.encode("ascii", "replace").decode("ascii"))
    platform.window.eval(js)
    return fn


def out_dir():
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Documents"), os.path.join(home, "Desktop"), home):
        if os.path.isdir(base):
            d = os.path.join(base, "Journey of a Zebrafish")
            try:
                os.makedirs(d, exist_ok=True)
                return d
            except OSError:
                continue
    return home


def save(name, st):
    tier = max(0, st["tier"])
    path = os.path.join(out_dir(), file_name(name, st))
    write_pdf(path, render(name, st), TIERS[tier][0] + " - " + name)
    return path


def open_file(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass

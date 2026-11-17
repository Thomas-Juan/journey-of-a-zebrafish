# -*- coding: utf-8 -*-
"""Question picking and the knowledge score.

Questions come from two sources: the hand-written bank in facts.QUIZ, and
'fill in the year' questions generated from notebook pages the player has
actually collected - so reading the pages pays off."""
import re
from facts import FACTS, QUIZ

YEAR = re.compile(r"\b(1[89]\d\d|20[0-2]\d)\b")
RANKS = [(0, "Undergraduate"), (60, "PhD student"), (150, "Postdoc"), (280, "Group leader"),
         (450, "Professor"), (650, "Nobel laureate")]
GAIN, LOSS = 10, 5


def rank(k):
    name = RANKS[0][1]
    for t, n in RANKS:
        if k >= t:
            name = n
    return name


def next_rank(k):
    for t, n in RANKS:
        if k < t:
            return t, n
    return None


def cloze(world, idx, rnd):
    when, title, text = FACTS[world][idx]
    m = YEAR.search(text)
    if not m:
        return None
    y = int(m.group(1))
    if text.count(m.group(1)) > 1 or m.group(1) in title:
        return None      # the answer would be visible elsewhere in the question
    q = "From your notebook page '%s' - which year is missing?\n%s" % (title, text[:m.start()] + "_____" + text[m.end():])
    wrong = set()
    while len(wrong) < 2:
        c = y + rnd.choice([-1, 1]) * rnd.randint(3, 22)
        if 1800 < c <= 2025 and c != y and str(c) not in text:
            wrong.add(c)
    return q, [str(y)] + [str(c) for c in sorted(wrong)]


def pick(slot, world, rnd, asked=(), use_cloze=True):
    """Pick a question: a year question from collected pages, one about this world's
    history, or one from the general biology / methods / ethics bank."""
    cl = []
    if use_cloze:
        found = [int(f.split("-")[1]) for f in slot["pages"] if f.startswith("%d-" % world)]
        cl = [c for c in (cloze(world, i, rnd) for i in found) if c and c[0] not in asked]
    hw = [q for q in QUIZ[world] if q[0] not in asked] or QUIZ[world]
    bio = [q for q in QUIZ["bio"] if q[0] not in asked and q[0] not in slot.get("seen_q", [])] or \
          [q for q in QUIZ["bio"] if q[0] not in asked] or QUIZ["bio"]
    r = rnd.random()
    if cl and r < 0.3:
        item = rnd.choice(cl)
    elif r < 0.65:
        item = rnd.choice(hw)
    else:
        item = rnd.choice(bio)
        seen = slot.setdefault("seen_q", [])     # cycle through the whole bank before repeating
        seen.append(item[0])
        if len(seen) >= len(QUIZ["bio"]) - 3:
            del seen[:]
    o = list(item[1])
    rnd.shuffle(o)
    return dict(q=item[0], opts=o, correct=item[1][0], sel=0, answer=None, why=item[2] if len(item) > 2 else "")


def score(slot, right):
    slot["know"] = max(0, slot.get("know", 0) + (GAIN if right else -LOSS))
    slot["quiz"][1] += 1
    if right:
        slot["quiz"][0] += 1

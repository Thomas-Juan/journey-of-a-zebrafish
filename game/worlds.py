# -*- coding: utf-8 -*-
"""World, level and enemy definitions."""

# key: (ai, hp, speed, hit_w, hit_h, dashable, spiky, place, label)
ETYPES = {
    "nymph": ("crawl", 1, 0.8, 28, 16, True, False, "floor", "Dragonfly nymph"),
    "leech": ("float", 1, 0.6, 28, 12, True, False, "swim", "Leech"),
    "garfish": ("patrol", 1, 2.4, 54, 10, True, False, "swim", "Freshwater garfish"),
    "kingfisher": ("dive", 1, 7.0, 30, 36, True, False, "air", "Kingfisher"),
    "snakehead": ("lunge", 2, 6.5, 60, 20, True, False, "floor", "Snakehead"),
    "knifefish": ("chase", 2, 1.5, 50, 20, True, False, "swim", "Knifefish"),
    "net": ("dive", 99, 5.0, 44, 44, False, False, "air", "Fishing net"),
    "snail": ("crawl", 1, 0.4, 24, 18, True, False, "floor", "Snail"),
    "goldfish": ("patrol", 2, 1.2, 48, 30, True, False, "swim", "Goldfish"),
    "betta": ("chase", 2, 1.9, 44, 30, True, False, "swim", "Fighting fish"),
    "angelfish": ("bob", 2, 1.3, 34, 46, True, False, "swim", "Angelfish"),
    "ich": ("float", 1, 0.5, 14, 14, False, True, "swim", "Ich parasite"),
    "handnet": ("dive", 99, 5.5, 44, 44, False, False, "air", "Aquarium net"),
    "heater": ("beam", 99, 0, 16, 40, False, False, "floor", "Broken heater"),
    "phage": ("chase", 1, 1.0, 22, 30, True, False, "swim", "Bacteriophage T4"),
    "fly": ("dive", 1, 6.0, 24, 18, True, False, "air", "Fruit fly"),
    "mouse": ("hop", 2, 3.6, 36, 24, True, False, "floor", "Lab mouse"),
    "mouse2": ("hop", 3, 4.2, 36, 24, True, False, "floor", "Knockout mouse"),
    "frog": ("kick", 2, 3.4, 34, 28, True, False, "swim", "Xenopus frog"),
    "worm": ("crawl", 1, 1.6, 32, 10, True, False, "floor", "C. elegans"),
    "uvlamp": ("beam", 99, 0, 36, 14, False, False, "ceil", "UV lamp"),
    "reject": ("patrol", 1, 2.8, 28, 18, True, False, "swim", "Rejection letter"),
    "enu": ("emit", 99, 0, 18, 24, False, False, "ceil", "ENU dropper"),
    "cyclops": ("chase", 2, 1.7, 44, 18, True, False, "swim", "Cyclops mutant"),
    "notail": ("circle", 1, 1.6, 22, 18, True, False, "swim", "No-tail mutant"),
    "pipette": ("dive", 99, 6.0, 18, 60, False, False, "air", "Pipette"),
    "medaka": ("chase", 2, 2.3, 38, 16, True, False, "swim", "Medaka"),
    "bug": ("crawl", 1, 1.3, 24, 18, True, False, "floor", "Database bug"),
    "morpholino": ("homing", 1, 2.5, 28, 12, True, False, "swim", "Off-target morpholino"),
    "transposon": ("hop", 1, 5.2, 24, 24, True, False, "floor", "Jumping gene"),
    "paralog": ("split", 1, 1.3, 34, 34, True, False, "swim", "Paralog"),
    "paralog_s": ("chase", 1, 1.8, 20, 20, True, False, "swim", "Paralog copy"),
    "repeat": ("patrol", 3, 1.0, 74, 16, True, False, "swim", "Repeat element"),
    "vortex": ("vortex", 99, 0, 26, 26, False, False, "swim", "Assembly gap"),
    "fugu": ("puff", 2, 1.2, 34, 22, True, False, "swim", "Fugu"),
    "stickleback": ("patrol", 2, 1.9, 38, 16, True, False, "swim", "Stickleback"),
    "scissors": ("bounce", 1, 2.4, 26, 26, True, False, "swim", "Off-target Cas9"),
    "laser": ("beam", 99, 0, 36, 14, False, False, "ceil", "Laser"),
    "myco": ("float", 1, 0.9, 20, 10, True, False, "swim", "Mycobacterium"),
    "spore": ("float", 1, 0.5, 16, 16, False, True, "swim", "Pseudoloma spore"),
    "reviewer": ("shoot", 3, 0.8, 30, 44, True, False, "swim", "Reviewer"),
    "killifish": ("chase", 2, 2.6, 38, 18, True, False, "swim", "Killifish"),
    "danionella": ("patrol", 1, 3.0, 22, 8, True, False, "swim", "Danionella"),
    "organoid": ("split", 2, 0.9, 38, 38, True, False, "swim", "Organoid"),
    "organoid_s": ("chase", 1, 1.5, 22, 22, True, False, "swim", "Mini organoid"),
    "robot": ("shoot", 3, 0.6, 30, 34, True, False, "swim", "In-silico model"),
    "cut": ("dive", 99, 6.5, 50, 56, False, False, "air", "Funding cut"),
    "debris": ("bounce", 2, 1.8, 26, 26, True, False, "swim", "Space debris"),
}
SPLIT_INTO = {"paralog": "paralog_s", "organoid": "organoid_s"}
BEAM = {"heater": ("up", (255, 120, 40), 150, 70), "uvlamp": ("down", (190, 120, 255), 130, 60),
        "laser": ("down", (90, 255, 255), 90, 45)}  # dir, colour, period, on-time

WORLDS = {
    0: dict(name="Zebrafish handbook", years="always open", boss=None, intro=""),
    1: dict(name="Rivers of the Ganges", years="Before 1822", boss="b_snakehead",
            intro="For millions of years, small striped fish have shoaled in the warm, shallow waters of the Ganges and Brahmaputra floodplains. You are one of them. Nobody has given you a name yet - and everything out there wants to eat you."),
    2: dict(name="The Aquarium Trade", years="1905 - 1958", boss="b_cat",
            intro="A net, a tin can, and a long sea voyage: the zebra danio becomes a star of European and American living rooms. And here and there, a curious scientist begins to look closely at your transparent eggs."),
    3: dict(name="A Fish Room in Oregon", years="1960 - 1990", boss="b_mouse",
            intro="In Eugene, Oregon, the phage geneticist George Streisinger wants a vertebrate he can do real genetics with. The mouse, the fly, the frog and the worm already rule the laboratory. He bets on a pet-shop fish."),
    4: dict(name="The Big Screen", years="1990 - 2000", boss="b_fly",
            intro="Tubingen and Boston: two giant mutagenesis screens, thousands of tanks and thousands of mutants with unforgettable names. Around them a community builds its tools - ZFIN, ZIRC, The Zebrafish Book."),
    5: dict(name="The Genome", years="2000 - 2013", boss="b_fugu",
            intro="Morpholinos, transposons, a heart that regrows - and 1.4 billion letters of DNA to put in order. Swim through the sequence sea, where every gene seems to come in two copies."),
    6: dict(name="A Leading Model", years="2013 - today", boss="b_reviewer",
            intro="CRISPR, light-sheet microscopes, drug screens, patient avatars. The little fish from the rice paddies is now one of the leading vertebrate models in biomedical research. Only one obstacle remains. It has comments."),
    7: dict(name="Orbit (bonus)", years="1976 - 2024", boss=None,
            intro="Bonus world! Zebrafish have left the planet more than once. In microgravity, water floats in blobs and so do you: outside the water you drift in straight lines until you touch something."),
}


def L(id, name, when, lon, lat, style, length, dens, pool, segs, blurb, **flags):
    w = int(id[0])
    length = int(length * (1.25 if id == "1-1" else 1.6))
    dens = dens * (1.0 if w == 1 else 1.25)
    d = dict(id=id, world=w, name=name, when=when, lon=lon, lat=lat, style=style, len=length,
             dens=dens, pool=pool.split(), segs=segs.split(), blurb=blurb, boss=None)
    d.update(flags)
    return d


def B(id, name, when, lon, lat, boss, blurb):
    return dict(id=id, world=int(id[0]), name=name, when=when, lon=lon, lat=lat, boss=boss, blurb=blurb,
                style="arena", len=30, dens=0, pool=[], segs=[])


LEVELS = [
 L("1-1", "Rice Paddy Nursery", "Bengal, long ago", 88, 25.5, "river", 150, 0.5, "nymph leech leech", "open open pillars islands",
   "A flooded rice field: warm, shallow and full of food. A good place to learn to swim.",
   signs=[(4, "Arrow keys or WASD: swim"), (22, "SPACE: dash. A dash knocks out most enemies."), (44, "Collect notebook pages - each one is a true story."),
          (66, "Dash UPWARD near the surface to leap over walls."), (96, "Flags are checkpoints. Bubbles hold power-ups."),
          (120, "Find the letters D-A-N-I-O for a bonus. Bubble jets launch you!")], force=[(70, "leap"), (126, "jets")]),
 L("1-2", "Shoal Stream", "Bengal, long ago", 84.5, 27, "river", 180, 0.7, "nymph leech garfish garfish", "open pillars islands leap hazard",
   "Zebrafish live in shoals. Find companions: each one will take a hit for you.",
   signs=[(14, "Cracked blocks break when you dash into them."), (40, "A glowing gate asks a question: a wrong answer costs a heart!")], force=[(20, "vault")]),
 L("1-3", "Kingfisher Shallows", "Ganges plain", 80.5, 27.5, "river", 200, 0.9, "kingfisher kingfisher garfish nymph leech", "open leap pillars hazard islands",
   "Shallow water is warm and rich - and exposed. Watch the sky."),
 L("1-4", "Monsoon Flood", "Monsoon season", 77, 30, "river", 220, 0.8, "leech garfish knifefish nymph", "open pillars islands open",
   "The monsoon turns streams into torrents. Keep ahead of the muddy flood wave!", chase=1.75),
 L("1-5", "Snakehead Hollow", "Under the roots", 79.5, 23, "cave", 220, 1.0, "snakehead snakehead knifefish nymph leech", "tunnel pillars open shaft hazard",
   "Under the tangled roots it is dark, and snakeheads wait motionless for small fish.", dark=True),
 L("1-6", "Hamilton's Survey", "Bengal, 1822", 86, 21.5, "river", 240, 1.1, "net net snakehead kingfisher garfish knifefish", "open leap pillars hazard islands tunnel arena",
   "A Scottish surveyor, Francis Hamilton, is netting every fish in the Ganges to describe them. One of them will be you."),
 B("1-B", "The Great Snakehead", "BOSS", 91, 24.5, "b_snakehead",
   "The old predator of the floodplain blocks the way to the sea. Dodge its charge - and dash it while it is dazed."),

 L("2-1", "The Shipping Can", "At sea, c. 1905", 60, 12, "cave", 200, 0.9, "snail ich ich leech", "tunnel pillars current open hazard",
   "Weeks at sea in a sloshing tin can, bound for the aquarium dealers of Germany."),
 L("2-2", "Pet Shop Row", "Hamburg, 1900s", 10, 54, "tank", 220, 1.0, "goldfish snail handnet ich", "leap open islands leap pillars",
   "Rows of glass tanks. Leap from one to the next - and avoid the shopkeeper's net."),
 L("2-3", "Community Tank", "Berlin, 1910s", 14.5, 51.5, "tank", 230, 1.1, "goldfish betta angelfish snail", "open islands pillars arena leap",
   "A peaceful community aquarium, they said. Somebody forgot to tell the fighting fish."),
 L("2-4", "The Heater Is Broken", "Paris, 1920s", 2.3, 48.5, "tank", 240, 1.2, "heater heater ich betta handnet goldfish", "hazard leap pillars open islands",
   "Swinging temperatures invite 'ich', the white-spot parasite. Wait for the hot plumes to stop."),
 L("2-5", "Creaser's Laboratory", "Detroit, 1934", -83, 42.3, "tank", 250, 1.2, "handnet angelfish goldfish ich betta", "leap shaft islands arena pillars open",
   "Charles Creaser explains how to obtain zebrafish eggs for embryology at any time of year. A scientist is watching you."),
 L("2-6", "Embryos on Film", "1930s - 1958", -122.3, 47.6, "cave", 260, 1.3, "betta angelfish ich goldfish leech", "tunnel pillars shaft open hazard islands",
   "Roosen-Runge films your embryos; Hisaoka and Battle draw every stage. Swim through the flicker of the projector.", dark=True),
 B("2-B", "The House Cat", "BOSS", -88, 41.5, "b_cat",
   "Every aquarium fish knows this shadow. When the paw gets stuck in the gravel, dash it!"),

 L("3-1", "Phage Country", "Cold Spring Harbor, 1950s", -74.5, 40.3, "open", 240, 1.2, "phage phage phage reject leech", "open islands pillars arena hazard",
   "Before fish, George Streisinger was a master of bacteriophage T4. The phages have not forgotten."),
 L("3-2", "A Fish Room in Eugene", "Oregon, late 1960s", -123, 44, "tank", 250, 1.2, "snail fly fly handnet worm goldfish", "leap open islands pillars leap arena",
   "Streisinger sets up tanks at the University of Oregon. Fruit flies buzz over from the lab next door."),
 L("3-3", "UV and Pressure", "Oregon, 1970s", -119, 41.5, "cave", 250, 1.3, "uvlamp uvlamp phage worm frog", "current shaft tunnel hazard pillars open",
   "UV light to silence the sperm's DNA; a pulse of pressure to double the egg's. Time your way through."),
 L("3-4", "Clone Waters", "Nature, 1981", -117.5, 48.5, "tank", 260, 1.3, "fly frog uvlamp reject worm", "leap islands arena pillars open hazard",
   "'Production of clones of homozygous diploid zebra fish'. The paper is out! Shoals of clones are waiting to join you.", buddies=True),
 L("3-5", "The Skeptics", "1980s", -81, 37, "cave", 270, 1.4, "mouse mouse frog fly worm reject", "open pillars arena islands hazard tunnel",
   "'Why not just use mice?' Established models guard their territory - and their funding."),
 L("3-6", "Carrying the Torch", "Eugene, 1984 - 1990", -113, 46.5, "river", 280, 1.3, "mouse frog phage reject fly", "open pillars islands leap open",
   "Streisinger dies suddenly in 1984. Kimmel, Westerfield, Eisen, Walker and others refuse to let the project sink. Keep moving!", chase=1.9),
 B("3-B", "Mus Rex", "BOSS", -68, 44.5, "b_mouse",
   "The reigning vertebrate model, in a diving helmet. It must surface for air - that is your moment."),

 L("4-1", "The Tubingen Fish House", "Germany, 1992", 9, 47, "tank", 260, 1.3, "fly pipette cyclops snail fly", "leap open islands leap pillars arena",
   "Christiane Nusslein-Volhard builds a fish house with thousands of tanks. Mind the pipettes."),
 L("4-2", "ENU Rain", "1994", 13.5, 47.5, "cave", 270, 1.4, "enu enu notail cyclops worm", "hazard pillars open tunnel shaft",
   "ENU, a powerful mutagen, drips from above. What it touches, it changes."),
 L("4-3", "Mutant Menagerie", "1993 - 1996", 5.5, 45, "open", 280, 1.5, "cyclops notail notail frog medaka", "open islands arena pillars hazard",
   "One-eyed pinhead, no tail, dracula, van gogh... the screen's mutants swim in every direction."),
 L("4-4", "Boston Harbor Screen", "Boston, 1993 - 1996", -71, 42.4, "river", 280, 1.5, "enu pipette cyclops medaka fly notail", "open leap pillars islands hazard arena",
   "Across the Atlantic, Wolfgang Driever and Mark Fishman run a second great screen."),
 L("4-5", "ZFIN Online", "Oregon, 1994", -126, 42, "cave", 290, 1.5, "bug bug notail reject uvlamp", "tunnel shaft pillars open hazard islands",
   "Monte Westerfield's team builds a database for the whole community. Every database has bugs.", theme=5),
 L("4-6", "The Zebrafish Issue", "December 1996", -3, 54.5, "tank", 300, 1.6, "reject reject cyclops medaka pipette enu fly", "leap open islands pillars arena hazard leap",
   "Thirty-seven papers in one issue of Development. The deadline is right behind you!", chase=2.0),
 B("4-B", "Queen Drosophila", "BOSS", 8.5, 50.5, "b_fly",
   "The queen of developmental genetics hovers above the water. Leap out and dash her from below!"),

 L("5-1", "Morpholino Rush", "Minnesota, 2000", -93.3, 45, "open", 280, 1.5, "morpholino morpholino stickleback paralog", "open islands pillars arena hazard",
   "Knock down any gene in a week! But some morpholinos hit targets they were never aimed at."),
 L("5-2", "Sequence Sea", "Hinxton, 2001", 1.5, 52.8, "open", 290, 1.5, "repeat repeat transposon paralog stickleback", "open islands pillars hazard arena",
   "The Sanger Institute starts to read your genome: 1.4 billion letters, more than half of them repeats."),
 L("5-3", "Transposon Reef", "Mishima, 2000 - 2004", 139, 35.5, "cave", 300, 1.6, "transposon transposon medaka medaka repeat", "open pillars islands tunnel arena hazard",
   "Koichi Kawakami tames Tol2, a jumping gene - borrowed from your rival, the medaka."),
 L("5-4", "Paralog Passage", "320 million years deep", -105, 40, "cave", 300, 1.6, "paralog paralog paralog fugu repeat", "tunnel shaft pillars open arena islands",
   "An ancestral fish doubled its whole genome. Hit a paralog and you will see what that means."),
 L("5-5", "Regeneration Deep", "2002", -79, 35.5, "open", 310, 1.6, "stickleback fugu morpholino paralog vortex", "open islands hazard arena pillars",
   "Poss, Wilson and Keating show that a zebrafish heart grows back. Down here, hearts are plentiful.", hearts=True),
 L("5-6", "Assembly Gaps", "Hinxton, 2013", -5, 50.5, "cave", 320, 1.7, "vortex vortex repeat transposon morpholino paralog", "shaft tunnel pillars open hazard arena",
   "The reference genome is nearly finished - except for the gaps, which swallow anything that swims too close.", dark=True),
 B("5-B", "Fugu, the Compact Genome", "BOSS", 103.8, 1.3, "b_fugu",
   "Sydney Brenner's pufferfish: a genome an eighth the size of ours, and a very short temper. Strike when it deflates."),

 L("6-1", "CRISPR Cut", "Boston, 2013", -72.5, 45.5, "open", 300, 1.6, "scissors scissors danionella medaka reject", "open islands pillars arena hazard",
   "Genome editing arrives. Pick up the CRISPR power-up and press X - but watch for off-target cuts."),
 L("6-2", "Light-Sheet Lagoon", "Janelia, 2013", -77.4, 39.3, "cave", 310, 1.7, "laser laser laser danionella scissors robot", "shaft pillars open tunnel hazard islands",
   "Sheets of laser light scan the water to film every cell and every neuron. Slip between the scans.", dark=True),
 L("6-3", "The Facility Outbreak", "A fish facility near you", -121.5, 37.5, "tank", 320, 1.8, "myco myco spore spore vortex handnet", "leap open pillars islands hazard arena leap",
   "Pseudoloma and Mycobacterium are loose in the racks, and a pump has failed. Quarantine yourself - quickly."),
 L("6-4", "Drug Screen Plates", "Salt Lake City", -111.9, 40.7, "tank", 320, 1.8, "pipette pipette robot scissors organoid enu", "leap leap open arena islands pillars hazard",
   "Ninety-six wells, thousands of compounds, one whole living vertebrate in each. Hop from well to well."),
 L("6-5", "Rival Models", "Everywhere", 132, 33.5, "open", 330, 1.9, "killifish killifish danionella organoid robot mouse2 medaka", "open islands arena pillars hazard arena",
   "Killifish, Danionella, medaka, organoids, in-silico models, knockout mice: everyone wants your grant."),
 L("6-6", "Valley of Death", "Bench to bedside", -9, 38.7, "cave", 340, 2.0, "cut cut reviewer reviewer robot organoid killifish spore", "shaft tunnel pillars open hazard arena islands",
   "Between a discovery in fish and a treatment for patients lies a long dark valley of funding cuts and peer review.", chase=1.9),
 B("6-B", "Reviewer #2", "FINAL BOSS", -0.5, 51.3, "b_reviewer",
   "'The authors should repeat all experiments in mice.' Survive the comments, then dash while the reviewer reads your rebuttal."),

 L("7-1", "Salyut 5", "Low Earth orbit, 1976", -40, 74, "space", 220, 1.2, "debris debris leech", "open islands pillars",
   "Zebrafish orbit the Earth aboard a Soviet space station.", zero_g=True),
 L("7-2", "The Aquatic Habitat", "ISS, 2012", 20, 74, "space", 260, 1.5, "debris medaka medaka laser", "open islands pillars hazard arena",
   "JAXA's aquarium on the International Space Station. The medaka got here first.", zero_g=True),
 L("7-3", "Tiangong", "2024", 100, 74, "space", 300, 1.8, "debris killifish danionella laser scissors", "open islands pillars hazard arena",
   "Four zebrafish and some water plants in a closed ecosystem aboard China's space station.", zero_g=True),
]
INDEX = {lv["id"]: i for i, lv in enumerate(LEVELS)}

ENDING = ("From the rice paddies of Bengal to more than a thousand laboratories: in two centuries the zebrafish went from "
          "'Cyprinus rerio' in Hamilton's notebook to one of the leading vertebrate models of biomedical research.\n\n"
          "It got there because people shared - fish lines, protocols, mutants, a genome, a database - and because a small "
          "transparent embryo lets us watch life build itself.\n\nThank you for swimming along.")

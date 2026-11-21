# Journey of a Zebrafish

A side-scrolling swimming adventure that retraces the history of *Danio rerio*: from the
rice paddies of Bengal, through the aquarium trade and George Streisinger's fish room in
Oregon, the big mutagenesis screens and the genome project, to today's CRISPR-era model
organism. 6 worlds + a bonus world, 39 levels, 6 bosses, 135 collectible "lab notebook"
pages of zebrafish history and a quiz after every level.

Made by the [Juan Lab](https://juanlab.org), Uppsala University.

## Play

**In a browser:** on [juanlab.org](https://juanlab.org/#games), press *Play in browser* (needs a
keyboard; progress is kept in that browser).

**Download:** the latest Windows and macOS builds are on the
[Releases page](https://github.com/Thomas-Juan/journey-of-a-zebrafish/releases/latest).

- **Windows:** download `JourneyOfAZebrafish-Windows.exe` and double-click it. The program is not
  code-signed, so Windows may show a "Windows protected your PC" notice the first time:
  choose *More info*, then *Run anyway*.
- **macOS (Apple silicon):** download `JourneyOfAZebrafish-macOS.zip`, unzip it, then right-click
  the app and choose *Open* the first time (the app is not signed by Apple).
- **Any system, from source:** install Python 3.10+ and run
  `pip install pygame-ce numpy`, then `python game/main.py`
  (on macOS you can double-click `run_from_source.command`).

To build the downloads yourself: `build_windows.bat` on Windows (the program goes to `dist/`), `build_mac.command` on a Mac (to `dist-mac/`).
Pushing a tag such as `v1.0` to GitHub builds both automatically and attaches them to a release.

## Controls

| Key | Action |
| --- | --- |
| Arrows / WASD | Swim; move on the world map |
| Space (or Z) | Dash - knocks out most enemies; dash upward at the surface to leap |
| X | CRISPR shot (when you have the power-up) |
| Enter / Space | Confirm |
| Esc | Pause / back |
| Tab (on map) | Fishipedia - every notebook page you have found |
| U (on map) | Upgrades, bought with collected food |
| F11 | Fullscreen (the game always starts in a window) |
| F3 | Show frame rate and sound status |

Progress is saved automatically (3 save slots) in
`%APPDATA%\JourneyOfAZebrafish` on Windows and
`~/Library/Application Support/JourneyOfAZebrafish` on macOS.

## In each level

- 3 notebook pages (true facts, kept in the Fishipedia)
- the letters D-A-N-I-O (collect all five for a bonus)
- 2 checkpoint flags, power-up bubbles (shoal-mates, regeneration, GFP glow, casper, CRISPR)
- bubble jets that launch you over walls

## Learning is part of the game

- **Peer-review gate** (glowing column half-way through each level): one question. Right: +1 heart, +30 food.
  Wrong: -1 heart, -15 food.
- **Qualifying exam** before every boss: three questions. Each wrong answer costs a heart for the fight;
  three right answers earn a shoal-mate.
- **Final question** after each level: +25 food if right, -15 if wrong.
- Many questions are "fill in the year" questions built from the notebook pages you actually collected,
  so reading them pays off. Every answer moves your **knowledge score** (+10 / -5), which sets your
  academic rank from Undergraduate to Nobel laureate.

The questions cover the history told in each world and a general bank on zebrafish biology,
development, genetics, husbandry, methods, the advantages and limits of the model, and ethics
(3Rs, legislation, welfare, good experimental practice). After every answer a one-line explanation
is shown, and the same material can be read at any time in the **Zebrafish handbook**, the first
section of the Fishipedia.

## Certificates

When you defeat the final boss you receive a certificate from the Juan Lab; it is also available
later from the map menu (ESC > Certificate). Type the name to print on it and choose *Save as PDF*:
an A4 landscape PDF is written to `Documents/Journey of a Zebrafish/` and opened.

| Certificate | Requirements |
| --- | --- |
| Completion | Defeat Reviewer #2 |
| Merit | + at least 90 notebook pages and 60 % of questions correct |
| Distinction | + all 45 levels, all 135 pages and 75 % correct |
| Excellence (summa cum laude) | + D-A-N-I-O in all 39 levels and 90 % correct |

The laboratory name, signatory and wording are plain constants at the top of `game/certificate.py`.

Other things to find: cracked blocks (dash to break into hidden chambers), rising and sinking water
columns, and three stars per level on the map (cleared / all pages / D-A-N-I-O).

## Source

Everything is in `game/` (Python + pygame-ce; all graphics and sound are generated in code,
except `game/juanlab.png`, the lab logo shown at start-up).
`facts.py` holds the historical facts and quiz questions if you want to correct or extend them.
Rebuild the Windows exe with `build_windows.bat`.

The game is laid out on a 960 x 540 stage. On the desktop it is drawn at twice that resolution
and scaled smoothly to the window, so it stays sharp in a large window or full screen
(*Options > Graphics: sharp*). *Graphics: fast* draws at 960 x 540 for slower computers; the game
switches to it by itself if a level cannot keep up. The browser version always uses the fast setting.
`core.py` holds the drawing layer (`Hi`, `Canvas`, `dr`), `gfx.py` the sprites.

The typeface is Inter by Rasmus Andersson (SIL Open Font License, `game/fonts/Inter-LICENSE.txt`),
embedded in `game/fontdata.py` so it is the same in every build.

The same source runs in a browser: `python -m pygbag --build game` (after `pip install pygbag`)
writes a web build to `game/build/web/`. In the browser, saves go to the browser's local storage
and the certificate PDF is offered as a download.

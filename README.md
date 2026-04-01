# Addventure

A compiler for paper-based text adventures where **addition is the parser**.

Players solve games using only pencil, paper, and arithmetic: look up a Verb ID and an Entity ID, add them together, find the sum in a potentials list, then read the corresponding ledger entry. No electronics needed at the table.

## How It Works

A game compiles down to a printable PDF with four sheet types:

- **Verb Sheet** — lists each action (LOOK, USE, TAKE...) with its numeric ID
- **Room Sheets** — one per location, listing objects and their IDs
- **Inventory & Potentials List** — tracks carried items; maps every valid sum to a ledger entry
- **Story Ledger** — numbered narrative entries with instructions ("cross out X, write Y")

The player's loop: pick a verb, pick a target, add the IDs, look up the sum. If it's in the potentials list, read the ledger entry and follow the instructions (state changes, item transfers, room transitions).

## Quick Start

Python 3.10+, no external dependencies. Uses [uv](https://docs.astral.sh/uv/) as the runner. PDF output requires [Typst](https://typst.app/) installed on your system.

```bash
uv run adv run                     # compile example game to PDF (example.pdf)
uv run adv run games/example       # same thing, explicit path
uv run adv run path/to/game        # your own game
uv run adv run --text              # plain text output instead of PDF
uv run adv run -o output.pdf       # custom output path
uv run adv new my-game             # scaffold a new game directory
```

If `typst` is not on your PATH, the compiler falls back to plain text output automatically.

## Writing Games

A game is a directory of `.md` files. You need one `index.md` for metadata, verbs, and items; all other `.md` files define rooms and are loaded alphabetically.

### `index.md`

```markdown
---
title: The Facility
author: Example
---

# Verbs
USE
TAKE
LOOK

# Items
CROWBAR
KEYCARD
KNIFE
```

The frontmatter metadata (`title`, `author`) is used in PDF sheet titles and page footers.

### Room files

```markdown
# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout.
  - KEYCARD -> trash
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    + HATCH -> room
      + LOOK: A dark opening, just wide enough to squeeze through.
      + USE:
        You lower yourself into the darkness.
        - player -> "Basement"

CRATE
+ LOOK: A heavy wooden crate, nailed shut.
+ USE + CROWBAR:
  You pry it open. A keycard glints inside.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - KEYCARD -> room
    + LOOK: A small keycard among the splinters.
    + TAKE:
      You pocket the keycard.
      - KEYCARD -> player
  - CROWBAR -> trash
```

### Script syntax reference

| Syntax | Meaning |
|---|---|
| `+ VERB: text` | Interaction on an entity |
| `+ VERB + TARGET:` | Multi-entity interaction (verb + two things) |
| `ENTITY__STATE` | Double-underscore separates entity from state |
| `- ENTITY -> destination` | Arrow — moves/transforms an entity |
| `-> player` | Move to inventory |
| `-> trash` | Remove from game |
| `-> "RoomName"` | Move player to another room |
| `-> room` | Place in current room |
| `-> ENTITY__STATE` | Transform entity to a new state |
| `@room` | Reference to the current room entity |
| `*` wildcard | Matches all entities in room |

Room-level interactions use `VERB: text` without the `+` prefix. Entity interactions and arrows use `+` and `-` prefixes respectively. Indentation defines the hierarchy: arrows nested under an interaction fire when that interaction triggers, and child interactions on a state-changed entity only apply in that state.

### Interactions section

Room files can have a `# Interactions` section for interactions that don't belong to a specific noun:

```markdown
# Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

## Example Output

Running `uv run adv run` generates a PDF with sheets like:

```
THE FACILITY — VERB SHEET
========================================

  USE                  [ 32 ]
  TAKE                 [ 21 ]
  LOOK                 [ 51 ]
```

```
ROOM: CONTROL ROOM
Room ID: 144

Objects in this room:
  TERMINAL                 951
  CRATE                    963
  WALL_PANEL               662
  BINDINGS                 949
```

The potentials list maps sums to ledger entries (e.g., `LOOK + TERMINAL = 51 + 951 = 1002 → Entry #5`), and the story ledger contains the narrative with physical instructions for updating your sheets.

IDs are randomly assigned each compilation, so every printout is a unique puzzle.

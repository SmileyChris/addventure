# Getting Started

This guide walks you through creating and compiling your first Addventure game.

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — Python package runner
- **[Typst](https://typst.app/)** (optional, recommended) — for PDF output. Without it, use `--md` for plain text.

## Running Addventure

Install once with uv:

```bash
uv tool install addventure
```

This puts the `addventure` command in your PATH. For a one-off run without installing, use `uvx addventure`.

The rest of this guide uses `addventure`.

## Scaffold a new game

```bash
addventure new "Sunken Library"
```

This creates a game directory with a starter `index.md`:

```
games/sunken-library/
  index.md
```

For an interactive setup (choose your own verbs, set an author name):

```bash
addventure new
```

## The index file

Open `games/sunken-library/index.md`. You'll see something like:

```markdown
---
title: Sunken Library
---

# Verbs
LOOK
USE
TAKE

# Inventory

```

This file defines three things:

**Frontmatter** (between `---` fences)
:   Metadata for your game. `title` appears on printed sheets. You can also add `author` and `start` (which room players begin in).

**Verbs** (under `# Verbs`)
:   The actions players can perform. List one per line, in `ALL_CAPS`. Three verbs is a good starting point — you can always add more.

**Inventory objects** (under `# Inventory`)
:   Objects that live in the player's inventory. Inventory objects can be picked up, carried between rooms, and used in interactions. Leave this empty for now — we'll add inventory objects as we build out rooms.

## Create your first room

Create a new file `games/sunken-library/reading_room.md`:

```markdown
# Reading Room
LOOK: Water-stained shelves sag under the weight of ruined books. A faint
  glow pulses from somewhere beneath the debris.

DESK
+ LOOK: A heavy oak desk, mostly intact. Papers are scattered across it.

LANTERN
+ LOOK: An old brass lantern, half-buried in soggy pages. Still has fuel.
+ TAKE:
  You pull the lantern free and light it. The room brightens.
  - LANTERN -> player
```

Let's break this down:

- `# Reading Room` — declares a room. The header text becomes the room name.
- `LOOK: ...` at the top — the room-level description. Players see this when they LOOK at the room itself.
- `DESK` and `LANTERN` — room objects. Bare `ALL_CAPS` names on their own line. These are objects in the room.
- `+ LOOK:` and `+ TAKE:` — interactions on a room object. The `+` prefix marks an interaction.
- Indented text — narrative. The story the player reads when the interaction triggers.
- `- LANTERN -> player` — an arrow. Moves the lantern to the player's inventory.

## Build and play

Compile to PDF:

```bash
addventure build games/sunken-library
```

Or markdown if you don't have Typst:

```bash
addventure build games/sunken-library --md
```

You can also build from inside the game directory:

```bash
cd games/sunken-library
addventure build
```

The PDF contains all the sheets players need — print it out and play.

## Try the example game

Addventure ships with a complete example game. If you have the source code checked out, build it with:

```bash
addventure build games/example
```

Browse the source files at [github.com/SmileyChris/addventure/tree/main/games/example](https://github.com/SmileyChris/addventure/tree/main/games/example) to see a full game with entity states, multi-target interactions, verb states, and room transitions.

## Design tips

**Start small.** A good first game has 2-3 rooms with a few puzzles. The [example game](https://github.com/SmileyChris/addventure/tree/main/games/example) is a good template.

**Name things clearly.** `RUSTY_KEY` is better than `KEY2`. Players see these names on their sheets.

**Test by building often.** Run `addventure build --md` frequently as you write. The compiler catches errors (undefined room objects, bad arrows) and reports them with line numbers.

**Think about the paper experience.** Every state change means the player has to cross something out and write something new. Complex chains of arrows create complex instructions — keep it manageable.

## Next steps

Now that you have a game building, learn how to flesh out rooms with richer interactions in [Writing Rooms](writing-rooms.md).

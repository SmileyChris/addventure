# Getting Started

This guide walks you through creating and compiling your first Addventure game.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** — Python package runner
- **[Typst](https://typst.app/)** (optional) — for PDF output. If Typst isn't installed, Addventure falls back to plain text.

## Install Addventure

Clone the repository and you're ready to go:

```bash
git clone https://github.com/user/addventure.git
cd addventure
```

## Scaffold a new game

```bash
uv run adv new "Sunken Library"
```

This creates a game directory with a starter `index.md`:

```
games/sunken-library/
  index.md
```

For an interactive setup (choose your own verbs, set an author name):

```bash
uv run adv new
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

# Items

```

This file defines three things:

**Frontmatter** (between `---` fences)
:   Metadata for your game. `title` appears on printed sheets. You can also add `author` and `start` (which room players begin in).

**Verbs** (under `# Verbs`)
:   The actions players can perform. List one per line, in `ALL_CAPS`. Three verbs is a good starting point — you can always add more.

**Items** (under `# Items`)
:   Objects that live in the player's inventory. Items can be picked up, carried between rooms, and used in interactions. Leave this empty for now — we'll add items as we build out rooms.

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
- `DESK` and `LANTERN` — nouns. Bare `ALL_CAPS` names on their own line. These are objects in the room.
- `+ LOOK:` and `+ TAKE:` — interactions on a noun. The `+` prefix marks an interaction.
- Indented text — narrative. The story the player reads when the interaction triggers.
- `- LANTERN -> player` — an arrow. Moves the lantern to the player's inventory.

## Build and play

Compile to PDF:

```bash
uv run adv build games/sunken-library
```

Or markdown if you don't have Typst:

```bash
uv run adv build games/sunken-library --md
```

You can also build from inside the game directory:

```bash
cd games/sunken-library
uv run adv build
```

The PDF contains all the sheets players need — print it out and play.

## Try the example game

Addventure ships with a complete example game you can study:

```bash
uv run adv build games/example
```

Look at the files in `games/example/` to see a full game with entity states, multi-target interactions, verb states, and room transitions.

## Next steps

Now that you have a game building, learn how to flesh out rooms with richer interactions in [Writing Rooms](writing-rooms.md).

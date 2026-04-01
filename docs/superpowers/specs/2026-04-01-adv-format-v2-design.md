# Addventure — .md Format Specification

## Overview

Game scripts use `.md` files with markdown conventions. Files render readably in any markdown viewer while serving as the source format for the Addventure compiler.

## CLI

```
adv build [dir] [--text] [-o FILE]   # Compile game to PDF (default) or text
adv build                            # Build cwd if game dir, else games/example from project root
adv new [name]                       # Scaffold new game (interactive if no name)
adv new "Chapter Name"               # From inside a game dir: creates chapter subdirectory
```

`adv new` is context-aware:
- From project root (has `games/` dir): creates `games/<slugified-name>/`
- From inside a game dir (has `index.md` with `# Verbs`): creates a chapter subdirectory
- Elsewhere: creates `<slugified-name>/` in cwd
- Name is slugified for directories (e.g. "The Underground" → `the-underground/`), preserved as title

## File Structure

```
games/my-game/
  index.md              # Frontmatter + description + verbs + items
  control_room.md       # Room script
  basement.md           # Room script
  the-underground/      # Chapter B
    index.md            # New verbs/items for this chapter
    tunnels.md          # Room script
```

- Entry point: `index.md` (frontmatter, description, `# Verbs`, `# Items`)
- Room scripts: all other `.md` files, loaded alphabetically
- `games/.gitignore` tracks only `example/`, ignores user-created games

## index.md Structure

```markdown
---
title: The Facility
author: Chris
start: Control Room
entry_prefix: A
chapters: The Underground, The Surface
---

You wake up bound to a chair. Your wrists burn against coarse rope.
The air tastes of rust and stale electricity.

You need to get out. Use what you can find. Trust nothing.

# Verbs
USE
TAKE
LOOK

# Items
CROWBAR
KEYCARD
KNIFE
```

### Frontmatter (between `---` fences)

All keys optional:
- `title` — game/chapter title, used in PDF header and output filename
- `author` — shown in PDF footer
- `start` — starting room name (falls back to first base room)
- `entry_prefix` — ledger entry prefix, default `A` (chapter B uses `B`, etc.)
- `chapters` — comma-separated list of chapter subdirectory names, defines order

### Description (body text before first `#` header)

Plain text between frontmatter and the first `# Header`. Rendered at 11pt in PDF with an HR separator before the how-to-play instructions. Supports Typst markup (`*italic*`, `**bold**`) via `eval()`.

## Syntax Reference

### Headers

```markdown
# Verbs          // Known section (case-insensitive)
# Items          // Known section
# Interactions   // Known section (freeform, room-level)
# Control Room   // Anything else = room name
```

### List Markers

- `+` — additions: interactions and behaviors on an entity
- `-` — state changes: arrows (movement, destruction, transformation)
- No marker — narrative text (indented under an interaction)

### Comments

```markdown
// This is a comment
```

### Arrows

```markdown
- THING -> trash           // Destroy
- THING -> player          // To inventory
- THING -> room            // Reveal in current room
- THING -> "Other Room"    // Move to another room (quotes required for room names)
- THING -> THING__STATE    // Transform to new state
- player -> "Room Name"    // Player movement
- ? -> "Room Name"         // Cue: deferred cross-room effect
    Narrative text here.   //   resolved when player enters target room
    - THING -> room        //   arrows execute in target room
```

### Entity Names

- `ALL_CAPS` with underscores — entity names
- `ENTITY__STATE` — double underscore separates base from state
- `@room` — reference to current room entity
- `*` wildcard — matches all entities in room

### Indentation

2-space increments define hierarchy:

```markdown
TERMINAL                           // Entity declaration (indent 0)
+ LOOK: A dusty CRT.              // Behavior of TERMINAL
+ USE + KEYCARD:                   // Interaction on TERMINAL
  You slide the keycard.           // Narrative (no marker)
  - TERMINAL -> TERMINAL__UNLOCKED // Arrow (state change)
    + LOOK: Scrolling text.        // Behavior of new state
  - KEYCARD -> trash               // Arrow
```

## Room Script Example

```markdown
# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
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

# Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

## PDF Output

Page order:
1. **Title page** — game title, description, how-to-play, start room, verbs
2. **Start room sheet** — marked with ★ START
3. **Inventory & Potentials** — inventory slots (scaled to item count), 3-column potentials list
4. **Other room sheets** — one per room
5. **Story Ledger** — two-column layout, bordered entries, `A-1` format

Entry format: `{prefix}-{number}` (e.g. `A-1`, `A-29`). Prefix from `entry_prefix` metadata.

Narratives and descriptions support Typst markup via `eval(text, mode: "markup")`.

## Multi-Chapter Stories (Future)

Not yet implemented. Design:

### Structure
- `chapters:` frontmatter key defines order explicitly
- Root-level files = Chapter A
- Each subdirectory = subsequent chapter (B, C, ...)
- Each chapter has its own `index.md` for new verbs/items, inherits from prior chapters
- `adv build` defaults to Chapter A; `adv build --chapter B` or `adv build --all` for more

### Validation (must implement)
- Verify every directory listed in `chapters:` exists and contains an `index.md`
- Warn if subdirectories with an `index.md` exist but are not listed in `chapters:`
- Error if `chapters:` references a non-existent directory

## Model

`GameData` dataclass fields:
- `metadata: dict[str, str]` — frontmatter + description
- `verbs`, `nouns`, `items`, `rooms` — entity registries
- `interactions` → `resolved` — compiled interactions with sum IDs
- `cues` — cross-room cue checks

## Compiler Pipeline

1. `parse_global` — frontmatter, description, verbs, items
2. `parse_room_file` — rooms, nouns, interactions
3. `_try_allocate` — random ID assignment (verbs 11–99, entities 100–999, no multiples of 5/10)
4. `register_verb_states` — temporary verb states (e.g. `USE__RESTRAINED`)
5. `apply_inheritance` — auto-generate child interactions for entity states
6. `resolve_interactions` — expand verb+entity combos into sums
7. `resolve_cues` — cross-room cue interactions
8. Validate — collision detection (up to 200 retries on ID allocation)

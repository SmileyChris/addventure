# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Addventure is a compiler and writer for paper-based text adventures where "addition IS the parser." Players solve games by adding numbers: Verb ID + Entity ID = Sum ID → Ledger Entry. Python 3.10+ required, zero external dependencies.

## Running

```bash
uv run adv                       # Show help
uv run adv build                 # Build game in cwd (or example if not in a game dir)
uv run adv build games/example   # Explicit game directory
uv run adv build --text          # Plain text output instead of PDF
uv run adv new                   # Scaffold a new game (interactive)
uv run adv new "My Game"         # Scaffold with defaults (oneshot)
```

Games are directories of `.md` files. Each game directory needs an `index.md` (metadata + verbs + items); all other `.md` files are room scripts loaded alphabetically.

## Project Structure

```
pyproject.toml             # Package config — `uv run adv` entry point
addventure.py              # Legacy entry point (delegates to cli.py)
src/addventure/
  __init__.py              # Re-exports: compile_game, GameWriter, print_full_report
  cli.py                   # CLI: `adv run`, `adv new` subcommands
  models.py                # All dataclasses (Verb, Noun, Item, Room, Arrow, Interaction, etc.)
  parser.py                # .md script parsing (markdown-based, indentation-sensitive)
  compiler.py              # ID allocation, inheritance, resolver, collision detection
  writer.py                # GameWriter — generates printable player-facing components
docs/
  grammar.ebnf             # Formal EBNF grammar for .md script syntax
games/
  example/                 # Example game (.md files)
```

## Architecture

Two-stage pipeline: **Compiler** → **Writer**

Dependency flow: `models` ← `parser` ← `compiler` ← `writer`

### Compiler (`parser.py` + `compiler.py`)

Transforms `.md` script sources into a validated `GameData` model. Pipeline:

1. `parse_global` — extract metadata (frontmatter), verbs and items
2. `parse_room_file` — extract rooms, nouns, interactions (indentation-sensitive)
3. `_try_allocate` — randomly assign IDs (verbs: 11–99, entities: 100–999, excluding multiples of 5/10)
4. `register_verb_states` — create temporary verb states (e.g., `USE__RESTRAINED`)
5. `apply_inheritance` — auto-generate child interactions for entity states
6. `resolve_interactions` — expand verb+entity combinations into sums (Cartesian product for multi-target)
7. `resolve_cues` — resolve cross-room cue interactions
8. Validate — check for authored and potential ID collisions

`compile_game()` orchestrates this with up to 200 retries if ID collisions occur.

### Writer (`writer.py`)

`GameWriter` transforms `GameData` into four printable components:
- **Verb Sheet** — verb reference with IDs
- **Room Sheets** — per-location state and discovery slots
- **Inventory Sheet** — item tracking + Cue Checks (cross-room triggers) + Master Potentials List (sum lookups)
- **Story Ledger** — narratives + human-readable instructions from arrows

### Script Syntax (`.md` files)

Game scripts use markdown-based syntax:

- `# Section` — headers for sections (`# Verbs`, `# Items`, `# Interactions`) and room names (`# Control Room`)
- `---` fences — YAML frontmatter for metadata (title, author, etc.) at top of `index.md`
- `+ line` — additions: interactions and behaviors on an entity
- `- line` — state changes: arrows (movement, destruction, transformation)
- Unquoted text — narrative text, no markers needed (just indented under an interaction)
- `//` — comments
- `ENTITY__STATE` — double-underscore separates base name from state
- `VERB + TARGET:` — multi-entity interactions
- Arrow destinations: `player`, `trash`, `"RoomName"`, `room` (current room), `ENTITY__STATE`
- `? -> "RoomName"` — cue (deferred cross-room effect, resolved when player enters target room)
- `@room` — reference to current room entity
- `*` wildcard — matches all entities in room
- Indentation (2-space) defines hierarchy within `+`/`-` blocks

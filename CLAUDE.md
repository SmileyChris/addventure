# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Addventure is a compiler and writer for paper-based text adventures where "addition IS the parser." Players solve games by adding numbers: Verb ID + Entity ID = Sum ID → Ledger Entry. Python 3.10+ required, zero external dependencies.

## Running

```bash
uv run python addventure.py                # Runs example game, prints full report
uv run python addventure.py games/example   # Explicit game directory
```

Games are directories of `.adv` files. Each game directory needs a `global.adv` (verbs + items); all other `.adv` files are room scripts loaded alphabetically.

## Project Structure

```
addventure.py              # Thin CLI entry point — loads .adv files, runs pipeline
src/addventure/
  __init__.py              # Re-exports: compile_game, GameWriter, print_full_report
  models.py                # All dataclasses (Verb, Noun, Item, Room, Arrow, Interaction, etc.)
  parser.py                # .adv script parsing (indentation-sensitive)
  compiler.py              # ID allocation, inheritance, resolver, collision detection
  writer.py                # GameWriter — generates printable player-facing components
games/
  example/                 # Example game (.adv files)
```

## Architecture

Two-stage pipeline: **Compiler** → **Writer**

Dependency flow: `models` ← `parser` ← `compiler` ← `writer`

### Compiler (`parser.py` + `compiler.py`)

Transforms `.adv` script sources into a validated `GameData` model. Pipeline:

1. `parse_global` — extract verbs and items
2. `parse_room_file` — extract rooms, nouns, interactions (indentation-sensitive)
3. `_try_allocate` — randomly assign IDs (verbs: 11–99, entities: 100–999, excluding multiples of 5/10)
4. `register_verb_states` — create temporary verb states (e.g., `USE__RESTRAINED`)
5. `apply_inheritance` — auto-generate child interactions for entity states
6. `resolve_interactions` — expand verb+entity combinations into sums (Cartesian product for multi-target)
7. `generate_room_alerts` — create cross-room alerts
8. Validate — check for authored and potential ID collisions

`compile_game()` orchestrates this with up to 200 retries if ID collisions occur.

### Writer (`writer.py`)

`GameWriter` transforms `GameData` into four printable components:
- **Verb Sheet** — verb reference with IDs
- **Room Sheets** — per-location state and discovery slots
- **Inventory Sheet** — item tracking + Master Potentials List (sum lookups)
- **Story Ledger** — narratives + human-readable instructions from arrows

### Script Syntax (`.adv` files)

- `ENTITY__STATE` — double-underscore separates base name from state
- `VERB + TARGET:` — multi-entity interactions
- Arrow destinations: `player`, `trash`, `"RoomName"`, `room` (current room), `ENTITY__STATE`
- `@room` — reference to current room entity
- `*` wildcard — matches all entities in room
- Indentation defines arrow hierarchies and state-conditional blocks

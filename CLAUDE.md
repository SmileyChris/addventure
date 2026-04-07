# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Addventure is a compiler and writer for paper-based text adventures where "addition IS the parser." Players solve games by adding numbers: Verb ID + Entity ID = Sum ID → Ledger Entry. Python 3.10+ required. pypdf for fillable PDF fields, Typst for PDF generation.

## Running

```bash
uv run addventure                       # Show help
uv run addventure build                 # Build game in cwd (or example if not in a game dir)
uv run addventure build games/example   # Explicit game directory
uv run addventure build --md             # Markdown output instead of PDF
uv run addventure new                   # Scaffold a new game (interactive)
uv run addventure new "My Game"         # Scaffold with defaults (oneshot)
uv run addventure build --all           # Build parent + all chapter subdirs into one PDF
```

Games are directories of `.md` files. Each game directory needs an `index.md` (metadata + verbs + inventory objects); all other `.md` files are room scripts loaded alphabetically. Subdirectories with their own `index.md` are chapters — each gets an auto-assigned `entry_prefix` (B, C, D...) so ledger entries don't collide.

## Project Structure

```
pyproject.toml             # Package config — `uv run addventure` entry point
src/addventure/
  __init__.py              # Re-exports: compile_game, GameWriter, print_build_summary
  cli.py                   # CLI: `addventure build`, `addventure new` subcommands
  models.py                # All dataclasses (Verb, RoomObject, InventoryObject, Room, Arrow, Interaction, etc.)
  parser.py                # .md script parsing (markdown-based, indentation-sensitive)
  compiler.py              # ID allocation, inheritance, resolver, collision detection
  writer.py                # GameWriter — shared presentation logic + build summary
  md_writer.py             # Markdown output (--md flag)
  pdf_writer.py            # PDF output via Typst (default)
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

1. `parse_global` — extract metadata (frontmatter), verbs and inventory objects
2. `parse_room_file` — extract rooms, room objects, interactions (indentation-sensitive)
3. `auto_register_items` — auto-create inventory objects from `-> player` arrows (ID = TAKE + room object ID)
4. `_try_allocate` — randomly assign IDs (verbs: 11–99, entities: 100–999, excluding multiples of 5/10)
5. `register_verb_states` — create temporary verb states (e.g., `USE__RESTRAINED`)
6. `apply_inheritance` — auto-generate child interactions for entity states
7. `resolve_interactions` — expand verb+entity combinations into sums (Cartesian product for multi-target)
8. `duplicate_item_interactions` — create parallel sums for inventory object IDs
9. `resolve_cues` — resolve cross-room cue interactions
10. Validate — check for authored and potential ID collisions

`compile_game()` orchestrates this with up to 200 retries if ID collisions occur.

### Writer (`writer.py`)

`GameWriter` transforms `GameData` into four printable components:
- **Verb Sheet** — verb reference with IDs
- **Room Sheets** — per-location state and discovery slots
- **Inventory Sheet** — inventory object tracking + Cue Checks (cross-room triggers) + Master Potentials List (sum lookups)
- **Story Ledger** — narratives + human-readable instructions from arrows

### Script Syntax (`.md` files)

Game scripts use markdown-based syntax:

- `# Section` — headers for sections (`# Verbs`, `# Inventory`, `## Interactions`) and room names (`# Control Room`)
- `---` fences — YAML frontmatter for metadata (title, author, etc.) at top of `index.md`
- `+ line` — additions: interactions and behaviors on an entity
- `- line` — state changes: arrows (movement, destruction, transformation)
- `> line` — actions: direct ledger lookups (no addition), e.g. `> GO_NORTH`
- Unquoted text — narrative text, no markers needed (just indented under an interaction)
- `//` — comments
- `ENTITY__STATE` — double-underscore separates base name from state
- `VERB + TARGET:` — multi-entity interactions
- Arrow destinations: `player`, `trash`, `"RoomName"`, `room` (current room), `ENTITY__STATE`, `room__STATE`
- `? -> "RoomName"` — cue (deferred cross-room effect, resolved when player enters target room)
- `*` wildcard — matches all entities in room
- Indentation (2-space) defines hierarchy within `+`/`-` blocks

## Language Changes

Any change to the script language must update all of:

- `src/addventure/parser.py` — parser behavior
- `docs/grammar.ebnf` — formal syntax spec
- User-facing docs (`docs/reference.md`, `docs/writing-rooms.md`) if applicable
- `games/example/` if applicable
- Tests

The parser is strict: every block type rejects unexpected lines. Do not add silent skips (`i += 1` on unrecognized input). Unknown frontmatter keys are valid but produce build warnings.

## Releasing

To create a new release:

1. Bump `version` in `pyproject.toml`
2. `uv lock` to update the lockfile
3. Commit: `bump version to X.Y.Z`
4. Push to main
5. Create a GitHub release with `gh release create vX.Y.Z --generate-notes` — add a human-written summary of changes above the auto-generated notes
6. The PyPI publish workflow triggers automatically on GitHub release

# Typst PDF Output Design

## Overview

Add PDF output to Addventure using Typst as the typesetting engine. The compiler pipeline gains a new stage: `GameData` → JSON → Typst → PDF. This replaces text output as the default, with text available via `--text` flag or as automatic fallback when Typst isn't installed.

## CLI Changes

**`addventure.py`:**
- Default: generate PDF → `<game_dir_name>.pdf` in the current working directory (e.g., `games/example` → `example.pdf`)
- `--text` flag: plain text output to stdout (current behavior)
- `--output <path>`: override PDF output path
- `--theme <name>`: select template theme (default: `default`)
- If `typst` binary not found on `PATH`: fall back to text output with a warning to stderr

## Architecture

### Data Flow

```
GameData → serialize_game_data() → JSON dict → temp file
  → typst compile <theme>/main.typ output.pdf --input data=<json_path>
  → cleanup temp file
```

### JSON Data Bridge

A `serialize_game_data(game, writer)` function produces a JSON structure organized by what the Typst templates consume. It reuses `GameWriter` for generating human-readable instruction strings rather than duplicating that logic.

```json
{
  "verbs": [{"name": "USE", "id": 32}],
  "rooms": [
    {
      "name": "Control Room",
      "id": 144,
      "objects": [{"name": "TERMINAL", "id": 951}],
      "discovery_slots": 1
    }
  ],
  "inventory_slots": 12,
  "potentials": [{"sum": 1002, "entry": 5}],
  "ledger": [
    {"entry": 1, "narrative": "A dusty CRT.", "instructions": ["Cross out TERMINAL (951) on your room sheet."]}
  ]
}
```

### New Module: `src/addventure/pdf_writer.py`

Responsibilities:
- `serialize_game_data(game, writer)` — build the JSON dict using `GameWriter` for instruction text
- `generate_pdf(game, output_path, theme="default")` — orchestrate the pipeline: serialize → write temp JSON → locate templates → shell out to `typst compile` → cleanup
- `find_typst()` — check if `typst` is on `PATH`, return path or `None`

### Typst Templates

Templates organized by theme for future extensibility:

```
src/addventure/templates/
  default/
    main.typ          # Entry point — reads JSON, imports partials, assembles pages
    style.typ         # Shared page setup, fonts, spacing, decorative elements
    verb-sheet.typ    # Verb reference page
    room-sheet.typ    # Room page (called once per room)
    inventory.typ     # Inventory + Master Potentials List
    ledger.typ        # Story Ledger entries
```

`main.typ` receives the JSON file path via Typst input variable: `typst compile main.typ output.pdf --input data=game.json`

Each partial is a function that takes the relevant slice of parsed JSON and returns content. `style.typ` defines the shared look — page size (US Letter), margins, fonts, table styling, write-in slot boxes, horizontal rules.

### Page Structure

Each section starts on its own page:
1. Verb Sheet — one page
2. Room Sheets — one page per room
3. Inventory & Potentials — starts on new page (may span multiple)
4. Story Ledger — starts on new page (may span multiple)

### Integration with Existing Code

- `addventure.py` (CLI) handles output mode decision: parse `--text`/`--output`/`--theme` flags, check for Typst, choose PDF or text path
- `__init__.py` re-exports `generate_pdf` alongside existing `compile_game`, `GameWriter`, `print_full_report`
- Existing `GameWriter` and `print_full_report` unchanged — `pdf_writer.py` imports and uses `GameWriter` internally

## Dependencies

- **Runtime:** `typst` binary on `PATH` (not a Python dependency — system install)
- **Python:** No new dependencies. Uses `subprocess`, `tempfile`, `shutil.which`, `json` from stdlib.

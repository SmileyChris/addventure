# Typst PDF Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate pretty PDF game sheets via Typst, replacing text output as the default.

**Architecture:** Python serializes `GameData` into JSON. Typst templates read the JSON and render verb sheets, room sheets, inventory/potentials, and story ledger as a multi-page PDF. The CLI shells out to `typst compile`. Falls back to text if Typst isn't installed.

**Tech Stack:** Python 3.10+ stdlib (`json`, `subprocess`, `shutil`, `tempfile`, `argparse`), Typst 0.14+

---

## File Structure

**New files:**
- `src/addventure/pdf_writer.py` — JSON serialization + Typst compilation orchestration
- `src/addventure/templates/default/main.typ` — entry point, reads JSON, imports partials
- `src/addventure/templates/default/style.typ` — shared page setup, fonts, decorative elements
- `src/addventure/templates/default/verb-sheet.typ` — verb reference page
- `src/addventure/templates/default/room-sheet.typ` — per-room page
- `src/addventure/templates/default/inventory.typ` — inventory + potentials list
- `src/addventure/templates/default/ledger.typ` — story ledger entries
- `tests/test_pdf_writer.py` — tests for JSON serialization and PDF generation

**Modified files:**
- `addventure.py` — add `--text`/`--output`/`--theme` flags, default to PDF
- `src/addventure/__init__.py` — re-export `generate_pdf`

---

### Task 1: JSON Serialization

**Files:**
- Create: `src/addventure/pdf_writer.py`
- Create: `tests/test_pdf_writer.py`

- [ ] **Step 1: Write failing test for `serialize_game_data`**

Create `tests/test_pdf_writer.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data


def _make_game():
    global_src = "--- verbs ---\nUSE\nLOOK\n\n--- items ---\nKEY\n"
    room_src = '--- "Room" ---\nLOOK: "A room."\n\nBOX\n  LOOK: "A box."\n  USE + KEY:\n    "You open it."\n    BOX -> BOX__OPEN\n      LOOK: "An open box."\n    KEY -> trash\n'
    return compile_game(global_src, [room_src])


def test_serialize_top_level_keys():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert set(data.keys()) == {"verbs", "rooms", "inventory_slots", "potentials", "ledger"}


def test_serialize_verbs():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    base_verbs = [v for v in data["verbs"] if "__" not in v["name"]]
    assert len(base_verbs) == 2
    assert all("name" in v and "id" in v for v in data["verbs"])


def test_serialize_rooms():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    base_rooms = [r for r in data["rooms"] if r.get("state") is None]
    assert len(base_rooms) == 1
    room = base_rooms[0]
    assert room["name"] == "Room"
    assert isinstance(room["id"], int)
    assert isinstance(room["objects"], list)
    assert isinstance(room["discovery_slots"], int)


def test_serialize_potentials():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert len(data["potentials"]) == len(game.resolved)
    assert all("sum" in p and "entry" in p for p in data["potentials"])
    sums = [p["sum"] for p in data["potentials"]]
    assert sums == sorted(sums), "Potentials should be sorted by sum"


def test_serialize_ledger():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert len(data["ledger"]) == len(game.resolved)
    for entry in data["ledger"]:
        assert "entry" in entry
        assert "narrative" in entry
        assert "instructions" in entry
        assert isinstance(entry["instructions"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_pdf_writer.py -v`
Expected: ImportError — `pdf_writer` doesn't exist yet.

- [ ] **Step 3: Implement `serialize_game_data`**

Create `src/addventure/pdf_writer.py`:

```python
import json
import subprocess
import tempfile
from pathlib import Path
from shutil import which

from .models import GameData
from .writer import GameWriter
from .compiler import get_entity_id, check_authored_collisions, check_potential_collisions


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def serialize_game_data(game: GameData, writer: GameWriter) -> dict:
    """Transform GameData into a JSON-serializable dict for Typst templates."""
    verbs = [
        {"name": v.name, "id": v.id}
        for v in game.verbs.values()
        if "__" not in v.name
    ]

    rooms = []
    for room_name, rm in game.rooms.items():
        if rm.state is not None:
            continue

        # Initial visible objects (not discovered via arrows)
        discovered_names = set()
        for ix in game.interactions:
            for a in ix.arrows:
                if a.destination == "room" and ix.room == room_name:
                    discovered_names.add(a.subject)

        objects = [
            {"name": n.name, "id": n.id}
            for n in game.nouns.values()
            if n.room == room_name and n.state is None and n.name not in discovered_names
        ]

        disc_count = sum(
            1 for ix in game.interactions if ix.room == room_name
            for a in ix.arrows if a.destination == "room"
        )

        rooms.append({
            "name": room_name,
            "id": rm.id,
            "objects": objects,
            "discovery_slots": disc_count,
        })

    potentials = sorted(
        [{"sum": ri.sum_id, "entry": ri.entry_number} for ri in game.resolved],
        key=lambda p: p["sum"],
    )

    ledger = []
    for ri in game.resolved:
        instructions = writer._generate_instructions(ri)
        ledger.append({
            "entry": ri.entry_number,
            "narrative": ri.narrative,
            "instructions": instructions,
        })

    return {
        "verbs": verbs,
        "rooms": rooms,
        "inventory_slots": 12,
        "potentials": potentials,
        "ledger": ledger,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_pdf_writer.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/pdf_writer.py tests/test_pdf_writer.py
git commit -m "Add serialize_game_data for Typst JSON bridge"
```

---

### Task 2: Typst Style and Verb Sheet Templates

**Files:**
- Create: `src/addventure/templates/default/style.typ`
- Create: `src/addventure/templates/default/verb-sheet.typ`
- Create: `src/addventure/templates/default/main.typ`

- [ ] **Step 1: Create `style.typ`**

```typst
// Shared page setup and styling for Addventure sheets

#let page-setup = (
  paper: "us-letter",
  margin: (top: 0.75in, bottom: 0.75in, left: 0.75in, right: 0.75in),
)

#let title-font = "serif"
#let body-font = "sans-serif"

#let sheet-title(text) = {
  align(center)[
    #set text(size: 18pt, weight: "bold", font: title-font)
    #text
  ]
  v(4pt)
  line(length: 100%, stroke: 1.5pt)
  v(12pt)
}

#let section-title(text) = {
  v(8pt)
  set text(size: 14pt, weight: "bold")
  text
  v(2pt)
  line(length: 100%, stroke: 0.5pt)
  v(6pt)
}

#let write-slot(width: 2in) = {
  box(
    width: width,
    stroke: (bottom: 0.5pt + gray),
    inset: (bottom: 2pt),
    []
  )
}

#let id-box(content) = {
  box(
    stroke: 0.5pt,
    inset: (x: 6pt, y: 3pt),
    radius: 2pt,
    content
  )
}

#let separator() = {
  v(8pt)
  line(length: 60%, stroke: 0.5pt + gray)
  v(8pt)
}
```

- [ ] **Step 2: Create `verb-sheet.typ`**

```typst
#import "style.typ": *

#let verb-sheet(data) = {
  sheet-title("ADDVENTURE — VERB SHEET")

  [Your available actions. Each has an ID number. \
  When the game changes a verb, cross out the old ID and write the new one.]

  v(12pt)

  for verb in data.verbs {
    grid(
      columns: (1fr, auto),
      align: (left, right),
      text(size: 12pt, weight: "bold", verb.name),
      id-box(text(size: 12pt, str(verb.id))),
    )
    v(6pt)
  }

  v(16pt)
  text(size: 10pt, fill: gray)[(Blank slots for verb changes:)]
  v(6pt)

  for _ in range(3) {
    grid(
      columns: (1fr, auto),
      align: (left, right),
      write-slot(width: 2in),
      id-box(write-slot(width: 0.5in)),
    )
    v(6pt)
  }
}
```

- [ ] **Step 3: Create initial `main.typ`**

```typst
#import "style.typ": *
#import "verb-sheet.typ": verb-sheet

#set page(..page-setup)
#set text(font: body-font, size: 11pt)

#let data = json(sys.inputs.at("data"))

#verb-sheet(data)
```

- [ ] **Step 4: Test manually with example game JSON**

Run:
```bash
uv run python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, 'src')
from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data

gd = Path('games/example')
gs = (gd / 'global.adv').read_text()
rs = [f.read_text() for f in sorted(gd.glob('*.adv')) if f.name != 'global.adv']
game = compile_game(gs, rs)
w = GameWriter(game)
data = serialize_game_data(game, w)
Path('/tmp/addventure-test.json').write_text(json.dumps(data, indent=2))
print('JSON written')
"
typst compile src/addventure/templates/default/main.typ /tmp/addventure-verb-test.pdf --root / --input data=/tmp/addventure-test.json
echo "PDF generated at /tmp/addventure-verb-test.pdf"
```

Expected: PDF file with verb sheet renders without errors.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/templates/default/style.typ src/addventure/templates/default/verb-sheet.typ src/addventure/templates/default/main.typ
git commit -m "Add Typst style and verb sheet templates"
```

---

### Task 3: Room Sheet Template

**Files:**
- Create: `src/addventure/templates/default/room-sheet.typ`
- Modify: `src/addventure/templates/default/main.typ`

- [ ] **Step 1: Create `room-sheet.typ`**

```typst
#import "style.typ": *

#let room-sheet(room) = {
  sheet-title("ROOM: " + room.name)

  grid(
    columns: (auto, auto),
    column-gutter: 8pt,
    text(weight: "bold", "Room ID:"),
    id-box(text(str(room.id))),
  )

  v(12pt)
  section-title("Objects in this room")

  for obj in room.objects {
    grid(
      columns: (1fr, auto),
      align: (left, right),
      text(obj.name),
      id-box(text(str(obj.id))),
    )
    v(4pt)
  }

  if room.discovery_slots > 0 {
    v(12pt)
    text(size: 10pt, fill: gray)[(Discoverable — #str(room.discovery_slots) slots:)]
    v(6pt)
    for _ in range(room.discovery_slots) {
      grid(
        columns: (1fr, auto),
        align: (left, right),
        write-slot(width: 2in),
        id-box(write-slot(width: 0.5in)),
      )
      v(4pt)
    }
  }

  v(16pt)
  section-title("Room Alerts")
  [If you have alert numbers for this room, add the alert number + #str(room.id) *(Room ID)* and check the Potentials List.]
}
```

- [ ] **Step 2: Update `main.typ` to include room sheets**

```typst
#import "style.typ": *
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet

#set page(..page-setup)
#set text(font: body-font, size: 11pt)

#let data = json(sys.inputs.at("data"))

#verb-sheet(data)

#for room in data.rooms {
  pagebreak()
  room-sheet(room)
}
```

- [ ] **Step 3: Test manually**

Run:
```bash
uv run python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, 'src')
from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data
gd = Path('games/example')
gs = (gd / 'global.adv').read_text()
rs = [f.read_text() for f in sorted(gd.glob('*.adv')) if f.name != 'global.adv']
game = compile_game(gs, rs)
data = serialize_game_data(game, GameWriter(game))
Path('/tmp/addventure-test.json').write_text(json.dumps(data, indent=2))
"
typst compile src/addventure/templates/default/main.typ /tmp/addventure-rooms-test.pdf --root / --input data=/tmp/addventure-test.json
echo "PDF at /tmp/addventure-rooms-test.pdf"
```

Expected: PDF with verb sheet on page 1, then one page per room.

- [ ] **Step 4: Commit**

```bash
git add src/addventure/templates/default/room-sheet.typ src/addventure/templates/default/main.typ
git commit -m "Add Typst room sheet template"
```

---

### Task 4: Inventory and Potentials Template

**Files:**
- Create: `src/addventure/templates/default/inventory.typ`
- Modify: `src/addventure/templates/default/main.typ`

- [ ] **Step 1: Create `inventory.typ`**

```typst
#import "style.typ": *

#let inventory-sheet(data) = {
  sheet-title("ADDVENTURE — INVENTORY & POTENTIALS")

  section-title("Inventory")
  [Items you're carrying. Cross out when used.]
  v(8pt)

  for _ in range(data.inventory_slots) {
    grid(
      columns: (1fr, auto),
      align: (left, right),
      write-slot(width: 2in),
      id-box(write-slot(width: 0.5in)),
    )
    v(4pt)
  }

  v(16pt)
  section-title("Master Potentials List")
  [Look up your calculated sum here.]
  v(8pt)

  table(
    columns: (auto, auto),
    align: (right, left),
    stroke: 0.5pt + gray,
    inset: 6pt,
    table.header(
      text(weight: "bold", "Sum"),
      text(weight: "bold", "Ledger Entry"),
    ),
    ..data.potentials.map(p => (
      str(p.sum),
      [Ledger \##str(p.entry)],
    )).flatten()
  )
}
```

- [ ] **Step 2: Update `main.typ`**

```typst
#import "style.typ": *
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet

#set page(..page-setup)
#set text(font: body-font, size: 11pt)

#let data = json(sys.inputs.at("data"))

#verb-sheet(data)

#for room in data.rooms {
  pagebreak()
  room-sheet(room)
}

#pagebreak()
#inventory-sheet(data)
```

- [ ] **Step 3: Test manually**

Run:
```bash
uv run python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, 'src')
from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data
gd = Path('games/example')
gs = (gd / 'global.adv').read_text()
rs = [f.read_text() for f in sorted(gd.glob('*.adv')) if f.name != 'global.adv']
game = compile_game(gs, rs)
data = serialize_game_data(game, GameWriter(game))
Path('/tmp/addventure-test.json').write_text(json.dumps(data, indent=2))
"
typst compile src/addventure/templates/default/main.typ /tmp/addventure-inv-test.pdf --root / --input data=/tmp/addventure-test.json
echo "PDF at /tmp/addventure-inv-test.pdf"
```

Expected: PDF with verb, rooms, then inventory + potentials table.

- [ ] **Step 4: Commit**

```bash
git add src/addventure/templates/default/inventory.typ src/addventure/templates/default/main.typ
git commit -m "Add Typst inventory and potentials template"
```

---

### Task 5: Story Ledger Template

**Files:**
- Create: `src/addventure/templates/default/ledger.typ`
- Modify: `src/addventure/templates/default/main.typ`

- [ ] **Step 1: Create `ledger.typ`**

```typst
#import "style.typ": *

#let story-ledger(data) = {
  sheet-title("ADDVENTURE — STORY LEDGER")

  [Only read an entry when directed to by the Potentials List.]
  v(12pt)

  for entry in data.ledger {
    text(weight: "bold", size: 11pt)[Entry \##str(entry.entry)]
    v(4pt)
    emph["#entry.narrative"]
    v(4pt)

    if entry.instructions.len() > 0 {
      for inst in entry.instructions {
        block(
          inset: (left: 12pt),
          text(size: 10pt)[→ #inst]
        )
      }
    }

    separator()
  }
}
```

- [ ] **Step 2: Update `main.typ` to final form**

```typst
#import "style.typ": *
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet
#import "ledger.typ": story-ledger

#set page(..page-setup)
#set text(font: body-font, size: 11pt)

#let data = json(sys.inputs.at("data"))

#verb-sheet(data)

#for room in data.rooms {
  pagebreak()
  room-sheet(room)
}

#pagebreak()
#inventory-sheet(data)

#pagebreak()
#story-ledger(data)
```

- [ ] **Step 3: Test manually — full PDF**

Run:
```bash
uv run python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, 'src')
from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data
gd = Path('games/example')
gs = (gd / 'global.adv').read_text()
rs = [f.read_text() for f in sorted(gd.glob('*.adv')) if f.name != 'global.adv']
game = compile_game(gs, rs)
data = serialize_game_data(game, GameWriter(game))
Path('/tmp/addventure-test.json').write_text(json.dumps(data, indent=2))
"
typst compile src/addventure/templates/default/main.typ /tmp/addventure-full-test.pdf --root / --input data=/tmp/addventure-test.json
echo "PDF at /tmp/addventure-full-test.pdf"
```

Expected: Complete PDF with all four sections, each on its own page.

- [ ] **Step 4: Commit**

```bash
git add src/addventure/templates/default/ledger.typ src/addventure/templates/default/main.typ
git commit -m "Add Typst story ledger template, complete all templates"
```

---

### Task 6: PDF Generation Pipeline (`generate_pdf` and `find_typst`)

**Files:**
- Modify: `src/addventure/pdf_writer.py`
- Modify: `tests/test_pdf_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_pdf_writer.py`:

```python
from addventure.pdf_writer import find_typst, generate_pdf


def test_find_typst():
    result = find_typst()
    # On a system with typst installed, should return a path
    # On CI without typst, should return None
    assert result is None or Path(result).name.startswith("typst")


def test_generate_pdf(tmp_path):
    game = _make_game()
    output = tmp_path / "test-output.pdf"
    result = generate_pdf(game, output)
    if find_typst() is None:
        assert result is False
    else:
        assert result is True
        assert output.exists()
        assert output.stat().st_size > 0


def test_generate_pdf_custom_theme_missing(tmp_path):
    game = _make_game()
    output = tmp_path / "test-output.pdf"
    try:
        generate_pdf(game, output, theme="nonexistent")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `uv run python -m pytest tests/test_pdf_writer.py -v`
Expected: ImportError for `find_typst` and `generate_pdf`.

- [ ] **Step 3: Implement `find_typst` and `generate_pdf`**

Add to `src/addventure/pdf_writer.py`:

```python
def find_typst() -> str | None:
    """Return path to typst binary, or None if not found."""
    return which("typst")


def generate_pdf(game: GameData, output_path: Path, theme: str = "default") -> bool:
    """Generate a PDF from GameData. Returns True on success, False if typst not found."""
    typst_bin = find_typst()
    if typst_bin is None:
        return False

    theme_dir = TEMPLATES_DIR / theme
    if not theme_dir.exists():
        raise FileNotFoundError(f"Theme not found: {theme} (looked in {theme_dir})")

    writer = GameWriter(game)
    data = serialize_game_data(game, writer)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        json_path = f.name

    try:
        main_typ = theme_dir / "main.typ"
        output_path = Path(output_path)
        subprocess.run(
            [
                typst_bin, "compile",
                str(main_typ),
                str(output_path),
                "--root", "/",
                "--input", f"data={json_path}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Typst error:\n{e.stderr}", file=__import__('sys').stderr)
        raise
    finally:
        Path(json_path).unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_pdf_writer.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/pdf_writer.py tests/test_pdf_writer.py
git commit -m "Add generate_pdf pipeline with Typst compilation"
```

---

### Task 7: CLI Integration

**Files:**
- Modify: `addventure.py`
- Modify: `src/addventure/__init__.py`

- [ ] **Step 1: Update `__init__.py` to re-export `generate_pdf`**

Replace contents of `src/addventure/__init__.py` with:

```python
from .compiler import compile_game
from .writer import GameWriter, print_full_report
from .pdf_writer import generate_pdf, find_typst
```

- [ ] **Step 2: Update `addventure.py` with argument parsing and PDF default**

Replace contents of `addventure.py` with:

```python
"""
Addventure CLI — load .adv files and run the compiler + writer pipeline.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from addventure import compile_game, print_full_report, generate_pdf, find_typst


def load_game(game_dir: Path) -> tuple[str, list[str]]:
    """Load global.adv and all room .adv files from a game directory."""
    global_file = game_dir / "global.adv"
    if not global_file.exists():
        print(f"ERROR: No global.adv found in {game_dir}", file=sys.stderr)
        sys.exit(1)

    global_source = global_file.read_text()
    room_sources = [
        f.read_text()
        for f in sorted(game_dir.glob("*.adv"))
        if f.name != "global.adv"
    ]
    return global_source, room_sources


def main():
    parser = argparse.ArgumentParser(description="Addventure — compile paper text adventures")
    parser.add_argument("game_dir", nargs="?", default="games/example",
                        help="Path to game directory (default: games/example)")
    parser.add_argument("--text", action="store_true",
                        help="Output plain text instead of PDF")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PDF path (default: <game_name>.pdf)")
    parser.add_argument("--theme", type=str, default="default",
                        help="Typst template theme (default: default)")
    args = parser.parse_args()

    game_dir = Path(args.game_dir)
    global_source, room_sources = load_game(game_dir)
    game = compile_game(global_source, room_sources)

    if args.text:
        print_full_report(game)
        return

    if find_typst() is None:
        print("WARNING: typst not found on PATH, falling back to text output",
              file=sys.stderr)
        print_full_report(game)
        return

    output_path = Path(args.output) if args.output else Path(f"{game_dir.name}.pdf")
    if generate_pdf(game, output_path, theme=args.theme):
        print(f"PDF written to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Test CLI — PDF output**

Run: `uv run python addventure.py`
Expected: Prints "PDF written to example.pdf" and the file exists.

- [ ] **Step 4: Test CLI — text fallback**

Run: `uv run python addventure.py --text`
Expected: Plain text output to stdout (same as before).

- [ ] **Step 5: Test CLI — custom output path**

Run: `uv run python addventure.py -o /tmp/my-game.pdf`
Expected: PDF written to `/tmp/my-game.pdf`.

- [ ] **Step 6: Commit**

```bash
git add addventure.py src/addventure/__init__.py
git commit -m "Wire up CLI with PDF default, --text fallback, --output and --theme flags"
```

---

### Task 8: End-to-End Test

**Files:**
- Modify: `tests/test_pdf_writer.py`

- [ ] **Step 1: Add end-to-end test using example game**

Append to `tests/test_pdf_writer.py`:

```python
def test_end_to_end_example_game(tmp_path):
    """Compile the example game and generate a PDF."""
    if find_typst() is None:
        return  # skip if typst not installed

    gd = Path(__file__).resolve().parent.parent / "games" / "example"
    gs = (gd / "global.adv").read_text()
    rs = [f.read_text() for f in sorted(gd.glob("*.adv")) if f.name != "global.adv"]
    game = compile_game(gs, rs)

    output = tmp_path / "example.pdf"
    assert generate_pdf(game, output) is True
    assert output.exists()
    # PDF should have reasonable size (at least a few KB for multiple pages)
    assert output.stat().st_size > 1000
```

- [ ] **Step 2: Run full test suite**

Run: `uv run python -m pytest tests/test_pdf_writer.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_pdf_writer.py
git commit -m "Add end-to-end PDF generation test"
```

---

### Task 9: Clean Up and Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Test complete CLI workflow**

```bash
rm -f example.pdf
uv run python addventure.py
ls -la example.pdf
uv run python addventure.py --text | head -20
uv run python addventure.py -o /tmp/final-test.pdf
ls -la /tmp/final-test.pdf
```

Expected: PDF generated in both default and custom paths, text output works.

- [ ] **Step 3: Clean up generated test files**

```bash
rm -f example.pdf
echo "example.pdf" >> .gitignore  # if .gitignore exists, otherwise create it
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "Add .gitignore for generated PDF output"
```

# Cue Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken room alerts system with cue checks — portable tokens on the inventory sheet that resolve via addition when entering rooms.

**Architecture:** Cues are parsed from `? -> "RoomName"` arrows, stored as `Cue` objects on `GameData`, allocated IDs from the entity pool, and resolved into `ResolvedInteraction`s. The writer generates "Write N in your Cue Checks" on trigger and "Cross out N" on resolution. Room alert code is removed entirely.

**Tech Stack:** Python 3.10+, Typst templates, pytest

**Test runner:** `uv run --with pytest pytest tests/ -v`

**Note:** Two pre-existing test failures exist (`test_serialize_top_level_keys` and `test_generate_pdf_custom_theme_missing`). These are unrelated to this feature. Don't fix them unless they intersect with cue work.

---

### Task 1: Model — Replace RoomAlert with Cue

**Files:**
- Modify: `src/addventure/models.py`
- Create: `tests/test_cues.py`

- [ ] **Step 1: Write the test for the Cue model**

Create `tests/test_cues.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure.models import Cue, Arrow, GameData


def test_cue_dataclass():
    cue = Cue(
        target_room="Basement",
        narrative="A shaft of light appears.",
        arrows=[Arrow("LIGHT", "room", 5)],
        source_line=10,
        trigger_room="Control Room",
    )
    assert cue.target_room == "Basement"
    assert cue.trigger_room == "Control Room"
    assert cue.id == 0
    assert cue.sum_id == 0
    assert cue.entry_number == 0
    assert len(cue.arrows) == 1


def test_gamedata_has_cues():
    game = GameData()
    assert game.cues == []
    game.cues.append(Cue(
        target_room="X", narrative="n", arrows=[],
        source_line=1, trigger_room="Y",
    ))
    assert len(game.cues) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: FAIL — `Cue` does not exist yet, `GameData` has no `cues` field.

- [ ] **Step 3: Replace RoomAlert with Cue in models.py**

In `src/addventure/models.py`, replace the `RoomAlert` class (lines 65–71) with:

```python
@dataclass
class Cue:
    target_room: str
    narrative: str
    arrows: list[Arrow]
    source_line: int
    trigger_room: str
    id: int = 0
    sum_id: int = 0
    entry_number: int = 0
```

In `GameData`, replace `alerts: list[RoomAlert] = field(default_factory=list)` with:

```python
    cues: list[Cue] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/models.py tests/test_cues.py
git commit -m "Replace RoomAlert with Cue model"
```

---

### Task 2: Parser — Parse ? arrows and create Cue objects

**Files:**
- Modify: `src/addventure/parser.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the test for parsing ? arrows**

Append to `tests/test_cues.py`:

```python
from addventure.compiler import compile_game


def test_parse_cue_arrow():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: Another room.
"""
    game = compile_game(global_src, [room_src])
    assert len(game.cues) == 1
    cue = game.cues[0]
    assert cue.target_room == "Room B"
    assert cue.trigger_room == "Room A"
    assert cue.narrative == "A gate appears."
    assert len(cue.arrows) == 1
    assert cue.arrows[0].subject == "GATE"
    assert cue.arrows[0].destination == "room"


def test_parse_multiple_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room
  - ? -> "Room C"
    A panel slides open.
    - PANEL -> room

# Room B
LOOK: B.

# Room C
LOOK: C.
"""
    game = compile_game(global_src, [room_src])
    assert len(game.cues) == 2
    targets = {c.target_room for c in game.cues}
    assert targets == {"Room B", "Room C"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_cues.py::test_parse_cue_arrow tests/test_cues.py::test_parse_multiple_cues -v`
Expected: FAIL — parser doesn't handle `?` subject yet.

- [ ] **Step 3: Update parser to handle ? arrows**

In `src/addventure/parser.py`:

First, add `Cue` to the import at line 2:

```python
from .models import (
    GameData, Verb, Noun, Item, Room, Arrow, Interaction, Cue,
)
```

In `_parse_arrow_children` (around line 345), the function currently handles various destinations. We need to add handling for `?` subject arrows. Add a new branch at the **top** of the function, before the existing `dest in ("trash", "player")` check:

```python
def _parse_arrow_children(lines, i, game, room_name, arrow, child_indent):
    dest = arrow.destination

    # ? -> "Room" is a cue (cross-room deferred effect)
    if arrow.subject == "?":
        if not (dest.startswith('"') and dest.endswith('"')):
            raise ParseError(arrow.source_line, "Cue arrow (?) must target a quoted room name")
        target_room = dest[1:-1]
        narrative = ""
        cue_arrows = []
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped or _is_comment(stripped):
                i += 1
                continue
            if _indent(line) < child_indent or _is_header(line):
                break
            marker, content = _strip_marker(stripped)
            if marker == "-" and _is_arrow(content):
                a = _parse_arrow(content, i + 1)
                cue_arrows.append(a)
                i += 1
            elif _is_narrative(stripped):
                if narrative:
                    narrative += " " + stripped
                else:
                    narrative = stripped
                i += 1
            else:
                i += 1
        game.cues.append(Cue(
            target_room=target_room,
            narrative=narrative,
            arrows=cue_arrows,
            source_line=arrow.source_line,
            trigger_room=room_name,
        ))
        # Register any nouns that the cue arrows reveal in the target room
        for ca in cue_arrows:
            if ca.destination == "room":
                subj = ca.subject
                base, state = _split_name(subj)
                key = f"{target_room}::{subj}"
                if key not in game.nouns:
                    game.nouns[key] = Noun(subj, base, state, target_room)
        return i

    if dest in ("trash", "player"):
```

Also, in `_parse_inline_interaction` (around line 314), when parsing `- ? -> ...` arrows inside an interaction, the `?` arrow is parsed by `_parse_arrow` which creates `Arrow("?", '"RoomName"', line)`. The arrow is appended to the interaction's `arrows` list (line 318), then `_parse_arrow_children` is called (line 321) which creates the `Cue`. The `?` arrow stays on the parent interaction so the writer can match it. This flow works with the existing code — no changes needed in `_parse_inline_interaction`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/parser.py tests/test_cues.py
git commit -m "Parse ? arrows into Cue objects"
```

---

### Task 3: Compiler — Allocate cue IDs and resolve cue sums

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the test for cue ID allocation and resolution**

Append to `tests/test_cues.py`:

```python
def test_cue_gets_id_and_sum():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    assert cue.id != 0, "Cue should have an allocated ID"
    assert 100 <= cue.id <= 999, "Cue ID should be in entity range"
    room_b = game.rooms["Room B"]
    assert cue.sum_id == cue.id + room_b.id


def test_cue_appears_in_resolved():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    # Find the resolved interaction for this cue
    cue_ri = [ri for ri in game.resolved if ri.sum_id == cue.sum_id]
    assert len(cue_ri) == 1
    ri = cue_ri[0]
    assert ri.narrative == "A gate appears."
    assert ri.entry_number > 0
    assert cue.entry_number == ri.entry_number


def test_cue_sum_in_collision_check():
    """Cue sums participate in collision detection."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    # The cue's resolved interaction should be in the resolved list
    sums = [ri.sum_id for ri in game.resolved]
    assert cue.sum_id in sums
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_cues.py::test_cue_gets_id_and_sum tests/test_cues.py::test_cue_appears_in_resolved tests/test_cues.py::test_cue_sum_in_collision_check -v`
Expected: FAIL — cue IDs are 0, no resolved interactions for cues.

- [ ] **Step 3: Update compiler to allocate cue IDs and resolve cues**

In `src/addventure/compiler.py`:

Update the import at line 4-6 to replace `RoomAlert` with `Cue`:

```python
from .models import (
    GameData, Verb, Noun, Interaction, ResolvedInteraction, Cue,
)
```

In `_try_allocate` (around line 19), after allocating item IDs (line 32), add:

```python
    for cue in game.cues:
        cue.id = entity_pool.pop()
```

Delete the entire `generate_room_alerts` function (lines 99–116).

Add a new `resolve_cues` function in its place:

```python
def resolve_cues(game: GameData):
    """Create ResolvedInteractions for each cue (cue.id + target_room.id)."""
    for cue in game.cues:
        target_rm = game.rooms.get(cue.target_room)
        if not target_rm:
            raise ParseError(cue.source_line, f"Cue targets unknown room: {cue.target_room}")
        cue.sum_id = cue.id + target_rm.id
        game.resolved.append(ResolvedInteraction(
            verb="CUE",
            targets=[],
            sum_id=cue.sum_id,
            narrative=cue.narrative,
            arrows=cue.arrows,
            source_line=cue.source_line,
            room=cue.target_room,
            parent_label=f"Cue #{cue.id}",
        ))
```

In `compile_game` (around line 253), replace the `generate_room_alerts(game)` call (line 279) with:

```python
    resolve_cues(game)
```

The `resolve_cues` call should be placed **after** `resolve_interactions` (which assigns entry numbers). Since cue resolved interactions are appended to `game.resolved`, they need entry numbers too. Move the entry number assignment out of `resolve_interactions` and into `compile_game` so it covers both regular and cue resolved interactions. Alternatively, just renumber after `resolve_cues`:

In `compile_game`, after the `resolve_cues(game)` call, add:

```python
    # Renumber all entries (cue resolutions were appended after initial numbering)
    for idx, ri in enumerate(game.resolved, 1):
        ri.entry_number = idx
    # Copy entry numbers back to cue objects
    for cue in game.cues:
        for ri in game.resolved:
            if ri.sum_id == cue.sum_id:
                cue.entry_number = ri.entry_number
                break
```

Also in `compile_game`, cue IDs must be reset on retry like other IDs. In the retry loop, after `game.resolved = []` (line 275), add:

```python
        for cue in game.cues:
            cue.id = 0
            cue.sum_id = 0
            cue.entry_number = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/compiler.py tests/test_cues.py
git commit -m "Allocate cue IDs and resolve cue sums into potentials"
```

---

### Task 4: Writer — Cue trigger and resolution instructions

**Files:**
- Modify: `src/addventure/writer.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the test for cue instructions in the ledger**

Append to `tests/test_cues.py`:

```python
from addventure.writer import GameWriter


def test_trigger_instruction_writes_cue():
    """The ledger entry that triggers a cue should say 'Write N in your Cue Checks.'"""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    cue = game.cues[0]

    # Find the USE + LEVER resolved interaction
    use_lever = [ri for ri in game.resolved if ri.verb == "USE" and "LEVER" in ri.targets]
    assert len(use_lever) == 1
    instructions = writer._generate_instructions(use_lever[0])
    cue_instr = [i for i in instructions if "Cue Checks" in i]
    assert len(cue_instr) == 1
    assert str(cue.id) in cue_instr[0]
    assert "Write" in cue_instr[0]


def test_resolution_instruction_crosses_out_cue():
    """The cue resolution ledger entry should say 'Cross out N from your Cue Checks.'"""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    cue = game.cues[0]

    # Find the cue's resolved interaction
    cue_ri = [ri for ri in game.resolved if ri.sum_id == cue.sum_id]
    assert len(cue_ri) == 1
    instructions = writer._generate_instructions(cue_ri[0])
    cross_out = [i for i in instructions if "Cross out" in i]
    assert len(cross_out) == 1
    assert str(cue.id) in cross_out[0]
    assert "Cue Checks" in cross_out[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_cues.py::test_trigger_instruction_writes_cue tests/test_cues.py::test_resolution_instruction_crosses_out_cue -v`
Expected: FAIL — writer still has old alert code.

- [ ] **Step 3: Update writer to handle cue instructions**

In `src/addventure/writer.py`:

Replace the `# THING -> "Other Room" (remote reveal / alert)` block (lines 201–212) with:

```python
            # ? -> "Room" (cue trigger — deferred cross-room effect)
            elif subj == "?":
                target_room = dest[1:-1]
                cue = next(
                    (c for c in self.game.cues
                     if c.target_room == target_room
                     and c.trigger_room == ri.room),
                    None
                )
                if cue:
                    instructions.append(
                        f"Write {cue.id} in your Cue Checks."
                    )
```

Now handle the resolution side. The cue resolved interactions have `verb="CUE"`. Their arrows are normal arrows that operate in the target room. The existing instruction generation handles `-> room`, `-> trash`, transforms, etc. — those will just work for the cue's arrows. But we need to append a "Cross out" instruction at the end.

Add a new check after the arrow loop in `_generate_instructions`, just before the blind mode block (before `if self.blind:`):

```python
        # Cue resolution: append "Cross out N from your Cue Checks"
        if ri.verb == "CUE":
            cue = next(
                (c for c in self.game.cues if c.sum_id == ri.sum_id),
                None
            )
            if cue:
                instructions.append(
                    f"Cross out {cue.id} from your Cue Checks."
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/writer.py tests/test_cues.py
git commit -m "Generate cue trigger and resolution instructions in ledger"
```

---

### Task 5: Writer — Cue Checks section on inventory sheet, remove Room Alerts

**Files:**
- Modify: `src/addventure/writer.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the tests**

Append to `tests/test_cues.py`:

```python
def test_inventory_sheet_has_cue_checks_when_cues_exist():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    inv = writer.write_inventory_sheet()
    assert "CUE CHECKS" in inv
    assert "Cue Checks" in inv or "cue" in inv.lower()


def test_inventory_sheet_no_cue_checks_without_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\nKEY\n"
    room_src = """# Room
LOOK: A room.

BOX
+ LOOK: A box.
+ USE + KEY:
  You open it.
  - BOX -> BOX__OPEN
    + LOOK: Open box.
  - KEY -> trash
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    inv = writer.write_inventory_sheet()
    assert "CUE" not in inv


def test_room_sheet_no_alerts():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    sheet = writer.write_room_sheet("Room A")
    assert "Alert" not in sheet
    assert "alert" not in sheet
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_cues.py::test_inventory_sheet_has_cue_checks_when_cues_exist tests/test_cues.py::test_inventory_sheet_no_cue_checks_without_cues tests/test_cues.py::test_room_sheet_no_alerts -v`
Expected: FAIL

- [ ] **Step 3: Add Cue Checks section to inventory sheet**

In `src/addventure/writer.py`, in `write_inventory_sheet` (around line 104), add a cue checks section between the inventory slots and the potentials list. After the inventory slots loop (after line 111, before the `\n\nMASTER POTENTIALS LIST` line), add:

```python
        if self.game.cues:
            lines.append("\n\nCUE CHECKS")
            lines.append("-" * 40)
            lines.append("On room entry, add each cue + Room ID and check the Potentials List.\n")
            lines.append("  ____  ____  ____  ____  ____  ____")
```

- [ ] **Step 4: Remove Room Alerts from room sheet**

In `write_room_sheet` (around line 56), delete lines 94–98 (the Room Alerts section):

```python
        # Room alert check area
        lines.append(f"\nRoom Alerts (check on entry):")
        lines.append(f"  If you have alert numbers for this room,")
        lines.append(f"  add the alert number + {rm.id} (Room ID)")
        lines.append(f"  and check the Potentials List.")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/addventure/writer.py tests/test_cues.py
git commit -m "Add Cue Checks to inventory sheet, remove Room Alerts from room sheet"
```

---

### Task 6: PDF serialization — Include cue data

**Files:**
- Modify: `src/addventure/pdf_writer.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the test**

Append to `tests/test_cues.py`:

```python
from addventure.pdf_writer import serialize_game_data


def test_serialize_includes_cue_slots():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert "cue_slots" in data
    assert data["cue_slots"] > 0


def test_serialize_no_cue_slots_without_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\nKEY\n"
    room_src = """# Room
LOOK: A room.

BOX
+ LOOK: A box.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert data["cue_slots"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_cues.py::test_serialize_includes_cue_slots tests/test_cues.py::test_serialize_no_cue_slots_without_cues -v`
Expected: FAIL — `cue_slots` not in serialized data.

- [ ] **Step 3: Add cue_slots to serialize_game_data**

In `src/addventure/pdf_writer.py`, in `serialize_game_data` (around line 22), add `cue_slots` to the returned dict. In the `return` block (line 81), add:

```python
        "cue_slots": len(game.cues),
```

Add it after the `"inventory_slots"` line.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_cues.py::test_serialize_includes_cue_slots tests/test_cues.py::test_serialize_no_cue_slots_without_cues -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/pdf_writer.py tests/test_cues.py
git commit -m "Include cue_slots in PDF serialization data"
```

---

### Task 7: Typst templates — Cue Checks on inventory, remove Room Alerts

**Files:**
- Modify: `src/addventure/templates/default/inventory.typ`
- Modify: `src/addventure/templates/default/room-sheet.typ`

- [ ] **Step 1: Add Cue Checks section to inventory.typ**

In `src/addventure/templates/default/inventory.typ`, after the inventory slots grid (after line 33 `}`) and before the potentials section (`v(1.5em)`), add:

```typst
  // Cue Checks section (only if game has cues)
  let cue-slots = data.at("cue_slots", default: 0)
  if cue-slots > 0 {
    v(1.5em)
    section-title("Cue Checks")
    block(below: 0.6em)[
      #text(size: 9pt, style: "italic")[On room entry, add each cue + Room ID and check the Potentials List.]
    ]
    v(0.4em)
    let cue-count = calc.max(cue-slots, 6)
    grid(
      columns: (3.5em,) * 6,
      gutter: (0.8em, 0.6em),
      ..for i in range(cue-count) {
        (write-slot(width: 100%),)
      }
    )
  }
```

- [ ] **Step 2: Remove Room Alerts section from room-sheet.typ**

In `src/addventure/templates/default/room-sheet.typ`, delete lines 139–155 (the entire Room Alerts section):

```typst
  // Room alerts section
  v(1em)
  section-title("Room Alerts")
  block(
    width: 100%,
    stroke: (left: 2pt + luma(180)),
    inset: (left: 8pt, y: 6pt),
  )[
    #text(size: 9pt, style: "italic")[
      Some actions in other rooms may affect what you find here. If instructed to update this room's state, record it below.
    ]
  ]
  v(0.5em)
  write-slot()
  v(0.4em)
  write-slot()
```

- [ ] **Step 3: Test by building the example game**

Run: `uv run adv build games/example --text`
Check: No errors. Room sheets should not mention "Alert". Inventory sheet should not yet have Cue Checks (example game has no cues yet).

- [ ] **Step 4: Commit**

```bash
git add src/addventure/templates/default/inventory.typ src/addventure/templates/default/room-sheet.typ
git commit -m "Add Cue Checks to inventory template, remove Room Alerts from room sheet"
```

---

### Task 8: Clean up old alert references

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `src/addventure/writer.py`

- [ ] **Step 1: Remove any remaining alert references from compiler.py**

In `src/addventure/compiler.py`, verify that:
- `RoomAlert` is no longer imported (should already be `Cue` from Task 3)
- `generate_room_alerts` function is deleted (should already be done in Task 3)
- No remaining references to `alerts` or `RoomAlert`

Run: `grep -n "alert\|RoomAlert" src/addventure/compiler.py` — should return nothing.

- [ ] **Step 2: Remove alert references from writer.py**

In `src/addventure/writer.py`, in `print_full_report` (line 385), change:

```python
    print(f"  Alerts: {len(game.alerts)}")
```

to:

```python
    print(f"  Cues: {len(game.cues)}")
```

Run: `grep -n "alert\|RoomAlert" src/addventure/writer.py` — should return nothing.

- [ ] **Step 3: Run all tests**

Run: `uv run --with pytest pytest tests/ -v`
Expected: All cue tests pass. The two pre-existing failures may still fail (unrelated).

- [ ] **Step 4: Commit**

```bash
git add src/addventure/compiler.py src/addventure/writer.py
git commit -m "Clean up remaining alert references"
```

---

### Task 9: Example game — Add a cue interaction

**Files:**
- Modify: `games/example/control_room.md`
- Modify: `games/example/basement.md`

- [ ] **Step 1: Add cue arrow to control_room.md**

In `games/example/control_room.md`, in the `USE + KEYCARD` interaction block (line 7), add a cue arrow after the existing arrows. The block currently reads:

```markdown
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
```

Add after `- KEYCARD -> trash` and before `- room -> room__POWERED`:

```markdown
  - ? -> "Basement"
    The power surge triggers the fuse box. A hidden compartment clicks open behind it.
    - COMPARTMENT -> room
```

- [ ] **Step 2: Add COMPARTMENT noun to basement.md**

In `games/example/basement.md`, add after the existing entities:

```markdown
COMPARTMENT
+ LOOK: A small compartment behind the fuse box. Something glints inside.
```

- [ ] **Step 3: Build and verify**

Run: `uv run adv build games/example --text`
Check the output:
- The USE + KEYCARD ledger entry should include "Write N in your Cue Checks"
- There should be a new ledger entry for the cue resolution with "A hidden compartment clicks open" and "Write COMPARTMENT (N) in a discovery slot"
- The inventory section should show a "CUE CHECKS" area
- Room sheets should have no "Room Alerts" section
- The Potentials List should include the cue sum

- [ ] **Step 4: Run all tests (including end-to-end)**

Run: `uv run --with pytest pytest tests/ -v`
Expected: `test_end_to_end_example_game` should still pass (if typst is installed).

- [ ] **Step 5: Commit**

```bash
git add games/example/control_room.md games/example/basement.md
git commit -m "Add cue interaction to example game (lever triggers basement compartment)"
```

---

### Task 10: Documentation updates

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md Script Syntax section**

In `CLAUDE.md`, in the Script Syntax section, add `? -> "RoomName"` to the arrow destinations list. The current list reads:

```markdown
- Arrow destinations: `player`, `trash`, `"RoomName"`, `room` (current room), `ENTITY__STATE`
```

Change to:

```markdown
- Arrow destinations: `player`, `trash`, `"RoomName"`, `room` (current room), `ENTITY__STATE`
- `? -> "RoomName"` — cue (deferred cross-room effect, resolved when player enters target room)
```

In the Architecture section, the Compiler pipeline list mentions "generate_room_alerts". Change step 7:

```markdown
7. `generate_room_alerts` — create cross-room alerts
```

to:

```markdown
7. `resolve_cues` — resolve cross-room cue interactions
```

In the Writer section, add to the components list:

After `- **Inventory Sheet** — item tracking + Master Potentials List (sum lookups)` add that it also includes Cue Checks:

```markdown
- **Inventory Sheet** — item tracking + Cue Checks (cross-room triggers) + Master Potentials List (sum lookups)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "Update docs for cue checks system"
```

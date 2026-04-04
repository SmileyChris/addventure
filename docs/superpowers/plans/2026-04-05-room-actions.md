# Room Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct-lookup "actions" to rooms that bypass the verb+noun addition system, giving players pre-printed or discoverable ledger entry references on room sheets.

**Architecture:** New `Action` dataclass, `>` syntax marker in parser, ledger ID assignment interleaved with resolved interactions, writer generates room sheet action slots and standard ledger entries. Also fix arrow room context so arrows after `player -> "Room"` resolve against the destination room.

**Tech Stack:** Python 3.10+, pytest

---

### Task 1: Action dataclass and GameData field

**Files:**
- Modify: `src/addventure/models.py:77-89`
- Test: `tests/test_actions.py` (create)

- [ ] **Step 1: Write the failing test**

```python
from addventure.models import Action, Arrow, GameData


def test_action_dataclass():
    action = Action(
        name="GO_NORTH",
        room="Forest",
        narrative="You head north.",
        arrows=[Arrow("player", '"Clearing"', 5)],
        discovered=False,
    )
    assert action.name == "GO_NORTH"
    assert action.room == "Forest"
    assert action.narrative == "You head north."
    assert action.discovered is False
    assert action.ledger_id == 0
    assert len(action.arrows) == 1


def test_gamedata_has_actions():
    game = GameData()
    assert game.actions == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py -v`
Expected: FAIL with ImportError (Action not defined)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/models.py`, add the `Action` dataclass before `GameData` and add the `actions` field to `GameData`:

```python
@dataclass
class Action:
    name: str
    room: str
    narrative: str
    arrows: list[Arrow]
    discovered: bool
    ledger_id: int = 0
```

Add to `GameData`:
```python
    actions: dict[str, Action] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/models.py tests/test_actions.py
git commit -m "feat: add Action dataclass and GameData.actions field"
```

---

### Task 2: Parse `>` action declarations at room level

**Files:**
- Modify: `src/addventure/parser.py:1-4` (imports), `src/addventure/parser.py:181-222` (`_parse_room_body`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
from addventure.compiler import compile_game


def test_parse_room_level_action():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A dense forest.

> GO_NORTH
  You head north through the trees.
  - player -> "Clearing"

# Clearing
LOOK: A sunlit clearing.
"""
    game = compile_game(global_src, [room_src])
    assert "Forest::GO_NORTH" in game.actions
    action = game.actions["Forest::GO_NORTH"]
    assert action.name == "GO_NORTH"
    assert action.room == "Forest"
    assert action.narrative == "You head north through the trees."
    assert action.discovered is False
    assert len(action.arrows) == 1
    assert action.arrows[0].subject == "player"
    assert action.arrows[0].destination == '"Clearing"'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_parse_room_level_action -v`
Expected: FAIL (parser doesn't recognize `>` lines)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/parser.py`:

Add `Action` to the import from `.models`:
```python
from .models import (
    GameData, Verb, Noun, Item, Room, Arrow, Interaction, Cue, Action,
)
```

Add a helper to detect action lines:
```python
def _is_action(s: str) -> bool:
    return s.startswith("> ")
```

Add the action parsing function:
```python
def _parse_action(lines, i, game, room_name, discovered, parent_indent):
    """Parse a > ACTION_NAME block. Returns next line index."""
    line = lines[i]
    stripped = line.strip()
    action_name = stripped[2:].strip()  # strip "> "
    source_line = i + 1
    current_indent = _indent(line)
    i += 1

    narrative = ""
    arrows = []

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or _is_comment(bstripped):
            i += 1
            continue
        if _indent(bline) <= current_indent or _is_header(bline):
            break

        bmarker, bcontent = _strip_marker(bstripped)

        if bmarker == "-" and _is_arrow(bcontent):
            arrow = _parse_arrow(bcontent, i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=arrows)
        elif _is_narrative(bstripped) and not narrative:
            narrative = bstripped
            i += 1
        elif _is_narrative(bstripped) and narrative:
            narrative += "\n\n" + bstripped
            i += 1
        else:
            i += 1

    key = f"{room_name}::{action_name}"
    game.actions[key] = Action(
        name=action_name,
        room=room_name,
        narrative=narrative,
        arrows=arrows,
        discovered=discovered,
    )
    return i
```

In `_parse_room_body`, add action handling. Before the existing `if ind == 0 and not marker:` block (around line 192), add a check for action lines:

```python
        if _is_action(stripped):
            i = _parse_action(lines, i, game, room_name, discovered=False, parent_indent=-1)
            continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_parse_room_level_action -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/parser.py tests/test_actions.py
git commit -m "feat: parse room-level action declarations with > marker"
```

---

### Task 3: Parse discoverable actions nested under interactions

**Files:**
- Modify: `src/addventure/parser.py:280-348` (`_parse_inline_interaction`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
def test_parse_discoverable_action():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A gnarled oak.
+ USE:
  You push the tree aside.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path is revealed.
    - player -> "Cave"

# Cave
LOOK: A dark cave.
"""
    game = compile_game(global_src, [room_src])
    assert "Forest::HIDDEN_PATH" in game.actions
    action = game.actions["Forest::HIDDEN_PATH"]
    assert action.discovered is True
    assert action.narrative == "A path is revealed."
    assert len(action.arrows) == 1
    assert action.arrows[0].destination == '"Cave"'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_parse_discoverable_action -v`
Expected: FAIL (action lines inside interactions not parsed)

- [ ] **Step 3: Write minimal implementation**

In `_parse_inline_interaction`, inside the `while i < len(lines):` loop, after the arrow handling block and before the narrative check, add action detection:

```python
        elif _is_action(bstripped):
            i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=current_indent)
```

Similarly, in `_parse_arrow_children` for the `dest == "trash"` case, the loop already skips children — no change needed. For arrow children that parse entity blocks or other nested content, the `_parse_entity_block` function needs to handle `>` lines too.

In `_parse_entity_block`, inside the `else:` branch (no marker, line 265-276), before the bare entity name check, add:

```python
            if _is_action(stripped):
                i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=entity_indent)
                continue
```

In `_parse_freeform_interactions`, inside the body parsing loop, add action detection similarly:

```python
                elif _is_action(bs):
                    i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_parse_discoverable_action -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/parser.py tests/test_actions.py
git commit -m "feat: parse discoverable actions nested under interactions"
```

---

### Task 4: Action ledger ID assignment and deduplication

**Files:**
- Modify: `src/addventure/compiler.py:534-573` (dedup/shuffle section in `compile_game`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
def test_action_gets_ledger_id():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    action = game.actions["Forest::GO_NORTH"]
    assert action.ledger_id > 0


def test_action_deduplication():
    """Actions with identical arrows and compatible narratives share ledger IDs."""
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head to the clearing.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.

> GO_SOUTH
  - player -> "Forest"

# Village
LOOK: A village.

> GO_SOUTH
  You walk south to the forest.
  - player -> "Forest"
"""
    game = compile_game(global_src, [room_src])
    # Clearing::GO_SOUTH has no narrative, Village::GO_SOUTH has narrative
    # Both go to Forest — they should share a ledger ID, with Clearing
    # inheriting Village's narrative
    clearing_action = game.actions["Clearing::GO_SOUTH"]
    village_action = game.actions["Village::GO_SOUTH"]
    assert clearing_action.ledger_id == village_action.ledger_id
    assert clearing_action.narrative == "You walk south to the forest."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_action_gets_ledger_id tests/test_actions.py::test_action_deduplication -v`
Expected: FAIL (ledger_id still 0)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/compiler.py`, in the `compile_game` function, after the existing entry renumbering/dedup section and before the shuffle, integrate actions into the entry numbering.

Add `Action` to the imports:
```python
from .models import (
    GameData, Verb, Noun, Item, Interaction, ResolvedInteraction, Cue, Action,
)
```

After the existing dedup loop (after line 566 `content_entry[key] = entry_num`), add action dedup:

```python
    # Assign ledger entry numbers to actions, deduplicating by arrows + narrative
    action_content = {}  # (narrative, arrows_key) -> (entry_number, action_with_narrative)
    for action in game.actions.values():
        arrows_key = tuple((a.subject, a.destination) for a in action.arrows)
        key = arrows_key  # Group by arrows first for narrative inheritance
        if key in action_content:
            existing_entry, existing_action = action_content[key]
            # Check narrative compatibility
            if action.narrative and existing_action.narrative and action.narrative != existing_action.narrative:
                # Different narratives — unique entry
                entry_num += 1
                action.ledger_id = entry_num
            else:
                # Share entry; inherit narrative if needed
                action.ledger_id = existing_entry
                if not action.narrative and existing_action.narrative:
                    action.narrative = existing_action.narrative
                elif action.narrative and not existing_action.narrative:
                    existing_action.narrative = action.narrative
        else:
            entry_num += 1
            action.ledger_id = entry_num
            action_content[key] = (entry_num, action)
```

Update the shuffle section to include action entry numbers. Change the `unique_entries` and `remap` lines to cover the expanded range, and add a loop to remap action ledger IDs:

```python
    # After the existing remap loop for ri.entry_number:
    for action in game.actions.values():
        action.ledger_id = remap[action.ledger_id]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_action_gets_ledger_id tests/test_actions.py::test_action_deduplication -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/compiler.py tests/test_actions.py
git commit -m "feat: assign and deduplicate action ledger IDs"
```

---

### Task 5: Action -> trash resolution in writer

**Files:**
- Modify: `src/addventure/writer.py:58-70` (`_generate_instructions`, trash branch)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
from addventure.writer import GameWriter, _display_name


def test_action_trash_instruction():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You cross the bridge.
  - player -> "Clearing"

LEVER
+ LOOK: A rusty lever.
+ USE:
  You pull the lever. The bridge collapses!
  - GO_NORTH -> trash

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    # Find the USE + LEVER interaction
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "LEVER" in ri.targets)
    instructions = writer._generate_instructions(ri)
    assert any("Cross out" in inst and "GO NORTH" in inst for inst in instructions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_action_trash_instruction -v`
Expected: FAIL (writer doesn't know how to trash actions)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/writer.py`, in `_generate_instructions`, in the `dest == "trash"` branch (line 59), after checking verbs and before the else that calls `_locate_entity`, add a check for actions:

```python
            elif dest == "trash":
                if subj in self.game.verbs:
                    verb = self.game.verbs[subj]
                    instructions.append(
                        f"Cross out {dn(subj)} ({verb.id}) on your Verb Sheet."
                    )
                else:
                    # Check if subject is an action in this room
                    action_key = f"{ri.room}::{subj}"
                    action = self.game.actions.get(action_key)
                    if action:
                        prefix = self.entry_prefix
                        instructions.append(
                            f"Cross out {dn(subj)} ({prefix}-{action.ledger_id}) on this room sheet."
                        )
                    else:
                        sheet, entity_id = self._locate_entity(
                            subj, ri.room, ri.from_inventory)
                        instructions.append(
                            f"Cross out {dn(subj)} ({entity_id}) on your {sheet}."
                        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_action_trash_instruction -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/writer.py tests/test_actions.py
git commit -m "feat: generate cross-out instructions for action -> trash"
```

---

### Task 6: Action ledger entries in writer and discovery slot counting

**Files:**
- Modify: `src/addventure/writer.py:30-180` (`_generate_instructions`), `src/addventure/writer.py:240-255` (`_max_discovery_slots`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
def test_action_ledger_entry_instructions():
    """Actions generate ledger entries with instructions like regular interactions."""
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    action = game.actions["Forest::GO_NORTH"]
    # Create a ResolvedInteraction-like object for the action to test instruction generation
    # The writer should be able to generate instructions from action arrows
    writer = GameWriter(game)
    from addventure.models import ResolvedInteraction
    ri = ResolvedInteraction(
        verb="ACTION", targets=[], sum_id=0,
        narrative=action.narrative, arrows=action.arrows,
        source_line=0, room=action.room, parent_label=action.name,
    )
    instructions = writer._generate_instructions(ri)
    assert any("Switch to" in inst and "Clearing" in inst for inst in instructions)


def test_discoverable_action_counts_toward_discovery_slots():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A tree.
+ USE:
  You push the tree.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path revealed.
    - player -> "Cave"

# Cave
LOOK: A cave.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    assert writer._max_discovery_slots() >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_action_ledger_entry_instructions tests/test_actions.py::test_discoverable_action_counts_toward_discovery_slots -v`
Expected: First test may pass (existing arrow handling works for `player -> "Room"`). Second test FAIL (discovery slots don't count actions).

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/writer.py`, update `_max_discovery_slots` to count discoverable actions:

```python
    def _max_discovery_slots(self) -> int:
        """Max discovery slot count across all base rooms."""
        max_count = 0
        for room_name, rm in self.game.rooms.items():
            if rm.state is not None:
                continue
            count = sum(
                1 for ix in self.game.interactions if ix.room == room_name
                for a in ix.arrows if a.destination == "room"
            ) + sum(
                1 for cue in self.game.cues if cue.target_room == room_name
                for a in cue.arrows if a.destination == "room"
            ) + sum(
                1 for a in self.game.actions.values()
                if a.room == room_name and a.discovered
            )
            if count > max_count:
                max_count = count
        return max_count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_action_ledger_entry_instructions tests/test_actions.py::test_discoverable_action_counts_toward_discovery_slots -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/writer.py tests/test_actions.py
git commit -m "feat: count discoverable actions toward discovery slots"
```

---

### Task 7: Markdown writer — actions on room sheets and in ledger

**Files:**
- Modify: `src/addventure/md_writer.py:75-127` (`_room_section`), `src/addventure/md_writer.py:183-206` (`_ledger_section`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
from addventure.md_writer import generate_markdown


def test_markdown_room_shows_actions():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    md, warnings = generate_markdown(game)
    # The room section should show the action with its ledger reference
    assert "GO NORTH" in md
    entry_prefix = game.metadata.get("entry_prefix", "A")
    action = game.actions["Forest::GO_NORTH"]
    assert f"{entry_prefix}-{action.ledger_id}" in md


def test_markdown_ledger_includes_action_entries():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    md, warnings = generate_markdown(game)
    action = game.actions["Forest::GO_NORTH"]
    entry_prefix = game.metadata.get("entry_prefix", "A")
    # Ledger should contain the action's entry
    assert f"{entry_prefix}-{action.ledger_id}" in md
    assert "You head north." in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_markdown_room_shows_actions tests/test_actions.py::test_markdown_ledger_includes_action_entries -v`
Expected: FAIL (actions not rendered in markdown)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/md_writer.py`:

Update `_room_section` to add an actions subsection. After the objects section (before the discovery slots), add actions rendering. The function needs access to `game.actions` and `entry_prefix`:

```python
    # Actions (pre-printed)
    room_actions = [
        a for a in game.actions.values()
        if a.room == room_name and not a.discovered
    ]
    if room_actions:
        lines.append("\n### Actions\n")
        lines.append("| Action | Entry |")
        lines.append("|--------|------:|")
        for a in room_actions:
            lines.append(f"| {_display_name(a.name)} | {entry_prefix}-{a.ledger_id} |")

    # Action discovery slots
    action_disc_count = sum(
        1 for a in game.actions.values()
        if a.room == room_name and a.discovered
    )
    if (not blind or is_start) and action_disc_count > 0:
        # These are included in the general discovery slots
        pass  # Discovery slots already counted in the discoveries section
```

Update `_ledger_section` to include action ledger entries alongside resolved interaction entries. After building the sorted resolved list and rendering, also render action entries:

```python
def _ledger_section(
    game: GameData, writer: GameWriter, entry_prefix: str,
) -> str:
    lines = [
        "## Story Ledger",
        "\n*Only read an entry when directed to by the Potentials List or a room sheet action."
        " Read the narrative aloud, then follow any instructions.*",
    ]

    # Collect all ledger entries: resolved interactions + actions
    all_entries = []

    seen_entries = set()
    for ri in game.resolved:
        if ri.entry_number in seen_entries:
            continue
        seen_entries.add(ri.entry_number)
        instructions = writer._generate_instructions(ri)
        all_entries.append((ri.entry_number, ri.narrative, instructions))

    seen_action_entries = set()
    for action in game.actions.values():
        if action.ledger_id in seen_entries or action.ledger_id in seen_action_entries:
            continue
        seen_action_entries.add(action.ledger_id)
        from .models import ResolvedInteraction
        ri = ResolvedInteraction(
            verb="ACTION", targets=[], sum_id=0,
            narrative=action.narrative, arrows=action.arrows,
            source_line=0, room=action.room, parent_label=action.name,
        )
        instructions = writer._generate_instructions(ri)
        all_entries.append((action.ledger_id, action.narrative, instructions))

    all_entries.sort(key=lambda e: e[0])

    for entry_num, narrative, instructions in all_entries:
        lines.append(f"\n{entry_prefix}-{entry_num}")
        body = narrative
        if instructions:
            body += "\n\n" + "\n".join(f"- *{inst}*" for inst in instructions)
        lines.append(indent(body, ": ", lambda line: True))

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_markdown_room_shows_actions tests/test_actions.py::test_markdown_ledger_includes_action_entries -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/md_writer.py tests/test_actions.py
git commit -m "feat: render actions on room sheets and in ledger (markdown)"
```

---

### Task 8: PDF writer — serialize actions for Typst templates

**Files:**
- Modify: `src/addventure/pdf_writer.py:21-108` (`serialize_game_data`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
from addventure.pdf_writer import serialize_game_data


def test_pdf_serialization_includes_actions():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    # Rooms should have an "actions" key
    forest = next(r for r in data["rooms"] if r["name"] == "Forest")
    assert "actions" in forest
    assert len(forest["actions"]) == 1
    assert forest["actions"][0]["name"] == "GO_NORTH"
    assert forest["actions"][0]["entry"] > 0
    # Action should appear in the ledger
    action_entry = game.actions["Forest::GO_NORTH"].ledger_id
    assert any(e["entry"] == action_entry for e in data["ledger"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_pdf_serialization_includes_actions -v`
Expected: FAIL (no "actions" key in room data)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/pdf_writer.py`, in `serialize_game_data`:

In the room loop, after computing `disc_count`, add action serialization:

```python
        # Actions for this room
        room_actions = [
            {"name": a.name, "entry": a.ledger_id, "discovered": a.discovered}
            for a in game.actions.values()
            if a.room == room_name and not a.discovered
        ]

        # Count discoverable actions toward discovery slots
        action_disc_count = sum(
            1 for a in game.actions.values()
            if a.room == room_name and a.discovered
        )
```

Add `"actions": room_actions` to the room dict and add `action_disc_count` to `disc_count`.

For the ledger, after the existing dedup loop, add action entries:

```python
    seen_action_entries = set()
    for action in game.actions.values():
        if action.ledger_id in seen_entries or action.ledger_id in seen_action_entries:
            continue
        seen_action_entries.add(action.ledger_id)
        from .models import ResolvedInteraction
        ri = ResolvedInteraction(
            verb="ACTION", targets=[], sum_id=0,
            narrative=action.narrative, arrows=action.arrows,
            source_line=0, room=action.room, parent_label=action.name,
        )
        instructions = writer._generate_instructions(ri)
        ledger.append({
            "entry": action.ledger_id,
            "narrative": action.narrative,
            "instructions": instructions,
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_pdf_serialization_includes_actions -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/pdf_writer.py tests/test_actions.py
git commit -m "feat: serialize actions for PDF output"
```

---

### Task 9: Typst template — render actions on room sheets

**Files:**
- Modify: `src/addventure/templates/default/room-sheet.typ`

- [ ] **Step 1: Add actions section to room sheet template**

In `src/addventure/templates/default/room-sheet.typ`, after the Objects section and before the Discovery slots section (before line 136), add an Actions section:

```typst
  // Actions section (direct ledger references)
  let prefix = if "entry_prefix" in room { room.entry_prefix } else { "A" }
  let room-actions = if "actions" in room { room.actions } else { () }
  if room-actions.len() > 0 {
    v(1em)
    section-title("Actions")
    v(0.3em)

    for act in room-actions {
      block(
        width: 100%,
        below: 0.4em,
      )[
        #grid(
          columns: (1fr, auto),
          gutter: 0.5em,
          align(left + horizon)[
            #strike-text(text(font: "Liberation Sans", size: 10pt)[#act.name.replace("_", " ")])
          ],
          align(right + horizon)[
            #text(font: "Liberation Sans", size: 10pt, weight: "bold")[#prefix\-#str(act.entry)]
          ],
        )
      ]
      line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
    }
  }
```

Note: The `entry_prefix` needs to be passed to each room dict in `serialize_game_data`. Update `pdf_writer.py` to add `"entry_prefix": entry_prefix` to each room dict.

- [ ] **Step 2: Build example game and verify PDF output**

Run: `uv run adv build --md` with a test game that has actions, and verify the output includes actions on room sheets.

- [ ] **Step 3: Commit**

```bash
git add src/addventure/templates/default/room-sheet.typ src/addventure/pdf_writer.py
git commit -m "feat: render actions on room sheets in PDF output"
```

---

### Task 10: Arrow room context — resolve post-transition arrows against destination

**Files:**
- Modify: `src/addventure/writer.py:30-180` (`_generate_instructions`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
def test_arrow_room_context_after_player_transition():
    """Arrows after player -> 'Room' should resolve against the destination room."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

BRIDGE
+ LOOK: A rickety bridge.
+ USE:
  You cross the bridge. A fountain appears!
  - BRIDGE -> trash
  - player -> "Clearing"
  - FOUNTAIN -> room

# Clearing
LOOK: A clearing.

FOUNTAIN
+ LOOK: A sparkling fountain.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "BRIDGE" in ri.targets)
    instructions = writer._generate_instructions(ri)
    # BRIDGE -> trash should reference Forest (exit room)
    bridge_inst = next(i for i in instructions if "BRIDGE" in i)
    assert "room sheet" in bridge_inst  # Forest room sheet
    # FOUNTAIN -> room should reference Clearing (entry room)
    fountain_inst = next(i for i in instructions if "FOUNTAIN" in i)
    assert "room sheet" in fountain_inst  # Clearing room sheet

    # The fountain ID should be from the Clearing room, not Forest
    clearing_fountain = game.nouns.get("Clearing::FOUNTAIN")
    assert clearing_fountain is not None
    assert str(clearing_fountain.id) in fountain_inst
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_arrow_room_context_after_player_transition -v`
Expected: FAIL (FOUNTAIN resolves against Forest, not Clearing)

- [ ] **Step 3: Write minimal implementation**

In `src/addventure/writer.py`, in `_generate_instructions`, track the current room context and update it when a `player -> "Room"` transition is encountered:

At the start of the method, add:
```python
        current_room = ri.room
```

In the `player -> "Room"` handler (line 48), after generating the instruction, update the room context:
```python
            if subj == "player" and dest.startswith('"'):
                room_name = dest[1:-1]
                rm = self.game.rooms.get(room_name)
                if rm:
                    if self.blind:
                        room_ref = f"room sheet {rm.id}"
                    else:
                        room_ref = f"the {room_name} room sheet"
                    instructions.append(f"Switch to {room_ref}.")
                    current_room = room_name  # Subsequent arrows resolve here
```

Then replace all uses of `ri.room` in the arrow processing loop with `current_room`. Specifically:
- Line 67: `self._locate_entity(subj, current_room, ri.from_inventory)`
- Line 100: `self._get_id(subj, current_room)`
- Line 109-112: cue trigger matching uses `ri.room` for trigger_room — this should stay as `ri.room` since cues are defined relative to the interaction's source room
- Line 124: `base_room = current_room.split("__")[0]`
- Line 127-128: `self._get_id(resolved_subj, current_room)` and `self._get_id(resolved_dest, current_room)`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_arrow_room_context_after_player_transition -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass (existing tests should still pass since they don't have arrows after player transitions)

- [ ] **Step 6: Commit**

```bash
git add src/addventure/writer.py tests/test_actions.py
git commit -m "feat: resolve arrows after player transition against destination room"
```

---

### Task 11: Discovery instruction for discoverable actions

**Files:**
- Modify: `src/addventure/writer.py:30-180` (`_generate_instructions`)
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_actions.py`:

```python
def test_discoverable_action_instruction():
    """When an interaction reveals an action, the instruction says to write it on the room sheet."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A gnarled oak.
+ USE:
  You push the tree aside.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path is revealed.
    - player -> "Cave"

# Cave
LOOK: A cave.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "OLD_TREE" in ri.targets)
    instructions = writer._generate_instructions(ri)
    # Should have instruction to write action in discovery slot
    action = game.actions["Forest::HIDDEN_PATH"]
    prefix = game.metadata.get("entry_prefix", "A")
    assert any(
        "HIDDEN PATH" in inst and f"{prefix}-{action.ledger_id}" in inst and "discovery" in inst.lower()
        for inst in instructions
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actions.py::test_discoverable_action_instruction -v`
Expected: FAIL (no discovery instruction for actions)

- [ ] **Step 3: Write minimal implementation**

The discoverable action needs to be linked to its parent interaction. When the parser creates a discoverable action inside `_parse_inline_interaction`, we need to add a synthetic arrow to the parent interaction that tells the writer to generate a discovery instruction.

Approach: In the parser's `_parse_action`, when `discovered=True`, append a synthetic `Arrow` to the parent interaction via the `propagated_arrows` pattern. However, this is complex. A simpler approach: after parsing, in the writer, check if any action in the room is discovered and was declared inside the current interaction's arrows.

Actually, the cleanest approach: when `_parse_action` creates a discovered action inside an interaction, add the action reference to the parent interaction's arrows list as a sentinel. We can use a convention like `Arrow(">ACTION_NAME", "room", source_line)` — the `>` prefix marks it as an action discovery.

In `_parse_inline_interaction`, after the call to `_parse_action` with `discovered=True`, append a synthetic arrow:

```python
        elif _is_action(bstripped):
            action_name = bstripped[2:].strip()
            i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=current_indent)
            arrows.append(Arrow(f">{action_name}", "room", i))
```

In `_generate_instructions`, add handling for the `>` prefix sentinel before the normal `-> room` handling:

```python
            elif dest == "room" and subj.startswith(">"):
                # Action discovery: write action name and entry on room sheet
                action_name = subj[1:]
                action_key = f"{current_room}::{action_name}"
                action = self.game.actions.get(action_key)
                if action:
                    prefix = self.entry_prefix
                    instructions.append(
                        f"Write {dn(action_name)} ({prefix}-{action.ledger_id}) "
                        f"in a discovery slot on this room sheet."
                    )
```

Do the same in `_parse_entity_block` and `_parse_freeform_interactions` where `_parse_action` is called with `discovered=True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_discoverable_action_instruction -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/parser.py src/addventure/writer.py tests/test_actions.py
git commit -m "feat: generate discovery instructions for revealed actions"
```

---

### Task 12: Build summary and grammar updates

**Files:**
- Modify: `src/addventure/writer.py:295-312` (`print_build_summary`)
- Modify: `docs/grammar.ebnf`

- [ ] **Step 1: Update build summary to include action count**

In `src/addventure/writer.py`, in `print_build_summary`, add actions to the parts list:

```python
    # Count unique actions (deduped by ledger_id)
    action_count = len({a.ledger_id for a in game.actions.values()})
    parts = [
        p(len(game.verbs), "verbs"),
        p(len(game.rooms), "rooms"),
        p(len(game.nouns), "nouns"),
        p(len(game.items), "items"),
        p(len(game.resolved) + action_count, "entries"),
        p(len(game.cues), "cues"),
        p(len(game.actions), "actions"),
    ]
```

- [ ] **Step 2: Update EBNF grammar**

In `docs/grammar.ebnf`, add action syntax. In the room-level-line production:

```ebnf
room-level-line = room-interaction
                | room-arrow
                | entity-declaration
                | action-declaration ;

action-declaration = INDENT(n) , ">" , " " , ENTITY-NAME , newline ,
                     action-body(n) ;

action-body(n)  = { INDENT(>n) , narrative-line
                  | INDENT(>n) , "-" , " " , arrow-line } ;
```

Add a note that `>` can also appear nested inside interaction bodies to declare discoverable actions.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 4: Build example game**

Run: `uv run adv build --md`
Expected: Build succeeds with action count in summary

- [ ] **Step 5: Commit**

```bash
git add src/addventure/writer.py docs/grammar.ebnf
git commit -m "docs: update build summary and EBNF grammar for actions"
```

---

### Task 13: Integration test — full action game

**Files:**
- Test: `tests/test_actions.py`

- [ ] **Step 1: Write comprehensive integration test**

Add to `tests/test_actions.py`:

```python
def test_full_action_game():
    """End-to-end test: game with pre-printed actions, discoverable actions, and action removal."""
    global_src = """---
title: Action Test
start: Village
---
# Verbs
LOOK
USE

# Items
"""
    room_src = """# Village
LOOK: A quiet village.

> GO_NORTH
  You walk north to the forest.
  - player -> "Forest"

> GO_EAST
  You head east to the river.
  - player -> "River"

# Forest
LOOK: A dense forest.

> GO_SOUTH
  You return to the village.
  - player -> "Village"

OLD_TREE
+ LOOK: A massive oak tree.
+ USE:
  You push the tree aside revealing a hidden trail.
  - OLD_TREE -> trash
  > HIDDEN_TRAIL
    - player -> "Glade"

# River
LOOK: A rushing river.

> GO_WEST
  You head back to the village.
  - player -> "Village"

BRIDGE
+ LOOK: A rope bridge.
+ USE:
  The bridge snaps behind you!
  - GO_WEST -> trash
  - player -> "Island"

# Glade
LOOK: A peaceful glade.

# Island
LOOK: A small island.
"""
    game = compile_game(global_src, [room_src])

    # Check all actions parsed
    assert "Village::GO_NORTH" in game.actions
    assert "Village::GO_EAST" in game.actions
    assert "Forest::GO_SOUTH" in game.actions
    assert "Forest::HIDDEN_TRAIL" in game.actions
    assert "River::GO_WEST" in game.actions

    # Check pre-printed vs discovered
    assert game.actions["Village::GO_NORTH"].discovered is False
    assert game.actions["Forest::HIDDEN_TRAIL"].discovered is True

    # All actions have ledger IDs
    for action in game.actions.values():
        assert action.ledger_id > 0

    # Markdown output succeeds
    md, warnings = generate_markdown(game)
    assert "GO NORTH" in md
    assert "GO EAST" in md
    assert "GO SOUTH" in md
    assert "GO WEST" in md

    # Actions should NOT appear in the potentials list
    # (potentials are for sum-based lookups only)
    action_ledger_ids = {a.ledger_id for a in game.actions.values()}
    for ri in game.resolved:
        assert ri.entry_number not in action_ledger_ids or ri.verb == "ACTION"

    # Ledger entries exist for actions
    entry_prefix = game.metadata.get("entry_prefix", "A")
    for action in game.actions.values():
        assert f"{entry_prefix}-{action.ledger_id}" in md
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_actions.py::test_full_action_game -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_actions.py
git commit -m "test: comprehensive integration test for room actions"
```

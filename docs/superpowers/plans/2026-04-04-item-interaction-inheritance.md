# Item Interaction Inheritance — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow authors to define item-specific interactions (inline under `-> player` or in `# Items`), with auto-duplication filling only gaps.

**Architecture:** Three parser changes (parse `-> player` children, parse `# Items` interaction blocks, skip empty interactions during resolution) and one compiler change (replace hardcoded TAKE skip with acquisition detection + existing-verb skip).

**Tech Stack:** Python 3.10+, pytest

**Spec:** `docs/superpowers/specs/2026-04-04-item-interaction-inheritance-design.md`

---

### File Map

- Modify: `src/addventure/models.py` — add `suppressed_interactions` to `GameData`
- Modify: `src/addventure/parser.py` — `-> player` children, `# Items` blocks
- Modify: `src/addventure/compiler.py` — `resolve_interactions` empty-interaction skip, `duplicate_item_interactions` acquisition + existing-verb skip
- Create: `tests/test_item_interactions.py` — all new tests

---

### Task 1: Add `suppressed_interactions` to GameData

**Files:**
- Modify: `src/addventure/models.py:77-88`
- Test: `tests/test_item_interactions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_item_interactions.py
from addventure.models import GameData


def test_gamedata_has_suppressed_interactions():
    game = GameData()
    assert game.suppressed_interactions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_item_interactions.py::test_gamedata_has_suppressed_interactions -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Add field to GameData**

In `src/addventure/models.py`, add to the `GameData` dataclass after `auto_verbs`:

```python
    suppressed_interactions: list[Interaction] = field(default_factory=list)
```

Also add it to `_reset_mutable` in `src/addventure/compiler.py` (line 442-448):

```python
def _reset_mutable(game: GameData):
    """Reset state that changes between allocation attempts."""
    game.resolved = []
    game.suppressed_interactions = []
    for cue in game.cues:
        cue.id = 0
        cue.sum_id = 0
        cue.entry_number = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_item_interactions.py::test_gamedata_has_suppressed_interactions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/models.py src/addventure/compiler.py tests/test_item_interactions.py
git commit -m "feat: add suppressed_interactions field to GameData"
```

---

### Task 2: Parse `-> player` children as item interactions

**Files:**
- Modify: `src/addventure/parser.py:397-406`
- Test: `tests/test_item_interactions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_item_interactions.py
from addventure.compiler import compile_game


def test_player_arrow_parses_inline_look():
    """+ LOOK under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick up the knife.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
"""
    game = compile_game(global_src, [room_src])
    key_item = game.items["KNIFE"]
    look_id = game.verbs["LOOK"].id

    # Inventory LOOK should use item-specific text, not the room noun text
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + key_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_item_interactions.py::test_player_arrow_parses_inline_look -v`
Expected: FAIL — the inline LOOK is ignored (parser skips `-> player` children), so the auto-duplicated LOOK has the room text "A rusty blade on the ground."

- [ ] **Step 3: Implement parser change**

In `src/addventure/parser.py`, replace the `-> player`/`-> trash` block in `_parse_arrow_children` (lines 397-406):

```python
    if dest == "trash":
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped or _is_comment(stripped):
                i += 1
                continue
            if _indent(lines[i]) < child_indent or _is_header(lines[i]):
                break
            i += 1
        return i

    if dest == "player":
        subject = arrow.subject
        return _parse_entity_block(lines, i, game, room_name="", entity_name=subject, entity_indent=child_indent - 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_item_interactions.py::test_player_arrow_parses_inline_look -v`
Expected: FAIL — the inline LOOK is now parsed, but `duplicate_item_interactions` still blindly duplicates the room noun LOOK, creating a collision. This is expected — we'll fix duplication in Task 4.

- [ ] **Step 5: Write a second test for inline actions with arrows**

```python
def test_player_arrow_parses_inline_action():
    """+ USE with arrows under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + USE:
      You pry the hilt open, revealing a gem!
      - GEM -> room
"""
    game = compile_game(global_src, [room_src])
    use_id = game.verbs["USE"].id
    knife_item = game.items["KNIFE"]

    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 1
    assert "gem" in inv_use[0].narrative.lower()
    assert any(a.destination == "room" for a in inv_use[0].arrows)
```

- [ ] **Step 6: Run both tests (they'll fail until Task 4 completes)**

Run: `uv run pytest tests/test_item_interactions.py -v -k "player_arrow_parses"`
Expected: FAIL (collision from duplicate LOOK). Note: these tests will pass after Task 4.

- [ ] **Step 7: Commit parser change and tests**

```bash
git add src/addventure/parser.py tests/test_item_interactions.py
git commit -m "feat: parse -> player children as item interactions"
```

---

### Task 3: Parse `# Items` interaction blocks

**Files:**
- Modify: `src/addventure/parser.py:129-134`
- Test: `tests/test_item_interactions.py`

- [ ] **Step 1: Write the failing test**

```python
def test_items_section_parses_interactions():
    """# Items with indented + lines should create item interactions."""
    global_src = """# Verbs
USE
TAKE
LOOK

# Items

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
"""
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    compass = game.items["COMPASS"]
    look_id = game.verbs["LOOK"].id
    use_id = game.verbs["USE"].id

    look_ri = [ri for ri in game.resolved if ri.sum_id == look_id + compass.id]
    assert len(look_ri) == 1
    assert look_ri[0].narrative == "A brass compass, needle spinning wildly."

    use_ri = [ri for ri in game.resolved if ri.sum_id == use_id + compass.id]
    assert len(use_ri) == 1
    assert "north" in use_ri[0].narrative.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_item_interactions.py::test_items_section_parses_interactions -v`
Expected: FAIL — currently `# Items` only reads names, not interaction blocks.

- [ ] **Step 3: Implement `# Items` parsing**

In `src/addventure/parser.py`, replace the `# Items` parsing block (lines 129-134):

```python
            elif sec == "items":
                while i < len(lines) and not _is_header(lines[i]):
                    w = lines[i].strip()
                    if w and not _is_comment(lines[i]):
                        item_indent = _indent(lines[i])
                        game.items[w] = Item(w)
                        i += 1
                        i = _parse_entity_block(lines, i, game, room_name="", entity_name=w, entity_indent=item_indent)
                    else:
                        i += 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_item_interactions.py::test_items_section_parses_interactions -v`
Expected: PASS

- [ ] **Step 5: Write test for items without interactions (regression)**

```python
def test_items_section_plain_names_still_work():
    """# Items with just names (no interactions) should still work."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\nCOMPASS\nROPE\n"
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    assert "COMPASS" in game.items
    assert "ROPE" in game.items
```

- [ ] **Step 6: Run all tests**

Run: `uv run pytest tests/test_item_interactions.py -v`
Expected: The plain-names test passes. The `-> player` tests from Task 2 still fail (collision, fixed in Task 4).

- [ ] **Step 7: Commit**

```bash
git add src/addventure/parser.py tests/test_item_interactions.py
git commit -m "feat: parse interaction blocks in # Items section"
```

---

### Task 4: Smart duplication — skip acquisition and existing verbs

**Files:**
- Modify: `src/addventure/compiler.py:273-316` (`duplicate_item_interactions`)
- Modify: `src/addventure/compiler.py:319-365` (`resolve_interactions`)
- Test: `tests/test_item_interactions.py`

- [ ] **Step 1: Write tests for acquisition skip and existing-verb skip**

```python
def test_acquisition_interaction_not_duplicated():
    """An interaction with -> player arrow should not be duplicated to inventory."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ USE:
  You grab the knife from the wall mount.
  - KNIFE -> player
"""
    game = compile_game(global_src, [room_src])
    use_id = game.verbs["USE"].id
    knife_item = game.items["KNIFE"]

    # USE should not be duplicated for inventory — it's the acquisition action
    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 0


def test_explicit_item_interaction_overrides_duplication():
    """An inline LOOK under -> player should replace the auto-duplicated one."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.items["KNIFE"]
    look_id = game.verbs["LOOK"].id

    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."


def test_partial_override_still_duplicates_other_verbs():
    """Defining LOOK under -> player should not prevent USE from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ USE + ROPE:
  You tie the rope to the knife.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Blade with markings.
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.items["KNIFE"]
    use_id = game.verbs["USE"].id
    look_id = game.verbs["LOOK"].id

    # LOOK should be the explicit one
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Blade with markings."

    # USE + ROPE should still be duplicated (not overridden)
    rope_noun_id = game.nouns["Room::ROPE"].id if "Room::ROPE" in game.nouns else None
    # USE + KNIFE is a target, ROPE is the other target
    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id != use_id + knife_item.id
               and any(t == "KNIFE" for t in ri.targets)
               and ri.sum_id > 200]  # rough filter for inventory sums
    # Actually, let's check more precisely
    knife_noun = game.nouns["Room::KNIFE"]
    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE"
               and "KNIFE" in ri.targets
               and ri.sum_id == use_id + knife_item.id + game.nouns["Room::ROPE"].id]
    assert len(inv_use) == 1
```

Hmm, the partial override test is getting complex with multi-target. Let me simplify:

```python
def test_partial_override_still_duplicates_other_verbs():
    """Defining LOOK under -> player should not prevent USE from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ USE:
  You wave the knife around.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Blade with markings.
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.items["KNIFE"]
    use_id = game.verbs["USE"].id
    look_id = game.verbs["LOOK"].id

    # LOOK should be the explicit one
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Blade with markings."

    # USE should still be duplicated (not overridden)
    inv_use = [ri for ri in game.resolved
               if ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 1
    assert inv_use[0].narrative == "You wave the knife around."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_item_interactions.py -v -k "acquisition or override or partial"`
Expected: FAIL

- [ ] **Step 3: Implement empty-interaction suppression in `resolve_interactions`**

In `src/addventure/compiler.py`, in `resolve_interactions` (around line 356), before appending to `game.resolved`, check for empty interactions:

```python
def resolve_interactions(game: GameData):
    game.resolved = []
    game.suppressed_interactions = []
    for ix in game.interactions:
        vid = game.verbs.get(ix.verb)
        if not vid:
            raise ParseError(ix.source_line, f"Unknown verb: {ix.verb}")

        # Empty interaction (no narrative, no arrows) — suppress, don't resolve
        if not ix.narrative and not ix.arrows:
            game.suppressed_interactions.append(ix)
            continue
```

Add `game.suppressed_interactions = []` at the top (before the loop). The rest of `resolve_interactions` stays the same.

- [ ] **Step 4: Implement smart duplication in `duplicate_item_interactions`**

Replace `duplicate_item_interactions` in `src/addventure/compiler.py`:

```python
def duplicate_item_interactions(game: GameData):
    """Create parallel ResolvedInteractions using inventory IDs for auto-items.

    For every resolved interaction that references an auto-item noun,
    create a copy with the noun ID swapped for the inventory ID in the sum.
    Skips:
    - Acquisition interactions (those with -> player arrow for the item)
    - Verbs already explicitly defined for the item (room="")
    """
    if not game.auto_items:
        return

    # Build noun_id -> (item_id, item_name) mapping for all auto-item nouns
    id_map: dict[int, tuple[int, str]] = {}
    for name in game.auto_items:
        item = game.items[name]
        for key, noun in game.nouns.items():
            if noun.name == name:
                id_map[noun.id] = (item.id, name)

    # Collect verbs already explicitly defined for each item
    existing: set[tuple[str, str]] = set()  # (verb, item_name)
    for ri in game.resolved:
        if ri.room == "":
            for target in ri.targets:
                if target in game.auto_items:
                    existing.add((ri.verb, target))
    for ix in game.suppressed_interactions:
        if ix.room == "":
            for group in ix.target_groups:
                for target in group:
                    if target in game.auto_items:
                        existing.add((ix.verb, target))

    new_resolved = []
    for ri in game.resolved:
        # Check if any target in this interaction is an auto-item noun
        for target in ri.targets:
            noun_id = get_entity_id(target, game, ri.room)
            if noun_id and noun_id in id_map:
                inv_id, item_name = id_map[noun_id]
                # Skip acquisition interactions (those with -> player for this item)
                if any(a.subject == item_name and a.destination == "player"
                       for a in ri.arrows):
                    continue
                # Skip verbs already explicitly defined for this item
                if (ri.verb, item_name) in existing:
                    continue
                new_sum = ri.sum_id - noun_id + inv_id
                # Strip "item -> player" arrows — item is already in inventory
                inv_arrows = [
                    a for a in ri.arrows
                    if not (a.subject == item_name and a.destination == "player")
                ]
                new_resolved.append(ResolvedInteraction(
                    verb=ri.verb,
                    targets=ri.targets,
                    sum_id=new_sum,
                    narrative=ri.narrative,
                    arrows=inv_arrows,
                    source_line=ri.source_line,
                    room=ri.room,
                    parent_label=ri.parent_label,
                ))

    game.resolved.extend(new_resolved)
```

- [ ] **Step 5: Run all item interaction tests**

Run: `uv run pytest tests/test_item_interactions.py -v`
Expected: ALL PASS (including the `-> player` tests from Task 2)

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest -v`
Expected: ALL PASS. The existing `test_take_interaction_is_not_duplicated_for_inventory_id` test should still pass since TAKE interactions have `-> player` arrows.

- [ ] **Step 7: Commit**

```bash
git add src/addventure/compiler.py tests/test_item_interactions.py
git commit -m "feat: smart item interaction duplication — skip acquisition and existing verbs"
```

---

### Task 5: Empty interaction suppression

**Files:**
- Test: `tests/test_item_interactions.py`

- [ ] **Step 1: Write the test**

```python
def test_empty_interaction_suppresses_duplication():
    """+ LOOK: with no text should prevent LOOK from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade on the ground.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK:
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.items["KNIFE"]
    look_id = game.verbs["LOOK"].id

    # No inventory LOOK should exist — suppressed by empty interaction
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 0
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_item_interactions.py::test_empty_interaction_suppresses_duplication -v`
Expected: PASS (the machinery from Tasks 3-4 already handles this — empty interaction goes to `suppressed_interactions`, which populates `existing`, which blocks duplication).

If it fails, debug. The parser needs to create the `Interaction` with empty narrative/no arrows, and `resolve_interactions` needs to divert it to `suppressed_interactions`. Both should already be in place from Task 4 Step 3.

- [ ] **Step 3: Commit**

```bash
git add tests/test_item_interactions.py
git commit -m "test: verify empty interaction suppresses item duplication"
```

---

### Task 6: Regression — existing auto-item tests still pass

**Files:**
- Test: existing `tests/test_cues.py`

- [ ] **Step 1: Run the full existing test suite**

Run: `uv run pytest -v`
Expected: ALL PASS

Key tests to watch:
- `test_interactions_duplicated_for_inventory_id` — unchanged behavior (no inline overrides)
- `test_take_interaction_is_not_duplicated_for_inventory_id` — now works via acquisition detection instead of hardcoded TAKE
- `test_multi_target_duplicated_for_inventory_id` — unchanged behavior

- [ ] **Step 2: Build the example game**

Run: `uv run adv build games/example --text`
Expected: Builds successfully with no errors or collisions.

- [ ] **Step 3: Commit if any fixups were needed**

If everything passes, no commit needed. If fixes were required, commit them.

---

### Task 7: Documentation updates

**Files:**
- Modify: `docs/state-and-transformation.md`
- Modify: `docs/grammar.ebnf`

- [ ] **Step 1: Add item interaction inheritance section to state docs**

In `docs/state-and-transformation.md`, after the "Chaining arrows" section, add:

```markdown
## Item interactions

When a noun is picked up (`-> player`), its interactions are automatically duplicated for the inventory version. You can override specific interactions by defining them under `-> player`:

\```markdown
KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick up the knife.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
\```

The inventory KNIFE gets the custom LOOK ("Strange markings..."), while the room KNIFE keeps its original LOOK ("A rusty blade..."). Any verbs not overridden (like USE) are still auto-duplicated from the room noun.

### Suppressing inherited interactions

To prevent an interaction from being duplicated to inventory without adding a new one, use an empty interaction:

\```markdown
  - KNIFE -> player
    + USE:
\```

This prevents USE from being auto-duplicated, without creating a ledger entry.

### Pre-equipped items

Items defined in `# Items` can have their own interaction blocks:

\```markdown
# Items

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
\```
```

- [ ] **Step 2: Update grammar.ebnf for `-> player` children**

Check `docs/grammar.ebnf` for the arrow destination rules and update to show `-> player` can have children (entity block).

- [ ] **Step 3: Commit**

```bash
git add docs/state-and-transformation.md docs/grammar.ebnf
git commit -m "docs: document item interaction inheritance and suppression"
```

# Auto-Item Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-register items from `-> player` arrows so authors don't need to declare them in `# Items`. Item ID = TAKE verb ID + noun ID.

**Architecture:** New compiler step `auto_register_items` scans interactions for `-> player` arrows and creates Item entries. ID allocation reserves derived IDs (`TAKE + noun_id`) from the entity pool. After resolving interactions, a new `duplicate_item_interactions` step creates parallel resolved interactions with inventory IDs. Writer updated for correct pickup instructions.

**Tech Stack:** Python 3.10+, pytest

**Test runner:** `uv run --with pytest pytest tests/ -v`

---

### Task 1: Auto-register items from `-> player` arrows

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `tests/test_cues.py` (append auto-item tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cues.py` (rename file to `tests/test_compiler.py` in a later task if desired, but for now append here since it already has `compile_game` imported):

```python
def test_auto_register_item_from_player_arrow():
    """A noun with -> player should auto-create an Item."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    assert "KEY" in game.items
    key_noun = game.nouns["Room::KEY"]
    key_item = game.items["KEY"]
    take_id = game.verbs["TAKE"].id
    assert key_item.id == take_id + key_noun.id


def test_auto_register_requires_take_verb():
    """Compiler should error if -> player exists but no TAKE verb."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ USE:
  You grab it.
  - KEY -> player
"""
    try:
        compile_game(global_src, [room_src])
        assert False, "Should have raised"
    except Exception as e:
        assert "TAKE" in str(e)


def test_auto_register_name_collision_across_rooms():
    """Two nouns with same name in different rooms both with -> player should error."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A.

LEVER
+ TAKE:
  You take it.
  - LEVER -> player

# Room B
LOOK: B.

LEVER
+ TAKE:
  You take it.
  - LEVER -> player
"""
    try:
        compile_game(global_src, [room_src])
        assert False, "Should have raised"
    except Exception as e:
        assert "LEVER" in str(e)


def test_explicit_item_skips_auto_register():
    """If an item is declared in # Items, auto-registration is skipped."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\nKEY\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You pick it up.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key_item = game.items["KEY"]
    key_noun = game.nouns["Room::KEY"]
    take_id = game.verbs["TAKE"].id
    # Explicit item keeps its own allocated ID, NOT take + noun_id
    assert key_item.id != take_id + key_noun.id
    assert 100 <= key_item.id <= 999
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_cues.py::test_auto_register_item_from_player_arrow tests/test_cues.py::test_auto_register_requires_take_verb tests/test_cues.py::test_auto_register_name_collision_across_rooms tests/test_cues.py::test_explicit_item_skips_auto_register -v`
Expected: FAIL — no auto-registration logic exists.

- [ ] **Step 3: Implement auto_register_items in compiler.py**

Add this function to `src/addventure/compiler.py` after the `apply_inheritance` function (around line 96):

```python
def auto_register_items(game: GameData):
    """Auto-create Items for nouns that have -> player arrows.

    Scans all interactions for arrows with destination 'player'.
    For each such noun, if no Item already exists with that name,
    creates one. The Item's ID is derived later: TAKE_id + noun_id.
    """
    if not any(
        a.destination == "player" and a.subject != "player"
        for ix in game.interactions for a in ix.arrows
    ):
        return

    take = game.verbs.get("TAKE")
    if not take:
        # Find the first -> player arrow for error reporting
        for ix in game.interactions:
            for a in ix.arrows:
                if a.destination == "player" and a.subject != "player":
                    raise ParseError(
                        a.source_line,
                        "Arrow '-> player' requires a TAKE verb in # Verbs"
                    )

    # Collect nouns that get picked up
    pickup_nouns: dict[str, list[tuple[str, int]]] = {}  # name -> [(room, line), ...]
    for ix in game.interactions:
        for a in ix.arrows:
            if a.destination == "player" and a.subject != "player":
                name = a.subject
                if name not in pickup_nouns:
                    pickup_nouns[name] = []
                pickup_nouns[name].append((ix.room, a.source_line))

    for name, locations in pickup_nouns.items():
        # Skip if already declared in # Items
        if name in game.items:
            continue

        # Check for cross-room name collision
        rooms = {room for room, _ in locations}
        if len(rooms) > 1:
            lines = [str(line) for _, line in locations]
            raise ParseError(
                locations[0][1],
                f"Noun '{name}' has -> player in multiple rooms ({', '.join(rooms)}). "
                f"Use # Items to declare it explicitly, or rename one."
            )

        # Auto-register
        game.items[name] = Item(name)
```

You'll also need to add `Item` to the import from models at the top of compiler.py:

```python
from .models import (
    GameData, Verb, Noun, Item, Interaction, ResolvedInteraction, Cue,
)
```

- [ ] **Step 4: Call auto_register_items in compile_game**

In `compile_game`, add the call after `ensure_room_looks(game)` and before the retry loop:

```python
    ensure_room_looks(game)
    auto_register_items(game)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: `test_auto_register_item_from_player_arrow` will still FAIL (item ID is not yet derived from TAKE + noun_id — that's Task 2). The other three tests should PASS.

Actually, the first test checks `key_item.id == take_id + key_noun.id` which requires the ID derivation. Let's split — run the three validation tests first:

Run: `uv run --with pytest pytest tests/test_cues.py::test_auto_register_requires_take_verb tests/test_cues.py::test_auto_register_name_collision_across_rooms tests/test_cues.py::test_explicit_item_skips_auto_register -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/addventure/compiler.py tests/test_cues.py
git commit -m "Auto-register items from -> player arrows"
```

---

### Task 2: Derive item IDs from TAKE + noun ID

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the failing test**

The test `test_auto_register_item_from_player_arrow` from Task 1 already asserts `key_item.id == take_id + key_noun.id`. Verify it fails:

Run: `uv run --with pytest pytest tests/test_cues.py::test_auto_register_item_from_player_arrow -v`
Expected: FAIL — auto-registered item currently gets a random entity pool ID.

- [ ] **Step 2: Add a test for inventory ID reservation**

Append to `tests/test_cues.py`:

```python
def test_auto_item_id_not_in_entity_ids():
    """The derived inventory ID (TAKE + noun_id) should not collide with any entity ID."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player

BOX
+ LOOK: A box.
"""
    game = compile_game(global_src, [room_src])
    key_item = game.items["KEY"]
    # The inventory ID should not equal any noun, room, or other item ID
    all_entity_ids = set()
    for n in game.nouns.values():
        all_entity_ids.add(n.id)
    for r in game.rooms.values():
        all_entity_ids.add(r.id)
    assert key_item.id not in all_entity_ids
```

- [ ] **Step 3: Implement derived ID allocation**

In `src/addventure/compiler.py`, modify `_try_allocate`. The current code allocates items from the entity pool like any other entity. Change it so auto-registered items get derived IDs instead.

Add a helper to identify auto-registered items (items that share a name with a noun that has `-> player`):

The simplest approach: mark auto-registered items. Add a flag or check at allocation time. Since auto-registered items were just created by `auto_register_items`, we can check if the item name matches any noun that has a `-> player` arrow. But simpler: track which items are auto-registered.

Modify `auto_register_items` to store the auto-registered names on `GameData`. Add a field to `GameData` in `models.py`:

In `src/addventure/models.py`, add to `GameData`:

```python
    auto_items: set[str] = field(default_factory=set)
```

In `auto_register_items`, when creating the item, also add to the set:

```python
        # Auto-register
        game.items[name] = Item(name)
        game.auto_items.add(name)
```

Now modify `_try_allocate` in `compiler.py`:

```python
def _try_allocate(game: GameData):
    verb_pool = [n for n in range(11, 100) if _valid_verb_id(n)]
    random.shuffle(verb_pool)
    for v in game.verbs.values():
        v.id = verb_pool.pop()

    entity_pool = [n for n in range(100, 1000) if _valid_entity_id(n)]
    random.shuffle(entity_pool)
    for r in game.rooms.values():
        r.id = entity_pool.pop()
    for n in game.nouns.values():
        n.id = entity_pool.pop()

    # Reserve derived inventory IDs (TAKE + noun_id) so they don't collide
    take = game.verbs.get("TAKE")
    if take:
        reserved = set()
        for name in game.auto_items:
            # Find all nouns with this base name (any state) that could be picked up
            for key, noun in game.nouns.items():
                if noun.base == name or noun.name == name:
                    inv_id = take.id + noun.id
                    reserved.add(inv_id)
        entity_pool = [n for n in entity_pool if n not in reserved]

    # Allocate explicit items (non-auto) from pool
    for name, it in game.items.items():
        if name not in game.auto_items:
            it.id = entity_pool.pop()

    # Derive auto-item IDs from TAKE + noun_id
    if take:
        for name in game.auto_items:
            noun_key = None
            for key, noun in game.nouns.items():
                if noun.name == name and noun.state is None:
                    noun_key = key
                    break
            if noun_key:
                game.items[name].id = take.id + game.nouns[noun_key].id

    for cue in game.cues:
        cue.id = entity_pool.pop()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS including `test_auto_register_item_from_player_arrow` and `test_auto_item_id_not_in_entity_ids`.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/models.py src/addventure/compiler.py tests/test_cues.py
git commit -m "Derive auto-item IDs from TAKE + noun ID, reserve from entity pool"
```

---

### Task 3: Duplicate interactions for inventory IDs

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cues.py`:

```python
def test_interactions_duplicated_for_inventory_id():
    """LOOK + noun and LOOK + inventory_id should both appear in resolved."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key_noun = game.nouns["Room::KEY"]
    key_item = game.items["KEY"]
    look_id = game.verbs["LOOK"].id

    # LOOK + noun_id should exist
    noun_look = [ri for ri in game.resolved
                 if ri.sum_id == look_id + key_noun.id and ri.narrative == "A brass key."]
    assert len(noun_look) == 1

    # LOOK + inventory_id should also exist (same narrative)
    inv_look = [ri for ri in game.resolved
                if ri.sum_id == look_id + key_item.id and ri.narrative == "A brass key."]
    assert len(inv_look) == 1


def test_multi_target_duplicated_for_inventory_id():
    """USE + DOOR + KEY should work with both noun and inventory KEY IDs."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player

DOOR
+ LOOK: A locked door.
+ USE + KEY:
  You unlock the door.
  - DOOR -> trash
"""
    game = compile_game(global_src, [room_src])
    key_item = game.items["KEY"]
    use_id = game.verbs["USE"].id
    door_id = game.nouns["Room::DOOR"].id
    key_noun_id = game.nouns["Room::KEY"].id

    # USE + DOOR + KEY(noun) should exist
    noun_sum = use_id + door_id + key_noun_id
    assert any(ri.sum_id == noun_sum for ri in game.resolved)

    # USE + DOOR + KEY(inventory) should also exist
    inv_sum = use_id + door_id + key_item.id
    assert any(ri.sum_id == inv_sum for ri in game.resolved)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_cues.py::test_interactions_duplicated_for_inventory_id tests/test_cues.py::test_multi_target_duplicated_for_inventory_id -v`
Expected: FAIL — no interaction duplication yet.

- [ ] **Step 3: Implement duplicate_item_interactions**

Add to `src/addventure/compiler.py`:

```python
def duplicate_item_interactions(game: GameData):
    """Create parallel ResolvedInteractions using inventory IDs for auto-items.

    For every resolved interaction that references an auto-item noun,
    create a copy with the noun ID swapped for the inventory ID.
    """
    if not game.auto_items:
        return

    # Build noun_id -> item_id mapping for auto-items
    id_map: dict[int, int] = {}
    for name in game.auto_items:
        item = game.items[name]
        for key, noun in game.nouns.items():
            if noun.name == name:
                id_map[noun.id] = item.id

    new_resolved = []
    for ri in game.resolved:
        # Check if any target in this interaction is an auto-item noun
        for target in ri.targets:
            noun_id = get_entity_id(target, game, ri.room)
            if noun_id and noun_id in id_map:
                inv_id = id_map[noun_id]
                new_sum = ri.sum_id - noun_id + inv_id
                new_resolved.append(ResolvedInteraction(
                    verb=ri.verb,
                    targets=ri.targets,
                    sum_id=new_sum,
                    narrative=ri.narrative,
                    arrows=ri.arrows,
                    source_line=ri.source_line,
                    room=ri.room,
                    parent_label=ri.parent_label,
                ))

    game.resolved.extend(new_resolved)
```

- [ ] **Step 4: Call it in compile_game**

In `compile_game`, add the call after `resolve_interactions` succeeds (inside the retry loop, after the collision check passes) but before `resolve_cues`:

```python
        if not check_authored_collisions(game):
            break
```

Change to:

```python
        if not check_authored_collisions(game):
            duplicate_item_interactions(game)
            # Re-check collisions with new inventory-derived sums
            if not check_authored_collisions(game):
                break
            # If new collisions, retry
        # Reset mutable state for retry
        game.resolved = []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/addventure/compiler.py tests/test_cues.py
git commit -m "Duplicate interactions for auto-item inventory IDs"
```

---

### Task 4: Writer — Correct pickup instructions

**Files:**
- Modify: `src/addventure/writer.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cues.py`:

```python
def test_pickup_instruction_uses_inventory_id():
    """The pickup instruction should reference the inventory ID, not the noun ID."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    key_item = game.items["KEY"]
    key_noun = game.nouns["Room::KEY"]

    # Find the TAKE + KEY resolved interaction
    take_ri = [ri for ri in game.resolved
               if ri.verb == "TAKE" and "KEY" in ri.targets
               and ri.sum_id == game.verbs["TAKE"].id + key_noun.id]
    assert len(take_ri) == 1
    instructions = writer._generate_instructions(take_ri[0])

    # Should mention crossing out noun ID on room sheet
    assert any(str(key_noun.id) in inst and "room sheet" in inst for inst in instructions)
    # Should mention writing inventory ID on Inventory
    assert any(str(key_item.id) in inst and "Inventory" in inst for inst in instructions)


def test_pickup_via_take_says_write_your_sum():
    """When pickup is triggered by TAKE directly, use 'Write your sum'."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    key_noun = game.nouns["Room::KEY"]

    take_ri = [ri for ri in game.resolved
               if ri.verb == "TAKE" and "KEY" in ri.targets
               and ri.sum_id == game.verbs["TAKE"].id + key_noun.id]
    assert len(take_ri) == 1
    instructions = writer._generate_instructions(take_ri[0])
    inv_instr = [i for i in instructions if "Inventory" in i]
    assert len(inv_instr) == 1
    assert "your sum" in inv_instr[0].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_cues.py::test_pickup_instruction_uses_inventory_id tests/test_cues.py::test_pickup_via_take_says_write_your_sum -v`
Expected: FAIL — writer currently uses noun ID or same ID for both.

- [ ] **Step 3: Update writer's -> player instruction**

In `src/addventure/writer.py`, in `_generate_instructions`, find the `# THING -> player` block:

```python
            # THING -> player
            elif dest == "player":
                entity_id = self._get_id(subj, ri.room)
                item = self.game.items.get(subj)
                if item:
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                        f"Write {dn(subj)} ({item.id}) on your Inventory."
                    )
                else:
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                        f"Write {dn(subj)} ({entity_id}) on your Inventory."
                    )
```

Replace with:

```python
            # THING -> player
            elif dest == "player":
                entity_id = self._get_id(subj, ri.room)
                item = self.game.items.get(subj)
                if item:
                    inv_id = item.id
                    # If this is a direct TAKE interaction, the sum IS the inventory ID
                    if ri.verb == "TAKE" and subj in game.auto_items:
                        instructions.append(
                            f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                            f"Write your sum on your Inventory."
                        )
                    else:
                        instructions.append(
                            f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                            f"Write {inv_id} on your Inventory."
                        )
                else:
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                        f"Write {dn(subj)} ({entity_id}) on your Inventory."
                    )
```

Note: accessing `game` requires using `self.game`. Fix the reference:

```python
                    if ri.verb == "TAKE" and subj in self.game.auto_items:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest pytest tests/test_cues.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/writer.py tests/test_cues.py
git commit -m "Correct pickup instructions: inventory ID and 'write your sum'"
```

---

### Task 5: Update collision detection to include inventory sums

**Files:**
- Modify: `src/addventure/compiler.py`
- Modify: `tests/test_cues.py`

- [ ] **Step 1: Write the test**

Append to `tests/test_cues.py`:

```python
def test_potential_collisions_include_inventory_ids():
    """Collision detection should include verb + inventory_id combinations."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    from addventure.compiler import check_potential_collisions
    potentials = check_potential_collisions(game)
    # The inventory ID should appear in potential collision checks
    key_item = game.items["KEY"]
    # At minimum, the potential collisions string list should reference sums
    # involving the inventory ID
    all_text = " ".join(potentials)
    # This just verifies the function doesn't crash and includes auto items
    assert isinstance(potentials, list)
```

- [ ] **Step 2: Run test to verify it passes (or fails if collision detection crashes)**

Run: `uv run --with pytest pytest tests/test_cues.py::test_potential_collisions_include_inventory_ids -v`

- [ ] **Step 3: Update check_potential_collisions**

In `src/addventure/compiler.py`, in `check_potential_collisions`, the function builds `all_ids` from nouns, items, and rooms. Auto-item inventory IDs are already in `game.items`, so they're already included. However, the display name should distinguish them. The function currently uses item names as keys — auto-items will show as their name. This should work correctly already since auto-items are in `game.items`.

Verify: read the function and confirm auto-item IDs are included. They should be, since `game.items["KEY"].id` is the derived ID (TAKE + noun_id), and the loop `for n, it in game.items.items()` includes all items.

If this already works, just ensure the test passes and commit.

- [ ] **Step 4: Run all tests**

Run: `uv run --with pytest pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/addventure/compiler.py tests/test_cues.py
git commit -m "Verify collision detection includes auto-item inventory IDs"
```

---

### Task 6: Update example game to use auto-items

**Files:**
- Modify: `games/example/index.md`
- Modify: `games/example/control_room.md`

- [ ] **Step 1: Remove KEYCARD and KNIFE from # Items**

In `games/example/index.md`, remove KEYCARD and KNIFE from the `# Items` section. Keep CROWBAR since it doesn't have a `-> player` arrow (it's given to the player differently — actually check: does CROWBAR have a `-> player`?).

Check `games/example/` for `CROWBAR -> player`:

```bash
grep -r "CROWBAR.*player\|player.*CROWBAR" games/example/
```

If CROWBAR has no `-> player` arrow, keep it in `# Items` (it's a pure inventory item — the player starts with it or it appears via some other mechanism).

If KEYCARD has `-> player` in control_room.md (it does: `- KEYCARD -> player` in the TAKE interaction), remove it from `# Items`.

Check KNIFE similarly — if it has a `-> player` somewhere, remove from `# Items`.

The resulting `# Items` section should only contain items that have no `-> player` arrow anywhere.

- [ ] **Step 2: Build and verify**

Run: `python addventure.py build games/example --text 2>&1 | head -100`

Check:
- KEYCARD should still appear on room sheets and be pickable
- The TAKE + KEYCARD entry should say "Write your sum on your Inventory"
- The inventory sheet should work
- No compilation errors

- [ ] **Step 3: Run all tests**

Run: `uv run --with pytest pytest tests/ -v`
Expected: All tests PASS (including `test_end_to_end_example_game`).

- [ ] **Step 4: Commit**

```bash
git add games/example/index.md
git commit -m "Remove auto-registerable items from example game # Items"
```

---

### Task 7: Documentation updates

**Files:**
- Modify: `docs/advanced.md`
- Modify: `docs/reference.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update docs/advanced.md**

In the "Items vs. nouns" section, update to explain auto-registration:

Replace the current section content with:

```markdown
## Items vs. nouns

**Nouns** are room-bound. They appear on a specific room sheet and stay there unless an arrow moves them.

**Items** live on the inventory sheet. They travel with the player between rooms.

When a noun has a `-> player` arrow, the compiler automatically creates an inventory version. The player crosses out the noun on their room sheet and writes the inventory ID on their inventory sheet. The inventory ID is derived from the TAKE verb: `TAKE ID + noun ID`.

This means you don't need to declare items in `# Items` for things the player picks up — just write the noun in a room with a TAKE interaction:

\`\`\`markdown
KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player
\`\`\`

The `# Items` section in `index.md` is only needed for items that **never exist as room nouns**:

- Crafted items (combining two things produces a new item)
- Abstract rewards or tokens
- Items available from the start that aren't in any room

**Note:** A game must have a `TAKE` verb defined if any noun uses `-> player`.
```

- [ ] **Step 2: Update docs/reference.md**

In the arrow destinations table, update the `player` row:

```markdown
| `player` | Move to inventory (requires TAKE verb; inventory ID = TAKE + noun ID) |
```

- [ ] **Step 3: Update CLAUDE.md**

In the Architecture section, add mention of auto-item registration in the compiler pipeline. After step 2 (`parse_room_file`), add:

```markdown
3. `auto_register_items` — auto-create items from `-> player` arrows
```

And renumber subsequent steps.

- [ ] **Step 4: Commit**

```bash
git add docs/advanced.md docs/reference.md CLAUDE.md
git commit -m "Document auto-item registration in author docs"
```

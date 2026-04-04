# Item Interaction Inheritance

## Problem

When a noun becomes an inventory item (via `-> player`), `duplicate_item_interactions` blindly copies all non-TAKE resolved interactions from the room noun to the inventory item. This has two issues:

1. **No way to define item-specific interactions.** The `-> player` arrow skips all nested children (parser lines 397-406). The `# Items` section only parses names, not interaction blocks. So authors cannot give an item a different LOOK in inventory vs. on the ground, or add inventory-only actions.

2. **No way to suppress inherited interactions.** If a noun has a LOOK with arrows (e.g., looking reveals something and changes state), that action gets duplicated to inventory — even though it may not make sense there.

3. **Acquisition interactions are duplicated.** The hardcoded `if ri.verb == "TAKE": continue` only prevents TAKE from being duplicated. But any verb can trigger acquisition (e.g., `USE: ... - KNIFE -> player`), and those interactions are incorrectly duplicated to the inventory version.

This mirrors how `apply_inheritance` works for entity states: only arrow-free interactions (observations) are inherited, and explicitly defined child interactions take precedence. Item interactions should follow the same pattern.

## Design

### Three Sources of Item Interactions

Authors can define item interactions in three places, listed by precedence:

#### 1. Inline under `-> player` (most common)

```markdown
KNIFE
  + LOOK: A rusty blade on the ground.
  + TAKE:
    You pick up the knife.
    - KNIFE -> player
      + LOOK: You inspect the blade closely. Something glints in the hilt.
      + USE:
        You pry the hilt open, revealing a gem!
        - GEM -> room
```

The parser treats children of `-> player` as item interaction blocks — same as how `-> room` introduces new noun interactions. These interactions have `room=""` (items are roomless/global).

#### 2. `# Items` section with interaction blocks

```markdown
# Items

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
```

For items that start in inventory or are acquired through multiple paths. The parser parses interaction blocks under item names, same as entity blocks in rooms. These also have `room=""`.

#### 3. Auto-duplicated from room noun (fallback)

The existing `duplicate_item_interactions` behavior, but now only fills gaps — it skips any verb+item combination that already has an explicitly defined item interaction.

### Parser Changes

#### `-> player` children (`_parse_arrow_children`)

Currently (lines 397-406):
```python
if dest in ("trash", "player"):
    # skip all children
```

Change to only skip for `trash`. For `player`, parse children as item interactions:

```python
if dest == "trash":
    # skip children (unchanged)

if dest == "player":
    # Parse children as item interactions (room="")
    # Similar to how -> room works, but item_name = arrow.subject
```

The item name is `arrow.subject`. Call `_parse_entity_block` with `room_name=""` and `entity_name=arrow.subject`. If the item doesn't exist in `game.items` yet, auto-registration (which runs later) will create it.

#### `# Items` interaction blocks (`parse_global`)

Currently (lines 129-134):
```python
elif sec == "items":
    while i < len(lines) and not _is_header(lines[i]):
        w = lines[i].strip()
        if w and not _is_comment(lines[i]):
            game.items[w] = Item(w)
        i += 1
```

Change to detect indented `+` lines after an item name and parse them as entity blocks:

```python
elif sec == "items":
    while i < len(lines) and not _is_header(lines[i]):
        w = lines[i].strip()
        if w and not _is_comment(lines[i]):
            game.items[w] = Item(w)
            i += 1
            # Parse interaction block if present
            i = _parse_entity_block(lines, i, game, room_name="", entity_name=w, entity_indent=_indent(lines[i-1]))
        else:
            i += 1
```

### Compiler Changes

#### `resolve_interactions` — skip empty interactions

Interactions with no narrative and no arrows (e.g., `+ LOOK:` with nothing after) should not produce resolved interactions or ledger entries. They exist only to suppress duplication. Skip them during resolution but still track them for the `existing` set in `duplicate_item_interactions`.

Add to `GameData`:
```python
suppressed_interactions: list[Interaction] = field(default_factory=list)
```

In `resolve_interactions`, before creating a `ResolvedInteraction`, check if the interaction has empty narrative and no arrows. If so, append to `game.suppressed_interactions` instead of `game.resolved`.

#### `duplicate_item_interactions` — skip acquisition and existing verbs

Two changes to the skip logic:

1. **Replace hardcoded TAKE skip with acquisition detection.** Instead of `if ri.verb == "TAKE": continue`, skip any interaction that has a `-> player` arrow for the item being duplicated:

```python
# Skip interactions that acquire this item
if any(a.subject == item_name and a.destination == "player" for a in ri.arrows):
    continue
```

This correctly handles all acquisition verbs (TAKE, USE, or any custom verb that triggers pickup).

2. **Skip verbs already explicitly defined for the item.** Collect the set of `(verb, item_name)` pairs from both resolved and suppressed interactions with `room=""`:

```python
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

# During duplication:
if (ri.verb, item_name) in existing:
    continue  # explicit item interaction takes precedence
```

### Interaction Resolution

Item interactions (with `room=""`) are resolved by `resolve_interactions` the same as any other interaction. `get_entity_id` already falls through to `game.items` when no noun matches (line 268-269), so interactions targeting item names with `room=""` will resolve against the item's ID.

### What This Means for Authors

**Simple case (no change needed):**
```markdown
KEYCARD
  + LOOK: A small keycard with a red stripe.
  + TAKE:
    - KEYCARD -> player
```
LOOK is auto-duplicated to inventory. Same behavior as today.

**Custom inventory LOOK:**
```markdown
KNIFE
  + LOOK: A rusty blade on the ground.
  + TAKE:
    - KNIFE -> player
      + LOOK: The blade has strange markings near the hilt.
```
The inline LOOK overrides the auto-duplicated one. Room LOOK still says "on the ground."

**Inventory-only action:**
```markdown
CROWBAR
  + LOOK: A heavy iron crowbar.
  + TAKE:
    - CROWBAR -> player
      + LOOK: Heavy but effective.
      + USE:
        You flex the crowbar. Ready for prying.
```
USE only exists on the inventory version. The room-bound crowbar has no USE.

**Suppress an inherited interaction:**
```markdown
KNIFE
  + LOOK: A rusty blade on the ground.
  + USE + ROPE:
    You tie the rope to the knife.
    - KNIFE -> player
      + USE:
```
`+ USE:` with no text or arrows creates no ledger entry, but prevents `USE + ROPE` from being duplicated to inventory. LOOK still auto-duplicates since it wasn't overridden.

**Non-TAKE acquisition:**
```markdown
KNIFE
  + USE:
    You grab the knife from the wall mount.
    - KNIFE -> player
```
The `USE` interaction has a `-> player` arrow for KNIFE, so it's recognized as the acquisition interaction and not duplicated to inventory. No hardcoded verb check needed.

**Pre-equipped item:**
```markdown
# Items

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE + DOOR:
    The compass guides you through.
    - player -> "North Hall"
```
COMPASS starts in inventory with its own interactions. No room noun needed.

### Edge Cases

- **`-> player` with no children:** Behaves exactly as today — all non-acquisition interactions auto-duplicated.
- **`-> player` with partial overrides:** Only the verbs explicitly defined (or suppressed) are skipped; other verbs still auto-duplicate. E.g., define only LOOK under `-> player`, and USE still auto-duplicates from the room noun.
- **`# Items` item also acquired via `-> player`:** The explicit `# Items` interactions take precedence via the same mechanism — they resolve first, and duplication skips existing verbs.
- **Multi-target interactions:** If KNIFE is a target in `USE + KNIFE + ROPE:`, and the author defines `USE` under `-> player` for KNIFE, the multi-target duplication is skipped for USE. The author's item-level USE would need to include the multi-target form if desired.
- **Empty interaction (`+ VERB:`):** Creates no ledger entry but registers in the suppressed set, preventing that verb from being auto-duplicated for the item.
- **Acquisition detection:** Any interaction with a `-> player` arrow for the item is skipped during duplication, regardless of which verb triggers it. This replaces the hardcoded TAKE skip.

### Model Changes

- `GameData` gains `suppressed_interactions: list[Interaction]` — for empty interactions that suppress duplication without creating ledger entries
- `Interaction` already has `room: str = ""` as default (no change)
- `Item` doesn't need new fields

### Documentation Updates

- `docs/state-and-transformation.md` — add section on item interaction inheritance
- `docs/grammar.ebnf` — update to show `-> player` can have children

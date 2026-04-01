# Auto-Item Registration

## Problem

Items and nouns have a confusing split. Nouns are room-bound with states and interactions. Items are global (inventory) but have no state, no interactions of their own, and must be pre-declared in `# Items`. When a noun is picked up (`-> player`), the system awkwardly bridges these two concepts — sometimes using the wrong sheet in instructions, and requiring authors to declare items they shouldn't need to think about.

Authors currently must declare a KEYCARD in both `# Items` (for the inventory version) and as a noun in a room (for the room version). The IDs differ but the relationship is implicit.

## Design

### Core Mechanic

When the compiler sees `NOUN -> player` on any noun, it **auto-registers an item** for that noun. The item ID is derived from the noun ID using the TAKE verb:

```
inventory_id = TAKE_verb_id + noun_id
```

The player already computes `TAKE + NOUN` to trigger the pickup. The sum they computed IS the number they write on their inventory sheet. No extra arithmetic for the transfer.

For pickups triggered by other verbs (e.g., `USE + CRATE + CROWBAR` where `KEYCARD -> player` is an arrow), the inventory ID is still `TAKE_id + noun_id` — the ledger explicitly tells the player the number to write.

### What Changes for Authors

**Before:** Must declare items in `# Items` AND as nouns in rooms.

**After:** Just write nouns in rooms. `-> player` handles everything. `# Items` is only for things that never exist as room nouns (crafted results, abstract rewards, etc.).

```markdown
KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player
```

No `# Items` entry needed. The compiler auto-creates the item with ID = `TAKE + KEYCARD_noun_id`.

### State and Pickup

A player always picks up a specific state of a noun. The noun's current ID (which reflects its state) determines the inventory ID:

- BOX (noun ID 727) → inventory ID = TAKE(21) + 727 = 748
- BOX__SMASHED (noun ID 239) → inventory ID = TAKE(21) + 239 = 260

Items don't have state. Once on inventory, it's just a number. No transforms on inventory — if the item is "used up," it's `-> trash` (cross it out).

### Interactions on Carried Items

All interactions defined on the noun are duplicated for the inventory ID. This means:

- `LOOK + inventory_id` works — the player can examine carried items
- `USE + inventory_id + DOOR_id` works — multi-target interactions in any room
- The narrative is the same as the room-bound version

The compiler generates `ResolvedInteraction`s for both the noun ID and the inventory ID, with different sums but the same narrative and arrows.

### Player Instructions

**Pickup (TAKE or other verb triggering `-> player`):**
> *"Cross out KEYCARD (211) on your room sheet. Write 232 on your Inventory."*

Where 232 = TAKE(21) + 211.

When the player triggers TAKE + KEYCARD directly, the sum they computed (232) IS the inventory number — the ledger can say:
> *"Cross out KEYCARD (211) on your room sheet. Write your sum on your Inventory."*

For indirect pickups (triggered by another verb), the ledger states the number explicitly.

### Compilation

#### ID Allocation (`compiler.py`)

During `_try_allocate`:

1. Allocate verb IDs (including TAKE)
2. Allocate noun/room IDs from entity pool
3. For every noun with a `-> player` arrow, compute `TAKE_id + noun_id` and **remove that number from the entity pool** before allocating further IDs. This prevents inventory IDs from colliding with entity IDs by construction.
4. Allocate remaining entities (items, cues, etc.)

#### Auto-Registration

New compiler step after parsing, before ID allocation:

1. Scan all interactions for `-> player` arrows
2. For each noun targeted by `-> player`, if no Item exists with that name, create one
3. **Error** if two nouns with the same name from different rooms both have `-> player`
4. **Error** if any `-> player` arrow exists but no TAKE verb is defined

The auto-registered Item doesn't get an independently allocated ID — its ID is derived: `TAKE_id + noun_id`. This is computed after ID allocation.

#### Interaction Duplication

After `resolve_interactions`, for every auto-registered item:

1. Find all `ResolvedInteraction`s that reference the noun (by noun ID in their sum)
2. Create parallel `ResolvedInteraction`s with the inventory ID substituted
3. The narrative and arrows are the same; only the sum changes
4. These go into the potentials list alongside the originals

#### Collision Detection

The collision checker must include inventory-derived sums:

- `verb_id + inventory_id` for all verbs and auto-items
- `verb_id + inventory_id + entity_id` for multi-target combinations
- These are checked alongside the standard `verb_id + entity_id` sums

### `# Items` Section

Remains for items that **only exist on inventory** — never as room nouns:

- Crafted items (combining two things produces a new item)
- Abstract rewards or tokens
- Items the player starts with

These items keep their independently allocated IDs from the entity pool (not derived from TAKE).

### Edge Cases

- **No TAKE verb:** Compiler errors if `-> player` exists without TAKE. Authors must define TAKE in `# Verbs`.
- **Name collision across rooms:** Two nouns named LEVER in different rooms both with `-> player` → compile error with line numbers.
- **Noun state with `-> player`:** Works naturally. TAKE + BOX__SMASHED_id = different inventory ID than TAKE + BOX_id.
- **Item already declared in `# Items`:** If an author both declares KEY in `# Items` AND has a KEY noun with `-> player`, the explicit item takes precedence (keeps its own allocated ID). The auto-registration is skipped. Deprecation warning suggested.
- **Multiple `-> player` on same noun in different interactions:** Fine — same item, same derived ID.

### Documentation Updates

- **`docs/advanced.md`**: Update "Items vs. nouns" section
- **`docs/reference.md`**: Update arrow destinations table, note TAKE requirement
- **`docs/grammar.ebnf`**: No syntax changes needed (existing `-> player` syntax)
- **`CLAUDE.md`**: Update architecture notes

### Example End-to-End

**Script:**
```markdown
# Verbs
USE
TAKE
LOOK

# Control Room

KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player
```

**Compilation assigns:** TAKE = 21, KEYCARD noun ID = 211, inventory ID = 232.

**Potentials list includes:**
- `LOOK(51) + KEYCARD_noun(211) = 262 → Ledger A-3` (look at it in room)
- `TAKE(21) + KEYCARD_noun(211) = 232 → Ledger A-4` (pick it up)
- `LOOK(51) + KEYCARD_inv(232) = 283 → Ledger A-5` (look at it in inventory)

**Ledger A-4 (TAKE + KEYCARD):**
> *"You pocket the keycard."*
> → Cross out KEYCARD (211) on your room sheet. Write your sum on your Inventory.

**Ledger A-5 (LOOK + KEYCARD on inventory):**
> *"A small keycard with a red stripe."*

(Same narrative as A-3 — duplicated for the inventory ID.)

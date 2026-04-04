# Room Actions Design

**Date:** 2026-04-05
**Status:** Approved

## Problem

Directional navigation (GO NORTH, GO SOUTH) and other simple room-level behaviors require verb + noun addition, consuming entity IDs and cluttering room sheets with nouns that exist solely as addition targets. This adds friction without adding fun.

## Solution

Introduce **actions** -- a parallel track to the addition-based system. Actions are direct ledger lookups: the player sees "GO NORTH ... A-42" on a room sheet, flips to ledger entry A-42, and follows the instructions. No verb, no noun, no addition.

Actions can do everything interactions can (narrative, arrows, state changes). They just bypass the verb+noun math.

## Data Model

New `Action` dataclass in `models.py`:

```python
@dataclass
class Action:
    name: str              # e.g., "GO NORTH", "HIDDEN_PATH"
    room: str              # room it belongs to
    narrative: str         # text the player reads
    arrows: list[Arrow]    # same Arrow type interactions use
    discovered: bool       # False = pre-printed, True = revealed by another interaction
    ledger_id: int = 0     # assigned by compiler, maps to a ledger entry
```

`GameData` gets a new field: `actions: dict[str, Action]` keyed as `"RoomName::ACTION_NAME"` (same pattern as nouns).

Actions do **not** consume entity IDs. They only consume ledger entry slots.

## Script Syntax

The `>` marker denotes actions in room scripts:

```markdown
# Forest

// Pre-printed actions (top-level in room)
> GO NORTH
  You head north through the trees.
  - player -> "Clearing"

> GO SOUTH
  - player -> "Village"

// Regular nouns and interactions
OLD_TREE
+ LOOK: A gnarled oak.
+ USE + AXE:
  - OLD_TREE -> trash
  // Discoverable action (nested under interaction)
  > HIDDEN_PATH
    A path is revealed behind the fallen tree.
    - player -> "Cave"
```

Rules:
- `>` at room indentation level = pre-printed on room sheet
- `>` nested under an interaction = discoverable (parent interaction's ledger entry says "Write HIDDEN_PATH ... A-XX in a discovery slot")
- Narrative text indented under `>` line, arrows with `-` prefix (same as interactions)
- Actions can contain arrows, which can reveal nouns. Those nouns can have `+` interactions, which can reveal further actions.
- Actions **cannot** be `+` targets (no verb interactions on actions).
- Actions **cannot** nest directly under actions.

## Compiler Changes

### Parser (`parser.py`)

New `parse_action()` handles `>` lines:
- At room level: `discovered=False`
- Nested under an interaction: `discovered=True`
- Actions stored in `game.actions`

### Ledger ID Allocation (`compiler.py`)

Actions get ledger entry numbers assigned alongside interaction ledger entries in a single interleaved/randomized sequence. They should be scattered throughout the ledger, indistinguishable from sum-based entries by numbering.

### Deduplication

Actions with identical arrows (and compatible narratives) share a ledger ID:
- Both have the same narrative, or one has no narrative: share, with the empty one inheriting narrative from the other.
- Different narratives: stay separate.

### No Collision Concerns

Actions don't participate in the verb+noun sum system, so they can't collide with interactions.

## Arrow Room Context (applies to all interactions and actions)

Arrow order is significant when a `player -> "RoomName"` transition is present. Arrows before the player transition resolve against the **exit room** (current room); arrows after resolve against the **entry room** (destination). This applies uniformly to both regular interactions and actions.

```markdown
> GO NORTH
  You cross the rickety bridge.
  - BRIDGE -> trash          // affects Forest (exit room)
  - player -> "Clearing"    // movement happens here
  - FOUNTAIN -> room         // reveals FOUNTAIN in Clearing (entry room)
```

This is a change to the existing writer arrow processing, which currently resolves all arrows against `ri.room` regardless of player transitions.

## Writer Changes

### Room Sheets

- **Pre-printed actions**: Listed on the room sheet with name and ledger ID (e.g., "GO NORTH ... A-42").
- **Discoverable actions**: Use existing discovery slots. The `_max_discovery_slots()` calculation counts discoverable actions toward the total.

### Ledger Entries

Actions produce ledger entries identical in format to interaction entries: narrative text followed by human-readable instructions from arrows. Indistinguishable from sum-based entries.

### Unchanged

- **Potentials list**: Actions don't appear (that's for sums only).
- **Verb sheet**: Actions don't appear (no verb involved).
- **Inventory sheet**: No changes.

## What's Unchanged

- Verb/noun/sum system untouched
- Entity ID pool untouched (actions don't consume entity IDs)
- Discovery slot mechanism reused as-is
- Ledger format unchanged

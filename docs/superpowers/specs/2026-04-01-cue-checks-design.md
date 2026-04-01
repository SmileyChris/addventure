# Cue Checks: Cross-Room Interactions

## Problem

The current "room alerts" system is half-built. Actions in one room can arrow entities to another room (`ENTITY -> "OtherRoom"`), but the resolution path is broken:

- The ledger tells the player to "write alert #N on your player sheet" — but there is no player sheet.
- The room sheet says to "add the alert number + Room ID and check the Potentials List" — but alerts never produce resolved interactions with sum IDs, so there's nothing to find.
- The `RoomAlert` model stores data that never gets wired into the potentials/ledger system.

The mechanism is disconnected: the trigger fires, but nothing resolves.

## Design: Cue Checks

Replace room alerts with **cues** — numbered tokens the player carries on their inventory sheet that resolve via the existing addition mechanic when they enter the right room.

### Player Flow

1. **Receive a cue.** An action in Room A produces a ledger entry that says: *"Write 347 in your Cue Checks."*
2. **Check cues on room entry.** When entering any room, the player adds each cue number to the Room ID and looks up the sum in the Potentials List.
3. **Resolve.** If a sum matches, the player reads the ledger entry. It contains narrative text and instructions (reveal entities, transform state, etc.) — the same as any other ledger entry.
4. **Cross out the cue.** The resolution ledger entry tells the player to cross out the cue number, so it doesn't fire again.

The player never knows which room a cue is "for" until the sum matches. This preserves surprise.

### Authoring Syntax

Use `?` as the marker for cue arrows in game scripts. The `?` means "deferred effect resolved elsewhere."

```markdown
HATCH
+ LOOK: A dark opening, just wide enough to squeeze through.
+ USE:
  You lower yourself into the darkness.
  - player -> "Basement"
  - ? -> "Basement"
    The hatch above casts a shaft of light into the room.
    - LIGHT_SHAFT -> room
```

The `? -> "RoomName"` arrow is followed by an indented block containing:
- **Narrative text** — what the player reads when the cue resolves in the target room.
- **Arrows** — state changes that happen in the target room (reveals, transforms, etc.).

This block defines the resolution ledger entry. The cue number itself is assigned at compile time — the author never sees or manages it.

Multiple cue arrows can target the same room or different rooms from the same interaction:

```markdown
+ USE:
  You pull the lever. Machinery groans throughout the building.
  - ? -> "Courtyard"
    The iron gate swings open.
    - GATE -> room
  - ? -> "Basement"
    A hidden panel slides aside.
    - PANEL -> room
```

### Compilation

#### Parser (`parser.py`)

When encountering `- ? -> "RoomName"` inside an interaction block:

1. Parse the `?` arrow like any other arrow (subject=`?`, destination=`"RoomName"`).
2. Parse the indented block beneath it: collect narrative text and child arrows, the same way interaction bodies are parsed today.
3. Create a `Cue` object with the target room, narrative, and arrows. Append it to `game.cues`.
4. Keep the `?` arrow on the parent interaction (so the writer knows to emit "Write N in your Cue Checks" when generating instructions for the parent ledger entry). The writer matches `?` arrows to cues by target room + parent interaction.

#### Model Changes (`models.py`)

Replace `RoomAlert` with a `Cue` model:

```python
@dataclass
class Cue:
    target_room: str          # Room where this cue resolves
    narrative: str            # Text shown when cue resolves
    arrows: list[Arrow]       # State changes in target room
    source_line: int
    trigger_room: str         # Room where cue is received
    id: int = 0               # Assigned during ID allocation
    sum_id: int = 0           # cue.id + target_room.id
    entry_number: int = 0     # Ledger entry number
```

On `GameData`, replace `alerts: list[RoomAlert]` with `cues: list[Cue]`.

#### ID Allocation (`compiler.py`)

Cue IDs come from the same entity pool (100–999, excluding multiples of 5/10). They participate in the same collision detection as all other entities.

During `_try_allocate`:
- Allocate an ID for each cue from the entity pool.
- Compute `cue.sum_id = cue.id + target_room.id`.

During `resolve_interactions` (or a new `resolve_cues` step):
- Create a `ResolvedInteraction` for each cue, with `sum_id = cue.id + target_room.id`.
- The narrative and arrows come from the cue's nested block.
- These resolved interactions get entry numbers and appear in the Potentials List and Story Ledger like any other.

During collision detection:
- Cue sums are checked against all other sums (verb+entity sums and other cue sums).

#### Writer Changes

**Trigger side (ledger instructions):** When generating instructions for a `?` arrow, emit: *"Write {cue.id} in your Cue Checks."*

**Resolution side (ledger entry):** The cue's resolved interaction generates a ledger entry like any other. Its instructions should include *"Cross out {cue.id} from your Cue Checks"* as the final instruction, so the cue doesn't fire again.

**Inventory sheet (text mode):** Add a "Cue Checks" section with blank slots for writing cue numbers:

```
CUE CHECKS
------------------------------------------
On room entry, add each cue + Room ID and check the Potentials List.

  ____  ____  ____  ____  ____  ____
```

**Room sheet:** Remove the current "Room Alerts" section entirely. The cue check instruction now lives on the inventory sheet, since cues are portable.

#### Typst Template Changes

**`inventory.typ`:** Add a "Cue Checks" section between Inventory and Master Potentials List, with write slots for cue numbers and the instruction text.

**`room-sheet.typ`:** Remove the "Room Alerts" section (lines 139–155).

### What Gets Removed

- `RoomAlert` dataclass from `models.py`
- `alerts` field from `GameData`
- `generate_room_alerts()` from `compiler.py`
- Alert-related code in `_generate_instructions()` in `writer.py` (the `? -> "OtherRoom"` branch replaces it)
- "Room Alerts" section from room sheet writer and typst template
- Alert count from stats output

### Edge Cases

- **No cues in a game:** Only render the Cue Checks section on the inventory sheet if the game has cues. Simpler for simple games, and the player doesn't need to learn a mechanic that isn't used.
- **Multiple cues to the same room:** Each gets its own ID and resolved interaction. They resolve independently.
- **Cue to a room the player has already visited:** Works fine — next time they enter (or if they're already there and re-LOOK), they check cues.
- **Cue that should persist (fire in multiple rooms):** The resolution ledger entry simply omits the "cross out" instruction. The author controls this by whether they include cleanup arrows. (This is a future consideration — for now, all cues are single-fire.)

### Example Game Update

Add a cue to the example game (`games/example/`) to demonstrate the feature. A natural fit: when the player powers on the Control Room (USE + KEYCARD on TERMINAL), it also causes something to happen in the Basement — e.g., the power surge activates the fuse box, revealing a hidden compartment.

In `control_room.md`, add a cue arrow to the `USE + KEYCARD` interaction:

```markdown
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  ...existing arrows...
  - ? -> "Basement"
    The power surge triggers the fuse box. A compartment clicks open.
    - COMPARTMENT -> room
```

In `basement.md`, add the COMPARTMENT noun (which will only appear when the cue resolves):

```markdown
COMPARTMENT
+ LOOK: A small compartment behind the fuse box. Something glints inside.
```

This gives the example game a cross-room interaction that players can discover naturally.

### Documentation Updates

**`CLAUDE.md`** — Update the Script Syntax section:
- Add `? -> "RoomName"` to the arrow destinations list.
- Mention cue checks in the architecture overview.

### Example End-to-End

**Script:**
```markdown
# Control Room

LEVER
+ USE:
  You pull the lever. Something heavy shifts in the distance.
  - ? -> "Courtyard"
    An iron gate has risen from the ground.
    - GATE -> room
```

**Compilation assigns:** Cue ID = 347, Courtyard Room ID = 512, Sum = 859, Entry = A-14.

**Trigger ledger entry (A-7, for USE + LEVER):**
> *"You pull the lever. Something heavy shifts in the distance."*
> → Write 347 in your Cue Checks.

**Resolution ledger entry (A-14, for cue 347 + Courtyard):**
> *"An iron gate has risen from the ground."*
> → Write GATE (628) in a discovery slot on your room sheet.
> → Cross out 347 from your Cue Checks.

**Potentials List includes:** `859 → Ledger A-14`

**Inventory sheet has:** Cue Checks section where 347 gets written/crossed out.

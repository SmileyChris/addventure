# State & Transformation

Interactions become interesting when they change the game world. Arrows are the mechanism — they move, transform, and destroy entities.

## Arrows

An arrow is a line with the `-` prefix that describes a state change:

```markdown
- ENTITY -> destination
```

Arrows are nested inside interactions. When the interaction triggers, all its arrows fire:

```markdown
LANTERN
+ TAKE:
  You pick up the lantern.
  - LANTERN -> player
```

When the player triggers TAKE + LANTERN, the narrative plays and the lantern moves to their inventory.

## Destinations

Arrows can point to six types of destination:

### `player` — move to inventory

```markdown
- KEYCARD -> player
```

The entity disappears from the room sheet and appears on the player's inventory sheet with a new ID.

### `trash` — remove from the game

```markdown
- CROWBAR -> trash
```

The entity is gone. The story entry tells the player to cross it out permanently. Verbs can be trashed the same way — `- EXAMINE -> trash` removes a verb from the player's verb sheet, making any interactions using it inaccessible.

### `room` — place in the current room

```markdown
- KEYCARD -> room
```

The entity appears on the current room sheet. Use this to reveal hidden objects or drop items from the player's inventory.

!!! tip "Mention what appears"
    The story entry instructs the player to write the new entity on their room sheet, but it doesn't explain *what* it is — the narrative does. Make sure your narrative text describes what the player found, or the instruction to "Write KEYCARD" comes out of nowhere.

### `"Room Name"` — move the player

```markdown
- player -> "Basement"
```

Sends the player to a different room. The room name must match a `#` header exactly and be wrapped in quotes. The story entry tells the player to switch to that room sheet. The player can then LOOK to read the room description.

To affect another room *without* moving the player there, use [cue checks](advanced.md#cue-checks-cross-room-effects) (`? -> "Room Name"`).

### `ENTITY__STATE` — transform an entity

```markdown
- CRATE -> CRATE__OPEN
```

The entity changes state. On paper, the player crosses out the old ID and writes in a new one. The new state can have its own interactions (see [Entity states](#entity-states) below). Only nouns and rooms can have states — inventory items cannot.

You can also revert to the base state:

```markdown
- CRATE__OPEN -> CRATE
```

### `VERB__STATE` — transform a verb

```markdown
- USE -> USE__RESTRAINED
```

Changes a verb's ID. On the verb sheet, the player crosses out the old ID and writes the new one. This makes the verb behave differently — any interactions defined for `USE__RESTRAINED` now activate instead of the normal `USE` interactions. Use this to temporarily replace a verb's behaviour — for example, blocking all USE actions while the player is restrained. See [Advanced Mechanics](advanced.md#verb-states) for a complete walkthrough.

### `-> VERB` — reveal a new verb

```markdown
- -> COMBINE
```

Grants the player a new verb. The story entry tells the player to record the verb name and ID on their verb sheet. The verb does not need to be listed in `# Verbs` — the compiler auto-registers it when it sees this arrow, just like `-> player` auto-registers items.

Define interactions for the new verb as normal — they'll resolve once the player has the verb:

```markdown
+ USE + STRANGE_DEVICE:
  The device hums. New possibilities flood your mind.
  - -> COMBINE

WIDGET
+ COMBINE + WIDGET:
  You reshape the widget into something new.
```

## Entity states

States let a noun or room change its behaviour after something happens. Items in the player's inventory cannot have states. The double-underscore separates the base name from the state: `CRATE__OPEN`, `TERMINAL__UNLOCKED`, `DOOR__BROKEN`.

Define state-specific interactions by nesting them under the arrow that creates the state:

```markdown
CRATE
+ LOOK: A heavy wooden crate, nailed shut.
+ USE + CROWBAR:
  You pry it open. A keycard glints inside.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - CROWBAR -> trash
```

After the player pries open the crate:

- `CRATE` becomes `CRATE__OPEN` with a new ID
- `CRATE__OPEN` responds to LOOK with the new description
- The crowbar is destroyed

### State inheritance

When an entity changes state, the new state **inherits observations** (arrow-free interactions like LOOK) from the base entity that aren't explicitly overridden. In the example above, if `CRATE__OPEN` didn't define its own LOOK, it would inherit the base `CRATE`'s LOOK text.

**Actions — interactions that have arrows — are never inherited.** If a state needs a TAKE, USE, or any other action, you must define it explicitly on that state. This prevents game-altering mechanics from silently carrying over to states where they don't belong.

In practice: only define observations (like LOOK) that differ from the base — the rest are inherited. But any actions the new state should support (TAKE, USE, etc.) must be written out explicitly, since they are never carried over automatically.

## Room states

Rooms are entities too, and they can change state. Use the special keyword `room` to reference the current room:

```markdown
+ USE + KEYCARD:
  You slide the keycard. The room powers up.
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    + HATCH -> room
      + LOOK: A dark opening leading down.
      + USE:
        You lower yourself into the darkness.
        - player -> "Basement"
```

When the room changes state:

- The room gets a new ID (players cross out the old one on their room sheet)
- New nouns can appear (HATCH, in this example)
- The room's LOOK description changes

Room states work just like entity states — new nouns and interactions nest under the arrow, and observations not overridden are inherited (actions are not).

## Chaining arrows

A single interaction can fire multiple arrows:

```markdown
+ USE + CROWBAR:
  You pry it open. A keycard glints inside.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - KEYCARD -> room
    + LOOK: A small keycard among the splinters.
    + TAKE:
      You pocket the keycard.
      - KEYCARD -> player
  - CROWBAR -> trash
```

This single interaction:

1. Transforms the crate to its open state
2. Places a keycard in the room (with its own interactions)
3. Destroys the crowbar

The story entry generated for this interaction contains all the instructions the player needs to update their sheets.

## Item interactions

When a noun is picked up (`-> player`), its interactions are automatically duplicated for the inventory version. You can override specific interactions by defining them under `-> player`:

````markdown
KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick up the knife.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
````

The inventory KNIFE gets the custom LOOK ("Strange markings..."), while the room KNIFE keeps its original LOOK ("A rusty blade..."). Any verbs not overridden (like USE) are still auto-duplicated from the room noun.

### Suppressing inherited interactions

To prevent an interaction from being duplicated to inventory without adding a new one, use an empty interaction:

````markdown
  - KNIFE -> player
    + USE:
````

This prevents USE from being auto-duplicated, without creating a ledger entry.

### Pre-equipped items

Items defined in `# Inventory` start directly in the player's inventory — they have no room noun and never need to be picked up. They can have their own interaction blocks:

````markdown
# Inventory

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
````

## A complete example

Here's a room that uses multiple arrow types:

```markdown
# Cell
LOOK: A bare concrete cell. Light seeps through a crack in the wall.

LOOSE_BRICK
+ LOOK: One brick juts out slightly from the wall.
+ USE:
  You work the brick free. Behind it, a rusty key.
  - LOOSE_BRICK -> LOOSE_BRICK__REMOVED
    + LOOK: A gap in the wall where the brick was.
  - KEY -> room
    + LOOK: A rusty iron key.
    + TAKE:
      You pocket the key.
      - KEY -> player

CELL_DOOR
+ LOOK: A heavy iron door. Locked.
+ USE + KEY:
  The key turns with a grinding shriek. The door swings open.
  - CELL_DOOR -> trash
  - KEY -> trash
  - player -> "Corridor"
```

Next: [Advanced Mechanics](advanced.md) covers multi-target interactions, verb states, wildcards, and more.

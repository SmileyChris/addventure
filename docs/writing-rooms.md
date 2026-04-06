# Writing Rooms

Every `.md` file in your game directory (besides `index.md`) defines a room. Files are loaded alphabetically, but the order doesn't affect gameplay.

## Room headers

A room starts with a `#` header. The header text becomes the room name:

```markdown
# Engine Room
```

You can define multiple rooms in one file if you prefer, but one room per file is easier to manage.

## Room descriptions

A room-level interaction sits directly under the header — no `+` prefix, no room object name:

```markdown
# Engine Room
LOOK: Pipes criss-cross the ceiling. The air is thick with steam.
```

This is what players read when they LOOK at the room itself. It sets the scene.

## Room objects

Room objects are objects inside a room. Write them as bare `ALL_CAPS` names on their own line:

```markdown
# Engine Room
LOOK: Pipes criss-cross the ceiling. The air is thick with steam.

VALVE
GAUGE
TOOLBOX
```

Each room object gets its own ID on the printed room sheet. Players can target room objects by adding verb + room object IDs.

### Naming rules

Room object names must be `ALL_CAPS` with optional underscores: `VALVE`, `FUEL_TANK`, `CONTROL_PANEL`. This distinguishes them from narrative text.

The same name can appear in different rooms — the compiler treats them as separate entities.

## Interactions

Interactions define what happens when a player uses a verb on a room object. They use the `+` prefix:

```markdown
TOOLBOX
+ LOOK: A rusted metal toolbox. The latch is broken.
+ TAKE:
  You grab the toolbox. Might come in handy.
  - TOOLBOX -> player
```

The pattern is:

```
+ VERB: inline narrative
```

or for longer responses:

```
+ VERB:
  Narrative text on the
  following lines, indented.
```

### Multiple interactions

A room object can respond to multiple verbs:

```markdown
GAUGE
+ LOOK: A pressure gauge. The needle is deep in the red.
+ USE: You tap the glass. The needle doesn't budge.
```

### Multi-target interactions

An interaction can require the player to combine two things. Add extra targets with `+`:

```markdown
DOOR
+ USE + KEY:
  The key turns smoothly. The door swings open.
  - DOOR -> DOOR__OPEN
  - KEY -> trash
```

The player must calculate verb + noun1 + noun2 to reach this entry. If the key is in the player's inventory, its inventory ID is used instead of the room ID — the compiler handles both automatically.

For interactions involving multiple room objects that don't belong naturally under a single room object's block, use a [`## Interactions` section](advanced.md#the-interactions-section).

### Inline vs. block narrative

Short responses can go on the same line as the verb:

```markdown
+ LOOK: A heavy iron door.
```

Longer narrative goes on indented lines below:

```markdown
+ USE:
  You heave the door open. It groans on corroded hinges,
  revealing a narrow passage beyond. Cold air rushes past.
```

Consecutive lines are joined into one paragraph. Separate paragraphs with a blank line:

```markdown
+ USE:
  You heave the door open.

  The passage beyond is dark and cold. Something moves in the shadows.
```

## Indentation

Addventure uses indentation to define structure. The hierarchy works like this:

```
ENTITY_NAME                  ← level 0: room object declaration
+ VERB:                      ← level 1: interaction
  Narrative text             ← level 2: narrative body
  - ENTITY -> destination    ← level 2: arrow (state change)
    + VERB:                  ← level 3: interaction on new state
      More narrative         ← level 4: nested narrative
```

Use spaces, not tabs. Each child line must be indented deeper than its parent. Indentation is how the compiler knows which arrows and interactions belong together.

## Comments

Use `//` to add comments that the compiler ignores:

```markdown
// TODO: add a puzzle here
VALVE
+ LOOK: A large red valve.
// + USE: You turn the valve. — disabled for now
```

You can also add trailing comments on structural lines:

```markdown
KEYCARD // starts hidden
- KEYCARD -> player // acquired here
```

Trailing comments are not stripped from narrative prose, so `//` inside story text is treated as literal text.

## Actions

Actions are direct ledger lookups — things the player can do without addition. They're declared with the `>` marker:

```markdown
# Forest

> GO_NORTH
  You head north through the trees.
  - player -> "Clearing"

> GO_SOUTH
  You retrace your steps to the village.
  - player -> "Village"
```

Each action gets a ledger entry number printed directly on the room sheet (e.g. "GO NORTH ... A-12"). Write action names as identifiers like `GO_NORTH`; the compiler renders them with spaces for display ("GO NORTH").

Identifiers use `ALL_CAPS` with optional single underscores: `GO_NORTH`, `WALL_PANEL`. Double underscores are reserved for states: `DOOR__OPEN`.

Actions are ideal for directional navigation, but they can do anything an interaction does: narrative, arrows, state changes.

### Discoverable actions

Nest an action under an interaction to make it discoverable. It won't appear on the room sheet until the parent interaction fires:

```markdown
HATCH
+ USE + CROWBAR:
  You pry the hatch open.
  - HATCH -> trash
  - CROWBAR -> trash
  > GO_DOWN
    You descend into darkness.
    - player -> "Basement"
```

When the player uses the crowbar on the hatch, the instructions include "Write GO DOWN (A-7) in a discovery slot."

### Removing actions

Actions can be removed with `-> trash`, just like room objects:

```markdown
LEVER
+ USE:
  The bridge collapses behind you!
  - GO_BACK -> trash
```

This generates "Cross out GO BACK on this room sheet."

## Fragments

A `::: fragment` block inside an interaction adds long-form hidden content — finale text, reveals, or anything players shouldn't read until directed. The content is kept separate from the main game flow.

```markdown
VAULT_DOOR
+ OVERRIDE:
  The door swings open. You step inside.
  - player -> "Vault"

  ::: fragment
  Inside the vault you find the letter. You read it slowly.

  *My dear,*

  *By the time you find this, I'll be long gone...*
  :::
```

When this entry fires, the ledger instruction tells the player which fragment to turn to (e.g. "Turn to Fragment Alpha"). Fragments are printed in a separate section at the back of the ledger, or as a separate document — see [Fragment modes](reference.md#fragment-modes).

The content inside `::: fragment` is Typst markup. Plain prose works as-is. Basic formatting:

- `*bold text*` — bold
- `_italic text_` — italic
- Blank line between paragraphs
- `\` at the end of a line — explicit line break (for verse, addresses, etc.)

## Putting it together

Here's a complete room with two interactive room objects, one of which changes state:

```markdown
# Storage Bay
LOOK: Crates are stacked floor to ceiling. A crowbar leans against the wall.

CRATE
+ LOOK: A heavy wooden crate, nailed shut.
+ USE + CROWBAR:
  You lever the lid off. Inside: a fuel canister.
  - CROWBAR -> trash
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid off.
  - FUEL -> room
    + LOOK: A metal fuel canister. Smells fresh.
    + TAKE:
      You grab the canister.
      - FUEL -> player

CROWBAR
+ LOOK: A solid iron crowbar. Good for prying.
+ TAKE:
  You pick up the crowbar.
  - CROWBAR -> player
```

This gives players two room objects to interact with, a multi-target puzzle, and a state change that reveals new content when solved.

Next: [State & Transformation](state-and-transformation.md).

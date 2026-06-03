# Addventure Authoring Reference

## Source Shape

`index.md`:

```markdown
---
title: Game Title
author: Author Name
start: Room Name
ledger_prefix: A
image: cover.jpg
image_height: 60%
name_style: upper_words
---

Intro text shown on the title page.

# Verbs
LOOK
USE
TAKE

# Inventory
COMPASS
  + LOOK: A brass compass, needle spinning wildly.
```

Known frontmatter keys: `title`, `author`, `start`, `ledger_prefix`, `image`, `image_height`, `name_style`. Unknown keys are accepted but warn.

Room files:

```markdown
# Room Name
LOOK: Room description.

OBJECT_NAME
+ LOOK: Object description.
+ USE + TOOL:
  Narrative.
  - OBJECT_NAME -> OBJECT_NAME__STATE
```

Identifiers must start with a capital letter and use only uppercase letters, digits, and single underscores. State names use double underscore: `BASE__STATE`. Room names are free text in `#` headers and quoted arrow destinations.

Indent with spaces only. A child block must be indented deeper than its parent. `//` comments are allowed on their own line and as trailing comments on structural lines; in narrative text `//` is literal prose.

Do not hard-wrap narrative prose in source files. Addventure's writers preserve line boundaries more than normal Markdown prose, so manually wrapped paragraphs can render as narrow, broken text. Write each prose paragraph as one source line unless you explicitly want a line break, and use blank lines only for intentional paragraph breaks.

## Interactions

Object interaction:

```markdown
OBJECT
+ VERB: Inline narrative.
+ VERB:
  Block narrative.
+ VERB + TARGET:
  Multi-target interaction.
```

Room-level interaction:

```markdown
# Engine Room
LOOK: Pipes cross the ceiling.
```

Freeform room logic:

```markdown
## Interactions

USE + KNIFE + BINDINGS:
  You cut yourself free.
  - BINDINGS -> trash
```

Target alternatives:

```markdown
+ USE + KEYCARD|ACCESS_BADGE:
  Either target satisfies this slot.
```

Wildcard catch-all:

```markdown
## Interactions

USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

`*` matches room objects in the current room, not inventory objects. It must be the whole target list or the second slot form supported by the compiler.

Empty interaction suppression:

```markdown
- KNIFE -> player
  + USE:
```

This prevents an inherited/duplicated inventory interaction from resolving.

## Arrows

Arrows fire when their parent interaction/action/cue/signal branch fires:

| Arrow | Effect |
|---|---|
| `- OBJECT -> player` | Move object to inventory; auto-registers inventory object; requires `TAKE` verb |
| `- OBJECT -> trash` | Remove room/inventory object |
| `- VERB -> trash` | Remove verb |
| `- OBJECT -> room` | Reveal/place object in current room |
| `- player -> "Room Name"` | Move player to another room or chapter |
| `- player -> "Room__"` | Move player, explicitly targeting the base state |
| `- OBJECT -> OBJECT__STATE` | Transform room object |
| `- OBJECT__STATE -> OBJECT` | Revert room object |
| `- room -> room__STATE` | Transform current room |
| `- room -> room__` | Revert current room to base state |
| `- USE -> USE__STATE` | Transform verb |
| `- USE__STATE -> USE` | Revert verb |
| `- -> VERB` | Reveal a new verb |
| `- ? -> "Room Name"` | Create a cue that resolves on room entry |
| `- ACTION_NAME -> trash` | Remove action |
| `- SIGNAL_NAME -> signal` | Emit signal code |

Nested children under reveal/transform arrows define the newly available object's, room state's, or inventory object's interactions:

```markdown
CRATE
+ USE + CROWBAR:
  You pry the lid open.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate.
  - KEYCARD -> room
    + LOOK: A red-striped keycard.
    + TAKE:
      You pocket it.
      - KEYCARD -> player
```

## State And Inheritance

Room objects and rooms can have states. Inventory objects cannot.

Observation inheritance:

```markdown
DOOR
+ LOOK: A steel door.
+ USE + KEY:
  It opens.
  - DOOR -> DOOR__OPEN
    + USE:
      You step through.
      - player -> "Hall"
```

`DOOR__OPEN` inherits the base `LOOK` because it has no arrows. It does not inherit arrowed interactions such as `USE + KEY`.

Room state example:

```markdown
+ USE + KEYCARD:
  Power returns.
  - room -> room__POWERED
    + LOOK: The room hums.
    + HATCH -> room
      + LOOK: A floor hatch.
      + USE:
        You climb down.
        - player -> "Basement"

Revert a room to its base state with `room__`:

```markdown
+ USE + CIRCUIT_BREAKER:
  The room powers down.
  - room -> room__
```

## Inventory Behavior

Auto inventory:

```markdown
LANTERN
+ TAKE:
  You take the lantern.
  - LANTERN -> player
```

The compiler creates inventory `LANTERN`. Its inventory ID is derived from `TAKE + room-object ID`. If the same base object is picked up from multiple rooms, validation fails unless the object is explicitly declared in `# Inventory` or renamed.

Explicit inventory is for starting, crafted, or abstract items:

```markdown
# Inventory
MASTER_KEY
  + LOOK: Heavy and old.
```

Inventory interaction override:

```markdown
KNIFE
+ LOOK: A rusty blade on the floor.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
```

## Actions

Actions are direct ledger lookups printed on the room sheet:

```markdown
> GO_NORTH
  You head north.
  - player -> "Clearing"
```

Discoverable action:

```markdown
HATCH
+ USE + CROWBAR:
  The hatch opens.
  - HATCH -> trash
  > GO_DOWN
    You descend.
    - player -> "Basement"
```

Remove with `- GO_DOWN -> trash`.

## Cues

Cues create delayed cross-room effects. The player records a cue number, then checks it against room IDs when entering rooms.

```markdown
LEVER
+ USE:
  Machinery shifts in the distance.
  - ? -> "Courtyard"
    A gate rises from the ground.
    - GATE -> room
```

Cue targets:

| Target | Resolves in |
|---|---|
| `"Room"` | Base room and all states |
| `"Room__STATE"` | Only that state |
| `"Room__"` | Only base state |

Use cues for remote changes without moving the player. Use ordinary `player -> "Room"` for movement.

## Signals

Signals are deterministic branch flags. Emitting a signal prints a consonant code for the player to record:

```markdown
- EVERYONE_OUT_ESCAPE -> signal
```

Signal checks can appear in the index description or interaction bodies:

```markdown
EVERYONE_OUT_ESCAPE?
  A companion catches up.
  - COMPANION -> room
WITNESS_ESCAPE?
  You are alone.
otherwise?
  The road is quiet.
```

All matching signal branches fire. `otherwise?` fires only when none match. Signals are useful across chapters because the same signal name produces the same code in each chapter.

## Fragments

Fragments are sealed/hidden long-form content attached to an interaction:

```markdown
VAULT_DOOR
+ OVERRIDE:
  The door swings open.

  ::: fragment
  Hidden finale text.
  - WITNESS_ESCAPE -> signal
  - player -> "Epilogue"
  :::
```

Build modes:

```bash
addventure build game --fragment included
addventure build game --fragment separate
addventure build game --fragment jigsaw
```

Fragment content is rendered as Typst markup and can contain arrows/signals that fire from the fragment.

## Chapters

Each chapter is a subdirectory with its own `index.md` and room files. Use unique `ledger_prefix` values. `addventure new` run inside a game directory assigns the next prefix.

```bash
addventure build my-game --all --md
```

Cross-chapter transitions use:

```markdown
- player -> "Epilogue"
```

Cross-chapter consequences should use signals.

## Validation Heuristics

Run `--md` early and often. The compiler catches syntax, unknown names, authored sum collisions, reachability, stale blind-mode room state risks, and cross-chapter signal mismatches.

Common failures:

- `Unknown verb`: the verb is not in `# Verbs`, not revealed with `-> VERB`, and not auto-registered as a state.
- `Unknown target`: the target object does not exist in that room/state or inventory.
- `Arrow '-> player' requires a TAKE verb`: add `TAKE` or avoid inventory pickup.
- `Unreachable`: check starting room, reveal arrows, state-specific interactions, consumed inventory, and verb states.
- `Room object ... has -> player in multiple rooms`: explicitly declare inventory or use different object names.
- Collision/runtime allocation failure: reduce dense wildcard/multi-target surfaces, split puzzles, or reduce object/verb count.

Paper-play checks:

- Every reveal narrative explains what the player is asked to write.
- Every trash/state-change instruction makes sense after the story text.
- Every room transition has a way back or an intentional point of no return.
- Critical items are not trashed before their last required use.
- State names describe the changed affordance, not just chronology.
- Wildcards do not mask a puzzle response that should be explicit.

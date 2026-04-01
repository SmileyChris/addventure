# Writing Rooms

Every `.md` file in your game directory (besides `index.md`) defines one or more rooms. Files are loaded alphabetically, but the order doesn't affect gameplay.

## Room headers

A room starts with a `#` header. The header text becomes the room name:

```markdown
# Engine Room
```

You can define multiple rooms in one file, but one room per file is easier to manage.

## Room descriptions

A room-level interaction sits directly under the header — no `+` prefix, no noun name:

```markdown
# Engine Room
LOOK: Pipes criss-cross the ceiling. The air is thick with steam.
```

This is what players read when they LOOK at the room itself. It sets the scene.

## Nouns

Nouns are objects inside a room. Write them as bare `ALL_CAPS` names on their own line:

```markdown
# Engine Room
LOOK: Pipes criss-cross the ceiling. The air is thick with steam.

VALVE
GAUGE
TOOLBOX
```

Each noun gets its own ID on the printed room sheet. Players can target nouns by adding verb + noun IDs.

### Naming rules

Noun names must be `ALL_CAPS` with optional underscores: `VALVE`, `FUEL_TANK`, `CONTROL_PANEL`. This distinguishes them from narrative text.

The same name can appear in different rooms — the compiler treats them as separate entities.

## Interactions

Interactions define what happens when a player uses a verb on a noun. They use the `+` prefix:

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

A noun can respond to multiple verbs:

```markdown
GAUGE
+ LOOK: A pressure gauge. The needle is deep in the red.
+ USE: You tap the glass. The needle doesn't budge.
```

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

## Indentation

Addventure uses 2-space indentation to define structure. The hierarchy works like this:

```
NOUN_NAME                    ← level 0: noun declaration
+ VERB:                      ← level 1: interaction
  Narrative text             ← level 2: narrative body
  - ENTITY -> destination    ← level 2: arrow (state change)
    + VERB:                  ← level 3: interaction on new state
      More narrative         ← level 4: nested narrative
```

Each level is two spaces deeper than the last. Indentation is how the compiler knows which arrows and interactions belong together.

## Comments

Use `//` to add comments that the compiler ignores:

```markdown
// TODO: add a puzzle here
VALVE
+ LOOK: A large red valve.
// + USE: You turn the valve. — disabled for now
```

## Putting it together

Here's a complete room with two interactive nouns:

```markdown
# Storage Bay
LOOK: Crates are stacked floor to ceiling. A forklift sits idle in the corner.

CRATE
+ LOOK: Shipping labels are torn off. Could be anything inside.

FORKLIFT
+ LOOK: Keys still in the ignition. Fuel gauge reads empty.
+ USE: The engine sputters and dies. No fuel.
```

This gives players a room to explore with two objects, each responding to LOOK, and one that also responds to USE. But nothing changes yet — for that, we need arrows and state changes.

Next: [State & Transformation](state-and-transformation.md).

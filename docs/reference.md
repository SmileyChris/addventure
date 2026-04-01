# Script Reference

Quick-reference for Addventure's script syntax.

## File structure

A game is a directory of `.md` files:

| File | Purpose |
|---|---|
| `index.md` | Metadata (frontmatter), verb list, item list |
| `*.md` (all others) | Room definitions, loaded alphabetically |

## Frontmatter

YAML metadata between `---` fences at the top of `index.md`:

```markdown
---
title: My Game
author: Jane Doe
start: Entrance Hall
---
```

| Field | Description |
|---|---|
| `title` | Game title, shown on printed sheets |
| `author` | Author name, shown in footers |
| `start` | Starting room name (must match a `#` header) |

## Index sections

```markdown
# Verbs
LOOK
USE
TAKE

# Items
CROWBAR
KEYCARD
```

List one name per line, `ALL_CAPS`.

## Room files

### Room header

```markdown
# Room Name
```

Starts a new room. The text after `#` is the room name.

### Room-level interaction

```markdown
LOOK: Description of the room.
```

No `+` prefix. Defines what happens when a verb targets the room itself.

### Nouns

```markdown
NOUN_NAME
```

Bare `ALL_CAPS` name on its own line. Declares an object in the room.

### Entity interactions

```markdown
+ VERB: Inline narrative.

+ VERB:
  Block narrative on
  indented lines.
```

### Multi-target interactions

```markdown
+ VERB + TARGET:
  Narrative text.
```

Requires verb + entity + target (three IDs added).

### Arrows

```markdown
- SUBJECT -> DESTINATION
```

Fires when the parent interaction triggers.

### Child interactions (state-specific)

```markdown
- ENTITY -> ENTITY__STATE
  + VERB: New response in this state.
```

Nested under the arrow that creates the state.

## Arrow destinations

| Destination | Effect |
|---|---|
| `player` | Move to inventory (auto-creates item; inventory ID = TAKE + noun ID) |
| `trash` | Remove entity from the game |
| `room` | Place entity in the current room |
| `"Room Name"` | Move the player to another room |
| `ENTITY__STATE` | Transform entity to a new state |
| `VERB__STATE` | Transform a verb to a new state |
| `? -> "Room"` | Cue: deferred cross-room effect (see [Advanced](advanced.md#cue-checks-cross-room-effects)) |

## Special syntax

| Syntax | Meaning |
|---|---|
| `ENTITY__STATE` | Double-underscore separates base name from state |
| `@room` | Reference to the current room entity |
| `*` | Wildcard — matches all entities in the room |
| `//` | Comment — ignored by the compiler |
| `# Interactions` | Section for standalone interactions in a room file |
| `? -> "Room"` | Cue arrow — deferred effect in another room |
| `? -> "Room__STATE"` | Cue targeting a specific room state |
| `? -> "Room__"` | Cue targeting only the base room state |

## Naming rules

- Nouns, items, and verbs: `ALL_CAPS` with optional underscores
- States: `BASE__STATE` (double underscore)
- Room names: any text after `#`, case-sensitive
- Room references in arrows: must be quoted (`"Room Name"`)

## ID ranges

The compiler randomly assigns IDs from these ranges:

| Entity type | Range | Excluded |
|---|---|---|
| Verbs | 11–99 | Multiples of 5 and 10 |
| Entities (rooms, nouns, items) | 100–999 | Multiples of 5 and 10 |

IDs are re-randomized on each build.

## CLI commands

```bash
uv run adv build [dir]           # Compile to PDF (default)
uv run adv build [dir] --text    # Compile to plain text
uv run adv build [dir] -o FILE   # Custom output path
uv run adv new [name]            # Scaffold a new game
```

If no directory is given, `adv build` looks for `index.md` in the current directory, then falls back to `games/example`.

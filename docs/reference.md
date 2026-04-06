# Script Reference

Quick-reference for Addventure's script syntax.

## File structure

A game is a directory of `.md` files:

| File | Purpose |
|---|---|
| `index.md` | Metadata (frontmatter), verb list, inventory object list |
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
| `entry_prefix` | Prefix for ledger entry labels (default: none) |
| `image` | Path to cover/watermark image |
| `image_height` | Height of the cover image |
| `name_style` | Identifier rendering style: `upper_words` (default) or `title` |

Unknown keys are accepted but produce a build warning.

## Index sections

```markdown
# Verbs
LOOK
USE
TAKE

# Inventory
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

### Room objects

```markdown
NOUN_NAME
```

Bare `ALL_CAPS` name on its own line. Declares a room object.

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

### Actions

```markdown
> GO_NORTH
  Narrative text.
  - player -> "Room Name"
```

Direct ledger lookup — no addition needed. Printed on room sheet with entry reference. Nested under an interaction, the action becomes discoverable.

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
| `player` | Move to inventory (auto-creates inventory object; inventory ID = TAKE + room object ID) |
| `trash` | Remove entity from the game |
| `room` | Place entity in the current room |
| `"Room Name"` | Move the player to another room |
| `ENTITY__STATE` | Transform entity to a new state |
| `VERB__STATE` | Transform a verb to a new state |
| `-> VERB` | Reveal a new verb on the player's verb sheet (no subject) |
| `VERB -> trash` | Remove a verb from the player's verb sheet |
| `? -> "Room"` | Cue: deferred cross-room effect (see [Advanced](advanced.md#cue-checks-cross-room-effects)) |
| `ACTION_NAME -> trash` | Remove an action from the room sheet |

## Special syntax

| Syntax | Meaning |
|---|---|
| `> ACTION_NAME` | Declare an action (direct ledger lookup, no addition) |
| `ENTITY__STATE` | Double-underscore separates base name from state |
| `*` | Wildcard — matches all entities in the room |
| `//` | Comment — ignored by the compiler |
| `## Interactions` | Section for standalone interactions in a room file |
| `? -> "Room"` | Cue arrow — deferred effect in another room |
| `? -> "Room__STATE"` | Cue targeting a specific room state |
| `? -> "Room__"` | Cue targeting only the base room state |

## Naming rules

- Room objects, inventory objects, verbs, and actions: `ALL_CAPS` with optional single underscores between segments
- States: `BASE__STATE` (double underscore)

Plain identifiers may not contain `__`. Double underscore is reserved for state syntax only.

## Name rendering

Identifiers are authored in strict machine form, such as `GO_NORTH` or `WALL_PANEL`.
By default they are rendered for players with spaces: `GO NORTH`, `WALL PANEL`.

You can change the default rendering style in frontmatter:

```markdown
---
name_style: title
---
```

Supported values:

- `upper_words` — `GO_NORTH` → `GO NORTH`
- `title` — `GO_NORTH` → `Go North`

## Wildcard

`*` is only valid as the entire target list of an interaction:

```markdown
LOOK + *:
  You scan the room.
```

It is not valid inside multi-target or alternation forms:

```markdown
USE + * + KEY:   // invalid
USE + BOX|*:     // invalid
```

## Comments

Use `//` for comments.

- Full-line comments are allowed anywhere.
- Trailing comments are allowed on structural lines such as frontmatter, declarations, interaction headers, arrows, and actions.
- Trailing comments are not stripped from narrative text, so `//` remains literal inside prose.
- Room names: any text after `#`, case-sensitive
- Room references in arrows: must be quoted (`"Room Name"`)

## ID ranges

The compiler randomly assigns IDs from these ranges:

| Entity type | Range | Excluded |
|---|---|---|
| Verbs | 11–99 | Multiples of 5 and 10 |
| Entities (rooms, room objects, inventory objects) | 100–999 | Multiples of 5 and 10 |

IDs are re-randomized on each build.

## CLI commands

```bash
addventure build [dir]                    # Compile to PDF (default)
addventure build [dir] --md              # Compile to markdown
addventure build [dir] -o FILE           # Custom output path
addventure build [dir] --paper a4        # Paper size: a4 (default), letter, legal
addventure build [dir] --blind           # Blind mode: room names/IDs hidden until discovered
addventure build [dir] --fragment MODE   # Fragment output mode (see below)
addventure new [name]                    # Scaffold a new game
```

If no directory is given, `addventure build` looks for `index.md` in the current directory, then falls back to `games/example`.

### Fragment modes

The `--fragment` flag controls how `::: fragment` blocks are output:

| Mode | Effect |
|------|--------|
| `included` | Fragments appended at the back of the main PDF (default) |
| `separate` | Fragments emitted as `<name>-fragments.pdf`; main PDF has none |
| `jigsaw` | Fragments sliced into shuffled rectangular pieces across cut pages |

`--fragment separate` is useful when you want to print and distribute fragments as physical notes — cut them out and hand them to players in envelopes labelled with the ref (e.g. `Alpha`).

# Reference

## File structure

A game is a directory of `.md` files:

| File | Purpose |
|---|---|
| `index.md` | Metadata (frontmatter), verb list, inventory object list |
| `*.md` (all others) | Room definitions, loaded alphabetically |

## CLI commands

### build

Compile a game to PDF (default) or markdown.

```bash
addventure build [dir]               # Compile to PDF (default)
addventure build [dir] --md          # Compile to markdown
addventure build [dir] -o FILE       # Custom output path
addventure build [dir] --paper SIZE  # Paper size: a4 (default), letter, legal
addventure build [dir] --blind       # Blind mode: room names/IDs hidden until discovered
addventure build [dir] --no-cover    # Omit the How to Play cover page
addventure build [dir] --fragment MODE  # Fragment output mode (see below)
addventure build [dir] --all           # Build all chapters into one output
```

If no directory is given, looks for `index.md` in the current directory.

`--all` discovers chapter subdirectories (those containing `index.md` with a `# Verbs` header), builds each independently, and combines them into a single PDF or markdown output. Warns if any chapters share the same `entry_prefix`.

#### Fragment modes

The `--fragment` flag controls how `::: fragment` blocks are output:

| Mode | Effect |
|------|--------|
| `included` | Fragments appended at the back of the main PDF (default) |
| `separate` | Fragments emitted as `<name>-fragments.pdf`; main PDF has none |
| `jigsaw` | Fragments sliced into shuffled rectangular pieces across cut pages |

`--fragment separate` is useful when you want to print and distribute fragments as physical notes — cut them out and hand them to players in envelopes labelled with the ref (e.g. `Alpha`).

### new

Scaffold a new game directory with a starter `index.md`.

```bash
addventure new [name]   # Scaffold with defaults (oneshot)
addventure new          # Interactive setup (choose verbs, set author name)
```

Run from inside an existing game directory to scaffold a new chapter subdirectory instead. The chapter is automatically assigned the next available ledger prefix (B, C, D...).

## Index files

### Frontmatter

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
| `entry_prefix` | Prefix for ledger entry labels (default: `A`). Auto-assigned by `addventure new` for chapters |
| `image` | Path to cover/watermark image |
| `image_height` | Height of the cover image |
| `name_style` | Identifier rendering style: `upper_words` (default) or `title` — see [Name rendering](#name-rendering) |

Unknown keys are accepted but produce a build warning.

### Sections

```markdown
# Verbs
LOOK
USE
TAKE

# Inventory
CROWBAR
KEYCARD
```

List one name per line, `ALL_CAPS`. `# Inventory` is only needed for objects that never exist as room objects — most objects are auto-registered when they have a `-> player` arrow in a room.

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
ENTITY_NAME
```

Bare `ALL_CAPS` name on its own line. Declares a room object.

### Interactions

```markdown
+ VERB: Inline narrative.

+ VERB:
  Block narrative on
  indented lines.

+ VERB + TARGET:
  Multi-target: requires verb + object + target (three IDs added).
```

### Actions

```markdown
> ACTION_NAME
  Narrative text.
  - player -> "Room Name"
```

Direct ledger lookup — no addition needed. Printed on the room sheet with an entry reference. Nested inside an interaction body, the action becomes discoverable.

### Arrows

```markdown
- SUBJECT -> DESTINATION
```

Fires when the parent interaction triggers. See [Arrow destinations](#arrow-destinations) below.

### State-specific interactions

```markdown
- ENTITY -> ENTITY__STATE
  + VERB: New response in this state.
```

Nested under the arrow that creates the state.

### Freeform interactions

```markdown
## Interactions

VERB + TARGET:
  Narrative.
```

Room-level interactions not tied to a specific room object. Goes at the bottom of a room file.

### Fragment blocks

```markdown
+ VERB:
  Narrative.

  ::: fragment
  Long-form hidden content revealed when this entry fires.
  :::
```

Content inside `::: fragment` is Typst markup. See [Fragment modes](#fragment-modes).

## Script reference

### Arrow destinations

| Destination | Effect |
|---|---|
| `player` | Move to inventory (auto-creates inventory object; inventory ID = TAKE + room object ID) |
| `trash` | Remove object from the game |
| `room` | Place object in the current room |
| `"Room Name"` | Move the player to another room |
| `ENTITY__STATE` | Transform object to a new state |
| `VERB__STATE` | Transform a verb to a new state |
| `-> VERB` | Reveal a new verb on the player's verb sheet (no subject) |
| `VERB -> trash` | Remove a verb from the player's verb sheet |
| `? -> "Room"` | Cue: deferred cross-room effect (see [Advanced](advanced.md#cue-checks-cross-room-effects)) |
| `ACTION_NAME -> trash` | Remove an action from the room sheet |

### Signals

Signals carry narrative state between chapters. A signal is a named flag — the player writes its numeric ID at the end of one chapter and checks it at the start of the next.

#### Defining signals

In the receiving chapter's `index.md`:

```
# Signals
EVERYONE_OUT_ESCAPE
WITNESS_ESCAPE
```

Signal IDs are derived automatically from the name (deterministic hash).

#### Emitting signals

In the sending chapter, use a signal arrow:

```
+ USE + AIR_DUCT:
  You escape through the vent...
  - -> signal EVERYONE_OUT_ESCAPE
```

The player instruction: "Write 64745 in your signals."

#### Signal checks

Signal checks branch narrative based on which signals the player has. They use `NAME?` syntax with `otherwise?` as the default.

In the index description (fires at chapter start):

```
EVERYONE_OUT_ESCAPE?
  A companion catches up to you...
WITNESS_ESCAPE?
  You're alone.
otherwise?
  Default text.
```

In interaction bodies (fires during play):

```
+ USE:
  Common narrative.
  EVERYONE_OUT_ESCAPE?
    Branch A text.
  otherwise?
    Default text.
```

All matching branches fire — if the player has multiple signals, they read every matching entry. `otherwise?` fires only when no signal matches.

On the printed sheet, signal checks render as: "Check your signals: **64745** → read B-3. **92951** → read B-7. Otherwise → read B-12."

### Special syntax

| Syntax | Meaning |
|---|---|
| `ENTITY__STATE` | Double-underscore separates base name from state |
| `*` | Wildcard — matches all room objects in an interaction (see [Wildcards](advanced.md#wildcards)) |
| `//` | Comment — ignored by the compiler |
| `## Interactions` | Section for freeform interactions in a room file (see [The Interactions section](advanced.md#the-interactions-section)) |
| `? -> "Room"` | Cue arrow — deferred effect in another room |
| `? -> "Room__STATE"` | Cue targeting a specific room state |
| `? -> "Room__"` | Cue targeting only the base room state |

`*` is only valid as the entire target of an interaction (`LOOK + *:`). It is not valid inside multi-target or alternation forms (`USE + * + KEY:`, `USE + BOX|*:`).

Trailing `//` comments are not stripped from narrative text — `//` inside prose is treated as literal text.

### Naming rules

- Room objects, inventory objects, verbs, and actions: `ALL_CAPS` with optional single underscores between segments
- States: `BASE__STATE` (double underscore)
- Room names: any text after `#`, case-sensitive
- Room references in arrows: must be quoted (`"Room Name"`)

Plain identifiers may not contain `__`. Double underscore is reserved for state syntax only.

### Name rendering

Identifiers are authored in strict machine form (`GO_NORTH`, `WALL_PANEL`) and rendered for players with spaces by default (`GO NORTH`, `WALL PANEL`). Set `name_style` in frontmatter to change this:

```markdown
---
name_style: title
---
```

| Value | Example |
|---|---|
| `upper_words` (default) | `GO_NORTH` → `GO NORTH` |
| `title` | `GO_NORTH` → `Go North` |

This affects verbs, room objects, inventory objects, states, and actions on the printed sheets. It does not affect free-text room names or narrative prose.


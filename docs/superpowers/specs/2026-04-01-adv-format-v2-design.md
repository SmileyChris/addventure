# .md Format — Markdown-Based Game Scripts

## Summary

Redesign the game script format to use `.md` files with markdown conventions: `#` headers, `---` frontmatter fences, `+`/`-` semantic list markers, unquoted narrative text, and `//` comments. Files render readably in any markdown viewer. The entry point is `index.md` (replaces `global.adv`), containing both metadata and global definitions.

## Format Changes

### Headers: `#` instead of `--- name ---`

Old:
```
--- verbs ---
--- "Control Room" ---
--- interactions ---
```

New:
```
# Verbs
# Control Room
# Interactions
```

Room names no longer need quotes — everything after `# ` is the header name. Section types (`Verbs`, `Items`, `Interactions`) are case-insensitive. Anything else is a room name.

### Frontmatter: `---` fences for metadata

```
---
title: The Facility
author: Chris
---

# Verbs
USE
```

Key-value pairs between `---` fences at the top of `index.md`. Parsed into a `metadata` dict on `GameData`. Optional — files without frontmatter work fine.

Supported keys (all optional): `title`, `author`, `version`, `description`, `parts` (comma-separated list of subdirectory names for multi-part games).

### List markers: `+` for additions, `-` for state changes

- `+` prefixes interactions and behaviors added to an entity (verbs, nested entity definitions)
- `-` prefixes arrows (state changes, movement, destruction)
- Narrative text has no prefix — just indented plain text under an interaction

Old:
```
TERMINAL
  LOOK: "A dusty CRT."
  USE + KEYCARD:
    "You slide the keycard."
    TERMINAL -> TERMINAL__UNLOCKED
    KEYCARD -> trash
```

New:
```
TERMINAL
+ LOOK: A dusty CRT.
+ USE + KEYCARD:
  You slide the keycard.
  - TERMINAL -> TERMINAL__UNLOCKED
  - KEYCARD -> trash
```

The `+`/`-` markers are **required** for structural lines nested under an entity. The parser uses them to distinguish structure from narrative. Top-level entity names (like `TERMINAL` itself) remain bare — they're at root indent of a room section.

### Unquoted narrative text

Narrative text no longer needs surrounding double quotes. Quotes are removed everywhere except room references in arrows, which still need them to distinguish multi-word room names from entity names:

```
- player -> "Basement"
```

Inline narratives after `:` are also unquoted:
```
+ LOOK: A dusty CRT. A keycard slot sits beside it.
```

### Comments: `//`

```
// This interaction requires the crowbar from Part 1
+ USE + CROWBAR:
```

`//` replaces `#` as the comment marker (since `#` is now headers).

## Indentation Rules

Indentation still uses 2-space increments and defines hierarchy. The `+`/`-` markers sit at the indentation level of their parent's children:

```
TERMINAL                    // indent 0: entity declaration
+ LOOK: A dusty CRT.       // indent 0: behavior of TERMINAL
+ USE + KEYCARD:            // indent 0: interaction on TERMINAL
  You slide the keycard.    // indent 1: narrative (no marker)
  - TERMINAL -> TERMINAL__UNLOCKED  // indent 1: arrow
    + LOOK: Scrolling text.         // indent 2: behavior of new state
  - KEYCARD -> trash        // indent 1: arrow
```

## Model Changes

Add `metadata: dict[str, str]` field to `GameData` (default empty dict).

## Parser Changes

1. **Frontmatter parsing**: Detect opening `---`, collect key-value lines until closing `---`
2. **Header detection**: `_is_header` matches lines starting with `# ` instead of `--- ... ---`
3. **Header parsing**: `_parse_header` strips `# ` prefix, checks for known sections (verbs/items/interactions case-insensitive), everything else is a room name
4. **Comment detection**: Skip lines starting with `//` (stripped) instead of `#`
5. **List marker parsing**: Strip leading `+`/`-` from structural lines, use the marker to validate line type (arrows must use `-`)
6. **Narrative parsing**: Accept unquoted text (lines without `+`, `-`, `->`, or `:` interaction headers) as narrative
7. **Arrow detection**: `_is_arrow` no longer needs the quote check since narratives are unquoted

## File Structure

Entry point is `index.md` (replaces `global.adv`). All other `.md` files in the directory are room scripts, loaded alphabetically.

```
games/facility/
  index.md           # meta + verbs + items
  control_room.md
  basement.md
  The Underground/   # part 2
    index.md         # new verbs/items for part 2
    tunnels.md
```

The CLI looks for `index.md` instead of `global.adv`.

## Multi-Part Stories (Future)

The frontmatter `parts` key and directory-based structure are designed but not implemented in this change. Future work:
- Subdirectories as parts, each with its own `index.md` for new verbs/items
- Root-level files = Part 1, directory name from `title` in frontmatter
- Each part compiles semi-independently, inheriting items from prior parts

## Migration

The example game files are rewritten from `.adv` to `.md`. The old format is no longer supported — this is a clean break (the project has no external users yet).

## Complete Example

```markdown
---
title: The Facility
author: Chris
---

# Verbs
USE
TAKE
LOOK

# Items
CROWBAR
KEYCARD
KNIFE

# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout.
  - KEYCARD -> trash
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    + HATCH -> room
      + LOOK: A dark opening, just wide enough to squeeze through.
      + USE:
        You lower yourself into the darkness.
        - player -> "Basement"

CRATE
+ LOOK: A heavy wooden crate, nailed shut.
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

WALL_PANEL
+ LOOK: Featureless steel bolted to the wall.

BINDINGS
+ LOOK: Thick rope bindings around your wrists.

# Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

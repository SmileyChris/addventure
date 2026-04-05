# Sealed Text Feature Design

## Summary

Sealed texts are long-form content blocks that get printed as separate foldable pages, hidden from the player until a ledger entry directs them to open one. They serve two purposes: dramatic reveals (finales, plot twists) and physical props (maps, cipher keys, puzzle pieces).

## Authoring Syntax

Sealed text is authored inline within an interaction block using `:::` fencing:

```markdown
+ USE + KEY:
  You turn the key and hear a heavy click.
  - player -> "Throne Room"

  ::: sealed
  The door groans open. Before you stretches a vast hall,
  its ceiling lost in shadow. At the far end, seated on
  a throne of twisted iron, sits the figure you've been
  hunting for three years...

  As many paragraphs as needed. Full Typst markup supported.
  :::
```

### Rules

- The `:::` fence must appear inside an interaction block (under a `+` line), at narrative indentation level (2-space indent, same as narrative text and arrows).
- Content outside the fence becomes the normal ledger entry narrative. Content inside the fence becomes the sealed page.
- If there is no narrative outside the fence, the ledger entry contains only the auto-generated "Open Sealed Text X-N" instruction (plus any arrow-generated instructions).
- Arrows (`-` lines) remain outside the fence and generate instructions in the normal ledger entry as usual.
- Images can be referenced inside the fence using `![](filename.png)` — resolved relative to the game directory, same as the existing `image:` metadata field.
- A single interaction can have at most one `::: sealed` block.

### Example: Physical Prop

```markdown
+ EXAMINE + DESK:
  You find a crumpled note tucked under the drawer lining.

  ::: sealed
  *Keep this page — you'll need it later.*

  ![](cipher_wheel.png)
  :::
```

### Example: Finale

```markdown
+ USE + CROWN + THRONE:
  A blinding light fills the room. Everything changes.
  - CROWN -> trash

  ::: sealed
  Chapter VII: The Reckoning

  The light fades slowly. You find yourself standing in a place
  you recognize — the village square where it all began, years ago.
  But something is different...

  [Multiple paragraphs of finale text]

  *Congratulations. You have completed The Crown of Iron.*
  :::
```

## Compiler Changes

### Model (`models.py`)

New dataclass:

```python
@dataclass
class SealedText:
    ref: str           # Opaque reference code, e.g. "K-7"
    content: str       # The sealed text content (may contain markup/image refs)
    images: list[str]  # Image filenames referenced in the content
    source_line: int
    room: str
    entry_number: int = 0  # The ledger entry that triggers this
```

Add to `GameData`:

```python
sealed_texts: list[SealedText] = field(default_factory=list)
```

### Parser (`parser.py`)

- Detect `:::` or `::: sealed` opening fence at narrative indentation level within a `+` block.
- Collect all lines until the closing `:::` fence.
- Store the content as a `SealedText` on the interaction (or in a parallel structure).
- Extract image references (`![](filename)`) and store filenames for later resolution.
- Reject `:::` fences that appear outside interaction blocks.
- Reject multiple `:::` fences within a single interaction.

### Compiler (`compiler.py`)

- Generate opaque reference codes for sealed texts: single uppercase letter + hyphen + random digit(s), e.g. "K-7", "M-3". Letters chosen to avoid ambiguity (no I/O/S/Z). Ensure uniqueness within the game.
- Link each `SealedText` to its parent `ResolvedInteraction` via `entry_number`.
- No new ID allocation pool needed — sealed texts don't participate in the addition system.

### Grammar (`docs/grammar.ebnf`)

Add `sealed_block` production:

```
sealed_block = sealed_open, { content_line }, sealed_close ;
sealed_open  = indent, ":::", [ " sealed" ], newline ;
sealed_close = indent, ":::", newline ;
```

## Writer Changes

### Instruction Generation (`writer.py`)

When a `ResolvedInteraction` has an associated sealed text, append an instruction:

```
Open Sealed Text {ref}.
```

This is appended after all arrow-generated instructions.

### PDF Output (`pdf_writer.py`)

Add sealed texts to the serialized data:

```python
"sealed_texts": [
    {
        "ref": "K-7",
        "content": "The door groans open...",
        "images": ["/absolute/path/to/cipher_wheel.png"],
    },
    ...
]
```

### Markdown Output (`md_writer.py`)

Sealed texts render as a separate section at the end:

```markdown
---

## Sealed Texts

### Sealed Text K-7
> ⚠ Do not read until directed.

The door groans open...
```

## PDF Layout (Typst Template)

### Page Structure

Each sealed text gets its own PDF page, placed **after the story ledger** (last pages of the document).

### Fold Design

The page is divided into two halves by a horizontal fold line:

**Top half (outer face when folded):**
- Centered: "SEALED TEXT {ref}" in large type
- Below: "Do not open until directed."
- Subtle fold-line indicator at the midpoint

**Bottom half (inner face when folded — printed upside-down relative to top half):**
- The sealed content, rotated 180° so it reads correctly when the page is unfolded
- Images rendered inline
- Full Typst markup supported (bold, italic, paragraphs, etc.)

The 180° rotation means even if the fold comes loose, a casual glance at the page shows upside-down text — not immediately readable.

### Prep Instructions

The verb sheet (or cover page) gains a prep note:

> **Before playing:** This game includes sealed texts. Cut or fold each sealed page along the marked line and keep them face-down. Do not read them until a ledger entry tells you to.

This note only appears when the game contains sealed texts.

## Scope and Non-Goals

- No decoy/padding pages. The player can see how many sealed texts exist.
- No new trigger mechanism. Sealed texts are triggered by normal interactions via the existing addition system.
- No special handling for blind mode beyond ensuring sealed text refs work the same way.
- No digital/interactive reveal mechanism — this is paper-only.
- Images inside sealed text are a stretch goal. The initial implementation may support text-only and add image support as a follow-up.

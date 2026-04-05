# Sealed Text Feature Design

## Summary

Sealed texts are content blocks hidden from the player until a ledger entry directs them to reveal one. They serve two purposes: dramatic reveals (finales, plot twists) and physical props (maps, cipher keys, puzzle pieces).

Two output modes are available, selected at build time:

- **Extended ledger** (default) — sealed content renders as a separate section at the back of the story ledger, after all normal entries. Simple, no prep work, relies on player discipline not to read ahead.
- **Jigsaw** (`--jigsaw` flag) — sealed content is sliced into rectangular grid pieces, shuffled, and interleaved with pieces from other sealed texts on shared cut pages. Random 180° rotation on individual pieces. No position labels — the player assembles by matching text flow across edges, like a real jigsaw. True physical concealment.

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
- Content outside the fence becomes the normal ledger entry narrative. Content inside the fence becomes the sealed content.
- If there is no narrative outside the fence, the ledger entry contains only the auto-generated sealed text instruction (plus any arrow-generated instructions).
- Arrows (`-` lines) remain outside the fence and generate instructions in the normal ledger entry as usual.
- Images can be referenced inside the fence using `![](filename.png)` — resolved relative to the game directory, same as the existing `image:` metadata field.
- A single interaction can have at most one `:::` sealed block.

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

- Detect `::: sealed` opening fence at narrative indentation level within a `+` block.
- Collect all lines until the closing `:::` fence.
- Store the content on the `Interaction` (new `sealed_content: str | None` field).
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
sealed_open  = indent, "::: sealed", newline ;
sealed_close = indent, ":::", newline ;
```

## Writer Changes

### Instruction Generation (`writer.py`)

When a `ResolvedInteraction` has an associated sealed text, append an instruction depending on output mode:

- **Extended ledger:** `Turn to Sealed Text {ref}.`
- **Jigsaw:** `Find and assemble the {ref} pieces.`

This is appended after all arrow-generated instructions.

### CLI (`cli.py`)

New flag on `adv build`:

```
--jigsaw    Output sealed texts as jigsaw cut pages (default: extended ledger)
```

The `--jigsaw` flag is independent of `--md`. In markdown mode, sealed texts always render as a plaintext section (no jigsaw).

### PDF Output (`pdf_writer.py`)

Sealed text data is serialized for both modes:

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

For jigsaw mode, additional grid data is computed by the two-pass pipeline (see below) and merged into the JSON.

### Markdown Output (`md_writer.py`)

Sealed texts always render as a separate section at the end (no concealment in markdown mode):

```markdown
---

## Sealed Texts

### Sealed Text K-7
> ⚠ Do not read until directed.

The door groans open...
```

## Extended Ledger Mode (Default PDF Layout)

Sealed texts render as a separate section after the main story ledger, titled "Sealed Texts." Each sealed text is a full-width block (not two-column like normal ledger entries) with its reference code as a header. Content supports full Typst markup. The section has a brief note: "Do not read ahead — turn to a sealed text only when directed by a ledger entry."

## Jigsaw Mode (PDF Layout, `--jigsaw`)

### Two-Pass Build Pipeline

Jigsaw mode uses a two-pass approach to achieve accurate content measurement:

**Pass 1 — Measure:** Each sealed text is rendered via Typst as a standalone page with `height: auto` and fixed content width (printable page width minus margins). The resulting PDF page dimensions give the exact rendered content size. Python reads these dimensions via pypdf.

**Python — Compute grid:** From the measured content dimensions, Python computes:
- Grid columns (fixed at 4 for standard content width)
- A **fixed cell height** shared across all sealed texts in the game (target ~25mm). Each text gets as many rows as needed to cover its content height — shorter texts have fewer rows, longer texts have more, but all cells are the same dimensions. This allows pieces from different sealed texts to be interleaved on the same cut pages.
- Grid rows per sealed text (content height / cell height, rounded up)
- Deterministic shuffle and flip assignments (see below)
- Interleaving of pieces from multiple sealed texts
- The complete piece list is written as JSON data

**Pass 2 — Slice:** The main Typst compilation receives the grid data as JSON input. For each piece, Typst uses `box(clip: true)` with `move(dx, dy)` to show only the piece's portion of the full content block. Flipped pieces are wrapped in `rotate(180deg)`. The `align(left + top)` rule must be set inside each clip box to prevent alignment inheritance.

**Border technique:** Each clip box is expanded by the stroke width (`kerf`) so that the stroke covers a thin strip of adjacent content rather than this piece's own content. The clip box is `cell-w + kerf` wide and offset by `-kerf/2`, so the border sits entirely outside the piece's actual content area. This prevents borders from obscuring text at any stroke width. Pass 1 uses a matching page margin so the content block has padding at the outer edges for the same purpose.

### Piece Layout

- Pieces are rectangular (wider than tall), matching the natural shape of text content.
- All pieces from all sealed texts are interleaved on shared cut pages with zero gaps.
- **Deterministic shuffle:** Pieces are reordered using an every-3rd interleave pattern (e.g. positions 1,4,7,2,5,8,3,6) so that no originally-adjacent pieces end up next to each other on the cut page. When multiple sealed texts are present, their pieces are interleaved with each other, further separating original neighbors.
- **Deterministic flips:** 180° rotation follows a checkerboard pattern on the cut page — alternating up/down per column, inverted each row. No randomness.
- No position numbers or grid dimension hints — the player assembles by matching text flow, line continuations, and paragraph breaks across piece edges.
- A small ref code (e.g. "K-7") appears in the corner of each piece for grouping only — so the player can sort pieces by sealed text before assembling.
- Empty pieces (cells with no visible content) are skipped from the output.

### Assembly Instructions

The verb sheet (or cover page) gains a note when the game contains sealed texts:

> **Sealed Texts:** This game includes hidden content on the cut pages. When directed by a ledger entry, find the matching pieces, cut them out, and assemble them to reveal the content.

## Scope and Non-Goals

- No decoy/padding pieces. The player can see the total count.
- No new trigger mechanism. Sealed texts are triggered by normal interactions via the existing addition system.
- No special handling for blind mode beyond ensuring sealed text refs work the same way.
- No digital/QR code delivery — paper-only for the initial implementation. QR codes as an alternative delivery mechanism are a potential future enhancement.
- Images inside sealed text are a stretch goal. The initial implementation may support text-only and add image support as a follow-up.

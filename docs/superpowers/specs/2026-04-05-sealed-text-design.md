# Sealed Text Feature Design

## Summary

Sealed texts are content blocks hidden from the player until a ledger entry directs them to reveal one. They serve two purposes: dramatic reveals (finales, plot twists) and physical props (maps, cipher keys, puzzle pieces).

Two output modes are available, selected at build time:

- **Extended ledger** (default) — sealed content renders as a separate section at the back of the story ledger, after all normal entries. Simple, no prep work, relies on player discipline not to read ahead.
- **Jigsaw** (`--jigsaw` flag) — sealed content is sliced into grid squares, shuffled, and interleaved with squares from other sealed texts on shared cut pages. The player cuts out the squares and assembles them by position number to reveal the content. True physical concealment — the scrambling itself prevents accidental reading.

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
- If there is no narrative outside the fence, the ledger entry contains only the auto-generated "Assemble Sealed Text X-N" instruction (plus any arrow-generated instructions).
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
- **Jigsaw:** `Cut out and assemble the {ref} squares.`

This is appended after all arrow-generated instructions.

### PDF Output (`pdf_writer.py`)

Add sealed texts to the serialized data:

```python
"sealed_texts": [
    {
        "ref": "K-7",
        "content": "The door groans open...",
        "images": ["/absolute/path/to/cipher_wheel.png"],
        "grid": 3,  # 3x3 grid
    },
    ...
]
```

### CLI (`cli.py`)

New flag on `adv build`:

```
--jigsaw    Output sealed texts as jigsaw cut pages (default: extended ledger)
```

The `--jigsaw` flag is independent of `--md`. In markdown mode, sealed texts always render as a plaintext section (no jigsaw).

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

### How It Works

1. The compiler renders each sealed text (or image) as a rectangular block.
2. The block is sliced into a grid (default 3×3 for short content, 4×4 for larger content).
3. Each square is labeled with its reference and position: e.g. "K-7:1" through "K-7:9".
4. All squares from all sealed texts are shuffled together and laid out on shared "cut pages" at the end of the PDF, with printed cut lines.
5. When a ledger entry tells the player to assemble a sealed text, they find and cut out the relevant squares and arrange them in grid order to reveal the content.

### Grid Size Selection

The compiler auto-selects grid size based on content:

| Content size | Grid | Squares |
|---|---|---|
| Short text or small image | 3×3 | 9 |
| Medium text or larger image | 4×4 | 16 |

Authors can override via metadata if needed (future option).

### Square Layout on Cut Pages

- Squares are arranged in a dense grid on each cut page, filling the printable area.
- Cut lines are printed between squares.
- Each square shows its content fragment on one side and its label (e.g. "K-7:5") in a small corner.
- Squares from different sealed texts are interleaved — no grouping by reference. This means even after cutting, a casual glance at loose squares reveals nothing coherent.

### Assembly Instructions

The verb sheet (or cover page) gains a note when the game contains sealed texts:

> **Sealed Texts:** This game includes hidden content. When directed by a ledger entry, find the matching squares on the cut pages, cut them out, and arrange them by number in a grid to reveal the content.

### Typst Template

New template file: `sealed.typ`

- Receives the list of sealed texts with their grid parameters.
- Renders each sealed text's content into a full block, then slices it into grid squares.
- Shuffles all squares across sealed texts.
- Lays out the shuffled squares on pages with cut lines and corner labels.

## Scope and Non-Goals

- No decoy/padding squares. The player can see the total count.
- No new trigger mechanism. Sealed texts are triggered by normal interactions via the existing addition system.
- No special handling for blind mode beyond ensuring sealed text refs work the same way.
- No digital/QR code delivery — paper-only for the initial implementation. QR codes as an alternative delivery mechanism are a potential future enhancement.
- Images inside sealed text are a stretch goal. The initial implementation may support text-only and add image support as a follow-up.

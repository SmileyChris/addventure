# Sealed Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sealed text blocks (`::: sealed` fencing) that produce either extended ledger sections or jigsaw cut pages for physical concealment.

**Architecture:** Two output modes: extended ledger (default, appends sealed content at the back of the ledger) and jigsaw (`--jigsaw`, two-pass Typst+Python pipeline that slices content into shuffled rectangular pieces). The parser detects `::: sealed` fences within interaction blocks, the compiler creates `SealedText` objects with opaque ref codes, and the writers render them to the appropriate output format.

**Tech Stack:** Python 3.10+, Typst (PDF generation), pypdf (PDF measurement), Pillow (empty-cell detection in jigsaw mode)

**Spec:** `docs/superpowers/specs/2026-04-05-sealed-text-design.md`

---

### Task 1: Model — Add SealedText dataclass and Interaction.sealed_content

**Files:**
- Modify: `src/addventure/models.py`
- Test: `tests/test_sealed.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sealed.py
from addventure.models import SealedText, Interaction, GameData

def test_sealed_text_dataclass():
    st = SealedText(
        ref="K-7",
        content="Secret finale text.",
        images=[],
        source_line=10,
        room="Dungeon",
    )
    assert st.ref == "K-7"
    assert st.entry_number == 0

def test_interaction_sealed_content_default():
    ix = Interaction(
        verb="USE", target_groups=[["KEY"]],
        narrative="You use the key.", room="Dungeon",
    )
    assert ix.sealed_content is None

def test_gamedata_sealed_texts_default():
    game = GameData()
    assert game.sealed_texts == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: FAIL — `SealedText` not defined, `Interaction` has no `sealed_content`

- [ ] **Step 3: Add SealedText and update Interaction/GameData**

In `src/addventure/models.py`, add after the `Action` dataclass:

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

Add `sealed_content` field to `Interaction`:

```python
@dataclass
class Interaction:
    verb: str
    target_groups: list[list[str]]
    narrative: str
    arrows: list[Arrow] = field(default_factory=list)
    source_line: int = 0
    room: str = ""
    sealed_content: str | None = None
```

Add `sealed_texts` field to `GameData`:

```python
    sealed_texts: list[SealedText] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/models.py tests/test_sealed.py
git commit -m "feat: add SealedText model and Interaction.sealed_content field"
```

---

### Task 2: Parser — Detect `::: sealed` fences in interaction blocks

**Files:**
- Modify: `src/addventure/parser.py`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sealed.py`:

```python
from addventure.compiler import compile_game
from addventure.parser import ParseError
import pytest

def test_parse_sealed_block():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: sealed
  The door opens to reveal a hidden chamber.
  Ancient treasures glitter in the torchlight.
  :::
"""
    game = compile_game(global_src, [room_src])
    ix = game.interactions[0]
    assert ix.narrative == "You turn the key."
    assert ix.sealed_content == (
        "The door opens to reveal a hidden chamber.\n\n"
        "Ancient treasures glitter in the torchlight."
    )

def test_parse_sealed_block_no_outer_narrative():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  - player -> "Exit"

  ::: sealed
  Secret text only.
  :::
"""
    game = compile_game(global_src, [room_src])
    ix = game.interactions[0]
    assert ix.narrative == ""
    assert ix.sealed_content == "Secret text only."

def test_parse_sealed_fence_outside_interaction_rejected():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY

::: sealed
This should fail.
:::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])

def test_parse_multiple_sealed_blocks_rejected():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text.

  ::: sealed
  First block.
  :::

  ::: sealed
  Second block.
  :::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: FAIL — parser doesn't recognize `::: sealed`

- [ ] **Step 3: Add sealed fence detection to the parser**

In `src/addventure/parser.py`, add a helper function near the other `_is_*` helpers:

```python
def _is_sealed_fence(s: str) -> bool:
    """Check if a line is a sealed block fence (opening or closing)."""
    return s == ":::" or s == "::: sealed"
```

In `_parse_inline_interaction()`, modify the while loop (after line 430) to detect sealed fences. Replace the narrative/arrow loop body with:

```python
    sealed_content = None

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or _is_comment(bstripped):
            i += 1
            continue
        if _indent(bline, i + 1) <= current_indent or _is_header(bline):
            break

        bmarker, bcontent = _strip_marker(bstripped)

        if bmarker == "-" and _is_arrow(bcontent):
            arrow = _parse_arrow(_strip_trailing_comment(bcontent), i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline, i + 1)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=arrows)
        elif bmarker == "+":
            raise ParseError(i + 1, f"Unexpected line in interaction body: {bstripped}")
        elif _is_sealed_fence(bstripped):
            if sealed_content is not None:
                raise ParseError(i + 1, "Multiple sealed blocks in one interaction")
            if bstripped != "::: sealed":
                raise ParseError(i + 1, "Expected '::: sealed' to open a sealed block")
            i += 1
            sealed_lines = []
            while i < len(lines):
                sline = lines[i]
                sstripped = sline.strip()
                if sstripped == ":::":
                    i += 1
                    break
                if _is_header(sline):
                    raise ParseError(i + 1, "Unclosed sealed block (hit header)")
                sealed_lines.append(sstripped)
                i += 1
            else:
                raise ParseError(i, "Unclosed sealed block (hit end of file)")
            # Join non-empty lines as paragraphs (same as narrative)
            paragraphs = []
            current_para = []
            for sl in sealed_lines:
                if not sl:
                    if current_para:
                        paragraphs.append(" ".join(current_para))
                        current_para = []
                else:
                    current_para.append(sl)
            if current_para:
                paragraphs.append(" ".join(current_para))
            sealed_content = "\n\n".join(paragraphs)
        elif _is_action(bstripped):
            action_name = bstripped[2:].strip()
            action_line = i + 1
            i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=current_indent)
            arrows.append(Arrow(f">{action_name}", "room", action_line))
        elif _is_narrative(bstripped) and not narrative:
            narrative = bstripped
            i += 1
        elif _is_narrative(bstripped) and narrative:
            narrative += "\n\n" + bstripped
            i += 1
        else:
            raise ParseError(i + 1, f"Unexpected line in interaction body: {bstripped}")

    ix = Interaction(
        verb=verb, target_groups=target_groups,
        narrative=narrative, arrows=arrows,
        source_line=source_line, room=room_name,
        sealed_content=sealed_content,
    )
    _register_interaction(game, ix)
    return i
```

Also add rejection of `::: sealed` in `_parse_entity_block()` — add a check before the final else clause:

```python
        elif _is_sealed_fence(stripped):
            raise ParseError(i + 1, "Sealed blocks must be inside an interaction (+ block)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/parser.py tests/test_sealed.py
git commit -m "feat: parse ::: sealed fences in interaction blocks"
```

---

### Task 3: Compiler — Generate SealedText objects with opaque ref codes

**Files:**
- Modify: `src/addventure/compiler.py`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sealed.py`:

```python
def test_sealed_text_created_with_ref():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: sealed
  Secret chamber revealed.
  :::

# Exit
LOOK: Freedom.
"""
    game = compile_game(global_src, [room_src])
    assert len(game.sealed_texts) == 1
    st = game.sealed_texts[0]
    assert st.content == "Secret chamber revealed."
    assert st.room == "Dungeon"
    assert st.entry_number > 0
    # Ref format: letter-digit(s)
    assert len(st.ref) >= 3
    assert st.ref[0].isalpha()
    assert st.ref[1] == "-"
    assert st.ref[2:].isdigit()

def test_sealed_text_refs_unique():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text one.

  ::: sealed
  Sealed one.
  :::

CHEST
+ LOOK:
  Text two.

  ::: sealed
  Sealed two.
  :::
"""
    game = compile_game(global_src, [room_src])
    assert len(game.sealed_texts) == 2
    refs = {st.ref for st in game.sealed_texts}
    assert len(refs) == 2  # unique

def test_sealed_text_linked_to_entry():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  The hidden truth.
  :::
"""
    game = compile_game(global_src, [room_src])
    st = game.sealed_texts[0]
    # Find the resolved interaction
    ri = next(r for r in game.resolved if r.verb == "USE")
    assert st.entry_number == ri.entry_number
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sealed.py::test_sealed_text_created_with_ref -v`
Expected: FAIL — `game.sealed_texts` is empty

- [ ] **Step 3: Generate SealedText objects in the compiler**

In `src/addventure/compiler.py`, add a function to generate ref codes:

```python
import string

# Letters that avoid visual ambiguity (no I, O, S, Z)
_REF_LETTERS = [c for c in string.ascii_uppercase if c not in "IOSZ"]

def _generate_sealed_refs(count: int) -> list[str]:
    """Generate unique opaque reference codes for sealed texts."""
    refs = set()
    i = 0
    while len(refs) < count:
        letter = _REF_LETTERS[i % len(_REF_LETTERS)]
        digit = (i // len(_REF_LETTERS)) + 1
        ref = f"{letter}-{digit}"
        refs.add(ref)
        i += 1
    result = list(refs)
    random.shuffle(result)
    return result
```

In `compile_game()`, after the entry renumbering section (after line 604), add:

```python
    # Create SealedText objects from interactions with sealed_content
    sealed_interactions = [
        (ix, ri) for ix in game.interactions if ix.sealed_content
        for ri in game.resolved
        if ri.verb == ix.verb and ri.room == ix.room
        and ri.source_line == ix.source_line
    ]
    if sealed_interactions:
        refs = _generate_sealed_refs(len(sealed_interactions))
        for (ix, ri), ref in zip(sealed_interactions, refs):
            game.sealed_texts.append(SealedText(
                ref=ref,
                content=ix.sealed_content,
                images=[],  # Image extraction is a stretch goal
                source_line=ix.source_line,
                room=ix.room,
                entry_number=ri.entry_number,
            ))
```

Add `SealedText` to the imports from `.models` at the top of `compiler.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/compiler.py tests/test_sealed.py
git commit -m "feat: generate SealedText objects with opaque ref codes"
```

---

### Task 4: Writer — Generate sealed text instructions in ledger entries

**Files:**
- Modify: `src/addventure/writer.py`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sealed.py`:

```python
from addventure.writer import GameWriter

def test_sealed_instruction_extended_ledger():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: sealed
  Secret text.
  :::

# Exit
LOOK: Freedom.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(r for r in game.resolved if r.verb == "USE" and "KEY" in r.targets)
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Turn to Sealed Text {st.ref}" in inst for inst in instructions)

def test_sealed_instruction_jigsaw():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  Secret text.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game, jigsaw=True)
    ri = next(r for r in game.resolved if r.verb == "USE")
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Find and assemble the {st.ref} pieces" in inst for inst in instructions)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sealed.py::test_sealed_instruction_extended_ledger -v`
Expected: FAIL — no sealed text instruction generated

- [ ] **Step 3: Add sealed text instruction generation**

In `src/addventure/writer.py`, update `GameWriter.__init__` to accept `jigsaw`:

```python
    def __init__(self, game: GameData, blind: bool = False, jigsaw: bool = False):
        self.game = game
        self.blind = blind
        self.jigsaw = jigsaw
        self.entry_prefix = game.metadata.get("entry_prefix", "A")
        self.name_style = game.metadata.get("name_style", "upper_words")
        self.warnings: list[str] = []
```

At the end of `_generate_instructions()`, before the blind mode section (before `if self.blind:`), add:

```python
        # Sealed text: append instruction to open/assemble sealed content
        sealed = next(
            (st for st in self.game.sealed_texts if st.entry_number == ri.entry_number),
            None
        )
        if sealed:
            if self.jigsaw:
                instructions.append(f"Find and assemble the {sealed.ref} pieces.")
            else:
                instructions.append(f"Turn to Sealed Text {sealed.ref}.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sealed.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/addventure/writer.py tests/test_sealed.py
git commit -m "feat: generate sealed text instructions in ledger entries"
```

---

### Task 5: Markdown writer — Sealed texts section at end

**Files:**
- Modify: `src/addventure/md_writer.py`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sealed.py`:

```python
from addventure.md_writer import generate_markdown

def test_markdown_sealed_section():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  The hidden chamber awaits.
  :::
"""
    game = compile_game(global_src, [room_src])
    md, _ = generate_markdown(game)
    st = game.sealed_texts[0]
    assert f"## Sealed Texts" in md
    assert f"### Sealed Text {st.ref}" in md
    assert "The hidden chamber awaits." in md
    assert "Do not read until directed" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sealed.py::test_markdown_sealed_section -v`
Expected: FAIL — no sealed texts section in markdown

- [ ] **Step 3: Add sealed texts section to markdown writer**

In `src/addventure/md_writer.py`, add a new function:

```python
def _sealed_section(game: GameData) -> str:
    """Render sealed texts as a section at the end."""
    if not game.sealed_texts:
        return ""
    lines = [
        "## Sealed Texts",
        "\n*Do not read ahead — turn to a sealed text only when directed by a ledger entry.*",
    ]
    for st in sorted(game.sealed_texts, key=lambda s: s.ref):
        lines.append(f"\n### Sealed Text {st.ref}")
        lines.append(f"> ⚠ Do not read until directed.\n")
        lines.append(st.content)
    return "\n".join(lines)
```

In `generate_markdown()`, after the ledger section and before the join, add the sealed section:

```python
    sections.append(_ledger_section(game, writer, entry_prefix))

    sealed = _sealed_section(game)
    if sealed:
        sections.append(sealed)

    return "\n\n---\n\n".join(sections) + "\n", writer.warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sealed.py::test_markdown_sealed_section -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/addventure/md_writer.py tests/test_sealed.py
git commit -m "feat: add sealed texts section to markdown output"
```

---

### Task 6: CLI — Add `--jigsaw` flag

**Files:**
- Modify: `src/addventure/cli.py`

- [ ] **Step 1: Add the flag and pass it through**

In `src/addventure/cli.py`, after the `--no-cover` argument (line 45), add:

```python
    parser.add_argument("--jigsaw", action="store_true",
                        help="Output sealed texts as jigsaw cut pages (default: extended ledger)")
```

Pass `jigsaw` to `generate_markdown`:

```python
        md, writer_warnings = generate_markdown(game, blind=parsed.blind, jigsaw=parsed.jigsaw)
```

Pass `jigsaw` to `generate_pdf`:

```python
        success, writer_warnings = generate_pdf(game, output_path, theme=parsed.theme, game_dir=game_dir.resolve(), paper=parsed.paper, blind=parsed.blind, cover=not parsed.no_cover, jigsaw=parsed.jigsaw)
```

- [ ] **Step 2: Update generate_markdown signature**

In `src/addventure/md_writer.py`, update `generate_markdown` to accept `jigsaw` (ignored in markdown mode):

```python
def generate_markdown(game: GameData, blind: bool = False, jigsaw: bool = False) -> tuple[str, list[str]]:
```

Pass `jigsaw` to `GameWriter`:

```python
    writer = GameWriter(game, blind=blind, jigsaw=jigsaw)
```

- [ ] **Step 3: Update generate_pdf signature**

In `src/addventure/pdf_writer.py`, update `generate_pdf` to accept `jigsaw`:

```python
def generate_pdf(
    game: GameData,
    output_path: Path,
    theme: str = "default",
    game_dir: Path | None = None,
    paper: str | None = None,
    blind: bool = False,
    cover: bool = False,
    jigsaw: bool = False,
) -> tuple[bool, list[str]]:
```

Pass `jigsaw` to `GameWriter`:

```python
    writer = GameWriter(game, blind=blind, jigsaw=jigsaw)
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 5: Test CLI manually**

Run: `uv run adv build --help`
Expected: `--jigsaw` flag appears in help output

- [ ] **Step 6: Commit**

```bash
git add src/addventure/cli.py src/addventure/md_writer.py src/addventure/pdf_writer.py
git commit -m "feat: add --jigsaw CLI flag, thread through to writers"
```

---

### Task 7: PDF writer — Extended ledger mode (default sealed text output)

**Files:**
- Modify: `src/addventure/pdf_writer.py`
- Modify: `src/addventure/templates/default/main.typ`
- Create: `src/addventure/templates/default/sealed-ledger.typ`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sealed.py`:

```python
from addventure.pdf_writer import serialize_game_data

def test_serialize_sealed_texts():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  The hidden chamber.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert "sealed_texts" in data
    assert len(data["sealed_texts"]) == 1
    assert data["sealed_texts"][0]["content"] == "The hidden chamber."
    assert "ref" in data["sealed_texts"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sealed.py::test_serialize_sealed_texts -v`
Expected: FAIL — no `sealed_texts` in serialized data

- [ ] **Step 3: Add sealed texts to serialized data**

In `src/addventure/pdf_writer.py`, in `serialize_game_data()`, before the `return` statement, add:

```python
    sealed_texts = [
        {
            "ref": st.ref,
            "content": st.content,
            "entry_number": st.entry_number,
        }
        for st in sorted(game.sealed_texts, key=lambda s: s.ref)
    ]
```

Add `"sealed_texts": sealed_texts,` to the return dict.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sealed.py::test_serialize_sealed_texts -v`
Expected: PASS

- [ ] **Step 5: Create the Typst sealed ledger template**

Create `src/addventure/templates/default/sealed-ledger.typ`:

```typst
#import "style.typ": *

#let sealed-ledger(data) = {
  if data.sealed_texts.len() == 0 { return }

  sheet-title("SEALED TEXTS")
  v(0.3em)
  text(size: 8pt, style: "italic")[
    Do not read ahead — turn to a sealed text only when directed by a ledger entry.
  ]
  v(0.5em)

  for st in data.sealed_texts {
    block(
      width: 100%,
      below: 0.8em,
      stroke: 0.5pt + luma(180),
      inset: 8pt,
    )[
      #text(font: title-font, size: 10pt, weight: "bold")[
        Sealed Text #st.ref
      ]
      #v(0.3em)
      #text(size: 9pt)[#eval(st.content, mode: "markup")]
    ]
  }
}
```

- [ ] **Step 6: Include sealed ledger in main template**

In `src/addventure/templates/default/main.typ`, add the import at the top with the other imports:

```typst
#import "sealed-ledger.typ": sealed-ledger
```

After the story ledger call, add:

```typst
  // Sealed texts (extended ledger mode)
  if not data.at("jigsaw", default: false) and data.at("sealed_texts", default: ()).len() > 0 {
    pagebreak(weak: true)
    sealed-ledger(data)
  }
```

- [ ] **Step 7: Add `jigsaw` flag to serialized data**

In `serialize_game_data()`, add `"jigsaw": False,` to the return dict. This will be set to `True` when jigsaw mode is active (Task 8).

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 9: Manual test with example game**

Add a sealed block to `games/example/` temporarily, build, and verify the sealed texts section appears in the PDF after the ledger.

- [ ] **Step 10: Commit**

```bash
git add src/addventure/pdf_writer.py src/addventure/templates/default/sealed-ledger.typ src/addventure/templates/default/main.typ tests/test_sealed.py
git commit -m "feat: extended ledger mode for sealed texts in PDF output"
```

---

### Task 8: Grammar update and documentation

**Files:**
- Modify: `docs/grammar.ebnf`

- [ ] **Step 1: Add sealed_block production to grammar**

In `docs/grammar.ebnf`, in the interaction body section, add:

```
(* Sealed text blocks — long-form hidden content within an interaction *)
sealed-block   = sealed-open , { sealed-line } , sealed-close ;
sealed-open    = indent , "::: sealed" , newline ;
sealed-close   = indent , ":::" , newline ;
sealed-line    = indent , text-line ;
```

Add `sealed-block` as an optional element in the interaction body production.

- [ ] **Step 2: Commit**

```bash
git add docs/grammar.ebnf
git commit -m "docs: add sealed block production to grammar"
```

---

### Task 9: Jigsaw — Add Pillow dependency and empty-cell detection

**Files:**
- Modify: `pyproject.toml`
- Create: `src/addventure/jigsaw.py`
- Test: `tests/test_sealed.py`

- [ ] **Step 1: Add Pillow dependency**

In `pyproject.toml`, add to dependencies:

```toml
dependencies = [
    "pypdf>=6.9.2",
    "Pillow>=10.0",
]
```

Run: `uv lock`

- [ ] **Step 2: Write the failing test for grid computation**

Append to `tests/test_sealed.py`:

```python
from addventure.jigsaw import compute_grid, interleave_pieces

def test_compute_grid_basic():
    grid = compute_grid(
        content_w_mm=160, content_h_mm=50,
        cols=4, target_cell_h_mm=25,
    )
    assert grid["cols"] == 4
    assert grid["rows"] == 2
    assert grid["cell_w_mm"] == pytest.approx(40.0)
    assert grid["cell_h_mm"] == pytest.approx(25.0)

def test_compute_grid_rounds_up():
    grid = compute_grid(
        content_w_mm=160, content_h_mm=60,
        cols=4, target_cell_h_mm=25,
    )
    # 60/25 = 2.4, rounds to 2, but need 3 to cover content
    assert grid["rows"] == 3

def test_interleave_no_adjacent():
    """Pieces should not be adjacent to their original neighbors."""
    pieces = list(range(8))  # 4x2 grid, positions 0-7
    cols = 4
    result = interleave_pieces(pieces, cols)
    assert len(result) == 8
    assert set(result) == set(pieces)
    # Check no original horizontal neighbors are adjacent in result
    for i in range(len(result) - 1):
        a, b = result[i], result[i + 1]
        # Original neighbors: same row, columns differ by 1
        a_row, a_col = divmod(a, cols)
        b_row, b_col = divmod(b, cols)
        if a_row == b_row:
            assert abs(a_col - b_col) != 1, f"Pieces {a} and {b} are original neighbors"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_sealed.py::test_compute_grid_basic -v`
Expected: FAIL — `jigsaw` module doesn't exist

- [ ] **Step 4: Implement jigsaw.py**

Create `src/addventure/jigsaw.py`:

```python
"""Jigsaw mode: compute grid, shuffle pieces, detect empty cells."""
import math


def compute_grid(
    content_w_mm: float,
    content_h_mm: float,
    cols: int = 4,
    target_cell_h_mm: float = 25.0,
) -> dict:
    """Compute grid dimensions for jigsaw slicing."""
    rows = max(2, math.ceil(content_h_mm / target_cell_h_mm))
    cell_w = content_w_mm / cols
    cell_h = content_h_mm / rows
    return {
        "cols": cols,
        "rows": rows,
        "cell_w_mm": cell_w,
        "cell_h_mm": cell_h,
    }


def interleave_pieces(pieces: list, cols: int) -> list:
    """Reorder pieces so no original neighbors are adjacent.

    Uses every-3rd interleave: positions 0,3,6,1,4,7,2,5,...
    """
    n = len(pieces)
    step = 3
    order = []
    for start in range(step):
        for i in range(start, n, step):
            order.append(i)
    return [pieces[i] for i in order]


def checkerboard_flips(rows: int, cols: int) -> list[list[bool]]:
    """Generate checkerboard flip pattern. True = 180° rotated."""
    return [
        [(r + c) % 2 == 1 for c in range(cols)]
        for r in range(rows)
    ]


def detect_empty_cells(
    png_path: str,
    cols: int,
    rows: int,
    brightness_threshold: int = 250,
) -> list[tuple[int, int]]:
    """Detect which grid cells are visually empty (all near-white).

    Returns list of (row, col) tuples for non-empty cells.
    """
    from PIL import Image

    img = Image.open(png_path).convert("L")  # grayscale
    w, h = img.size
    cell_w = w // cols
    cell_h = h // rows

    non_empty = []
    for r in range(rows):
        for c in range(cols):
            x0 = c * cell_w
            y0 = r * cell_h
            x1 = min(x0 + cell_w, w)
            y1 = min(y0 + cell_h, h)
            cell = img.crop((x0, y0, x1, y1))
            # Check if any pixel is dark enough to be content
            if cell.getextrema()[0] < brightness_threshold:
                non_empty.append((r, c))

    return non_empty
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_sealed.py -v -k "jigsaw or interleave or compute_grid"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/addventure/jigsaw.py tests/test_sealed.py
git commit -m "feat: jigsaw module with grid computation, interleave, empty detection"
```

---

### Task 10: Jigsaw — Two-pass PDF pipeline

**Files:**
- Modify: `src/addventure/pdf_writer.py`
- Create: `src/addventure/templates/default/sealed-jigsaw.typ`
- Create: `src/addventure/templates/default/sealed-measure.typ`

This is the most complex task. The two-pass pipeline:
1. Renders each sealed text as a standalone page (pass 1 — measure)
2. Measures the page with pypdf
3. Computes grid, detects empty cells, generates piece data
4. Passes piece data to the main Typst compilation (pass 2 — slice)

- [ ] **Step 1: Create the pass 1 measurement template**

Create `src/addventure/templates/default/sealed-measure.typ`:

```typst
// Pass 1: Render sealed text content to measure its natural height.
// Page width = content width + 2*margin, height = auto.
#let raw-data = read(sys.inputs.data)
#let data = json(raw-data)

#let margin = 2mm
#set page(width: eval(data.content_w) + 2 * margin, height: auto, margin: margin)
#set text(size: 10pt)
#set par(justify: true)
#set align(left)

#eval(data.content, mode: "markup")
```

- [ ] **Step 2: Create the pass 2 jigsaw template**

Create `src/addventure/templates/default/sealed-jigsaw.typ`:

```typst
#import "style.typ": *

#let sealed-jigsaw(data) = {
  let jigsaw = data.at("jigsaw_data", default: none)
  if jigsaw == none { return }

  let pieces = jigsaw.pieces
  if pieces.len() == 0 { return }

  // Reconstruct content blocks for each sealed text
  let contents = (:)
  for st in data.sealed_texts {
    let cw = eval(jigsaw.cell_w)
    let ch = eval(jigsaw.cell_h)
    let full-w = cw * jigsaw.cols
    let full-h = ch * st.rows
    let pad = eval(jigsaw.pad)
    contents.insert(st.ref, block(width: full-w, height: full-h, inset: pad)[
      #set text(size: 10pt)
      #set par(justify: true)
      #set align(left)
      #eval(st.content, mode: "markup")
    ])
  }

  let kerf = 1pt
  let cw = eval(jigsaw.cell_w)
  let ch = eval(jigsaw.cell_h)
  let cut-cols = jigsaw.cut_cols

  // Assembly instructions
  sheet-title("CUT PAGES")
  v(0.3em)
  text(size: 8pt, style: "italic")[
    When directed by a ledger entry, find the matching pieces, cut them out, and assemble them to reveal the content.
  ]
  v(0.5em)

  // Render pieces in grid
  let piece-boxes = ()
  for p in pieces {
    let src = contents.at(p.ref)
    let flipped = p.flip
    let inner = box(
      width: cw + kerf,
      height: ch + kerf,
      clip: true,
      stroke: kerf + black,
      align(left + top, move(
        dx: -(p.col * cw - kerf / 2),
        dy: -(p.row * ch - kerf / 2),
        src,
      ))
    )
    if flipped {
      piece-boxes.push(rotate(180deg, reflow: false, inner))
    } else {
      piece-boxes.push(inner)
    }
  }

  grid(
    columns: cut-cols,
    gutter: 0mm,
    ..piece-boxes
  )
}
```

- [ ] **Step 3: Implement the two-pass pipeline in pdf_writer.py**

In `src/addventure/pdf_writer.py`, add the jigsaw pipeline function:

```python
import math
from .jigsaw import compute_grid, interleave_pieces, checkerboard_flips, detect_empty_cells


MEASURE_MARGIN_MM = 2


def _jigsaw_pipeline(
    game: GameData, writer: GameWriter, theme_dir: Path
) -> dict:
    """Two-pass pipeline: measure sealed texts, compute grid, return jigsaw data."""
    if not game.sealed_texts:
        return {}

    typst_bin = find_typst()
    measure_typ = theme_dir / "sealed-measure.typ"

    # Fixed content width = page width minus margins (A4 = 210mm, margins = 0.5in each ≈ 25.4mm)
    content_w_mm = 160.0  # Approximate printable width

    # Pass 1: measure each sealed text
    measurements = {}
    for st in game.sealed_texts:
        measure_data = json.dumps({
            "content_w": f"{content_w_mm}mm",
            "content": st.content,
        })
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(measure_data)
            measure_json = f.name

        measure_pdf = tempfile.mktemp(suffix=".pdf")
        try:
            subprocess.run(
                [typst_bin, "compile", str(measure_typ), measure_pdf,
                 "--root", "/",
                 "--input", f"data={measure_json}"],
                check=True, capture_output=True, text=True,
            )
            from pypdf import PdfReader
            reader = PdfReader(measure_pdf)
            page = reader.pages[0]
            pt_to_mm = 25.4 / 72
            page_h_mm = float(page.mediabox.height) * pt_to_mm
            content_h_mm = page_h_mm - 2 * MEASURE_MARGIN_MM + 1  # +1mm padding
            measurements[st.ref] = content_h_mm
        finally:
            Path(measure_json).unlink(missing_ok=True)
            Path(measure_pdf).unlink(missing_ok=True)

    # Compute uniform cell height across all sealed texts
    target_cell_h = 25.0
    all_grids = {}
    for ref, h in measurements.items():
        grid = compute_grid(content_w_mm + 2 * MEASURE_MARGIN_MM, h + 2 * MEASURE_MARGIN_MM,
                            cols=4, target_cell_h_mm=target_cell_h)
        all_grids[ref] = grid

    # Use the max cell height across all sealed texts for uniformity
    cell_h = max(g["cell_h_mm"] for g in all_grids.values())
    cell_w = (content_w_mm + 2 * MEASURE_MARGIN_MM) / 4
    # Recompute rows with uniform cell height
    for ref, h in measurements.items():
        full_h = h + 2 * MEASURE_MARGIN_MM
        all_grids[ref]["rows"] = max(2, math.ceil(full_h / cell_h))
        all_grids[ref]["cell_h_mm"] = cell_h

    # Build piece list with empty-cell detection via PNG rasterization
    # (For now, use height-based detection; Pillow detection is a follow-up)
    all_pieces = []
    for st in game.sealed_texts:
        grid = all_grids[st.ref]
        for r in range(grid["rows"]):
            for c in range(grid["cols"]):
                all_pieces.append({
                    "ref": st.ref,
                    "row": r,
                    "col": c,
                })

    # Interleave and assign flips
    interleaved = interleave_pieces(all_pieces, 4)
    cut_cols = 4
    flips = checkerboard_flips(
        math.ceil(len(interleaved) / cut_cols), cut_cols
    )
    for idx, piece in enumerate(interleaved):
        fr = idx // cut_cols
        fc = idx % cut_cols
        piece["flip"] = flips[fr][fc] if fr < len(flips) else False

    # Build per-sealed-text row counts for the template
    sealed_data = []
    for st in game.sealed_texts:
        sealed_data.append({
            "ref": st.ref,
            "content": st.content,
            "rows": all_grids[st.ref]["rows"],
        })

    return {
        "jigsaw_data": {
            "cols": 4,
            "cell_w": f"{cell_w:.2f}mm",
            "cell_h": f"{cell_h:.2f}mm",
            "pad": f"{MEASURE_MARGIN_MM}mm",
            "cut_cols": cut_cols,
            "pieces": interleaved,
        },
        "sealed_texts_override": sealed_data,
    }
```

In `generate_pdf()`, after creating the `data` dict from `serialize_game_data()`, add:

```python
    if jigsaw and game.sealed_texts:
        jigsaw_data = _jigsaw_pipeline(game, writer, theme_dir)
        data["jigsaw"] = True
        if "jigsaw_data" in jigsaw_data:
            data["jigsaw_data"] = jigsaw_data["jigsaw_data"]
        if "sealed_texts_override" in jigsaw_data:
            data["sealed_texts"] = jigsaw_data["sealed_texts_override"]
    else:
        data["jigsaw"] = False
```

- [ ] **Step 4: Wire up the jigsaw template in main.typ**

In `src/addventure/templates/default/main.typ`, add:

```typst
#import "sealed-jigsaw.typ": sealed-jigsaw
```

After the sealed ledger section:

```typst
  // Sealed texts (jigsaw mode)
  if data.at("jigsaw", default: false) and data.at("jigsaw_data", default: none) != none {
    pagebreak(weak: true)
    sealed-jigsaw(data)
  }
```

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 6: Manual test**

Add a sealed block to the example game, build with `--jigsaw`:
```bash
uv run adv build games/example --jigsaw
```
Verify jigsaw cut pages appear in the PDF.

- [ ] **Step 7: Commit**

```bash
git add src/addventure/pdf_writer.py src/addventure/templates/default/sealed-measure.typ src/addventure/templates/default/sealed-jigsaw.typ src/addventure/templates/default/main.typ
git commit -m "feat: two-pass jigsaw pipeline for sealed text PDF output"
```

---

### Task 11: Empty cell detection via Pillow

**Files:**
- Modify: `src/addventure/pdf_writer.py`

- [ ] **Step 1: Add PNG-based empty cell detection to the pipeline**

In `_jigsaw_pipeline()`, replace the simple piece list generation with PNG-based detection. After the measurement loop, add a second pass that renders each sealed text as PNG and checks which cells have content:

```python
    # Pass 1b: detect empty cells via PNG rasterization
    non_empty_cells = {}
    for st in game.sealed_texts:
        measure_data = json.dumps({
            "content_w": f"{content_w_mm}mm",
            "content": st.content,
        })
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(measure_data)
            measure_json = f.name

        measure_png = tempfile.mktemp(suffix=".png")
        try:
            subprocess.run(
                [typst_bin, "compile", str(measure_typ), measure_png,
                 "--root", "/",
                 "--input", f"data={measure_json}",
                 "--ppi", "72"],
                check=True, capture_output=True, text=True,
            )
            grid = all_grids[st.ref]
            non_empty = detect_empty_cells(
                measure_png, grid["cols"], grid["rows"],
            )
            non_empty_cells[st.ref] = non_empty
        finally:
            Path(measure_json).unlink(missing_ok=True)
            Path(measure_png).unlink(missing_ok=True)
```

Replace the piece list generation to only include non-empty cells:

```python
    all_pieces = []
    for st in game.sealed_texts:
        cells = non_empty_cells.get(st.ref, [])
        for r, c in cells:
            all_pieces.append({
                "ref": st.ref,
                "row": r,
                "col": c,
            })
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 3: Manual test**

Build with jigsaw and verify no blank pieces appear.

- [ ] **Step 4: Commit**

```bash
git add src/addventure/pdf_writer.py
git commit -m "feat: PNG-based empty cell detection for jigsaw mode"
```

---

### Task 12: Build summary and final integration

**Files:**
- Modify: `src/addventure/writer.py`

- [ ] **Step 1: Add sealed text count to build summary**

In `src/addventure/writer.py`, in `print_build_summary()`, add after the action count:

```python
    sealed_count = len(game.sealed_texts)
```

Add to the parts list:

```python
        p(sealed_count, "sealed texts"),
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

- [ ] **Step 3: End-to-end test with both modes**

```bash
# Add a sealed block to the example game temporarily
# Test default mode (extended ledger)
uv run adv build games/example
# Test jigsaw mode
uv run adv build games/example --jigsaw
# Test markdown mode
uv run adv build games/example --md
```

- [ ] **Step 4: Commit**

```bash
git add src/addventure/writer.py
git commit -m "feat: add sealed text count to build summary"
```

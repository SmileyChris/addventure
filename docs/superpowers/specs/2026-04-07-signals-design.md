# Signals: Cross-Chapter State

Signals let authors carry narrative consequences between independently compiled chapters. A signal is a named flag — the player writes its numeric ID at the end of one chapter and checks it at the start (or during) the next. Signal IDs are deterministic (derived from the name), so both chapters can reference the same signal without coordination.

## Player experience

1. End of Chapter A: a ledger entry says *"Write 10347 in your signals."*
2. Start of Chapter B: the verb sheet says *"Check your signals: 10347 → read B-3. 10891 → read B-7. Otherwise → read B-12."*
3. The player checks, reads the matching entry, follows its instructions (which may add objects, set up rooms, change narrative).

Signals appear on the printed inventory/potentials sheet in a small **Signals** section — a place to write numbers, like Cue Checks.

## Script syntax

### Emitting signals (sending chapter)

In the sending chapter's room files, a signal arrow emits a signal:

```
+ USE + AIR_DUCT:
  You haul yourself into the vent...
  - EVERYONE_OUT_ESCAPE -> signal
```

The compiler hashes the name to a fixed numeric ID. The arrow renders as a player instruction: *"Write 10347 in your signals."*

No declaration section is needed. The compiler derives signal info from `NAME -> signal` arrows (emissions) and `NAME?` blocks (checks). The hash function is deterministic, so both chapters produce the same ID from the same name.

### Signal checks at chapter start

Signal checks can appear in the `index.md` description (the prose between frontmatter and `# Verbs`). They use `NAME?` syntax with `otherwise?` as the default:

```
---
title: The Outpost
ledger_prefix: B
start: Forest Road
---

You're out. Pine air hits your lungs like cold water.

EVERYONE_OUT_ESCAPE?
  A figure steps from the treeline behind you...
  - COMPANION -> "Forest Road"
WITNESS_ESCAPE?
  You're alone. The faces at the windows stay with you.
otherwise?
  The road stretches ahead.

# Verbs
...
```

The prose before the first signal check is common text — always shown. Each `NAME?` block is a conditional branch. **All matching branches fire** — if the player has multiple signals, they read every matching entry (signals are independent flags). `otherwise?` fires only when *no* signal matches. On the printed sheet, this renders naturally: the player checks each listed ID against their signals and reads every entry that matches.

On the printed verb sheet, this renders as:

> You're out. Pine air hits your lungs like cold water.
>
> Check your signals: **10347** → read B-3. **10891** → read B-7. Otherwise → read B-12.

Each branch is compiled to its own ledger entry containing the branch's narrative text and any arrows (object placement, room state changes, etc.).

### Signal checks within interactions

Signal checks can also appear inside interaction blocks, after the common narrative text:

```
CONSOLE__TUNED
+ USE:
  You lift the microphone and press transmit.
  EVERYONE_OUT_ESCAPE?
    Your companion grabs your arm. "Tell them how many. Tell them everything."
  otherwise?
    Your voice is the only one in the room.
```

On paper, the parent ledger entry contains the common narrative, then directs the player to check signals:

> B-24: You lift the microphone and press transmit.
>
> Check your signals: **10347** → also read B-25. Otherwise → also read B-26.

The signal-specific text and any arrows go in the follow-on entries. Arrows in the common section (before the signal checks) apply unconditionally.

As with index-level checks, all matching branches fire — the player reads every matching entry. `otherwise?` fires only when no signal matches.

Signal checks appear after any common narrative and unconditional arrows. Arrows before the first `NAME?` block apply to all branches. Arrows within a `NAME?` or `otherwise?` block are conditional:

```
+ USE + RADIO:
  You turn the dial.
  - RADIO -> RADIO__ACTIVE
  EVERYONE_OUT_ESCAPE?
    Your companion nods.
    - COMPANION_VOICE -> room
  otherwise?
    Silence.
    - STATIC -> room
```

Here `RADIO -> RADIO__ACTIVE` fires unconditionally. `COMPANION_VOICE -> room` only fires if the player has the signal.

## Syntax summary

| Context | Syntax | Meaning |
|---|---|---|
| Arrow in interaction | `- SIGNAL_NAME -> signal` | Emit a signal (player writes the ID) |
| Index description or interaction body | `SIGNAL_NAME?` | Conditional: if player has this signal |
| Index description or interaction body | `otherwise?` | Default branch when no signal matches |

## Signal ID generation

Signal IDs are derived deterministically from the signal name:

```python
def signal_id(name: str) -> int:
    h = hashlib.sha256(name.encode()).hexdigest()
    return int(h[:8], 16) % 89990 + 10010
```

Range: 10010–99999. This avoids overlap with entity IDs (100–9999) and verb IDs (11–999). The five-digit range provides ~90,000 possible values — collision between distinct signal names is negligible but the compiler should detect and error on it.

Both the sending and receiving chapters use the same hash function, so they produce the same ID from the same name without any coordination.

## Compiler changes

### Models (`models.py`)

New dataclass:

```python
@dataclass
class Signal:
    name: str
    id: int = 0  # Hash-derived, set during parsing

@dataclass
class SignalCheck:
    signal_name: str | None  # None = otherwise
    narrative: str
    arrows: list[Arrow]
    entry_number: int = 0
```

New fields on `GameData`:

```python
signals: dict[str, Signal] = field(default_factory=dict)
signal_checks: list[SignalCheck] = field(default_factory=list)  # Index-level signal checks (from description)
signal_emissions: set[str] = field(default_factory=set)  # All signal names emitted anywhere in this chapter
```

`signal_emissions` is populated by the compiler as it processes arrows — it is a chapter-level summary used for sheet layout (see Printed sheet layout) and cross-chapter validation.

New field on `Arrow`:

```python
signal_name: str | None = None  # Set when destination is `signal NAME`
```

This preserves which arrow emitted which signal, so the writer can generate per-entry "Write ID in your signals" instructions directly from the arrow that triggers them.

New field on `Interaction`:

```python
signal_checks: list[SignalCheck] = field(default_factory=list)
```

### Parser (`parser.py`)

1. **`# Signals` section** — parse signal names from `index.md`, compute hash IDs.
2. **`-> signal NAME` arrows** — new arrow destination type. Parser recognises `signal` keyword after `->`.
3. **`NAME?` blocks in index description** — after parsing prose lines, detect lines matching `NAME?` pattern followed by indented content. Parse each block's narrative and arrows. `otherwise?` is the default.
4. **`NAME?` blocks in interaction bodies** — after parsing the interaction's narrative and arrows, detect signal check blocks. Same syntax rules as index description checks.

Signal names follow the same naming rules as other identifiers: `[A-Z][A-Z0-9]*(_[A-Z0-9]+)*`.

### Compiler (`compiler.py`)

1. **Reserve signal IDs** — add all signal IDs to the exclusion set before entity/verb allocation.
2. **Compile signal checks** — each branch of a signal check becomes a separate ledger entry. Assign entry numbers. The parent interaction's entry references the child entries via signal check instructions.
3. **Validate (chapter-local)** — error if two signal names within this chapter hash to the same ID. Warning if a `NAME?` block references a signal not declared in `# Signals` (could be a typo). `otherwise?` is optional — if missing and the player has no matching signal, nothing additional happens (the common narrative still plays).

### Cross-chapter validation (`cli.py`, `--all` builds)

When `--all` compiles multiple chapters, a **repo-wide signal validation pass** runs after all chapters have been compiled individually. This collects every signal name and its hash-derived ID across all chapters and checks:

1. **Cross-chapter hash collision** — error if two distinct signal names from different chapters hash to the same ID. (Within a single chapter this is caught by step 3 above, but independent compilation means chapter A's `FOO` and chapter B's `BAR` could silently alias.)
2. **Orphaned emissions** — warning if a chapter emits a signal that no other chapter declares in `# Signals`. (Not an error — the receiving chapter may not be built yet.)
3. **Orphaned declarations** — warning if a chapter declares a signal that no other chapter emits. (Same rationale.)

This validation operates on the compiled `GameData` objects, which already contain `signals` (declared) and `signal_emissions` (emitted). No shared manifest file is needed — the `--all` build has access to all chapter data in memory.

For single-chapter builds (`addventure build` without `--all`), cross-chapter validation is not possible and is skipped.

### Writer (`writer.py`)

New instruction generation for signal checks:

- For signal checks in the index description: render as "Check your signals: **ID** → read PREFIX-N. **ID** → read PREFIX-N. Otherwise → read PREFIX-N." on the verb sheet.
- For signal checks in interactions: render as "Check your signals: **ID** → also read PREFIX-N. Otherwise → also read PREFIX-N." appended to the parent ledger entry's instructions.
- For signal emission arrows: render as "Write ID in your signals." in the ledger entry instructions.

### Markdown writer (`md_writer.py`)

- Render signal check instructions in the verb section (for index-level checks) and in ledger entries (for interaction-level checks).
- Signal section on the inventory/potentials page: a "Signals" subsection with blank slots.

### PDF writer (`pdf_writer.py`) and Typst templates

- Add signal check instructions to the verb sheet data and ledger entry data.
- Add a "Signals" section to the inventory sheet template — a small box with blank slots for writing signal IDs.
- Signal count for slot sizing: max(declared signals, emitted signals). Section omitted when both counts are zero.

## Printed sheet layout

The **Signals** section appears on the inventory/potentials sheet, near Cue Checks:

```
SIGNALS
Write signal codes here when instructed.
[____] [____] [____]
```

The section appears when a chapter declares signals in `# Signals` **or** emits any signal via `-> signal` arrows. Slot count = max(number of declared signals, number of distinct emitted signals), minimum 1. The section is omitted entirely only for chapters that neither declare nor emit signals.

## Grammar changes (`docs/grammar.ebnf`)

New productions:

```ebnf
signals_section   = "# Signals" newline { signal_decl } ;
signal_decl       = IDENTIFIER newline ;

signal_arrow      = NAME "->" "signal" ;

signal_check      = IDENTIFIER "?" newline indented_block ;
otherwise_check   = "otherwise?" newline indented_block ;
signal_check_group = { signal_check } [ otherwise_check ] ;
```

Signal check groups can appear in:
- Index description (between frontmatter and `# Verbs`)
- Interaction bodies (after narrative text and arrows)

## Error handling

| Condition | Severity | Message |
|---|---|---|
| Two signal names hash to same ID (within chapter) | Error | `Signal hash collision: X and Y both resolve to ID Z` |
| Two signal names hash to same ID (cross-chapter, `--all` only) | Error | `Cross-chapter signal hash collision: X and Y both resolve to ID Z` |
| `NAME?` references undeclared signal | Warning | `Signal check references unknown signal: NAME` |
| `otherwise?` appears before other signal checks | Error | `otherwise? must be the last branch in a signal check` |
| `otherwise?` appears more than once | Error | `Duplicate otherwise? in signal check` |
| `-> signal NAME` in a chapter with `# Signals` declaring the same name | Warning | `Chapter both emits and receives signal: NAME` |
| Signal emitted but not declared in any chapter (`--all` only) | Warning | `Signal NAME is emitted but not declared in any chapter` |
| Signal declared but not emitted by any chapter (`--all` only) | Warning | `Signal NAME is declared but not emitted by any chapter` |

## Testing

- **Unit tests:** signal ID hashing (deterministic, range, no collision for typical names), parser tests for `# Signals` section, `-> signal` arrows, `NAME?` / `otherwise?` blocks in index and interaction contexts.
- **Integration tests:** compile a two-chapter game where Chapter A emits a signal and Chapter B checks it. Verify the emitting entry has "Write ID in your signals" instruction. Verify the receiving chapter's verb sheet and ledger entries contain correct signal check instructions with matching IDs.
- **Example game:** update The Facility to emit signals on its two endings. Update The Outpost to receive them and branch the opening narrative and ending.

## Scope

This spec covers signals as a cross-chapter narrative branching mechanism. It does not cover:

- Signals that fire automatically (like cues) — signals are always explicit conditional checks that the player evaluates
- Signal arithmetic (combining signals) — a signal is a simple flag, present or absent
- Signals within a single chapter — while technically possible, the intended use is cross-chapter state

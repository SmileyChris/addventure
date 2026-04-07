# Advanced Mechanics

Once you're comfortable with rooms, room objects, interactions, and arrows, these features let you build richer puzzles.

## Objects

### Multi-target interactions

Some puzzles require combining two things. Multi-target interactions use a verb with two entities:

```markdown
TERMINAL
+ USE + KEYCARD:
  You slide the keycard into the slot. The screen flickers to life.
  - TERMINAL -> TERMINAL__UNLOCKED
  - KEYCARD -> trash
```

The syntax is `+ VERB + TARGET:` on the entity that "receives" the action. The player computes: `VERB + ENTITY + TARGET` (three IDs added together), and the sum maps to this interaction's story entry.

The second target can be any room object or inventory object — including things in the player's inventory. This is how you create "use X with Y" puzzles.

#### Multi-target on inventory objects

Inventory objects (defined in `index.md`) can be used as the second target in any room. The player adds the verb ID + entity ID + inventory object ID to get the sum.

```markdown
CELL_DOOR
+ USE + KEY:
  The key turns. The door swings open.
  - CELL_DOOR -> trash
  - KEY -> trash
  - player -> "Corridor"
```

Here KEY is an inventory object. The player needs to have it (on their inventory sheet) to compute the correct sum.

### Room and inventory objects

**Room objects** are room-bound. They appear on a specific room sheet and stay there unless an arrow moves them.

**Inventory objects** live on the inventory sheet. They travel with the player between rooms.

When a room object has a `-> player` arrow, the compiler automatically creates an inventory version. The player crosses out the room object on their room sheet and writes the inventory ID on their inventory sheet. The inventory ID is derived from the TAKE verb: `TAKE ID + room object ID`.

This means you don't need to declare inventory objects in `# Inventory` for things the player picks up — just write the room object in a room with a TAKE interaction:

```markdown
KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player
```

Most interactions on the room object (LOOK, multi-target USE, etc.) are duplicated for the inventory version, so the player can examine and use carried objects. The exception is acquisition interactions — those where the only arrow is `-> player` (the sole purpose is picking the object up). These aren't duplicated since re-acquiring from inventory is meaningless.

The `# Inventory` section in `index.md` is only needed for inventory objects that **never exist as room objects**:

- Crafted objects (combining two things produces a new object)
- Abstract rewards or tokens
- Objects available from the start that aren't in any room

**Note:** A game must have a `TAKE` verb defined if any room object uses `-> player`.

### The Interactions section

Some interactions don't belong to a specific room object — they apply to the room as a whole or involve standalone logic. Put these in a `## Interactions` section at the bottom of a room file:

```markdown
# Control Room
LOOK: Fluorescent lights buzz overhead.

TERMINAL
+ LOOK: A dusty CRT monitor.

## Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope.
  - BINDINGS -> trash
```

Interactions in this section follow the same syntax but aren't nested under a room object.

### Wildcards

The `*` wildcard matches all room objects in the current room (not inventory objects). Use it for catch-all responses:

```markdown
USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

This creates an interaction for every entity the player could target. It's useful for verb states that should block all normal actions, or for generic responses before a puzzle is solved.

## Verbs

### Verb states

Just as entities can change state, so can verbs. This lets you change what an action *does* partway through the game.

The example game uses this for restraints:

```markdown
## Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

Here's what's happening:

1. `USE__RESTRAINED` is a verb state. If the player starts with their verb sheet showing `USE__RESTRAINED` instead of `USE`, every attempt to USE anything triggers the wildcard response.
2. When the player cuts the bindings, the arrow `USE__RESTRAINED -> USE` restores the normal verb. On paper, the player crosses out the `USE__RESTRAINED` ID on their verb sheet and writes in the real `USE` ID.

To start the game with a modified verb, list the state variant in `# Verbs` instead of the base verb:

```markdown
# Verbs
USE__RESTRAINED
TAKE
LOOK
```

The player begins with `USE__RESTRAINED` on their verb sheet. Once they cut the bindings, the arrow `USE__RESTRAINED -> USE` replaces it with the normal verb.

### Adding and removing verbs

Beyond changing verb *state*, you can add entirely new verbs or remove existing ones mid-game.

#### Revealing a new verb

Use `-> VERBNAME` (an arrow with no subject) to grant the player a new ability:

```markdown
+ USE + ANCIENT_TOME:
  The symbols rearrange before your eyes. You understand how to combine things.
  - -> COMBINE
```

The verb doesn't need to be listed in `# Verbs` — the compiler auto-registers it (like `-> player` auto-registers inventory objects). It won't appear on the verb sheet at game start. When the arrow fires, the ledger tells the player to record the verb name and ID.

Define interactions for the new verb normally — they work as soon as the player has it:

```markdown
WIDGET
+ COMBINE + WIDGET:
  You reshape the widget into something useful.
```

#### Removing a verb

Use `VERB -> trash` to permanently remove a verb:

```markdown
+ USE + CURSED_IDOL:
  The idol crumbles. The knowledge drains from your mind.
  - EXAMINE -> trash
```

The ledger tells the player to cross out the verb on their verb sheet. Any interactions using that verb become inaccessible.

## Rooms

### Actions

Actions are direct ledger lookups — things the player can do without addition. They're declared with the `>` marker:

```markdown
# Forest

> GO_NORTH
  You head north through the trees.
  - player -> "Clearing"

> GO_SOUTH
  You retrace your steps to the village.
  - player -> "Village"
```

Each action gets a ledger entry number printed directly on the room sheet (e.g. "GO NORTH ... A-12"). Action names use `ALL_CAPS` with optional single underscores. Actions can do anything an interaction does: narrative, arrows, state changes.

#### Discoverable actions

Nest an action under an interaction to make it discoverable. It won't appear on the room sheet until the parent interaction fires:

```markdown
HATCH
+ USE + CROWBAR:
  You pry the hatch open.
  - HATCH -> trash
  - CROWBAR -> trash
  > GO_DOWN
    You descend into darkness.
    - player -> "Basement"
```

When the player uses the crowbar on the hatch, the instructions include "Write GO DOWN (A-7) in a discovery slot."

#### Removing actions

Actions can be removed with `-> trash`, just like room objects:

```markdown
LEVER
+ USE:
  The bridge collapses behind you!
  - GO_BACK -> trash
```

### Fragments

A `::: fragment` block inside an interaction adds long-form hidden content — finale text, reveals, or anything players shouldn't read until directed. The content is kept separate from the main game flow.

```markdown
VAULT_DOOR
+ OVERRIDE:
  The door swings open. You step inside.
  - player -> "Vault"

  ::: fragment
  Inside the vault you find the letter. You read it slowly.

  *My dear,*

  *By the time you find this, I'll be long gone...*
  :::
```

When this entry fires, the ledger instruction tells the player which fragment to turn to (e.g. "Turn to Fragment Alpha"). Fragments are printed in a separate section at the back of the ledger, or as a separate document — see [Fragment modes](reference.md#fragment-modes).

Fragment content uses the same narrative formatting as regular prose — see [Narrative formatting](writing-rooms.md#narrative-formatting) for the full syntax.

### Cue checks (cross-room effects)

Sometimes an action in one room should affect another room — pulling a lever that opens a gate elsewhere, flipping a switch that powers on a machine in the basement, etc. **Cue checks** handle this.

#### How it works

A cue is a number the player writes on their inventory sheet. When they enter any room, they add each cue number to the Room ID and check the Potentials List. If there's a match, a ledger entry fires — revealing entities, changing state, or whatever you need.

The player never knows which room a cue is "for" until the sum matches. This preserves surprise.

#### Writing a cue

Use `? -> "Room Name"` as the arrow subject, with the resolution content indented below it:

```markdown
LEVER
+ USE:
  You pull the lever. Something heavy shifts in the distance.
  - ? -> "Courtyard"
    An iron gate has risen from the ground.
    - GATE -> room
```

When the player triggers USE + LEVER:
1. The ledger says *"Write 347 in your Cue Checks"* (number assigned at compile time)
2. Later, when the player enters the Courtyard, they add 347 + Courtyard's Room ID
3. The sum matches a potentials entry → a new ledger entry fires
4. That entry says *"Write GATE in a discovery slot"* and *"Cross out 347 from your Cue Checks"*

The indented block under `?` defines what happens when the cue resolves. It works like any interaction body: narrative text, then arrows for state changes.

#### Multiple cues from one interaction

A single interaction can trigger cues in multiple rooms:

```markdown
+ USE:
  You pull the master lever. Machinery groans throughout the building.
  - ? -> "Courtyard"
    The iron gate swings open.
    - GATE -> room
  - ? -> "Basement"
    A hidden panel slides aside.
    - PANEL -> room
```

#### Cues and room states

By default, a cue resolves regardless of the target room's current state. If the Courtyard has base and `COURTYARD__NIGHT` states, `? -> "Courtyard"` fires in either.

You can target a specific state:

```markdown
- ? -> "Courtyard__NIGHT"
  A figure emerges from the shadows.
  - FIGURE -> room
```

This only fires when the Courtyard is in the `NIGHT` state.

To target *only* the base state (before any transformation), add a trailing `__`:

```markdown
- ? -> "Courtyard__"
  The fountain sparkles in daylight.
  - COIN -> room
```

| Syntax | Resolves in |
|---|---|
| `? -> "Room"` | Any state (base + all variants) |
| `? -> "Room__STATE"` | Only that specific state |
| `? -> "Room__"` | Only the base state |

### Signals

Signals let you branch narrative based on earlier decisions. A signal is a named flag — when the player triggers it, they write a numeric code on their sheet. Later, a signal check branches the story depending on which signals the player has.

This works both within a single game (branching based on a choice the player made earlier) and across chapters (carrying consequences from one booklet to the next).

#### Emitting a signal

Use `NAME -> signal` as an arrow. The player writes the signal's numeric code on their sheet:

```markdown
+ USE + PRISONER:
  The prisoner cups their hands and you step up. Together, you escape through the vent.
  - EVERYONE_OUT_ESCAPE -> signal
```

The ledger instruction: *"Write 64745 in your signals."*

Signal names follow the same ALL_CAPS naming rules as other identifiers. Choose names that describe the decision or outcome, not the mechanic: `EVERYONE_OUT_ESCAPE` is clearer than `ENDING_A`.

#### Checking signals

Signal checks use `NAME?` syntax with `otherwise?` as the default. All matching branches fire — if the player has multiple signals, they read every matching entry. `otherwise?` fires only when no signal matches.

In the index description (checked when starting the chapter):

```markdown
EVERYONE_OUT_ESCAPE?
  A companion catches up behind you.
WITNESS_ESCAPE?
  You're alone.
otherwise?
  You keep walking.
```

In an interaction (checked during play):

```markdown
CONSOLE
+ USE:
  You lift the microphone.
  EVERYONE_OUT_ESCAPE?
    Your companion leans close. "Tell them everything."
  otherwise?
    Your voice is the only one in the room.
```

Common narrative and arrows before the first `NAME?` block apply to all branches. Each `NAME?` and `otherwise?` block has its own narrative and arrows.

On the printed sheet, signal checks render as: *"Check your signals: 64745 → read B-3. 92951 → read B-7. Otherwise → read B-12."*

#### Signals across chapters

When used between chapters, the sending chapter emits a signal and the receiving chapter checks it — no coordination needed. Signal IDs are derived from the name, so both chapters produce the same number independently.

When building with `--all`, the compiler validates signal usage across chapters and warns about signals that are emitted but never checked, or checked but never emitted.

See the [Signals reference](reference.md#signals) for the full syntax summary.

## Chapters

Chapters let you split a game across multiple booklets — sequels, side quests, epilogues. Each chapter is a subdirectory within your game directory, with its own `index.md` and room files. Chapters are independently compiled with their own ID space.

### Creating chapters

Run `addventure new` from inside your game directory:

```bash
cd my-game
addventure new "The Escape"     # creates the-escape/index.md with prefix B
addventure new "The Surface"    # creates the-surface/index.md with prefix C
```

Each chapter is automatically assigned a unique ledger prefix (B, C, D...) so its ledger entries don't clash with other chapters. The parent game is always prefix A.

### Building

```bash
addventure build my-game --all          # all chapters in one PDF
addventure build my-game                # just the parent (chapter A)
addventure build my-game/the-escape     # just one chapter
```

When built standalone, a chapter's title nests under the parent: "The Facility — The Escape", and the PDF filename reflects this (`the-facility_the-escape.pdf`).

When built with `--all`, the output shares one Actions & Inventory page across all chapters. Each chapter gets its own title page (with potentials list and cue checks), rooms, and ledger.

### Transitioning between chapters

Use `player -> "ChapterName"` to direct the player to the next chapter:

```markdown
+ USE + AIR_DUCT:
  You escape through the vent.
  - player -> "Epilogue"
```

In a standalone build, this renders as: "Continue with the addventure booklet: The Facility — Epilogue." In a combined build: "Turn to the next chapter: Epilogue."

This works well inside [fragments](#fragments) — the player finishes reading the ending prose, then sees the transition instruction.

### Carrying state between chapters

Chapters can carry narrative consequences using [signals](#signals). The sending chapter emits a signal, and the receiving chapter branches the story based on which signals the player has.

See [Signals across chapters](#signals-across-chapters) for details.

## Compiler

### Game sizing and ID allocation

The compiler randomly assigns IDs to verbs and entities, then checks that no two interactions produce the same sum. If they do, it retries with a different random seed.

**How IDs work:**
- Verb IDs: 2-digit (11–99, excluding multiples of 5) — 72 possible values
- Entity IDs: 3-digit (100–999, excluding multiples of 5) — 720 possible values
- Sums range from ~111 to ~1100 for single-target, higher for multi-target

**When do collisions happen?** Two interactions collide when `verb1 + entity1 = verb2 + entity2`. This only occurs across *different* verbs (same verb + different entity always gives different sums). The number of verbs barely matters — what drives collisions is **total room object count** across all rooms.

**Rough sizing guide:**

| Total room objects | Entity IDs | Success rate per attempt | Notes |
|---|---|---|---|
| Up to ~80 | 3-digit | >50% (finds in 1–2 tries) | Comfortable |
| ~80–100 | 3-digit | ~1–10% (finds in 20–100 tries) | Pushes the limit |
| 100+ | 4-digit (auto) | >50% again | Compiler falls back automatically |
| 300+ | 4-digit | Starts getting tight | Consider splitting into chapters |


The compiler tries 3-digit IDs first (200 attempts). If no collision-free allocation is found, it automatically retries with 4-digit entity IDs (1000–9999, 7200 possible values) and 3-digit verb IDs (101–999). The wider verb range spreads sums out more, making it harder for players to reverse-engineer which verb was used. This is seamless — larger games just get slightly bigger numbers on the sheets.

**For very large games**, consider splitting into chapters (see [Chapters](#chapters) below).

**The player math tradeoff:** 3-digit addition is easy in your head. 4-digit works on paper but is slower. Design your game to stay in 3-digit territory if possible — most games will, since even a 6-room game with 10+ room objects per room stays well under 80 total.

### Ledger entry deduplication

The compiler merges interactions that produce identical ledger entries into a single entry. This happens most often with:

- **Wildcard expansions** — `USE__RESTRAINED + *:` creates one interaction per entity, but they all share the same narrative and arrows, so they share one entry.
- **Item duplication** — when a room object interaction is duplicated for the inventory version and nothing in the arrows references the inventory object differently (no `-> trash` of the inventory object), the room object and inventory versions share one entry.

Each version still has its own sum in the Potentials List, but they all point to the same entry number. This keeps the ledger compact.

Entries are **not** merged when:

- The arrows differ (e.g. the inventory version strips `OBJECT -> player`)
- An `OBJECT -> trash` arrow would generate different instructions ("Cross out on room sheet" vs "Cross out on Inventory")

### Formal grammar

The complete syntax is specified in [`docs/grammar.ebnf`](https://github.com/SmileyChris/addventure/blob/main/docs/grammar.ebnf) as an EBNF grammar. It documents the concrete source syntax accepted by the parser, with structural and semantic rules kept separate so the language definition stays precise.

The parser is strict — every block type rejects unexpected lines. If the compiler reports a parse error, the grammar is the authoritative reference for what's valid at that point.

Next: [Reference](reference.md) for a compact syntax cheat sheet.

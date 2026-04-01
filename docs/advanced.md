# Advanced Mechanics

Once you're comfortable with rooms, nouns, interactions, and arrows, these features let you build richer puzzles.

## Multi-target interactions

Some puzzles require combining two things. Multi-target interactions use a verb with two entities:

```markdown
TERMINAL
+ USE + KEYCARD:
  You slide the keycard into the slot. The screen flickers to life.
  - TERMINAL -> TERMINAL__UNLOCKED
  - KEYCARD -> trash
```

The syntax is `+ VERB + TARGET:` on the entity that "receives" the action. The player computes: `VERB + ENTITY + TARGET` (three IDs added together), and the sum maps to this interaction's story entry.

The second target can be any noun or item — including things in the player's inventory. This is how you create "use X with Y" puzzles.

### Multi-target on items

Items (defined in `index.md`) can be used as the second target in any room. The player adds the verb ID + entity ID + item ID to get the sum.

```markdown
CELL_DOOR
+ USE + KEY:
  The key turns. The door swings open.
  - CELL_DOOR -> trash
  - KEY -> trash
  - player -> "Corridor"
```

Here KEY is an inventory item. The player needs to have it (on their inventory sheet) to compute the correct sum.

## Verb states

Just as entities can change state, so can verbs. This lets you change what an action *does* partway through the game.

The example game uses this for restraints:

```markdown
# Interactions

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

To start the game with a modified verb, you'd set it up in your starting room's state or an initial interaction.

## The `# Interactions` section

Some interactions don't belong to a specific noun — they apply to the room as a whole or involve standalone logic. Put these in a `# Interactions` section at the bottom of a room file:

```markdown
# Control Room
LOOK: Fluorescent lights buzz overhead.

TERMINAL
+ LOOK: A dusty CRT monitor.

# Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope.
  - BINDINGS -> trash
```

Interactions in this section follow the same syntax but aren't nested under a noun.

## Wildcards

The `*` wildcard matches all entities in the current room. Use it for catch-all responses:

```markdown
USE__RESTRAINED + *:
  You strain against the bindings. No use.
```

This creates an interaction for every entity the player could target. It's useful for verb states that should block all normal actions, or for generic responses before a puzzle is solved.

## The `@room` reference

Use `@room` to reference the current room as an entity in interactions:

```markdown
+ LOOK: ...
```

When written at the room level (not under a noun), `LOOK` already targets the room. But `@room` is useful when you need to explicitly reference the room entity in arrows or other contexts.

## Items vs. nouns

**Nouns** are room-bound. They appear on a specific room sheet and stay there unless an arrow moves them.

**Items** live on the inventory sheet. They travel with the player between rooms.

When a noun has a `-> player` arrow, the compiler automatically creates an inventory version. The player crosses out the noun on their room sheet and writes the inventory ID on their inventory sheet. The inventory ID is derived from the TAKE verb: `TAKE ID + noun ID`.

This means you don't need to declare items in `# Items` for things the player picks up — just write the noun in a room with a TAKE interaction:

```markdown
KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player
```

All interactions on the noun (LOOK, multi-target USE, etc.) are duplicated for the inventory version, so the player can examine and use carried items.

The `# Items` section in `index.md` is only needed for items that **never exist as room nouns**:

- Crafted items (combining two things produces a new item)
- Abstract rewards or tokens
- Items available from the start that aren't in any room

**Note:** A game must have a `TAKE` verb defined if any noun uses `-> player`.

## Cue checks (cross-room effects)

Sometimes an action in one room should affect another room — pulling a lever that opens a gate elsewhere, flipping a switch that powers on a machine in the basement, etc. **Cue checks** handle this.

### How it works

A cue is a number the player writes on their inventory sheet. When they enter any room, they add each cue number to the Room ID and check the Potentials List. If there's a match, a ledger entry fires — revealing entities, changing state, or whatever you need.

The player never knows which room a cue is "for" until the sum matches. This preserves surprise.

### Writing a cue

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

### Multiple cues from one interaction

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

### Cues and room states

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

## Game sizing and ID allocation

The compiler randomly assigns IDs to verbs and entities, then checks that no two interactions produce the same sum. If they do, it retries with a different random seed.

**How IDs work:**
- Verb IDs: 2-digit (11–99, excluding multiples of 5) — 72 possible values
- Entity IDs: 3-digit (100–999, excluding multiples of 5) — 720 possible values
- Sums range from ~111 to ~1100 for single-target, higher for multi-target

**When do collisions happen?** Two interactions collide when `verb1 + entity1 = verb2 + entity2`. This only occurs across *different* verbs (same verb + different entity always gives different sums). The number of verbs barely matters — what drives collisions is **total noun count** across all rooms.

**Rough sizing guide:**

| Total nouns | Entity IDs | Success rate per attempt | Notes |
|---|---|---|---|
| Up to ~80 | 3-digit | >50% (finds in 1–2 tries) | Comfortable |
| ~80–100 | 3-digit | ~1–10% (finds in 20–100 tries) | Pushes the limit |
| 100+ | 4-digit (auto) | >50% again | Compiler falls back automatically |
| 300+ | 4-digit | Starts getting tight | Consider splitting into chapters |

The compiler tries 3-digit IDs first (200 attempts). If no collision-free allocation is found, it automatically retries with 4-digit entity IDs (1000–9999, 7200 possible values) and 3-digit verb IDs (101–999). The wider verb range spreads sums out more, making it harder for players to reverse-engineer which verb was used. This is seamless — larger games just get slightly bigger numbers on the sheets.

**For very large games**, split into chapters. Each chapter is an independent game with its own ID space. Use narrative handoffs at chapter boundaries: the ending ledger entry tells the player what they're carrying, and the next chapter's first entry sets up the new inventory with fresh IDs.

**The player math tradeoff:** 3-digit addition is easy in your head. 4-digit works on paper but is slower. Design your game to stay in 3-digit territory if possible — most games will, since even a 6-room game with 10+ nouns per room stays well under 80 total.

## Design tips

**Start small.** A good first game has 2-3 rooms with a few puzzles. The example game (`games/example/`) is a good template.

**Name things clearly.** `RUSTY_KEY` is better than `KEY2`. Players see these names on their sheets.

**Test by building often.** Run `uv run adv build --text` frequently as you write. The compiler catches errors (undefined entities, bad arrows) and reports them with line numbers.

**Think about the paper experience.** Every state change means the player has to cross something out and write something new. Complex chains of arrows create complex instructions — keep it manageable.

Next: [Script Reference](reference.md) for a compact syntax cheat sheet.

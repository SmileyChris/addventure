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

**Items** are defined in `index.md` under `# Items` and live on the inventory sheet. They travel with the player between rooms.

When to use which:

- Something the player picks up and carries → start as a **noun**, use `-> player` to move it to inventory (it becomes item-like)
- Something always in inventory from the start → define as an **item**
- A fixture in a room → **noun** (never moves to inventory)

Items defined in `index.md` don't start in the player's inventory — they need to be placed somewhere with an arrow (`-> player` or `-> room`) or revealed through an interaction.

## Cross-room alerts

When an interaction in one room affects another room (e.g., pulling a lever that opens a door elsewhere), the compiler generates a **room alert**. The story entry tells the player to go to the other room's sheet and make changes there.

This happens automatically when an arrow references an entity that belongs to a different room.

## Design tips

**Start small.** A good first game has 2-3 rooms with a few puzzles. The example game (`games/example/`) is a good template.

**Name things clearly.** `RUSTY_KEY` is better than `KEY2`. Players see these names on their sheets.

**Test by building often.** Run `uv run adv build --text` frequently as you write. The compiler catches errors (undefined entities, bad arrows) and reports them with line numbers.

**Think about the paper experience.** Every state change means the player has to cross something out and write something new. Complex chains of arrows create complex instructions — keep it manageable.

Next: [Script Reference](reference.md) for a compact syntax cheat sheet.

# Addventure

A compiler for paper-based text adventures where **addition is the parser**.

Players solve games using only pencil, paper, and arithmetic. No electronics at the table — just printed sheets and a bit of addition.

## How it works

You write game scripts in markdown. Addventure compiles them into a printable PDF (or plain text) with everything players need to play.

The core mechanic: every verb and every entity in the game has a numeric ID. To interact with something, the player **adds** the verb ID to the entity ID, looks up the sum in a potentials list, and reads the corresponding story entry.

```
LOOK (51) + TERMINAL (951) = 1002 → Read entry A-5
```

That entry contains narrative text and physical instructions — cross out this ID, write in a new one, flip to a different room sheet. The game state lives entirely on paper.

## What players get

A compiled game produces four types of sheet:

**Verb Sheet**
:   Lists every action (LOOK, USE, TAKE...) with its numeric ID. When the game changes a verb, players cross out the old ID and write in the new one.

**Room Sheets**
:   One per location. Lists the objects visible in that room and their IDs. Players flip between room sheets as they move through the game.

**Inventory & Potentials List**
:   Tracks carried items and their IDs. The potentials list maps every valid sum to a story entry number — this is the lookup table players use after adding.

**Story Ledger**
:   Numbered narrative entries. Each contains a passage of story text and instructions: cross out an entity, write a new ID, move an item to your inventory, go to a different room.

## A player's turn

1. Choose a **verb** from the verb sheet (e.g. USE = 51)
2. Choose a **target** from the current room sheet or inventory (e.g. CROWBAR = 237)
3. **Add** the two numbers (51 + 237 = 288)
4. Look up **288** in the potentials list
5. If it's there, read the story entry it points to and follow the instructions
6. If it's not there, nothing happens — try something else

IDs are randomly assigned each time a game is compiled, so every printout is a unique puzzle.

## What authors write

Game scripts are plain markdown files in a directory. You need one `index.md` for metadata, verbs, and items. Every other `.md` file defines rooms and is loaded alphabetically.

The script syntax is compact and readable:

```markdown
CRATE
+ LOOK: A heavy wooden crate, nailed shut.
+ USE + CROWBAR:
  You pry it open. A keycard glints inside.
  - CRATE -> CRATE__OPEN
  - KEYCARD -> room
  - CROWBAR -> trash
```

This defines a crate you can look at and pry open with a crowbar — transforming the crate, revealing a keycard, and consuming the crowbar. All in seven lines.

Ready to build your first game? Head to [Getting Started](getting-started.md).

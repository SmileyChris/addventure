---
name: addventure-authoring
description: "Author, edit, review, or troubleshoot Addventure games: printable interactive fiction written as Markdown rooms, verbs, inventory, state transitions, cues, signals, fragments, chapters, and addventure build validation."
---

# Addventure Authoring

Use this skill when creating or changing an Addventure game, designing puzzles, explaining the format, reviewing playability, or fixing `addventure build` warnings/errors.

Addventure games are paper-first interactive fiction. Players combine printed numeric IDs by addition: `VERB + target [+ target]` maps to a potentials-list entry, which points to a ledger entry containing narrative and physical sheet-update instructions.

## Workflow

1. Inspect the game directory before editing:
   - `index.md` defines metadata, description, starting verbs, and starting inventory.
   - Other `.md` files define rooms; files load alphabetically, but gameplay depends on room headers and arrows.
   - Chapter subdirectories contain their own `index.md`; `addventure build DIR --all` combines them.
2. Identify the current design surface:
   - Starting room: `start:` in frontmatter, otherwise first base room parsed.
   - Core verbs: usually `LOOK`, `USE`, `TAKE`; `TAKE` is required when any room object moves `-> player`.
   - Visible starting objects are base room objects not discovered through arrows, cues, or signal checks.
3. Author changes as a printable state machine:
   - Keep object and verb names `ALL_CAPS_WITH_SINGLE_UNDERSCORES`.
   - Use `LOOK` to describe rooms and objects.
   - Use arrows for all state changes: movement, inventory, reveals, trashing, state transforms, cues, signals, actions, and verbs.
   - Prefer small, legible update chains; every arrow becomes player-facing paper instructions.
4. Validate after meaningful edits:
   - From this repo: `uv run addventure build path/to/game --md`.
   - Installed CLI: `addventure build path/to/game --md`.
   - For chapters: also run `addventure build path/to/game --all --md`.
   - Use markdown output for fast syntax/reachability checks; PDF needs Typst.
5. Treat build warnings as design feedback:
   - Unreachable interactions usually mean a missing reveal, wrong room/state, unavailable verb, or consumed item.
   - Collision failures mean the random ID allocator could not find non-overlapping sums; simplify or split dense interactions if retries fail.
   - Unknown targets/rooms usually mean a name mismatch, missing declaration, or quoted room typo.
6. Review narrative and playability, not just syntax:
   - Check that room transitions, object reveals, state changes, and fragments make sense in the story moment when they fire.
   - Ensure the player has enough narrative affordance to try important verbs/targets before puzzle solutions are required.
   - Make irreversible moves, endings, consumed items, and chapter transitions intentional and legible.

## Authoring Defaults

- Start with 2-4 verbs. More verbs increase player arithmetic and collision pressure.
- Use one room per file unless a small cluster is easier to read together.
- Put object-specific interactions under the object; use `## Interactions` for room-level or multi-object logic.
- Do not hard-wrap prose. In Addventure output, source line breaks can become visible narrow text; write each narrative paragraph as one source line unless you explicitly want a line break.
- Use states for changed behavior: `DOOR__OPEN`, `GENERATOR__RUNNING`, `USE__RESTRAINED`.
- Only observation interactions without arrows inherit into states. Any interaction that changes the game must be redefined on the state.
- Inventory pickup auto-registers the inventory object from `- OBJECT -> player`; do not also list it in `# Inventory` unless it never exists as a room object or you need explicit starting/crafted inventory.
- When a room object is picked up, its non-acquisition interactions are duplicated for the inventory version unless explicitly overridden or suppressed with an empty interaction.
- Use cues (`? -> "Room"`) for delayed cross-room effects; use signals (`NAME -> signal`, then `NAME?`) for first-match branching narrative or cross-chapter consequences.
- Put `::: fragment` blocks last in their interaction. Fragments may end with signal checks to create conditional sealed variants.
- A game should read as a coherent playable path, not just a valid state graph: every mechanical update should have a clear narrative cause and player-facing effect.

## References

Read `references/authoring-reference.md` when you need syntax details, examples, validation heuristics, or advanced mechanics such as actions, cues, signals, fragments, chapters, wildcards, and inventory interaction inheritance.

For deeper context on specific topics, read the project docs (paths relative to repo root):
- `docs/reference.md` — complete syntax reference with all arrow destinations and special forms
- `docs/state-and-transformation.md` — state machines, arrows, inheritance, room states, chaining
- `docs/grammar.ebnf` — formal concrete syntax specification
- `docs/writing-rooms.md` — design guide for writing room puzzles
- `docs/advanced.md` — wildcards, multi-target, verb states, cue checks, signals
- `docs/getting-started.md` — tutorial for new game authors

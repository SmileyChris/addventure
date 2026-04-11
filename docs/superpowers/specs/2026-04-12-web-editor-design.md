# Addventure Web Editor — Design Spec

A browser-based visual editor for authoring Addventure games. Authors create rooms, objects, interactions, and cross-room logic through a form-based UI with progressive disclosure — simple visual editing by default, raw markdown source view for power users. Games are stored in localStorage and exported as `.zip` files ready for `addventure build`.

## Tech Stack

- **Svelte 5** (runes) with TypeScript
- **Vite** for dev server and static build
- **CodeMirror 6** for source/markdown view
- **JSZip** for export
- Built output is static HTML/JS/CSS — hostable anywhere, or bundled with the Python CLI as `addventure editor`

## Data Model

The editor's data model mirrors the Python `models.py` dataclasses, dropping compiler-only fields (IDs, resolved interactions, entry numbers, source lines). All types below are TypeScript interfaces.

### Editor Wrapper

```typescript
interface GameProject {
  id: string;               // Unique project ID (UUID)
  name: string;             // Display name
  lastModified: number;     // Unix timestamp
  game: GameData;
}
```

### Core Model (mirrors models.py)

```typescript
interface GameData {
  metadata: Record<string, string>;   // title, author, start, ledger_prefix, image, image_height, name_style, description
  verbs: Record<string, Verb>;        // Keyed by name
  objects: Record<string, RoomObject>;       // Keyed by "room::name"
  inventory: Record<string, InventoryObject>; // Keyed by name
  rooms: Record<string, Room>;        // Keyed by name
  interactions: Interaction[];
  cues: Cue[];
  actions: Record<string, Action>;    // Keyed by "room::name"
  signalChecks: SignalCheck[];        // Index-level signal checks
  signalEmissions: string[];          // All signal names emitted (Set in Python, array here)
}

interface Verb {
  name: string;
}

interface Room {
  name: string;
  base: string;
  state: string | null;
}

interface RoomObject {
  name: string;
  base: string;
  state: string | null;
  room: string;
  discovered: boolean;
}

interface InventoryObject {
  name: string;
}

interface Arrow {
  subject: string;
  destination: string;
  signalName: string | null;  // Set when destination is "signal"
}

interface Interaction {
  verb: string;
  targetGroups: string[][];   // Each group is alternatives, groups are combined via cartesian product
  narrative: string;
  arrows: Arrow[];
  room: string;               // Empty string for global inventory interactions
  sealedContent: string | null;
  sealedArrows: Arrow[];
  signalChecks: SignalCheck[];
}

interface Cue {
  targetRoom: string;
  narrative: string;
  arrows: Arrow[];
  triggerRoom: string;
}

interface Action {
  name: string;
  room: string;
  narrative: string;
  arrows: Arrow[];
  discovered: boolean;
}

interface SealedText {
  ref: string;
  content: string;
  images: string[];
  room: string;
  arrows: Arrow[];
  signalChecks: SignalCheck[];
}

interface SignalCheck {
  signalNames: string[];  // Empty array = "otherwise?"
  narrative: string;
  arrows: Arrow[];
}
```

### Fields Excluded (compiler-only)

These fields from the Python models are not stored in the editor — they are computed during compilation:

- All `id` fields (Verb, Room, RoomObject, InventoryObject, Cue)
- `sum_id`, `entry_number` on ResolvedInteraction, Cue, Action, SealedText, SignalCheck
- `source_line` on all types
- `ResolvedInteraction` (entire type — produced by compiler)
- `auto_inventory`, `auto_verbs` sets (derived by compiler from arrows)
- `suppressed_interactions` (compiler artifact)
- `warnings` (compiler output)
- `from_inventory` on ResolvedInteraction

## UI Layout

### Top Bar

- **Left**: Addventure logo + current project name (editable)
- **Right**: Game Settings button, Export .zip button, Import button

### Left Sidebar

Always visible. Contains five sections in order:

1. **Game Summary** — always first, visually distinct. Clicking it shows the `index.md` content in the main panel: metadata (title, author, start room), opening description/narrative, and index-level signal checks. This is the "home" of the project.

2. **Rooms** — list of all rooms. Active room highlighted. Click to navigate. "+ Add room" at bottom. Rooms with states show a subtle badge.

3. **Verbs** — list of declared verbs. Verb states (e.g. `USE__RESTRAINED`) shown with a state badge in a different color. "+ Add verb" at bottom.

4. **Inventory** — list of manually declared inventory objects (from `# Inventory` section). "+ Add item" at bottom. Auto-inventory items (derived from `-> player` arrows) are not shown here — they're a compiler concern.

5. **Signals & Cues** — registry of all signals and cues in the game. Signals shown with a lightning icon, cues shown with a diamond icon and their target room. These are created as a byproduct of authoring interactions (adding `-> signal` arrows or `? -> "Room"` cues) and appear here automatically. Other rooms can then reference them.

**Footer**: Map View toggle button.

### Main Panel

Displays content for the selected sidebar item.

#### Game Summary View (index.md)

- Metadata fields: title, author, start room (dropdown of rooms), ledger_prefix, image upload, image_height, name_style
- Description: rich text area for opening narrative
- Index-level signal checks: list of conditional branches (signal name(s) + narrative + arrows)

#### Room View

- **Room header**: room name (editable) + "start room" badge if applicable + Visual/Source toggle
- **Room description**: text area for the LOOK narrative of the room itself
- **Objects list**: collapsible cards for each object in the room
  - **Collapsed**: object name, state count badge, interaction count
  - **Expanded**: state tabs (base + named states) + interaction list for active state
- **Freeform interactions**: section for `## Interactions` block entries (wildcard matches, multi-target combinations that aren't tied to a specific object)
- **Actions**: pre-printed actions (`> ACTION_NAME`) and discoverable actions
- **"+ Add object"** and **"+ Add freeform interaction"** buttons

#### Source View

Full-room raw markdown in a CodeMirror editor with syntax highlighting for the Addventure script format. Bidirectional sync with the visual view — edits in either propagate to the other.

### Map View

Auto-generated graph of rooms as nodes and movement arrows (`player -> "Room"`) as directed edges. Replaces the main panel content (toggled via the sidebar footer button — click to enter map view, click again or click a room node to return to room editing).

- Rooms are draggable nodes — positions saved per project
- Clicking a room node navigates to it in the editor
- Edges labeled with the triggering interaction context
- Cues shown as dashed lines between rooms

### Object Editing (expanded card)

#### State Tabs

Tabs across the top of the expanded object card: one tab per state (base + named states like `OPEN`, `LOCKED`). Each tab shows that state's interactions independently.

- **"+ Add state"** button to create a new state variant
- Creating a state via an arrow (e.g. `DOOR -> DOOR__OPEN`) in another interaction automatically creates the state tab

#### Interaction List

Each interaction within a state is a card showing:

- **Verb label**: colored by verb
- **Targets**: chips showing target groups with alternation (e.g. `KEY | CROWBAR`)
- **Narrative preview**: truncated text
- **Arrow badges**: colored pills summarizing consequences:
  - Destroy (red-ink): "× ITEM"
  - Pick up (amber): "↑ ITEM → inventory"
  - Move (gold): "→ Room Name"
  - Transform (parchment): "ITEM → ITEM__STATE"
  - Reveal (green-ink): "ITEM appears"
  - Cue (parchment-dark): "? → Room Name"
  - Signal (amber): "⚡ SIGNAL_NAME"
  - Reveal verb (gold): "+ VERB"
  - Discover action (green-ink): "> ACTION"

Clicking an interaction expands it for full editing.

## Interaction Authoring

When adding or editing an interaction:

### Verb Picker

Dropdown of declared verbs from the sidebar. Verb states (`USE__RESTRAINED`) shown with a state badge. Typing filters the list. Option to create a new verb inline.

### Target Builder

- First target defaults to the current object (pre-filled, removable for freeform interactions)
- Within a target group, alternation shown as chips: `KEY | CROWBAR` — autocomplete from room objects + inventory items
- **"+ Add target group"** button for multi-group interactions (cartesian product)
- Special targets available: `@ROOM_NAME` (room itself), `*` (wildcard — all objects without explicit interactions)

### Narrative Editor

Text area for the player-facing description. Plain text — no markdown formatting within narratives.

### Arrows Panel

Below the narrative. Each arrow is a row with:

- **Type selector** (dropdown): Destroy / Pick up / Move player / Transform / Reveal in room / Cue / Signal / Reveal verb / Discover action / Change room state
- **Subject/destination fields** that adapt to the selected type:
  - "Destroy": pick object → `OBJECT -> trash`
  - "Pick up": pick object → `OBJECT -> player`
  - "Move player": pick room → `player -> "Room"`
  - "Transform": pick object + new state name → `OBJECT -> OBJECT__STATE`
  - "Reveal in room": pick object → `OBJECT -> room`
  - "Cue": pick target room → `? -> "Room"`
  - "Signal": enter signal name → `NAME -> signal`
  - "Reveal verb": pick/enter verb name → `-> VERB`
  - "Discover action": pick action name → `>ACTION -> room`
  - "Change room state": enter state name → `room -> room__STATE`
- **"+ Add arrow"** button
- Arrows that create new object states automatically prompt to define that state's interactions (or create an empty state tab for later)

### Sealed Content (optional, expandable)

- Toggle to add a fragment block (`::: fragment`)
- Text area for hidden content
- Optional arrows and signal checks within the fragment

### Signal Checks (optional, expandable)

- Toggle to add conditional branches
- Each branch: signal name(s) input, narrative text area, arrows panel
- "otherwise?" branch (empty signal names) available
- First matching branch wins (order matters — drag to reorder)

## Signals & Cues Sidebar

### Signals

When an author adds a `NAME -> signal` arrow in any interaction, the signal name automatically appears in the sidebar's Signals & Cues section. From there:

- Click a signal to see where it's emitted (which room/interaction) and where it's consumed (which signal checks reference it)
- Other interactions can reference it in signal checks
- Index-level signal checks (game/chapter start) are edited in the Game Summary view

### Cues

When an author adds a `? -> "Room"` arrow, the cue appears in the sidebar. The cue includes:

- **Trigger room**: where the cue is created (the current room being edited)
- **Target room**: where the effect fires
- **Narrative + arrows**: what happens when the cue fires in the target room

Cues are authored inline within the interaction that triggers them. The sidebar provides an overview of all cues in the game and their cross-room wiring.

## Storage

### localStorage Schema

```
addventure:projects          → JSON array of { id, name, lastModified }
addventure:project:{id}      → JSON serialized GameProject
addventure:project:{id}:undo → JSON array of GameData snapshots (last 50)
addventure:project:{id}:map  → JSON object of room positions { roomName: { x, y } }
```

### Auto-save

Every mutation to the game data triggers a debounced save (~500ms) to localStorage. The undo stack captures snapshots before each logical operation (add object, edit interaction, delete room, etc.) — not on every keystroke.

### Project Management

A landing page / project switcher shows all saved projects with name, last modified date, and action buttons (open, duplicate, delete, export). This is the entry point when no project is active.

## Export

### .zip Export

One-click export produces a `.zip` file containing:

- `index.md` — frontmatter (metadata), description, index-level signal checks, `# Verbs` section, `# Inventory` section (with any inventory-level interactions)
- `{room_name}.md` — one file per room (name lowercased, spaces to underscores), containing room description, objects with interactions organized by state, freeform interactions section, actions
- Referenced images (cover art, fragment images) if uploaded

The serializer walks the `GameData` model and emits `.md` files matching the format expected by the Addventure parser. The output is a valid game directory — unzip and run `addventure build`.

### Import

Accept a `.zip` file or individual `.md` files via drag-and-drop or file picker.

- Parse `.md` files using a JavaScript implementation of the Addventure parser's logic
- Extract frontmatter, verbs, inventory, rooms, objects, interactions, arrows, cues, signals
- Populate the editor's `GameData` model from the parsed result
- Round-trip fidelity: export → hand-edit → re-import works

## Visual Style

The editor uses the same design language as the existing Addventure website (`site/index.html`):

### Color Palette

```
--black: #0b0a09          (page background)
--dark: #151413            (panel backgrounds)
--dark-warm: #1c1a18       (sidebar background)
--mid-dark: #2a2725        (card backgrounds, borders)
--warm-gray: #3d3935       (subtle borders, dividers)
--parchment: #d4c5a9       (primary accent, highlights)
--parchment-light: #e8dcc6 (hover states)
--parchment-dark: #b8a88a  (secondary accent)
--gold: #c9a84c            (primary interactive elements, links)
--gold-bright: #e2c46d     (hover states for gold)
--gold-dim: #8a7235        (disabled/subtle gold)
--amber: #d4883a           (warnings, inventory accent)
--red-ink: #8b3a3a         (destructive actions, "destroy" arrows)
--green-ink: #4a7a4a       (positive actions, "reveal" arrows)
--ink: #1a1714             (text on light backgrounds)
--text-light: #c8c0b4      (primary text)
--text-mid: #9a9088        (secondary text)
--text-dim: #6b6158        (placeholder/hint text)
```

### Typography

- **Titles/headers**: Montserrat (800/900 weight, uppercase, tracked)
- **Body text/narratives**: Alegreya (serif, for the literary feel)
- **Code/identifiers**: JetBrains Mono (verb names, object names, signal names)

### Design Notes

- Warm, dark theme throughout — no cool blues or purples
- Gold accents for interactive elements (buttons, active states, links)
- Parchment tones for highlights and badges
- Subtle grain texture overlay (matching the site)
- Object/interaction cards use `--mid-dark` backgrounds on `--dark` panels
- Active sidebar items use gold left border + subtle gold background tint
- Arrow badges use semantic colors: red-ink for destroy, green-ink for reveal, amber for inventory, gold for movement

## Chapters

The editor builds single games (one `index.md` + room files). An author can set `ledger_prefix` in Game Settings to mark a game as a chapter, and export it as part of a multi-chapter game. Multi-chapter assembly (parent `index.md` + chapter subdirectories + `--all` build) is handled outside the editor for now.

## Future Considerations (not in scope)

- In-browser compilation and preview of the built game output
- File System Access API for direct folder read/write without zip
- Multi-chapter editing within a single project
- Collaborative editing
- `addventure editor` CLI command that serves the built editor and watches for file changes

# Addventure Web Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a browser-based visual editor for authoring Addventure games, stored in localStorage, exportable as `.zip` files ready for `addventure build`.

**Architecture:** Svelte 5 SPA with runes-based reactive store. Data model mirrors Python `models.py`. Three layers: types/helpers (pure logic, tested), reactive store (state management), UI components (Svelte). Serializer converts between GameData and `.md` files bidirectionally.

**Tech Stack:** Svelte 5, TypeScript, Vite, Vitest, CodeMirror 6, JSZip

**Spec:** `docs/superpowers/specs/2026-04-12-web-editor-design.md`

---

## File Structure

```
editor/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html                    # Vite entry point
├── src/
│   ├── main.ts                   # Mount App.svelte
│   ├── App.svelte                # Root: router between ProjectList and Editor
│   ├── lib/
│   │   ├── types.ts              # All TypeScript interfaces (GameProject, GameData, etc.)
│   │   ├── factory.ts            # Factory functions: createGameData(), createRoom(), etc.
│   │   ├── helpers.ts            # Name formatting, derived data (signals list, room exits)
│   │   ├── store.svelte.ts       # Reactive game store using Svelte 5 runes ($state, $derived)
│   │   ├── persistence.ts        # localStorage read/write, auto-save, undo stack
│   │   ├── serializer.ts         # GameData → .md file strings
│   │   ├── parser.ts             # .md file strings → GameData (import)
│   │   └── export.ts             # .zip generation via JSZip
│   ├── components/
│   │   ├── TopBar.svelte         # Logo, project name, settings/export/import buttons
│   │   ├── Sidebar.svelte        # Left panel: summary, rooms, verbs, inventory, signals/cues
│   │   ├── MainPanel.svelte      # Routes to GameSummary, RoomView, or MapView
│   │   ├── ProjectList.svelte    # Landing page: list projects, create/open/delete/duplicate
│   │   ├── GameSummary.svelte    # index.md editor: metadata, description, signal checks
│   │   ├── RoomView.svelte       # Room header, description, object cards, freeform interactions
│   │   ├── ObjectCard.svelte     # Collapsible card with state tabs
│   │   ├── InteractionCard.svelte # Compact display: verb, targets, narrative preview, arrow badges
│   │   ├── InteractionEditor.svelte # Full editor: verb picker, targets, narrative, arrows
│   │   ├── ArrowEditor.svelte    # Single arrow row: type selector + adaptive fields
│   │   ├── ArrowBadge.svelte     # Colored pill showing arrow consequence
│   │   ├── SignalCheckEditor.svelte # Conditional branch editor
│   │   ├── TargetBuilder.svelte  # Target group chips with autocomplete
│   │   ├── VerbPicker.svelte     # Dropdown with filter + inline create
│   │   ├── SourceView.svelte     # CodeMirror editor for raw .md
│   │   └── MapView.svelte        # Room graph with draggable nodes
│   └── styles/
│       └── theme.css             # CSS custom properties from site palette
└── tests/
    ├── factory.test.ts
    ├── helpers.test.ts
    ├── persistence.test.ts
    ├── serializer.test.ts
    ├── parser.test.ts
    └── export.test.ts
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `editor/package.json`
- Create: `editor/vite.config.ts`
- Create: `editor/tsconfig.json`
- Create: `editor/index.html`
- Create: `editor/src/main.ts`
- Create: `editor/src/App.svelte`
- Create: `editor/src/styles/theme.css`
- Modify: `.gitignore`

- [ ] **Step 1: Scaffold Svelte 5 + Vite project**

```bash
cd /home/chris/dev/addventure
mkdir editor
cd editor
npm create vite@latest . -- --template svelte-ts
```

Select Svelte and TypeScript when prompted. This creates the base Vite + Svelte project.

- [ ] **Step 2: Install dependencies**

```bash
cd /home/chris/dev/addventure/editor
npm install jszip
npm install -D vitest @testing-library/svelte jsdom
```

- [ ] **Step 3: Configure Vitest**

Replace `editor/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
  },
});
```

- [ ] **Step 4: Create theme.css with project palette**

Write `editor/src/styles/theme.css`:

```css
:root {
  --black: #0b0a09;
  --dark: #151413;
  --dark-warm: #1c1a18;
  --mid-dark: #2a2725;
  --warm-gray: #3d3935;
  --parchment: #d4c5a9;
  --parchment-light: #e8dcc6;
  --parchment-dark: #b8a88a;
  --gold: #c9a84c;
  --gold-bright: #e2c46d;
  --gold-dim: #8a7235;
  --amber: #d4883a;
  --red-ink: #8b3a3a;
  --green-ink: #4a7a4a;
  --ink: #1a1714;
  --text-light: #c8c0b4;
  --text-mid: #9a9088;
  --text-dim: #6b6158;

  --font-title: 'Montserrat', sans-serif;
  --font-body: 'Alegreya', Georgia, serif;
  --font-mono: 'JetBrains Mono', monospace;
}

*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  background: var(--black);
  color: var(--text-light);
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.6;
}

body {
  overflow: hidden;
  height: 100vh;
}

/* Grain overlay matching site */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 256px;
}

::selection {
  background: var(--gold);
  color: var(--black);
}

a { color: var(--gold); text-decoration: none; }
a:hover { color: var(--gold-bright); }

h1, h2, h3, h4 {
  font-family: var(--font-title);
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  line-height: 1.1;
}

input, textarea, select {
  font-family: var(--font-body);
  font-size: inherit;
  color: var(--text-light);
  background: var(--mid-dark);
  border: 1px solid var(--warm-gray);
  border-radius: 4px;
  padding: 6px 10px;
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--gold);
}

button {
  font-family: var(--font-body);
  font-size: inherit;
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 6px 14px;
  background: var(--mid-dark);
  color: var(--text-light);
}

button:hover {
  background: var(--warm-gray);
}

/* Identifier/code styling */
.mono {
  font-family: var(--font-mono);
  font-size: 0.9em;
}
```

- [ ] **Step 5: Update index.html with fonts**

Replace `editor/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Addventure Editor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@800;900&family=Alegreya:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 6: Write minimal App.svelte**

Replace `editor/src/App.svelte`:

```svelte
<script lang="ts">
  import './styles/theme.css';
</script>

<div class="app">
  <p>Addventure Editor</p>
</div>

<style>
  .app {
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
```

- [ ] **Step 7: Update .gitignore**

Append to `.gitignore`:

```
editor/node_modules/
editor/dist/
```

- [ ] **Step 8: Verify it runs**

```bash
cd /home/chris/dev/addventure/editor
npm run dev
```

Open the URL in a browser. Verify "Addventure Editor" text appears with the dark theme.

- [ ] **Step 9: Verify tests work**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: 0 tests (no test files yet), clean exit.

- [ ] **Step 10: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/ .gitignore
git commit -m "feat(editor): scaffold Svelte 5 + Vite + TypeScript project"
```

---

### Task 2: Data Model & Factory Functions

**Files:**
- Create: `editor/src/lib/types.ts`
- Create: `editor/src/lib/factory.ts`
- Create: `editor/tests/factory.test.ts`

- [ ] **Step 1: Write types.ts**

```typescript
export interface GameProject {
  id: string;
  name: string;
  lastModified: number;
  game: GameData;
}

export interface GameData {
  metadata: Record<string, string>;
  verbs: Record<string, Verb>;
  objects: Record<string, RoomObject>;
  inventory: Record<string, InventoryObject>;
  rooms: Record<string, Room>;
  interactions: Interaction[];
  cues: Cue[];
  actions: Record<string, Action>;
  signalChecks: SignalCheck[];
}

export interface Verb {
  name: string;
}

export interface Room {
  name: string;
  base: string;
  state: string | null;
}

export interface RoomObject {
  name: string;
  base: string;
  state: string | null;
  room: string;
  discovered: boolean;
}

export interface InventoryObject {
  name: string;
}

export interface Arrow {
  subject: string;
  destination: string;
  signalName: string | null;
}

export interface Interaction {
  verb: string;
  targetGroups: string[][];
  narrative: string;
  arrows: Arrow[];
  room: string;
  sealedContent: string | null;
  sealedArrows: Arrow[];
  signalChecks: SignalCheck[];
}

export interface Cue {
  targetRoom: string;
  narrative: string;
  arrows: Arrow[];
  triggerRoom: string;
}

export interface Action {
  name: string;
  room: string;
  narrative: string;
  arrows: Arrow[];
  discovered: boolean;
}

export interface SignalCheck {
  signalNames: string[];
  narrative: string;
  arrows: Arrow[];
}
```

- [ ] **Step 2: Write factory.ts**

```typescript
import type {
  GameProject, GameData, Verb, Room, RoomObject, InventoryObject,
  Arrow, Interaction, Cue, Action, SignalCheck,
} from './types';

export function createGameData(): GameData {
  return {
    metadata: {},
    verbs: {},
    objects: {},
    inventory: {},
    rooms: {},
    interactions: [],
    cues: [],
    actions: {},
    signalChecks: [],
  };
}

export function createGameProject(name: string): GameProject {
  return {
    id: crypto.randomUUID(),
    name,
    lastModified: Date.now(),
    game: createGameData(),
  };
}

export function createVerb(name: string): Verb {
  return { name };
}

export function createRoom(name: string): Room {
  const parts = name.split('__');
  return {
    name,
    base: parts[0],
    state: parts.length > 1 ? parts.slice(1).join('__') : null,
  };
}

export function createRoomObject(name: string, room: string, discovered = false): RoomObject {
  const parts = name.split('__');
  return {
    name,
    base: parts[0],
    state: parts.length > 1 ? parts.slice(1).join('__') : null,
    room,
    discovered,
  };
}

export function createInventoryObject(name: string): InventoryObject {
  return { name };
}

export function createArrow(subject: string, destination: string): Arrow {
  const signalName = destination === 'signal' ? subject : null;
  return { subject, destination, signalName };
}

export function createInteraction(verb: string, room: string): Interaction {
  return {
    verb,
    targetGroups: [],
    narrative: '',
    arrows: [],
    room,
    sealedContent: null,
    sealedArrows: [],
    signalChecks: [],
  };
}

export function createCue(triggerRoom: string, targetRoom: string): Cue {
  return {
    targetRoom,
    narrative: '',
    arrows: [],
    triggerRoom,
  };
}

export function createAction(name: string, room: string): Action {
  return {
    name,
    room,
    narrative: '',
    arrows: [],
    discovered: false,
  };
}

export function createSignalCheck(): SignalCheck {
  return {
    signalNames: [],
    narrative: '',
    arrows: [],
  };
}

/** Composite key for objects dict: "room::name" */
export function objectKey(room: string, name: string): string {
  return `${room}::${name}`;
}

/** Composite key for actions dict: "room::name" */
export function actionKey(room: string, name: string): string {
  return `${room}::${name}`;
}
```

- [ ] **Step 3: Write factory tests**

Write `editor/tests/factory.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import {
  createGameData, createGameProject, createRoom, createRoomObject,
  createArrow, createInteraction, objectKey,
} from '../src/lib/factory';

describe('createGameData', () => {
  it('returns empty game data with all required fields', () => {
    const data = createGameData();
    expect(data.metadata).toEqual({});
    expect(data.verbs).toEqual({});
    expect(data.objects).toEqual({});
    expect(data.inventory).toEqual({});
    expect(data.rooms).toEqual({});
    expect(data.interactions).toEqual([]);
    expect(data.cues).toEqual([]);
    expect(data.actions).toEqual({});
    expect(data.signalChecks).toEqual([]);
  });
});

describe('createGameProject', () => {
  it('generates unique IDs', () => {
    const a = createGameProject('A');
    const b = createGameProject('B');
    expect(a.id).not.toBe(b.id);
  });

  it('sets name and timestamp', () => {
    const project = createGameProject('Test Game');
    expect(project.name).toBe('Test Game');
    expect(project.lastModified).toBeGreaterThan(0);
  });
});

describe('createRoom', () => {
  it('parses base room', () => {
    const room = createRoom('Control Room');
    expect(room.base).toBe('Control Room');
    expect(room.state).toBeNull();
  });

  it('parses stated room', () => {
    const room = createRoom('Basement__FLOODED');
    expect(room.base).toBe('Basement');
    expect(room.state).toBe('FLOODED');
  });
});

describe('createRoomObject', () => {
  it('parses base object', () => {
    const obj = createRoomObject('CROWBAR', 'Basement');
    expect(obj.base).toBe('CROWBAR');
    expect(obj.state).toBeNull();
    expect(obj.room).toBe('Basement');
    expect(obj.discovered).toBe(false);
  });

  it('parses stated object', () => {
    const obj = createRoomObject('DOOR__OPEN', 'Control Room');
    expect(obj.base).toBe('DOOR');
    expect(obj.state).toBe('OPEN');
  });

  it('respects discovered flag', () => {
    const obj = createRoomObject('KEYCARD', 'Control Room', true);
    expect(obj.discovered).toBe(true);
  });
});

describe('createArrow', () => {
  it('sets signalName for signal arrows', () => {
    const arrow = createArrow('EVERYONE_OUT', 'signal');
    expect(arrow.signalName).toBe('EVERYONE_OUT');
  });

  it('leaves signalName null for non-signal arrows', () => {
    const arrow = createArrow('ITEM', 'trash');
    expect(arrow.signalName).toBeNull();
  });
});

describe('objectKey', () => {
  it('creates composite key', () => {
    expect(objectKey('Basement', 'CROWBAR')).toBe('Basement::CROWBAR');
  });
});
```

- [ ] **Step 4: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/types.ts editor/src/lib/factory.ts editor/tests/factory.test.ts
git commit -m "feat(editor): add data model types and factory functions"
```

---

### Task 3: Helpers (Derived Data)

**Files:**
- Create: `editor/src/lib/helpers.ts`
- Create: `editor/tests/helpers.test.ts`

- [ ] **Step 1: Write helpers.ts**

```typescript
import type { GameData, Arrow, Interaction, Cue } from './types';

/** Format an entity name for display: STEEL_DOOR → "Steel Door" */
export function displayName(name: string): string {
  // Strip state suffix for display
  const base = name.split('__')[0];
  return base
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/** Get all signal names emitted in the game (derived from arrows) */
export function getSignalEmissions(game: GameData): string[] {
  const signals = new Set<string>();
  const scanArrows = (arrows: Arrow[]) => {
    for (const arrow of arrows) {
      if (arrow.destination === 'signal' && arrow.signalName) {
        signals.add(arrow.signalName);
      }
    }
  };

  for (const interaction of game.interactions) {
    scanArrows(interaction.arrows);
    scanArrows(interaction.sealedArrows);
    for (const check of interaction.signalChecks) {
      scanArrows(check.arrows);
    }
  }

  for (const cue of game.cues) {
    scanArrows(cue.arrows);
  }

  for (const action of Object.values(game.actions)) {
    scanArrows(action.arrows);
  }

  return [...signals].sort();
}

/** Get all signal names consumed (referenced in signal checks) */
export function getSignalConsumers(game: GameData): Record<string, { room: string; context: string }[]> {
  const consumers: Record<string, { room: string; context: string }[]> = {};
  const addConsumer = (signalName: string, room: string, context: string) => {
    if (!consumers[signalName]) consumers[signalName] = [];
    consumers[signalName].push({ room, context });
  };

  for (const interaction of game.interactions) {
    for (const check of interaction.signalChecks) {
      for (const name of check.signalNames) {
        addConsumer(name, interaction.room, interaction.verb);
      }
    }
  }

  for (const check of game.signalChecks) {
    for (const name of check.signalNames) {
      addConsumer(name, '', 'index-level');
    }
  }

  return consumers;
}

/** Get room exits: rooms reachable via player -> "Room" arrows */
export function getRoomExits(game: GameData, roomName: string): { targetRoom: string; via: string }[] {
  const exits: { targetRoom: string; via: string }[] = [];

  for (const interaction of game.interactions) {
    if (interaction.room !== roomName) continue;
    for (const arrow of interaction.arrows) {
      if (arrow.subject === 'player' && arrow.destination.startsWith('"') && arrow.destination.endsWith('"')) {
        exits.push({
          targetRoom: arrow.destination.slice(1, -1),
          via: interaction.verb,
        });
      }
    }
  }

  return exits;
}

/** Get all objects in a specific room, grouped by base name */
export function getRoomObjects(game: GameData, roomName: string): Record<string, string[]> {
  const grouped: Record<string, string[]> = {};

  for (const obj of Object.values(game.objects)) {
    if (obj.room !== roomName) continue;
    if (!grouped[obj.base]) grouped[obj.base] = [];
    grouped[obj.base].push(obj.name);
  }

  return grouped;
}

/** Get interactions for a specific room */
export function getRoomInteractions(game: GameData, roomName: string): Interaction[] {
  return game.interactions.filter(i => i.room === roomName);
}

/** Get interactions for a specific object (by name, in a room) */
export function getObjectInteractions(game: GameData, roomName: string, objectName: string): Interaction[] {
  return game.interactions.filter(i =>
    i.room === roomName &&
    i.targetGroups.length > 0 &&
    i.targetGroups[0].includes(objectName)
  );
}

/** Classify an arrow into a human-readable type */
export function classifyArrow(arrow: Arrow): string {
  if (arrow.destination === 'trash') return 'destroy';
  if (arrow.destination === 'player') return 'pickup';
  if (arrow.destination === 'room') return 'reveal';
  if (arrow.destination === 'signal') return 'signal';
  if (arrow.subject === 'player') return 'move';
  if (arrow.subject === '?') return 'cue';
  if (arrow.subject === '' && arrow.destination.match(/^[A-Z]/)) return 'reveal_verb';
  if (arrow.subject.startsWith('>')) return 'discover_action';
  if (arrow.subject === 'room') return 'room_state';
  if (arrow.destination.includes('__')) return 'transform';
  // Verb state restore: VERB__STATE -> VERB
  if (arrow.subject.includes('__') && !arrow.destination.includes('__')) return 'verb_restore';
  return 'transform';
}

/** Get a display label for an arrow */
export function arrowLabel(arrow: Arrow): string {
  const type = classifyArrow(arrow);
  switch (type) {
    case 'destroy': return `× ${displayName(arrow.subject)}`;
    case 'pickup': return `↑ ${displayName(arrow.subject)} → inventory`;
    case 'move': return `→ ${arrow.destination.replace(/"/g, '')}`;
    case 'transform': return `${displayName(arrow.subject)} → ${displayName(arrow.destination)}`;
    case 'reveal': return `${displayName(arrow.subject)} appears`;
    case 'cue': return `? → ${arrow.destination.replace(/"/g, '')}`;
    case 'signal': return `⚡ ${arrow.signalName}`;
    case 'reveal_verb': return `+ ${arrow.destination}`;
    case 'discover_action': return `> ${arrow.subject.slice(1)}`;
    case 'room_state': return `room → ${arrow.destination}`;
    case 'verb_restore': return `${displayName(arrow.subject)} → ${displayName(arrow.destination)}`;
    default: return `${arrow.subject} → ${arrow.destination}`;
  }
}
```

- [ ] **Step 2: Write helper tests**

Write `editor/tests/helpers.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import {
  displayName, getSignalEmissions, classifyArrow, arrowLabel, getRoomExits,
} from '../src/lib/helpers';
import { createGameData, createInteraction, createArrow } from '../src/lib/factory';

describe('displayName', () => {
  it('converts underscored name', () => {
    expect(displayName('STEEL_DOOR')).toBe('Steel Door');
  });

  it('strips state suffix', () => {
    expect(displayName('DOOR__OPEN')).toBe('Door');
  });

  it('handles single word', () => {
    expect(displayName('CROWBAR')).toBe('Crowbar');
  });
});

describe('getSignalEmissions', () => {
  it('finds signals from interaction arrows', () => {
    const game = createGameData();
    const interaction = createInteraction('USE', 'Basement');
    interaction.arrows = [createArrow('ESCAPE_SIGNAL', 'signal')];
    game.interactions.push(interaction);

    expect(getSignalEmissions(game)).toEqual(['ESCAPE_SIGNAL']);
  });

  it('returns empty for no signals', () => {
    const game = createGameData();
    expect(getSignalEmissions(game)).toEqual([]);
  });
});

describe('classifyArrow', () => {
  it('classifies destroy', () => {
    expect(classifyArrow(createArrow('ITEM', 'trash'))).toBe('destroy');
  });

  it('classifies pickup', () => {
    expect(classifyArrow(createArrow('ITEM', 'player'))).toBe('pickup');
  });

  it('classifies move', () => {
    expect(classifyArrow(createArrow('player', '"Basement"'))).toBe('move');
  });

  it('classifies signal', () => {
    expect(classifyArrow(createArrow('ESCAPE', 'signal'))).toBe('signal');
  });

  it('classifies cue', () => {
    expect(classifyArrow(createArrow('?', '"Basement"'))).toBe('cue');
  });

  it('classifies reveal', () => {
    expect(classifyArrow(createArrow('KEYCARD', 'room'))).toBe('reveal');
  });

  it('classifies transform', () => {
    expect(classifyArrow(createArrow('DOOR', 'DOOR__OPEN'))).toBe('transform');
  });

  it('classifies reveal verb', () => {
    expect(classifyArrow(createArrow('', 'OVERRIDE'))).toBe('reveal_verb');
  });
});

describe('arrowLabel', () => {
  it('labels destroy arrow', () => {
    expect(arrowLabel(createArrow('CROWBAR', 'trash'))).toBe('× Crowbar');
  });

  it('labels move arrow', () => {
    expect(arrowLabel(createArrow('player', '"Basement"'))).toBe('→ Basement');
  });

  it('labels signal arrow', () => {
    expect(arrowLabel(createArrow('ESCAPE', 'signal'))).toBe('⚡ ESCAPE');
  });
});

describe('getRoomExits', () => {
  it('finds exits from player arrows', () => {
    const game = createGameData();
    const interaction = createInteraction('USE', 'Control Room');
    interaction.arrows = [createArrow('player', '"Basement"')];
    game.interactions.push(interaction);

    const exits = getRoomExits(game, 'Control Room');
    expect(exits).toEqual([{ targetRoom: 'Basement', via: 'USE' }]);
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/helpers.ts editor/tests/helpers.test.ts
git commit -m "feat(editor): add helper functions for derived data and display"
```

---

### Task 4: Reactive Store & Persistence

**Files:**
- Create: `editor/src/lib/store.svelte.ts`
- Create: `editor/src/lib/persistence.ts`
- Create: `editor/tests/persistence.test.ts`

- [ ] **Step 1: Write persistence.ts**

```typescript
import type { GameProject } from './types';

const PROJECTS_KEY = 'addventure:projects';
const projectKey = (id: string) => `addventure:project:${id}`;
const undoKey = (id: string) => `addventure:project:${id}:undo`;
const mapKey = (id: string) => `addventure:project:${id}:map`;

export interface ProjectEntry {
  id: string;
  name: string;
  lastModified: number;
}

export function loadProjectIndex(): ProjectEntry[] {
  const raw = localStorage.getItem(PROJECTS_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveProjectIndex(entries: ProjectEntry[]): void {
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(entries));
}

export function loadProject(id: string): GameProject | null {
  const raw = localStorage.getItem(projectKey(id));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveProject(project: GameProject): void {
  project.lastModified = Date.now();
  localStorage.setItem(projectKey(project.id), JSON.stringify(project));

  // Update index
  const index = loadProjectIndex();
  const existing = index.findIndex(e => e.id === project.id);
  const entry: ProjectEntry = {
    id: project.id,
    name: project.name,
    lastModified: project.lastModified,
  };
  if (existing >= 0) {
    index[existing] = entry;
  } else {
    index.push(entry);
  }
  saveProjectIndex(index);
}

export function deleteProject(id: string): void {
  localStorage.removeItem(projectKey(id));
  localStorage.removeItem(undoKey(id));
  localStorage.removeItem(mapKey(id));

  const index = loadProjectIndex().filter(e => e.id !== id);
  saveProjectIndex(index);
}

export function loadMapPositions(id: string): Record<string, { x: number; y: number }> {
  const raw = localStorage.getItem(mapKey(id));
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export function saveMapPositions(id: string, positions: Record<string, { x: number; y: number }>): void {
  localStorage.setItem(mapKey(id), JSON.stringify(positions));
}

const MAX_UNDO = 50;

export function loadUndoStack(id: string): string[] {
  const raw = localStorage.getItem(undoKey(id));
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

export function saveUndoStack(id: string, stack: string[]): void {
  localStorage.setItem(undoKey(id), JSON.stringify(stack.slice(-MAX_UNDO)));
}
```

- [ ] **Step 2: Write persistence tests**

Write `editor/tests/persistence.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import {
  loadProjectIndex, saveProjectIndex, loadProject, saveProject,
  deleteProject, loadUndoStack, saveUndoStack,
} from '../src/lib/persistence';
import { createGameProject } from '../src/lib/factory';

beforeEach(() => {
  localStorage.clear();
});

describe('project index', () => {
  it('returns empty array when nothing stored', () => {
    expect(loadProjectIndex()).toEqual([]);
  });

  it('round-trips entries', () => {
    const entries = [{ id: '1', name: 'Test', lastModified: 1000 }];
    saveProjectIndex(entries);
    expect(loadProjectIndex()).toEqual(entries);
  });
});

describe('saveProject / loadProject', () => {
  it('round-trips a project', () => {
    const project = createGameProject('My Game');
    saveProject(project);

    const loaded = loadProject(project.id);
    expect(loaded).not.toBeNull();
    expect(loaded!.name).toBe('My Game');
    expect(loaded!.game.verbs).toEqual({});
  });

  it('updates the project index', () => {
    const project = createGameProject('My Game');
    saveProject(project);

    const index = loadProjectIndex();
    expect(index).toHaveLength(1);
    expect(index[0].name).toBe('My Game');
  });
});

describe('deleteProject', () => {
  it('removes project and index entry', () => {
    const project = createGameProject('My Game');
    saveProject(project);
    deleteProject(project.id);

    expect(loadProject(project.id)).toBeNull();
    expect(loadProjectIndex()).toEqual([]);
  });
});

describe('undo stack', () => {
  it('round-trips', () => {
    saveUndoStack('test-id', ['snapshot1', 'snapshot2']);
    expect(loadUndoStack('test-id')).toEqual(['snapshot1', 'snapshot2']);
  });

  it('caps at 50 entries', () => {
    const big = Array.from({ length: 60 }, (_, i) => `snap${i}`);
    saveUndoStack('test-id', big);
    expect(loadUndoStack('test-id')).toHaveLength(50);
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Write store.svelte.ts**

```typescript
import type { GameProject, GameData } from './types';
import { createGameProject, createGameData } from './factory';
import { saveProject, loadProject, saveUndoStack, loadUndoStack } from './persistence';

let _project = $state<GameProject | null>(null);
let _undoStack = $state<string[]>([]);
let _redoStack = $state<string[]>([]);
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
let _activeView = $state<'summary' | 'room' | 'map'>('summary');
let _activeRoom = $state<string | null>(null);

export const store = {
  get project() { return _project; },
  get game() { return _project?.game ?? null; },
  get activeView() { return _activeView; },
  get activeRoom() { return _activeRoom; },
  get canUndo() { return _undoStack.length > 0; },
  get canRedo() { return _redoStack.length > 0; },

  /** Open an existing project by ID */
  open(id: string) {
    const loaded = loadProject(id);
    if (loaded) {
      _project = loaded;
      _undoStack = loadUndoStack(id);
      _redoStack = [];
      _activeView = 'summary';
      _activeRoom = null;
    }
  },

  /** Create and open a new project */
  create(name: string) {
    _project = createGameProject(name);
    _undoStack = [];
    _redoStack = [];
    _activeView = 'summary';
    _activeRoom = null;
    saveProject(_project);
  },

  /** Close the current project */
  close() {
    this.flushSave();
    _project = null;
    _undoStack = [];
    _redoStack = [];
    _activeView = 'summary';
    _activeRoom = null;
  },

  /** Navigate to game summary */
  showSummary() {
    _activeView = 'summary';
    _activeRoom = null;
  },

  /** Navigate to a room */
  showRoom(roomName: string) {
    _activeView = 'room';
    _activeRoom = roomName;
  },

  /** Navigate to map view */
  showMap() {
    _activeView = 'map';
  },

  /** Push undo snapshot and schedule save */
  mutate(fn: (game: GameData) => void) {
    if (!_project) return;

    // Push current state to undo stack
    _undoStack.push(JSON.stringify(_project.game));
    _redoStack = [];

    // Apply mutation
    fn(_project.game);

    // Schedule debounced save
    this._scheduleSave();
  },

  undo() {
    if (!_project || _undoStack.length === 0) return;
    _redoStack.push(JSON.stringify(_project.game));
    const prev = _undoStack.pop()!;
    _project.game = JSON.parse(prev);
    this._scheduleSave();
  },

  redo() {
    if (!_project || _redoStack.length === 0) return;
    _undoStack.push(JSON.stringify(_project.game));
    const next = _redoStack.pop()!;
    _project.game = JSON.parse(next);
    this._scheduleSave();
  },

  /** Flush any pending save immediately */
  flushSave() {
    if (_saveTimer) {
      clearTimeout(_saveTimer);
      _saveTimer = null;
    }
    if (_project) {
      saveProject(_project);
      saveUndoStack(_project.id, _undoStack);
    }
  },

  _scheduleSave() {
    if (_saveTimer) clearTimeout(_saveTimer);
    _saveTimer = setTimeout(() => {
      this.flushSave();
      _saveTimer = null;
    }, 500);
  },
};
```

- [ ] **Step 5: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/store.svelte.ts editor/src/lib/persistence.ts editor/tests/persistence.test.ts
git commit -m "feat(editor): add reactive store and localStorage persistence"
```

---

### Task 5: App Shell (TopBar, Sidebar, MainPanel Layout)

**Files:**
- Create: `editor/src/components/TopBar.svelte`
- Create: `editor/src/components/Sidebar.svelte`
- Create: `editor/src/components/MainPanel.svelte`
- Create: `editor/src/components/ProjectList.svelte`
- Modify: `editor/src/App.svelte`

- [ ] **Step 1: Write ProjectList.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { loadProjectIndex, deleteProject } from '../lib/persistence';

  let projects = $derived(loadProjectIndex());
  let newName = $state('');

  function handleCreate() {
    const name = newName.trim() || 'Untitled Game';
    store.create(name);
    newName = '';
  }

  function handleOpen(id: string) {
    store.open(id);
  }

  function handleDelete(id: string) {
    if (confirm('Delete this project? This cannot be undone.')) {
      deleteProject(id);
    }
  }
</script>

<div class="project-list">
  <h1>Addventure Editor</h1>
  <p class="subtitle">Create and edit paper-based text adventures</p>

  <div class="new-project">
    <input
      type="text"
      bind:value={newName}
      placeholder="Game title..."
      onkeydown={(e) => e.key === 'Enter' && handleCreate()}
    />
    <button class="primary" onclick={handleCreate}>New Game</button>
  </div>

  {#if projects.length > 0}
    <div class="projects">
      <h3>Your Games</h3>
      {#each projects as entry}
        <div class="project-entry">
          <div class="project-info" onclick={() => handleOpen(entry.id)}>
            <span class="project-name">{entry.name}</span>
            <span class="project-date">
              {new Date(entry.lastModified).toLocaleDateString()}
            </span>
          </div>
          <button class="danger" onclick={() => handleDelete(entry.id)}>Delete</button>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .project-list {
    max-width: 600px;
    margin: 0 auto;
    padding: 4rem 2rem;
    text-align: center;
  }
  h1 { color: var(--gold); margin-bottom: 0.5rem; }
  .subtitle { color: var(--text-mid); margin-bottom: 3rem; }
  .new-project {
    display: flex;
    gap: 8px;
    margin-bottom: 2rem;
  }
  .new-project input { flex: 1; }
  .primary {
    background: var(--gold);
    color: var(--black);
    font-weight: 700;
  }
  .primary:hover { background: var(--gold-bright); }
  .projects { text-align: left; }
  .projects h3 {
    color: var(--text-mid);
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
  }
  .project-entry {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    background: var(--mid-dark);
    border-radius: 6px;
    margin-bottom: 6px;
    cursor: pointer;
  }
  .project-entry:hover { background: var(--warm-gray); }
  .project-info { flex: 1; }
  .project-name { font-weight: 600; }
  .project-date { margin-left: 12px; color: var(--text-dim); font-size: 0.85rem; }
  .danger {
    background: var(--red-ink);
    color: var(--parchment-light);
    font-size: 0.8rem;
    padding: 4px 10px;
  }
</style>
```

- [ ] **Step 2: Write TopBar.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';

  let editing = $state(false);
  let nameInput = $state('');

  function startEdit() {
    nameInput = store.project?.name ?? '';
    editing = true;
  }

  function finishEdit() {
    if (store.project && nameInput.trim()) {
      store.mutate(() => {
        store.project!.name = nameInput.trim();
      });
    }
    editing = false;
  }
</script>

<header class="topbar">
  <div class="left">
    <button class="logo" onclick={() => store.close()}>▲ Addventure</button>
    {#if store.project}
      {#if editing}
        <input
          class="name-input"
          bind:value={nameInput}
          onblur={finishEdit}
          onkeydown={(e) => e.key === 'Enter' && finishEdit()}
        />
      {:else}
        <span class="project-name" ondblclick={startEdit}>{store.project.name}</span>
      {/if}
    {/if}
  </div>
  {#if store.project}
    <div class="right">
      <button onclick={() => store.undo()} disabled={!store.canUndo}>Undo</button>
      <button onclick={() => store.redo()} disabled={!store.canRedo}>Redo</button>
      <button class="export">↓ Export .zip</button>
      <button>Import</button>
    </div>
  {/if}
</header>

<style>
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background: var(--dark);
    border-bottom: 1px solid var(--warm-gray);
    height: 48px;
    flex-shrink: 0;
  }
  .left { display: flex; align-items: center; gap: 16px; }
  .right { display: flex; gap: 8px; }
  .logo {
    font-family: var(--font-title);
    font-weight: 800;
    color: var(--gold);
    background: none;
    font-size: 0.9rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 4px 0;
  }
  .logo:hover { color: var(--gold-bright); }
  .project-name {
    color: var(--text-mid);
    cursor: pointer;
  }
  .name-input {
    width: 200px;
    font-size: 0.9rem;
  }
  .export {
    background: var(--gold-dim);
    color: var(--parchment-light);
  }
  .export:hover { background: var(--gold); color: var(--black); }
  button:disabled { opacity: 0.3; cursor: default; }
</style>
```

- [ ] **Step 3: Write Sidebar.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';

  let game = $derived(store.game);
  let rooms = $derived(game ? Object.values(game.rooms).filter(r => r.state === null) : []);
  let verbs = $derived(game ? Object.values(game.verbs) : []);
  let inventoryItems = $derived(game ? Object.values(game.inventory) : []);
  let signals = $derived(game ? getSignalEmissions(game) : []);
  let cues = $derived(game ? game.cues : []);
</script>

<aside class="sidebar">
  <!-- Game Summary -->
  <div
    class="sidebar-item summary"
    class:active={store.activeView === 'summary'}
    onclick={() => store.showSummary()}
  >
    {game?.metadata.title || store.project?.name || 'Game Summary'}
  </div>

  <!-- Rooms -->
  <div class="section-header">Rooms</div>
  {#each rooms as room}
    <div
      class="sidebar-item"
      class:active={store.activeView === 'room' && store.activeRoom === room.name}
      onclick={() => store.showRoom(room.name)}
    >
      <span class="mono">{room.name}</span>
      {#if game?.metadata.start === room.name}
        <span class="badge start">start</span>
      {/if}
    </div>
  {/each}
  <button class="add-btn" onclick={() => { /* TODO: add room */ }}>+ Add room</button>

  <!-- Verbs -->
  <div class="section-header verbs">Verbs</div>
  {#each verbs as verb}
    <div class="sidebar-item small">
      <span class="mono">{verb.name}</span>
      {#if verb.name.includes('__')}
        <span class="badge state">state</span>
      {/if}
    </div>
  {/each}
  <button class="add-btn" onclick={() => { /* TODO: add verb */ }}>+ Add verb</button>

  <!-- Inventory -->
  <div class="section-header inventory">Inventory</div>
  {#each inventoryItems as item}
    <div class="sidebar-item small">
      <span class="mono">{item.name}</span>
    </div>
  {/each}
  <button class="add-btn" onclick={() => { /* TODO: add item */ }}>+ Add item</button>

  <!-- Signals & Cues -->
  <div class="section-header signals">Signals & Cues</div>
  {#each signals as signal}
    <div class="sidebar-item small">
      <span class="signal-icon">⚡</span>
      <span class="mono">{signal}</span>
    </div>
  {/each}
  {#each cues as cue}
    <div class="sidebar-item small">
      <span class="cue-icon">⟐</span>
      <span>Cue → {cue.targetRoom}</span>
    </div>
  {/each}

  <!-- Footer -->
  <div class="sidebar-footer">
    <button
      class:active={store.activeView === 'map'}
      onclick={() => store.activeView === 'map' ? store.showSummary() : store.showMap()}
    >
      🗺 Map View
    </button>
  </div>
</aside>

<style>
  .sidebar {
    width: 220px;
    background: var(--dark-warm);
    border-right: 1px solid var(--warm-gray);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    flex-shrink: 0;
  }
  .section-header {
    padding: 10px 12px 4px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--gold);
    font-weight: 600;
    font-family: var(--font-title);
    border-top: 1px solid var(--warm-gray);
    margin-top: 4px;
  }
  .section-header.verbs { color: var(--parchment); }
  .section-header.inventory { color: var(--amber); }
  .section-header.signals { color: var(--parchment-dark); }

  .sidebar-item {
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .sidebar-item:hover { background: var(--mid-dark); }
  .sidebar-item.active {
    background: rgba(201, 168, 76, 0.1);
    border-left: 3px solid var(--gold);
  }
  .sidebar-item.summary {
    padding: 10px 12px;
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--parchment-light);
  }
  .sidebar-item.small { font-size: 0.8rem; padding: 3px 12px; }

  .badge {
    font-size: 0.65rem;
    padding: 1px 5px;
    border-radius: 3px;
  }
  .badge.start { background: var(--gold-dim); color: var(--parchment-light); }
  .badge.state { background: var(--amber); color: var(--black); }

  .signal-icon { color: var(--amber); }
  .cue-icon { color: var(--parchment-dark); }

  .add-btn {
    display: block;
    width: 100%;
    text-align: left;
    padding: 3px 12px;
    font-size: 0.8rem;
    color: var(--gold-dim);
    background: none;
    border-radius: 0;
  }
  .add-btn:hover { color: var(--gold); background: var(--mid-dark); }

  .sidebar-footer {
    margin-top: auto;
    padding: 8px 12px;
    border-top: 1px solid var(--warm-gray);
  }
  .sidebar-footer button {
    font-size: 0.8rem;
    width: 100%;
    text-align: left;
  }
  .sidebar-footer button.active {
    background: var(--gold-dim);
    color: var(--parchment-light);
  }
</style>
```

- [ ] **Step 4: Write MainPanel.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import GameSummary from './GameSummary.svelte';
  import RoomView from './RoomView.svelte';
</script>

<main class="main-panel">
  {#if store.activeView === 'summary'}
    <GameSummary />
  {:else if store.activeView === 'room' && store.activeRoom}
    <RoomView roomName={store.activeRoom} />
  {:else if store.activeView === 'map'}
    <div class="placeholder">Map view — coming soon</div>
  {:else}
    <div class="placeholder">Select a room or view from the sidebar</div>
  {/if}
</main>

<style>
  .main-panel {
    flex: 1;
    overflow-y: auto;
    background: var(--dark);
  }
  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-dim);
    font-style: italic;
  }
</style>
```

- [ ] **Step 5: Write stub GameSummary.svelte and RoomView.svelte**

`editor/src/components/GameSummary.svelte`:

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
</script>

<div class="game-summary">
  <h2>Game Summary</h2>
  <p class="hint">Metadata, description, and index-level signal checks will go here.</p>
</div>

<style>
  .game-summary { padding: 24px; }
  h2 { color: var(--gold); margin-bottom: 8px; font-size: 1.2rem; }
  .hint { color: var(--text-dim); }
</style>
```

`editor/src/components/RoomView.svelte`:

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';

  let { roomName }: { roomName: string } = $props();
</script>

<div class="room-view">
  <h2>{roomName}</h2>
  <p class="hint">Room editing will go here.</p>
</div>

<style>
  .room-view { padding: 24px; }
  h2 { color: var(--gold); margin-bottom: 8px; font-size: 1.2rem; }
  .hint { color: var(--text-dim); }
</style>
```

- [ ] **Step 6: Update App.svelte to wire everything together**

```svelte
<script lang="ts">
  import './styles/theme.css';
  import { store } from './lib/store.svelte';
  import ProjectList from './components/ProjectList.svelte';
  import TopBar from './components/TopBar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import MainPanel from './components/MainPanel.svelte';
</script>

{#if store.project}
  <div class="editor">
    <TopBar />
    <div class="workspace">
      <Sidebar />
      <MainPanel />
    </div>
  </div>
{:else}
  <ProjectList />
{/if}

<style>
  .editor {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  .workspace {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
</style>
```

- [ ] **Step 7: Verify in browser**

```bash
cd /home/chris/dev/addventure/editor
npm run dev
```

Open in browser. Verify:
- Landing page shows with "New Game" input
- Creating a game opens the editor with TopBar, Sidebar, and MainPanel
- Clicking "▲ Addventure" in the top bar returns to the project list
- The warm dark color scheme is applied

- [ ] **Step 8: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/
git commit -m "feat(editor): add app shell with project list, sidebar, and main panel"
```

---

### Task 6: Game Summary View

**Files:**
- Modify: `editor/src/components/GameSummary.svelte`

- [ ] **Step 1: Implement GameSummary.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';

  let game = $derived(store.game);
  let rooms = $derived(game ? Object.values(game.rooms).filter(r => r.state === null) : []);

  function updateMeta(key: string, value: string) {
    store.mutate((g) => {
      g.metadata[key] = value;
    });
  }
</script>

<div class="game-summary">
  <h2>Game Settings</h2>

  <div class="form-grid">
    <label>
      <span class="label">Title</span>
      <input
        type="text"
        value={game?.metadata.title ?? ''}
        oninput={(e) => updateMeta('title', e.currentTarget.value)}
        placeholder="Game title..."
      />
    </label>

    <label>
      <span class="label">Author</span>
      <input
        type="text"
        value={game?.metadata.author ?? ''}
        oninput={(e) => updateMeta('author', e.currentTarget.value)}
        placeholder="Author name..."
      />
    </label>

    <label>
      <span class="label">Start Room</span>
      <select
        value={game?.metadata.start ?? ''}
        onchange={(e) => updateMeta('start', e.currentTarget.value)}
      >
        <option value="">Select...</option>
        {#each rooms as room}
          <option value={room.name}>{room.name}</option>
        {/each}
      </select>
    </label>

    <label>
      <span class="label">Ledger Prefix</span>
      <input
        type="text"
        value={game?.metadata.ledger_prefix ?? ''}
        oninput={(e) => updateMeta('ledger_prefix', e.currentTarget.value)}
        placeholder="A"
        maxlength="1"
        style="width: 60px;"
      />
    </label>

    <label>
      <span class="label">Name Style</span>
      <select
        value={game?.metadata.name_style ?? 'upper_words'}
        onchange={(e) => updateMeta('name_style', e.currentTarget.value)}
      >
        <option value="upper_words">UPPER WORDS</option>
        <option value="title">Title Case</option>
      </select>
    </label>
  </div>

  <div class="description-section">
    <span class="label">Description</span>
    <textarea
      rows="6"
      value={game?.metadata.description ?? ''}
      oninput={(e) => updateMeta('description', e.currentTarget.value)}
      placeholder="Opening narrative shown to the player..."
    ></textarea>
  </div>

  {#if game && game.signalChecks.length > 0}
    <div class="signal-checks-section">
      <span class="label">Signal Checks (Chapter Start)</span>
      <p class="hint">Conditional branches evaluated when the chapter begins.</p>
      <!-- Signal check editing will be implemented in Task 12 -->
    </div>
  {/if}
</div>

<style>
  .game-summary { padding: 24px; max-width: 700px; }
  h2 { color: var(--gold); margin-bottom: 1.5rem; font-size: 1.2rem; }
  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 1.5rem;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-mid);
    font-family: var(--font-title);
    font-weight: 800;
  }
  .description-section { margin-bottom: 1.5rem; }
  .description-section textarea {
    width: 100%;
    resize: vertical;
    margin-top: 4px;
    font-family: var(--font-body);
  }
  .signal-checks-section { margin-top: 1.5rem; }
  .hint { color: var(--text-dim); font-size: 0.85rem; }
</style>
```

- [ ] **Step 2: Verify in browser**

Create a new game, verify the Game Summary view shows metadata fields. Fill in some values, navigate away and back — verify they persist.

- [ ] **Step 3: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/GameSummary.svelte
git commit -m "feat(editor): implement game summary view with metadata form"
```

---

### Task 7: Sidebar Add Actions (Rooms, Verbs, Inventory)

**Files:**
- Modify: `editor/src/components/Sidebar.svelte`
- Modify: `editor/src/lib/store.svelte.ts`

- [ ] **Step 1: Add mutation methods to store**

Add to `editor/src/lib/store.svelte.ts` before the closing `};`:

```typescript
  addRoom(name: string) {
    this.mutate((game) => {
      const room = createRoom(name);
      game.rooms[name] = room;
    });
  },

  addVerb(name: string) {
    this.mutate((game) => {
      game.verbs[name] = createVerb(name);
    });
  },

  addInventoryItem(name: string) {
    this.mutate((game) => {
      game.inventory[name] = createInventoryObject(name);
    });
  },

  addObject(roomName: string, objectName: string, discovered = false) {
    this.mutate((game) => {
      const key = objectKey(roomName, objectName);
      game.objects[key] = createRoomObject(objectName, roomName, discovered);
    });
  },
```

Add the missing imports at the top of `store.svelte.ts`:

```typescript
import { createGameProject, createGameData, createRoom, createVerb, createInventoryObject, createRoomObject, objectKey } from './factory';
```

- [ ] **Step 2: Add inline add forms to Sidebar.svelte**

Replace the `+ Add room`, `+ Add verb`, and `+ Add item` buttons in `Sidebar.svelte` with inline add forms. For each section, add a state variable and a toggle:

```svelte
<script lang="ts">
  // ... existing imports ...
  let addingRoom = $state(false);
  let newRoomName = $state('');
  let addingVerb = $state(false);
  let newVerbName = $state('');
  let addingItem = $state(false);
  let newItemName = $state('');

  function submitRoom() {
    const name = newRoomName.trim();
    if (name && game && !game.rooms[name]) {
      store.addRoom(name);
      store.showRoom(name);
      newRoomName = '';
      addingRoom = false;
    }
  }

  function submitVerb() {
    const name = newVerbName.trim().toUpperCase().replace(/\s+/g, '_');
    if (name && game && !game.verbs[name]) {
      store.addVerb(name);
      newVerbName = '';
      addingVerb = false;
    }
  }

  function submitItem() {
    const name = newItemName.trim().toUpperCase().replace(/\s+/g, '_');
    if (name && game && !game.inventory[name]) {
      store.addInventoryItem(name);
      newItemName = '';
      addingItem = false;
    }
  }
</script>
```

Replace the `+ Add room` button with:

```svelte
  {#if addingRoom}
    <div class="inline-add">
      <input
        type="text"
        bind:value={newRoomName}
        placeholder="Room name..."
        onkeydown={(e) => {
          if (e.key === 'Enter') submitRoom();
          if (e.key === 'Escape') addingRoom = false;
        }}
      />
    </div>
  {:else}
    <button class="add-btn" onclick={() => addingRoom = true}>+ Add room</button>
  {/if}
```

Apply the same pattern for verbs and inventory. Add styles:

```css
  .inline-add {
    padding: 3px 12px;
  }
  .inline-add input {
    width: 100%;
    font-size: 0.8rem;
    padding: 3px 6px;
  }
```

- [ ] **Step 3: Verify in browser**

- Click "+ Add room" → inline input appears → type "Control Room" → Enter → room appears in sidebar, navigates to it
- Click "+ Add verb" → type "LOOK" → Enter → verb appears in verbs list
- Click "+ Add item" → type "KEYCARD" → Enter → item appears in inventory

- [ ] **Step 4: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/Sidebar.svelte editor/src/lib/store.svelte.ts
git commit -m "feat(editor): add inline create for rooms, verbs, and inventory items"
```

---

### Task 8: Room View with Object Cards

**Files:**
- Modify: `editor/src/components/RoomView.svelte`
- Create: `editor/src/components/ObjectCard.svelte`
- Create: `editor/src/components/InteractionCard.svelte`
- Create: `editor/src/components/ArrowBadge.svelte`

- [ ] **Step 1: Write ArrowBadge.svelte**

```svelte
<script lang="ts">
  import type { Arrow } from '../lib/types';
  import { classifyArrow, arrowLabel } from '../lib/helpers';

  let { arrow }: { arrow: Arrow } = $props();
  let type = $derived(classifyArrow(arrow));
  let label = $derived(arrowLabel(arrow));
</script>

<span class="arrow-badge {type}">{label}</span>

<style>
  .arrow-badge {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: var(--font-mono);
    white-space: nowrap;
  }
  .destroy { background: rgba(139, 58, 58, 0.2); color: var(--red-ink); }
  .pickup { background: rgba(212, 136, 58, 0.2); color: var(--amber); }
  .move { background: rgba(201, 168, 76, 0.2); color: var(--gold); }
  .transform { background: rgba(212, 197, 169, 0.15); color: var(--parchment); }
  .reveal { background: rgba(74, 122, 74, 0.2); color: var(--green-ink); }
  .cue { background: rgba(184, 168, 138, 0.15); color: var(--parchment-dark); }
  .signal { background: rgba(212, 136, 58, 0.2); color: var(--amber); }
  .reveal_verb { background: rgba(201, 168, 76, 0.2); color: var(--gold); }
  .discover_action { background: rgba(74, 122, 74, 0.2); color: var(--green-ink); }
  .room_state { background: rgba(212, 197, 169, 0.15); color: var(--parchment); }
  .verb_restore { background: rgba(201, 168, 76, 0.2); color: var(--gold); }
</style>
```

- [ ] **Step 2: Write InteractionCard.svelte**

```svelte
<script lang="ts">
  import type { Interaction } from '../lib/types';
  import ArrowBadge from './ArrowBadge.svelte';

  let { interaction, onclick }: { interaction: Interaction; onclick?: () => void } = $props();

  let targetLabel = $derived(() => {
    return interaction.targetGroups
      .map(g => g.join(' | '))
      .join(' + ');
  });
</script>

<div class="interaction-card" onclick={onclick} role="button" tabindex="0">
  <div class="header">
    <span class="verb mono">{interaction.verb}</span>
    {#if targetLabel()}
      <span class="targets mono">{targetLabel()}</span>
    {/if}
  </div>
  {#if interaction.narrative}
    <div class="narrative">{interaction.narrative.slice(0, 120)}{interaction.narrative.length > 120 ? '...' : ''}</div>
  {/if}
  {#if interaction.arrows.length > 0}
    <div class="arrows">
      {#each interaction.arrows as arrow}
        <ArrowBadge {arrow} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .interaction-card {
    padding: 8px 10px;
    background: var(--dark);
    border-radius: 6px;
    margin-bottom: 6px;
    border-left: 3px solid var(--parchment-dark);
    cursor: pointer;
  }
  .interaction-card:hover {
    border-left-color: var(--gold);
  }
  .header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 2px;
  }
  .verb {
    color: var(--gold);
    font-weight: 600;
    font-size: 0.85rem;
  }
  .targets {
    color: var(--text-mid);
    font-size: 0.8rem;
  }
  .targets::before { content: '+ '; color: var(--text-dim); }
  .narrative {
    color: var(--text-dim);
    font-size: 0.8rem;
    margin-bottom: 4px;
  }
  .arrows {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }
</style>
```

- [ ] **Step 3: Write ObjectCard.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getObjectInteractions } from '../lib/helpers';
  import type { Interaction } from '../lib/types';
  import InteractionCard from './InteractionCard.svelte';

  let { objectName, roomName }: { objectName: string; roomName: string } = $props();

  let expanded = $state(false);
  let game = $derived(store.game);

  // Find all states for this base object in this room
  let baseObj = $derived(() => {
    if (!game) return null;
    const key = `${roomName}::${objectName}`;
    return game.objects[key] ?? null;
  });

  let states = $derived(() => {
    if (!game) return [];
    const names: string[] = [];
    for (const obj of Object.values(game.objects)) {
      if (obj.room === roomName && obj.base === objectName) {
        names.push(obj.name);
      }
    }
    return names.sort((a, b) => {
      if (a === objectName) return -1;
      if (b === objectName) return 1;
      return a.localeCompare(b);
    });
  });

  let activeState = $state(objectName);

  let interactions = $derived(() => {
    if (!game) return [];
    return getObjectInteractions(game, roomName, activeState);
  });

  let stateCount = $derived(states().filter(s => s !== objectName).length);
  let interactionCount = $derived(() => {
    if (!game) return 0;
    let count = 0;
    for (const s of states()) {
      count += getObjectInteractions(game, roomName, s).length;
    }
    return count;
  });
</script>

<div class="object-card" class:expanded>
  <div
    class="object-header"
    onclick={() => expanded = !expanded}
    role="button"
    tabindex="0"
  >
    <div class="left">
      <span class="toggle">{expanded ? '▾' : '▸'}</span>
      <strong class="mono">{objectName}</strong>
      {#if stateCount > 0}
        <span class="badge state">{stateCount} state{stateCount !== 1 ? 's' : ''}</span>
      {/if}
      {#if baseObj()?.discovered}
        <span class="badge discovered">hidden</span>
      {/if}
    </div>
    <span class="count">{interactionCount()} interaction{interactionCount() !== 1 ? 's' : ''}</span>
  </div>

  {#if expanded}
    <!-- State tabs -->
    {#if states().length > 1}
      <div class="state-tabs">
        {#each states() as stateName}
          <button
            class="state-tab"
            class:active={activeState === stateName}
            onclick={() => activeState = stateName}
          >
            {stateName === objectName ? 'base' : stateName.split('__').slice(1).join('__')}
          </button>
        {/each}
        <button class="state-tab add" onclick={() => { /* TODO: add state */ }}>+</button>
      </div>
    {/if}

    <!-- Interactions for active state -->
    <div class="interactions">
      {#each interactions() as interaction}
        <InteractionCard {interaction} />
      {/each}
      <button class="add-interaction" onclick={() => { /* TODO: add interaction */ }}>
        + Add interaction
      </button>
    </div>
  {/if}
</div>

<style>
  .object-card {
    background: var(--mid-dark);
    border-radius: 8px;
    border: 1px solid var(--warm-gray);
    margin-bottom: 10px;
    overflow: hidden;
  }
  .object-card.expanded {
    border-color: rgba(201, 168, 76, 0.3);
  }
  .object-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    cursor: pointer;
  }
  .object-card.expanded .object-header {
    background: rgba(201, 168, 76, 0.05);
  }
  .left {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .toggle { color: var(--gold); font-size: 0.8rem; }
  .count { font-size: 0.75rem; color: var(--text-dim); }
  .badge {
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 3px;
  }
  .badge.state { background: rgba(201, 168, 76, 0.15); color: var(--gold); }
  .badge.discovered { background: rgba(212, 136, 58, 0.15); color: var(--amber); }

  .state-tabs {
    display: flex;
    padding: 0 14px;
    border-bottom: 1px solid var(--warm-gray);
    font-size: 0.8rem;
  }
  .state-tab {
    padding: 6px 12px;
    background: none;
    color: var(--text-mid);
    border-radius: 0;
    border-bottom: 2px solid transparent;
  }
  .state-tab.active {
    color: var(--parchment-light);
    border-bottom-color: var(--gold);
  }
  .state-tab.add {
    color: var(--gold-dim);
    font-size: 0.9rem;
  }

  .interactions { padding: 10px 14px; }
  .add-interaction {
    width: 100%;
    text-align: left;
    padding: 6px 0;
    color: var(--gold-dim);
    background: none;
    font-size: 0.8rem;
  }
  .add-interaction:hover { color: var(--gold); }
</style>
```

- [ ] **Step 4: Implement RoomView.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getRoomObjects, getRoomInteractions } from '../lib/helpers';
  import ObjectCard from './ObjectCard.svelte';
  import InteractionCard from './InteractionCard.svelte';

  let { roomName }: { roomName: string } = $props();

  let game = $derived(store.game);
  let room = $derived(game?.rooms[roomName] ?? null);

  // Get unique base object names in this room
  let objectNames = $derived(() => {
    if (!game) return [];
    const grouped = getRoomObjects(game, roomName);
    return Object.keys(grouped).sort();
  });

  // Room LOOK description: interaction with verb LOOK and target @ROOM or empty targets
  let roomDescription = $derived(() => {
    if (!game) return '';
    const lookInteraction = game.interactions.find(
      i => i.room === roomName && i.verb === 'LOOK' && (
        i.targetGroups.length === 0 ||
        (i.targetGroups.length === 1 && i.targetGroups[0].includes(`@${roomName}`))
      )
    );
    return lookInteraction?.narrative ?? '';
  });

  // Freeform interactions: those in ## Interactions section (not tied to a specific object's entity block)
  // For now, show interactions with wildcard or multi-group targets
  let freeformInteractions = $derived(() => {
    if (!game) return [];
    return getRoomInteractions(game, roomName).filter(i =>
      i.targetGroups.length > 0 &&
      (i.targetGroups[0].includes('*') || i.targetGroups.length > 1)
    );
  });

  let isStart = $derived(game?.metadata.start === roomName);

  function updateDescription(value: string) {
    store.mutate((g) => {
      // Find or create the room LOOK interaction
      let existing = g.interactions.find(
        i => i.room === roomName && i.verb === 'LOOK' && (
          i.targetGroups.length === 0 ||
          (i.targetGroups.length === 1 && i.targetGroups[0].includes(`@${roomName}`))
        )
      );
      if (existing) {
        existing.narrative = value;
      } else {
        g.interactions.push({
          verb: 'LOOK',
          targetGroups: [],
          narrative: value,
          arrows: [],
          room: roomName,
          sealedContent: null,
          sealedArrows: [],
          signalChecks: [],
        });
      }
    });
  }
</script>

<div class="room-view">
  <!-- Room Header -->
  <div class="room-header">
    <div class="title-row">
      <h2>{roomName}</h2>
      {#if isStart}
        <span class="badge start">start room</span>
      {/if}
    </div>
    <div class="view-toggle">
      <button class="active">Visual</button>
      <button disabled>Source</button>
    </div>
  </div>

  <!-- Room Description -->
  <div class="room-description">
    <span class="label">Room Description (LOOK)</span>
    <textarea
      rows="3"
      value={roomDescription()}
      oninput={(e) => updateDescription(e.currentTarget.value)}
      placeholder="What the player sees when they look around..."
    ></textarea>
  </div>

  <!-- Objects -->
  <div class="objects-section">
    <span class="label">Objects in this Room</span>
    {#each objectNames() as name}
      <ObjectCard objectName={name} {roomName} />
    {/each}
    <button class="add-btn" onclick={() => { /* TODO: add object */ }}>+ Add object</button>
  </div>

  <!-- Freeform Interactions -->
  {#if freeformInteractions().length > 0}
    <div class="freeform-section">
      <span class="label">Freeform Interactions</span>
      {#each freeformInteractions() as interaction}
        <InteractionCard {interaction} />
      {/each}
    </div>
  {/if}
  <button class="add-btn" onclick={() => { /* TODO: add freeform interaction */ }}>+ Add freeform interaction</button>
</div>

<style>
  .room-view { padding: 0; }
  .room-header {
    padding: 12px 24px;
    border-bottom: 1px solid var(--warm-gray);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .title-row { display: flex; align-items: center; gap: 12px; }
  h2 { color: var(--parchment-light); font-size: 1.2rem; }
  .badge.start {
    font-size: 0.65rem;
    padding: 2px 8px;
    background: var(--gold-dim);
    color: var(--parchment-light);
    border-radius: 4px;
  }
  .view-toggle { display: flex; gap: 4px; }
  .view-toggle button {
    font-size: 0.8rem;
    padding: 4px 12px;
  }
  .view-toggle button.active {
    background: rgba(201, 168, 76, 0.15);
    border: 1px solid rgba(201, 168, 76, 0.3);
    color: var(--gold);
  }

  .room-description {
    padding: 12px 24px;
    border-bottom: 1px solid var(--warm-gray);
  }
  .room-description textarea {
    width: 100%;
    resize: vertical;
    margin-top: 4px;
  }

  .label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-mid);
    font-family: var(--font-title);
    font-weight: 800;
    display: block;
    margin-bottom: 6px;
  }

  .objects-section, .freeform-section {
    padding: 12px 24px;
  }

  .add-btn {
    display: block;
    padding: 6px 24px;
    color: var(--gold-dim);
    background: none;
    font-size: 0.85rem;
    text-align: left;
    width: 100%;
  }
  .add-btn:hover { color: var(--gold); background: var(--mid-dark); }
</style>
```

- [ ] **Step 5: Verify in browser**

Create a game, add a room "Control Room", add verb "LOOK", set start room to "Control Room" in Game Summary. Navigate to the room. Verify:
- Room header shows name + "start room" badge
- Room description textarea works
- Visual/Source toggle is visible (Source disabled for now)
- Empty objects section with "+ Add object"

- [ ] **Step 6: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/
git commit -m "feat(editor): add room view with object cards and interaction display"
```

---

### Task 9: Interaction Editor

**Files:**
- Create: `editor/src/components/InteractionEditor.svelte`
- Create: `editor/src/components/VerbPicker.svelte`
- Create: `editor/src/components/TargetBuilder.svelte`
- Create: `editor/src/components/ArrowEditor.svelte`

- [ ] **Step 1: Write VerbPicker.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';

  let { value, onchange }: { value: string; onchange: (v: string) => void } = $props();

  let game = $derived(store.game);
  let verbs = $derived(game ? Object.keys(game.verbs) : []);
  let filter = $state('');
  let open = $state(false);

  let filtered = $derived(
    filter ? verbs.filter(v => v.includes(filter.toUpperCase())) : verbs
  );

  function select(verb: string) {
    onchange(verb);
    open = false;
    filter = '';
  }

  function handleInput(e: Event) {
    filter = (e.currentTarget as HTMLInputElement).value;
    open = true;
  }
</script>

<div class="verb-picker">
  <input
    type="text"
    class="mono"
    value={open ? filter : value}
    placeholder="Select verb..."
    oninput={handleInput}
    onfocus={() => open = true}
    onblur={() => setTimeout(() => open = false, 150)}
  />
  {#if open}
    <div class="dropdown">
      {#each filtered as verb}
        <button class="mono" onclick={() => select(verb)}>
          {verb}
          {#if verb.includes('__')}
            <span class="state-badge">state</span>
          {/if}
        </button>
      {/each}
      {#if filter && !verbs.includes(filter.toUpperCase())}
        <button class="create" onclick={() => {
          const name = filter.toUpperCase().replace(/\s+/g, '_');
          store.addVerb(name);
          select(name);
        }}>
          + Create "{filter.toUpperCase()}"
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .verb-picker { position: relative; }
  .verb-picker input { width: 100%; }
  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;
  }
  .dropdown button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    text-align: left;
    padding: 6px 10px;
    font-size: 0.85rem;
    background: none;
    border-radius: 0;
  }
  .dropdown button:hover { background: var(--mid-dark); }
  .state-badge {
    font-size: 0.6rem;
    background: var(--amber);
    color: var(--black);
    padding: 1px 4px;
    border-radius: 2px;
  }
  .create { color: var(--gold); }
</style>
```

- [ ] **Step 2: Write TargetBuilder.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';

  let { targetGroups, onchange, roomName }:
    { targetGroups: string[][]; onchange: (groups: string[][]) => void; roomName: string } = $props();

  let game = $derived(store.game);

  // Available targets: room objects + inventory items + special
  let suggestions = $derived(() => {
    if (!game) return [];
    const items: string[] = [];
    for (const obj of Object.values(game.objects)) {
      if (obj.room === roomName) items.push(obj.name);
    }
    for (const inv of Object.keys(game.inventory)) {
      items.push(inv);
    }
    return [...new Set(items)].sort();
  });

  function updateGroup(groupIdx: number, value: string) {
    const newGroups = targetGroups.map((g, i) =>
      i === groupIdx ? value.split('|').map(s => s.trim()).filter(Boolean) : [...g]
    );
    onchange(newGroups);
  }

  function addGroup() {
    onchange([...targetGroups, []]);
  }

  function removeGroup(idx: number) {
    onchange(targetGroups.filter((_, i) => i !== idx));
  }
</script>

<div class="target-builder">
  {#each targetGroups as group, i}
    <div class="target-group">
      {#if i > 0}
        <span class="plus">+</span>
      {/if}
      <input
        type="text"
        class="mono"
        value={group.join(' | ')}
        placeholder="TARGET or A | B"
        oninput={(e) => updateGroup(i, e.currentTarget.value)}
        list="targets-{i}"
      />
      <datalist id="targets-{i}">
        {#each suggestions() as s}
          <option value={s} />
        {/each}
        <option value="*" />
      </datalist>
      {#if targetGroups.length > 1}
        <button class="remove" onclick={() => removeGroup(i)}>×</button>
      {/if}
    </div>
  {/each}
  <button class="add-group" onclick={addGroup}>+ target group</button>
</div>

<style>
  .target-builder {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }
  .target-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .target-group input { width: 160px; font-size: 0.85rem; }
  .plus { color: var(--text-dim); font-size: 0.8rem; }
  .remove {
    background: none;
    color: var(--red-ink);
    padding: 2px 6px;
    font-size: 0.8rem;
  }
  .add-group {
    background: none;
    color: var(--gold-dim);
    font-size: 0.8rem;
    padding: 2px 6px;
  }
  .add-group:hover { color: var(--gold); }
</style>
```

- [ ] **Step 3: Write ArrowEditor.svelte**

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import type { Arrow } from '../lib/types';
  import { classifyArrow } from '../lib/helpers';

  let { arrow, onchange, ondelete, roomName }:
    { arrow: Arrow; onchange: (a: Arrow) => void; ondelete: () => void; roomName: string } = $props();

  let game = $derived(store.game);
  let type = $derived(classifyArrow(arrow));

  let rooms = $derived(game ? Object.values(game.rooms).filter(r => r.state === null).map(r => r.name) : []);
  let objects = $derived(() => {
    if (!game) return [];
    return Object.values(game.objects)
      .filter(o => o.room === roomName)
      .map(o => o.name);
  });

  const ARROW_TYPES = [
    { value: 'destroy', label: 'Destroy' },
    { value: 'pickup', label: 'Pick up' },
    { value: 'move', label: 'Move player' },
    { value: 'transform', label: 'Transform' },
    { value: 'reveal', label: 'Reveal in room' },
    { value: 'cue', label: 'Cue' },
    { value: 'signal', label: 'Signal' },
    { value: 'reveal_verb', label: 'Reveal verb' },
    { value: 'discover_action', label: 'Discover action' },
    { value: 'room_state', label: 'Change room state' },
  ];

  function setType(newType: string) {
    let subject = arrow.subject;
    let destination = arrow.destination;
    let signalName: string | null = null;

    switch (newType) {
      case 'destroy': destination = 'trash'; break;
      case 'pickup': destination = 'player'; break;
      case 'move': subject = 'player'; destination = `"${rooms[0] ?? ''}"`; break;
      case 'transform': destination = `${subject}__`; break;
      case 'reveal': destination = 'room'; break;
      case 'cue': subject = '?'; destination = `"${rooms[0] ?? ''}"`; break;
      case 'signal': destination = 'signal'; signalName = subject; break;
      case 'reveal_verb': subject = ''; break;
      case 'discover_action': subject = `>${subject}`; destination = 'room'; break;
      case 'room_state': subject = 'room'; destination = 'room__'; break;
    }

    onchange({ subject, destination, signalName });
  }
</script>

<div class="arrow-editor">
  <select value={type} onchange={(e) => setType(e.currentTarget.value)}>
    {#each ARROW_TYPES as t}
      <option value={t.value}>{t.label}</option>
    {/each}
  </select>

  {#if type === 'destroy' || type === 'pickup' || type === 'reveal'}
    <input
      class="mono"
      type="text"
      value={arrow.subject}
      placeholder="Object name"
      oninput={(e) => onchange({ ...arrow, subject: e.currentTarget.value })}
      list="arrow-objects"
    />
    <datalist id="arrow-objects">
      {#each objects() as o}<option value={o} />{/each}
    </datalist>
  {:else if type === 'move'}
    <select
      value={arrow.destination.replace(/"/g, '')}
      onchange={(e) => onchange({ ...arrow, subject: 'player', destination: `"${e.currentTarget.value}"` })}
    >
      {#each rooms as r}<option value={r}>{r}</option>{/each}
    </select>
  {:else if type === 'transform'}
    <input
      class="mono"
      type="text"
      value={arrow.subject}
      placeholder="Object"
      oninput={(e) => onchange({ ...arrow, subject: e.currentTarget.value })}
    />
    <span class="arrow-sym">→</span>
    <input
      class="mono"
      type="text"
      value={arrow.destination}
      placeholder="OBJECT__STATE"
      oninput={(e) => onchange({ ...arrow, destination: e.currentTarget.value })}
    />
  {:else if type === 'cue'}
    <select
      value={arrow.destination.replace(/"/g, '')}
      onchange={(e) => onchange({ ...arrow, subject: '?', destination: `"${e.currentTarget.value}"` })}
    >
      {#each rooms as r}<option value={r}>{r}</option>{/each}
    </select>
  {:else if type === 'signal'}
    <input
      class="mono"
      type="text"
      value={arrow.signalName ?? arrow.subject}
      placeholder="SIGNAL_NAME"
      oninput={(e) => {
        const name = e.currentTarget.value;
        onchange({ subject: name, destination: 'signal', signalName: name });
      }}
    />
  {:else if type === 'reveal_verb'}
    <input
      class="mono"
      type="text"
      value={arrow.destination}
      placeholder="VERB_NAME"
      oninput={(e) => onchange({ subject: '', destination: e.currentTarget.value, signalName: null })}
    />
  {:else if type === 'room_state'}
    <input
      class="mono"
      type="text"
      value={arrow.destination}
      placeholder="room__STATE"
      oninput={(e) => onchange({ subject: 'room', destination: e.currentTarget.value, signalName: null })}
    />
  {:else}
    <input class="mono" type="text" value={arrow.subject}
      oninput={(e) => onchange({ ...arrow, subject: e.currentTarget.value })} />
    <span class="arrow-sym">→</span>
    <input class="mono" type="text" value={arrow.destination}
      oninput={(e) => onchange({ ...arrow, destination: e.currentTarget.value })} />
  {/if}

  <button class="delete" onclick={ondelete}>×</button>
</div>

<style>
  .arrow-editor {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
    font-size: 0.85rem;
  }
  .arrow-editor select { font-size: 0.8rem; min-width: 120px; }
  .arrow-editor input { flex: 1; min-width: 100px; }
  .arrow-sym { color: var(--text-dim); }
  .delete {
    background: none;
    color: var(--red-ink);
    padding: 2px 6px;
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 4: Write InteractionEditor.svelte**

```svelte
<script lang="ts">
  import type { Interaction, Arrow } from '../lib/types';
  import { store } from '../lib/store.svelte';
  import { createArrow } from '../lib/factory';
  import VerbPicker from './VerbPicker.svelte';
  import TargetBuilder from './TargetBuilder.svelte';
  import ArrowEditor from './ArrowEditor.svelte';

  let { interaction, interactionIndex, onclose }:
    { interaction: Interaction; interactionIndex: number; onclose: () => void } = $props();

  function update(fn: (i: Interaction) => void) {
    store.mutate((game) => {
      fn(game.interactions[interactionIndex]);
    });
  }

  function addArrow() {
    update((i) => {
      i.arrows.push(createArrow('', ''));
    });
  }

  function updateArrow(idx: number, arrow: Arrow) {
    update((i) => { i.arrows[idx] = arrow; });
  }

  function deleteArrow(idx: number) {
    update((i) => { i.arrows.splice(idx, 1); });
  }

  function deleteInteraction() {
    store.mutate((game) => {
      game.interactions.splice(interactionIndex, 1);
    });
    onclose();
  }
</script>

<div class="interaction-editor">
  <div class="editor-header">
    <h4>Edit Interaction</h4>
    <div class="header-actions">
      <button class="danger" onclick={deleteInteraction}>Delete</button>
      <button onclick={onclose}>Done</button>
    </div>
  </div>

  <div class="field">
    <span class="label">Verb</span>
    <VerbPicker
      value={interaction.verb}
      onchange={(v) => update((i) => { i.verb = v; })}
    />
  </div>

  <div class="field">
    <span class="label">Targets</span>
    <TargetBuilder
      targetGroups={interaction.targetGroups}
      onchange={(g) => update((i) => { i.targetGroups = g; })}
      roomName={interaction.room}
    />
  </div>

  <div class="field">
    <span class="label">Narrative</span>
    <textarea
      rows="4"
      value={interaction.narrative}
      oninput={(e) => update((i) => { i.narrative = e.currentTarget.value; })}
      placeholder="What happens when the player does this..."
    ></textarea>
  </div>

  <div class="field">
    <span class="label">Arrows (Consequences)</span>
    {#each interaction.arrows as arrow, idx}
      <ArrowEditor
        {arrow}
        onchange={(a) => updateArrow(idx, a)}
        ondelete={() => deleteArrow(idx)}
        roomName={interaction.room}
      />
    {/each}
    <button class="add-arrow" onclick={addArrow}>+ Add arrow</button>
  </div>

  {#if interaction.sealedContent !== null}
    <div class="field">
      <span class="label">Sealed Content (Fragment)</span>
      <textarea
        rows="4"
        value={interaction.sealedContent ?? ''}
        oninput={(e) => update((i) => { i.sealedContent = e.currentTarget.value; })}
        placeholder="Hidden text revealed when this entry is read..."
      ></textarea>
    </div>
  {:else}
    <button class="toggle-sealed" onclick={() => update((i) => { i.sealedContent = ''; })}>
      + Add sealed content (fragment)
    </button>
  {/if}
</div>

<style>
  .interaction-editor {
    background: var(--dark-warm);
    border: 1px solid var(--gold-dim);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 10px;
  }
  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .editor-header h4 {
    font-size: 0.85rem;
    color: var(--gold);
  }
  .header-actions { display: flex; gap: 6px; }
  .header-actions button { font-size: 0.8rem; }
  .danger { background: var(--red-ink); color: var(--parchment-light); }

  .field { margin-bottom: 12px; }
  .label {
    display: block;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-mid);
    font-family: var(--font-title);
    font-weight: 800;
    margin-bottom: 4px;
  }
  textarea { width: 100%; resize: vertical; }

  .add-arrow, .toggle-sealed {
    background: none;
    color: var(--gold-dim);
    font-size: 0.8rem;
    padding: 4px 0;
  }
  .add-arrow:hover, .toggle-sealed:hover { color: var(--gold); }
</style>
```

- [ ] **Step 5: Wire interaction editing into ObjectCard and InteractionCard**

Modify `InteractionCard.svelte` to support toggling an edit mode. Add an `editing` prop and conditionally render `InteractionEditor` instead of the compact card:

In `ObjectCard.svelte`, add state tracking for which interaction is being edited, and pass the `interactionIndex` (the index within `game.interactions`) to `InteractionEditor`.

The key change: `ObjectCard` needs to track `editingIdx: number | null` and toggle between `InteractionCard` (display) and `InteractionEditor` (editing).

- [ ] **Step 6: Add "+ Add interaction" functionality**

In `ObjectCard.svelte`, wire the "+ Add interaction" button to create a new `Interaction` via `store.mutate`:

```typescript
function addInteraction() {
  store.mutate((game) => {
    game.interactions.push({
      verb: '',
      targetGroups: [[activeState]],
      narrative: '',
      arrows: [],
      room: roomName,
      sealedContent: null,
      sealedArrows: [],
      signalChecks: [],
    });
  });
  // Set editingIdx to the new interaction
}
```

- [ ] **Step 7: Verify in browser**

- Add a room, add an object, expand the object card
- Click "+ Add interaction" → editor appears with verb picker, target builder, narrative area, arrows
- Select a verb, add targets, write narrative, add arrows of different types
- Click "Done" → compact card shows with arrow badges
- Click the card → editor reopens

- [ ] **Step 8: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/
git commit -m "feat(editor): add interaction editor with verb picker, targets, and arrows"
```

---

### Task 10: Signal Check Editor

**Files:**
- Create: `editor/src/components/SignalCheckEditor.svelte`
- Modify: `editor/src/components/InteractionEditor.svelte`

- [ ] **Step 1: Write SignalCheckEditor.svelte**

```svelte
<script lang="ts">
  import type { SignalCheck, Arrow } from '../lib/types';
  import { createArrow } from '../lib/factory';
  import ArrowEditor from './ArrowEditor.svelte';

  let { checks, onchange, roomName }:
    { checks: SignalCheck[]; onchange: (checks: SignalCheck[]) => void; roomName: string } = $props();

  function addCheck() {
    onchange([...checks, { signalNames: [], narrative: '', arrows: [] }]);
  }

  function updateCheck(idx: number, field: string, value: any) {
    const updated = checks.map((c, i) => i === idx ? { ...c, [field]: value } : c);
    onchange(updated);
  }

  function removeCheck(idx: number) {
    onchange(checks.filter((_, i) => i !== idx));
  }

  function addArrowToCheck(idx: number) {
    const updated = [...checks];
    updated[idx] = { ...updated[idx], arrows: [...updated[idx].arrows, createArrow('', '')] };
    onchange(updated);
  }

  function updateCheckArrow(checkIdx: number, arrowIdx: number, arrow: Arrow) {
    const updated = [...checks];
    const arrows = [...updated[checkIdx].arrows];
    arrows[arrowIdx] = arrow;
    updated[checkIdx] = { ...updated[checkIdx], arrows };
    onchange(updated);
  }

  function deleteCheckArrow(checkIdx: number, arrowIdx: number) {
    const updated = [...checks];
    updated[checkIdx] = {
      ...updated[checkIdx],
      arrows: updated[checkIdx].arrows.filter((_, i) => i !== arrowIdx),
    };
    onchange(updated);
  }
</script>

<div class="signal-check-editor">
  {#each checks as check, idx}
    <div class="check-branch">
      <div class="branch-header">
        {#if check.signalNames.length === 0}
          <span class="otherwise">otherwise?</span>
        {:else}
          <input
            class="mono"
            type="text"
            value={check.signalNames.join(' + ')}
            placeholder="SIGNAL_NAME"
            oninput={(e) => {
              const names = e.currentTarget.value.split('+').map(s => s.trim()).filter(Boolean);
              updateCheck(idx, 'signalNames', names);
            }}
          />
          <span class="q">?</span>
        {/if}
        <button class="remove" onclick={() => removeCheck(idx)}>×</button>
      </div>
      <textarea
        rows="2"
        value={check.narrative}
        oninput={(e) => updateCheck(idx, 'narrative', e.currentTarget.value)}
        placeholder="Narrative for this branch..."
      ></textarea>
      {#each check.arrows as arrow, arrowIdx}
        <ArrowEditor
          {arrow}
          onchange={(a) => updateCheckArrow(idx, arrowIdx, a)}
          ondelete={() => deleteCheckArrow(idx, arrowIdx)}
          {roomName}
        />
      {/each}
      <button class="add-arrow" onclick={() => addArrowToCheck(idx)}>+ Add arrow</button>
    </div>
  {/each}
  <div class="add-buttons">
    <button onclick={addCheck}>+ Add signal branch</button>
    <button onclick={() => onchange([...checks, { signalNames: [], narrative: '', arrows: [] }])}>
      + Add otherwise
    </button>
  </div>
</div>

<style>
  .signal-check-editor {
    border-left: 2px solid var(--amber);
    padding-left: 12px;
    margin-top: 8px;
  }
  .check-branch {
    margin-bottom: 12px;
    padding: 8px;
    background: var(--mid-dark);
    border-radius: 6px;
  }
  .branch-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
  }
  .branch-header input { flex: 1; font-size: 0.85rem; }
  .q { color: var(--amber); font-weight: 700; }
  .otherwise {
    color: var(--amber);
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }
  .remove { background: none; color: var(--red-ink); padding: 2px 6px; }
  textarea { width: 100%; resize: vertical; margin-bottom: 4px; }
  .add-arrow, .add-buttons button {
    background: none;
    color: var(--gold-dim);
    font-size: 0.8rem;
    padding: 2px 0;
  }
  .add-buttons { display: flex; gap: 12px; }
</style>
```

- [ ] **Step 2: Wire into InteractionEditor.svelte**

Add signal check section to `InteractionEditor.svelte`, after the sealed content section:

```svelte
  {#if interaction.signalChecks.length > 0}
    <div class="field">
      <span class="label">Signal Checks (Conditional Branches)</span>
      <SignalCheckEditor
        checks={interaction.signalChecks}
        onchange={(checks) => update((i) => { i.signalChecks = checks; })}
        roomName={interaction.room}
      />
    </div>
  {:else}
    <button class="toggle-sealed" onclick={() => update((i) => {
      i.signalChecks = [{ signalNames: [], narrative: '', arrows: [] }];
    })}>
      + Add signal checks
    </button>
  {/if}
```

Add the import: `import SignalCheckEditor from './SignalCheckEditor.svelte';`

- [ ] **Step 3: Verify in browser**

Create an interaction, click "+ Add signal checks". Add a signal branch with a name, narrative, and arrow. Add an "otherwise" branch. Verify the UI shows conditional branches with the amber left border.

- [ ] **Step 4: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/SignalCheckEditor.svelte editor/src/components/InteractionEditor.svelte
git commit -m "feat(editor): add signal check editor for conditional branches"
```

---

### Task 11: Serializer (GameData → .md)

**Files:**
- Create: `editor/src/lib/serializer.ts`
- Create: `editor/tests/serializer.test.ts`

- [ ] **Step 1: Write serializer.ts**

```typescript
import type { GameData, Interaction, Arrow, SignalCheck, Cue, Action } from './types';

/** Serialize a GameData to a map of filename → content */
export function serializeGame(game: GameData): Record<string, string> {
  const files: Record<string, string> = {};

  files['index.md'] = serializeIndex(game);

  // One file per base room
  const baseRooms = Object.values(game.rooms).filter(r => r.state === null);
  for (const room of baseRooms) {
    const filename = room.name.toLowerCase().replace(/\s+/g, '_') + '.md';
    files[filename] = serializeRoom(game, room.name);
  }

  return files;
}

function serializeIndex(game: GameData): string {
  const lines: string[] = [];

  // Frontmatter
  const meta = game.metadata;
  if (Object.keys(meta).length > 0) {
    lines.push('---');
    for (const [key, value] of Object.entries(meta)) {
      if (key === 'description') continue;
      if (value) lines.push(`${key}: ${value}`);
    }
    lines.push('---');
    lines.push('');
  }

  // Description
  if (meta.description) {
    lines.push(meta.description);
    lines.push('');
  }

  // Index-level signal checks
  for (const check of game.signalChecks) {
    lines.push(...serializeSignalCheck(check, 0));
  }

  // Verbs
  if (Object.keys(game.verbs).length > 0) {
    lines.push('# Verbs');
    for (const name of Object.keys(game.verbs)) {
      if (!name.includes('__')) {
        lines.push(name);
      }
    }
    lines.push('');
  }

  // Inventory
  lines.push('# Inventory');
  for (const name of Object.keys(game.inventory)) {
    lines.push(name);
    // Inventory-level interactions
    const invInteractions = game.interactions.filter(i => i.room === '' && i.targetGroups.some(g => g.includes(name)));
    for (const interaction of invInteractions) {
      lines.push(...serializeInteraction(interaction, 2));
    }
  }
  lines.push('');

  return lines.join('\n');
}

function serializeRoom(game: GameData, roomName: string): string {
  const lines: string[] = [];

  lines.push(`# ${roomName}`);

  // Room LOOK description
  const roomLook = game.interactions.find(
    i => i.room === roomName && i.verb === 'LOOK' && i.targetGroups.length === 0
  );
  if (roomLook) {
    lines.push(`LOOK: ${roomLook.narrative}`);
    lines.push('');
  }

  // Objects in this room (grouped by base name)
  const objectsByBase = new Map<string, string[]>();
  for (const obj of Object.values(game.objects)) {
    if (obj.room !== roomName) continue;
    if (!objectsByBase.has(obj.base)) objectsByBase.set(obj.base, []);
    objectsByBase.get(obj.base)!.push(obj.name);
  }

  for (const [baseName, variants] of objectsByBase) {
    for (const variant of variants) {
      lines.push(variant);
      // Interactions targeting this object
      const objInteractions = game.interactions.filter(
        i => i.room === roomName &&
          i.targetGroups.length > 0 &&
          i.targetGroups[0].includes(variant)
      );
      for (const interaction of objInteractions) {
        lines.push(...serializeInteraction(interaction, 2));
      }
      lines.push('');
    }
  }

  // Actions
  for (const action of Object.values(game.actions)) {
    if (action.room !== roomName) continue;
    lines.push(`> ${action.name}`);
    if (action.narrative) {
      lines.push(`  ${action.narrative}`);
    }
    for (const arrow of action.arrows) {
      lines.push(`  - ${serializeArrow(arrow)}`);
    }
    lines.push('');
  }

  // Freeform interactions
  const freeform = game.interactions.filter(
    i => i.room === roomName &&
      i.targetGroups.length > 0 &&
      (i.targetGroups[0].includes('*') || i.targetGroups.length > 1) &&
      // Exclude object interactions already serialized
      !objectsByBase.has(i.targetGroups[0][0]?.split('__')[0])
  );
  if (freeform.length > 0) {
    lines.push('## Interactions');
    lines.push('');
    for (const interaction of freeform) {
      lines.push(...serializeInteraction(interaction, 0));
      lines.push('');
    }
  }

  return lines.join('\n');
}

function serializeInteraction(interaction: Interaction, indent: number): string[] {
  const prefix = ' '.repeat(indent);
  const lines: string[] = [];

  // Header: + VERB [+ TARGET]: narrative
  const targetStr = interaction.targetGroups
    .map(g => g.join(' | '))
    .join(' + ');

  let header = `${prefix}+ ${interaction.verb}`;
  if (targetStr) header += ` + ${targetStr}`;
  header += ':';

  if (interaction.narrative && !interaction.narrative.includes('\n')) {
    header += ` ${interaction.narrative}`;
    lines.push(header);
  } else {
    lines.push(header);
    if (interaction.narrative) {
      for (const line of interaction.narrative.split('\n')) {
        lines.push(`${prefix}  ${line}`);
      }
    }
  }

  // Arrows
  for (const arrow of interaction.arrows) {
    lines.push(`${prefix}  - ${serializeArrow(arrow)}`);
  }

  // Signal checks
  for (const check of interaction.signalChecks) {
    lines.push(...serializeSignalCheck(check, indent + 2));
  }

  // Sealed content
  if (interaction.sealedContent) {
    lines.push('');
    lines.push(`${prefix}  ::: fragment`);
    for (const line of interaction.sealedContent.split('\n')) {
      lines.push(`${prefix}  ${line}`);
    }
    // Sealed arrows
    for (const arrow of interaction.sealedArrows) {
      lines.push(`${prefix}  - ${serializeArrow(arrow)}`);
    }
    lines.push(`${prefix}  :::`);
  }

  return lines;
}

function serializeArrow(arrow: Arrow): string {
  if (arrow.subject) {
    return `${arrow.subject} -> ${arrow.destination}`;
  }
  return `-> ${arrow.destination}`;
}

function serializeSignalCheck(check: SignalCheck, indent: number): string[] {
  const prefix = ' '.repeat(indent);
  const lines: string[] = [];

  if (check.signalNames.length === 0) {
    lines.push(`${prefix}otherwise?`);
  } else {
    lines.push(`${prefix}${check.signalNames.join(' + ')}?`);
  }

  if (check.narrative) {
    for (const line of check.narrative.split('\n')) {
      lines.push(`${prefix}  ${line}`);
    }
  }

  for (const arrow of check.arrows) {
    lines.push(`${prefix}  - ${serializeArrow(arrow)}`);
  }

  return lines;
}
```

- [ ] **Step 2: Write serializer tests**

Write `editor/tests/serializer.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { serializeGame } from '../src/lib/serializer';
import { createGameData, createVerb, createRoom, createRoomObject, createArrow, objectKey } from '../src/lib/factory';

describe('serializeGame', () => {
  it('produces index.md with frontmatter and verbs', () => {
    const game = createGameData();
    game.metadata = { title: 'Test Game', author: 'Tester', start: 'Lobby' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');

    const files = serializeGame(game);
    const index = files['index.md'];

    expect(index).toContain('---');
    expect(index).toContain('title: Test Game');
    expect(index).toContain('# Verbs');
    expect(index).toContain('LOOK');
    expect(index).toContain('USE');
  });

  it('produces room files with objects and interactions', () => {
    const game = createGameData();
    game.rooms['Lobby'] = createRoom('Lobby');
    game.objects[objectKey('Lobby', 'DOOR')] = createRoomObject('DOOR', 'Lobby');
    game.interactions.push({
      verb: 'LOOK',
      targetGroups: [['DOOR']],
      narrative: 'A heavy wooden door.',
      arrows: [],
      room: 'Lobby',
      sealedContent: null,
      sealedArrows: [],
      signalChecks: [],
    });

    const files = serializeGame(game);
    expect(files['lobby.md']).toContain('# Lobby');
    expect(files['lobby.md']).toContain('DOOR');
    expect(files['lobby.md']).toContain('A heavy wooden door.');
  });

  it('serializes arrows correctly', () => {
    const game = createGameData();
    game.rooms['Room'] = createRoom('Room');
    game.objects[objectKey('Room', 'KEY')] = createRoomObject('KEY', 'Room');
    game.interactions.push({
      verb: 'TAKE',
      targetGroups: [['KEY']],
      narrative: 'You grab it.',
      arrows: [createArrow('KEY', 'player')],
      room: 'Room',
      sealedContent: null,
      sealedArrows: [],
      signalChecks: [],
    });

    const files = serializeGame(game);
    expect(files['room.md']).toContain('- KEY -> player');
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/serializer.ts editor/tests/serializer.test.ts
git commit -m "feat(editor): add serializer to convert GameData to .md files"
```

---

### Task 12: Export (.zip)

**Files:**
- Create: `editor/src/lib/export.ts`
- Create: `editor/tests/export.test.ts`
- Modify: `editor/src/components/TopBar.svelte`

- [ ] **Step 1: Write export.ts**

```typescript
import JSZip from 'jszip';
import type { GameData } from './types';
import { serializeGame } from './serializer';

export async function exportZip(game: GameData, projectName: string): Promise<Blob> {
  const files = serializeGame(game);
  const zip = new JSZip();

  const folderName = projectName.toLowerCase().replace(/\s+/g, '-');
  const folder = zip.folder(folderName)!;

  for (const [filename, content] of Object.entries(files)) {
    folder.file(filename, content);
  }

  return zip.generateAsync({ type: 'blob' });
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 2: Write export test**

Write `editor/tests/export.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import JSZip from 'jszip';
import { exportZip } from '../src/lib/export';
import { createGameData, createVerb, createRoom } from '../src/lib/factory';

describe('exportZip', () => {
  it('creates a zip with index.md and room files', async () => {
    const game = createGameData();
    game.metadata = { title: 'Test', author: 'Me', start: 'Lobby' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Lobby'] = createRoom('Lobby');

    const blob = await exportZip(game, 'Test Game');
    const zip = await JSZip.loadAsync(blob);

    const indexFile = zip.file('test-game/index.md');
    expect(indexFile).not.toBeNull();

    const content = await indexFile!.async('string');
    expect(content).toContain('title: Test');
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Wire export button in TopBar.svelte**

Add to `TopBar.svelte` script:

```typescript
  import { exportZip, downloadBlob } from '../lib/export';

  async function handleExport() {
    if (!store.project || !store.game) return;
    const blob = await exportZip(store.game, store.project.name);
    const filename = store.project.name.toLowerCase().replace(/\s+/g, '-') + '.zip';
    downloadBlob(blob, filename);
  }
```

Change the export button:

```svelte
<button class="export" onclick={handleExport}>↓ Export .zip</button>
```

- [ ] **Step 5: Verify in browser**

Create a game with some rooms, objects, verbs, and interactions. Click "↓ Export .zip". Verify:
- A `.zip` file downloads
- Unzipping produces a valid game directory with `index.md` and room `.md` files
- Run `uv run addventure build` on the exported directory (may fail if incomplete game, but files should parse)

- [ ] **Step 6: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/export.ts editor/tests/export.test.ts editor/src/components/TopBar.svelte
git commit -m "feat(editor): add zip export with download button"
```

---

### Task 13: Import (.md Parser)

**Files:**
- Create: `editor/src/lib/parser.ts`
- Create: `editor/tests/parser.test.ts`
- Modify: `editor/src/components/TopBar.svelte`

- [ ] **Step 1: Write parser.ts**

This is a JavaScript port of the Python parser's logic. It parses `.md` files into a `GameData` model. The parser needs to handle: frontmatter, verbs section, inventory section, room headers, objects with interactions, arrows, signal checks, sealed content, actions, and cues.

```typescript
import type { GameData, Interaction, Arrow, SignalCheck, Cue, Action } from './types';
import { createGameData, createVerb, createRoom, createRoomObject, createInventoryObject, createArrow, createAction, objectKey, actionKey } from './factory';

export function parseGameFiles(files: Record<string, string>): GameData {
  const game = createGameData();

  // Parse index.md first
  const indexContent = files['index.md'];
  if (indexContent) {
    parseIndex(indexContent, game);
  }

  // Parse room files
  for (const [filename, content] of Object.entries(files)) {
    if (filename === 'index.md') continue;
    if (!filename.endsWith('.md')) continue;
    parseRoomFile(content, game);
  }

  return game;
}

function parseIndex(content: string, game: GameData): void {
  const lines = content.split('\n');
  let i = 0;

  // Frontmatter
  if (lines[i]?.trim() === '---') {
    i++;
    while (i < lines.length && lines[i]?.trim() !== '---') {
      const match = lines[i].match(/^(\w+):\s*(.+)$/);
      if (match) {
        game.metadata[match[1]] = match[2].trim();
      }
      i++;
    }
    i++; // skip closing ---
  }

  // Description (free text before first # section)
  const descLines: string[] = [];
  while (i < lines.length && !lines[i]?.startsWith('#')) {
    // Check for signal checks
    if (lines[i]?.match(/^[A-Z][A-Z0-9_]*(\s*\+\s*[A-Z][A-Z0-9_]*)*\?/) || lines[i]?.trim() === 'otherwise?') {
      // Parse signal checks
      while (i < lines.length && !lines[i]?.startsWith('#')) {
        const check = parseSignalCheckLine(lines, i);
        if (check) {
          game.signalChecks.push(check.check);
          i = check.nextLine;
        } else {
          i++;
        }
      }
      break;
    }
    descLines.push(lines[i]);
    i++;
  }
  const desc = descLines.join('\n').trim();
  if (desc) game.metadata.description = desc;

  // Sections
  while (i < lines.length) {
    const line = lines[i]?.trim();

    if (line === '# Verbs') {
      i++;
      while (i < lines.length && !lines[i]?.startsWith('#')) {
        const verbName = lines[i]?.trim();
        if (verbName && verbName.match(/^[A-Z][A-Z0-9_]*$/)) {
          game.verbs[verbName] = createVerb(verbName);
        }
        i++;
      }
    } else if (line === '# Inventory') {
      i++;
      while (i < lines.length && !lines[i]?.startsWith('#')) {
        const itemName = lines[i]?.trim();
        if (itemName && itemName.match(/^[A-Z][A-Z0-9_]*(?:__[A-Z0-9_]+)*$/)) {
          game.inventory[itemName] = createInventoryObject(itemName);
        }
        // Skip inventory interaction lines (indented)
        i++;
        while (i < lines.length && lines[i]?.match(/^\s+/)) {
          i++;
        }
      }
    } else {
      i++;
    }
  }
}

function parseRoomFile(content: string, game: GameData): void {
  const lines = content.split('\n');
  let i = 0;
  let currentRoom = '';

  while (i < lines.length) {
    const line = lines[i];

    // Room header
    const roomMatch = line?.match(/^# (.+)$/);
    if (roomMatch) {
      currentRoom = roomMatch[1].trim();
      game.rooms[currentRoom] = createRoom(currentRoom);
      i++;
      continue;
    }

    if (!currentRoom) { i++; continue; }

    const trimmed = line?.trim() ?? '';

    // Room LOOK: description
    if (trimmed.startsWith('LOOK:') && !line?.startsWith(' ')) {
      const narrative = trimmed.slice(5).trim();
      const fullNarrative = collectMultilineNarrative(lines, i, narrative);
      game.interactions.push({
        verb: 'LOOK',
        targetGroups: [],
        narrative: fullNarrative.text,
        arrows: [],
        room: currentRoom,
        sealedContent: null,
        sealedArrows: [],
        signalChecks: [],
      });
      i = fullNarrative.nextLine;
      continue;
    }

    // Object name (unindented, uppercase)
    if (trimmed.match(/^[A-Z][A-Z0-9_]*(?:__[A-Z0-9_]+)*$/) && !line?.startsWith(' ')) {
      const objName = trimmed;
      const key = objectKey(currentRoom, objName);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(objName, currentRoom);
      }
      i++;

      // Parse indented interactions under this object
      while (i < lines.length && (lines[i]?.startsWith('  ') || lines[i]?.trim() === '')) {
        if (lines[i]?.trim() === '') { i++; continue; }

        const interactionMatch = lines[i]?.trim().match(/^\+ ([A-Z][A-Z0-9_]*(?:__[A-Z0-9_]+)?)(?:\s*\+\s*(.+?))?:\s*(.*)$/);
        if (interactionMatch) {
          const verb = interactionMatch[1];
          const targetsStr = interactionMatch[2];
          const inlineNarrative = interactionMatch[3] ?? '';

          const targetGroups: string[][] = [[objName]];
          if (targetsStr) {
            const extraGroups = targetsStr.split('+').map(g =>
              g.trim().split('|').map(s => s.trim()).filter(Boolean)
            );
            targetGroups.push(...extraGroups);
          }

          // Collect multi-line narrative and arrows
          const body = collectInteractionBody(lines, i + 1);

          const narrative = inlineNarrative || body.narrative;

          game.interactions.push({
            verb,
            targetGroups,
            narrative,
            arrows: body.arrows,
            room: currentRoom,
            sealedContent: body.sealedContent,
            sealedArrows: body.sealedArrows,
            signalChecks: body.signalChecks,
          });

          i = body.nextLine;
        } else {
          // Arrow line under object
          const arrowMatch = lines[i]?.trim().match(/^- (.+?) -> (.+)$/);
          if (arrowMatch) {
            // Object-level arrows (state transitions, etc.) — skip for now
          }
          i++;
        }
      }
      continue;
    }

    // Action: > ACTION_NAME
    const actionMatch = trimmed.match(/^> ([A-Z][A-Z0-9_]*)$/);
    if (actionMatch) {
      const actionName = actionMatch[1];
      const body = collectInteractionBody(lines, i + 1);
      const key = actionKey(currentRoom, actionName);
      game.actions[key] = {
        name: actionName,
        room: currentRoom,
        narrative: body.narrative,
        arrows: body.arrows,
        discovered: false,
      };
      i = body.nextLine;
      continue;
    }

    // Freeform interactions section
    if (trimmed === '## Interactions') {
      i++;
      while (i < lines.length && !lines[i]?.startsWith('#')) {
        const freeMatch = lines[i]?.trim().match(/^([A-Z][A-Z0-9_]*(?:__[A-Z0-9_]+)?)\s*\+\s*(.+?):\s*(.*)$/);
        if (freeMatch) {
          const verb = freeMatch[1];
          const targetsStr = freeMatch[2];
          const inlineNarrative = freeMatch[3] ?? '';

          const targetGroups = targetsStr.split('+').map(g =>
            g.trim().split('|').map(s => s.trim()).filter(Boolean)
          );

          const body = collectInteractionBody(lines, i + 1);
          game.interactions.push({
            verb,
            targetGroups,
            narrative: inlineNarrative || body.narrative,
            arrows: body.arrows,
            room: currentRoom,
            sealedContent: body.sealedContent,
            sealedArrows: body.sealedArrows,
            signalChecks: body.signalChecks,
          });
          i = body.nextLine;
        } else {
          i++;
        }
      }
      continue;
    }

    i++;
  }
}

interface InteractionBody {
  narrative: string;
  arrows: Arrow[];
  sealedContent: string | null;
  sealedArrows: Arrow[];
  signalChecks: SignalCheck[];
  nextLine: number;
}

function collectInteractionBody(lines: string[], startLine: number): InteractionBody {
  let i = startLine;
  const narrativeLines: string[] = [];
  const arrows: Arrow[] = [];
  const signalChecks: SignalCheck[] = [];
  let sealedContent: string | null = null;
  const sealedArrows: Arrow[] = [];

  const baseIndent = getIndent(lines[startLine] ?? '');

  while (i < lines.length) {
    const line = lines[i];
    if (line?.trim() === '') { i++; continue; }

    const indent = getIndent(line ?? '');
    if (indent < baseIndent && line?.trim() !== '') break;

    const trimmed = line?.trim() ?? '';

    // Arrow
    const arrowMatch = trimmed.match(/^- (.+?) -> (.+)$/);
    if (arrowMatch) {
      arrows.push(createArrow(arrowMatch[1].trim(), arrowMatch[2].trim()));
      i++;
      continue;
    }

    // Arrow with empty subject
    const arrowMatch2 = trimmed.match(/^- -> (.+)$/);
    if (arrowMatch2) {
      arrows.push(createArrow('', arrowMatch2[1].trim()));
      i++;
      continue;
    }

    // Fragment
    if (trimmed === '::: fragment') {
      i++;
      const fragmentLines: string[] = [];
      while (i < lines.length && lines[i]?.trim() !== ':::') {
        const fLine = lines[i]?.trim() ?? '';
        const fArrow = fLine.match(/^- (.+?) -> (.+)$/);
        if (fArrow) {
          sealedArrows.push(createArrow(fArrow[1].trim(), fArrow[2].trim()));
        } else {
          fragmentLines.push(fLine);
        }
        i++;
      }
      sealedContent = fragmentLines.join('\n').trim();
      i++; // skip :::
      continue;
    }

    // Narrative text
    narrativeLines.push(trimmed);
    i++;
  }

  return {
    narrative: narrativeLines.join('\n').trim(),
    arrows,
    sealedContent,
    sealedArrows,
    signalChecks,
    nextLine: i,
  };
}

function collectMultilineNarrative(lines: string[], startLine: number, firstLine: string): { text: string; nextLine: number } {
  const parts = [firstLine];
  let i = startLine + 1;
  while (i < lines.length && lines[i]?.startsWith('  ')) {
    parts.push(lines[i]!.trim());
    i++;
  }
  return { text: parts.join('\n').trim(), nextLine: i };
}

function parseSignalCheckLine(lines: string[], startLine: number): { check: SignalCheck; nextLine: number } | null {
  const line = lines[startLine]?.trim() ?? '';
  const match = line.match(/^((?:[A-Z][A-Z0-9_]*(?:\s*\+\s*[A-Z][A-Z0-9_]*)*))\?$/);
  const isOtherwise = line === 'otherwise?';

  if (!match && !isOtherwise) return null;

  const signalNames = isOtherwise ? [] : match![1].split('+').map(s => s.trim());
  const body = collectInteractionBody(lines, startLine + 1);

  return {
    check: {
      signalNames,
      narrative: body.narrative,
      arrows: body.arrows,
    },
    nextLine: body.nextLine,
  };
}

function getIndent(line: string): number {
  const match = line.match(/^(\s*)/);
  return match ? match[1].length : 0;
}
```

- [ ] **Step 2: Write parser tests**

Write `editor/tests/parser.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseGameFiles } from '../src/lib/parser';

describe('parseGameFiles', () => {
  it('parses index.md frontmatter and verbs', () => {
    const files = {
      'index.md': `---
title: Test Game
author: Tester
start: Lobby
---

Welcome to the game.

# Verbs
LOOK
USE
TAKE

# Inventory
`,
    };

    const game = parseGameFiles(files);
    expect(game.metadata.title).toBe('Test Game');
    expect(game.metadata.author).toBe('Tester');
    expect(game.metadata.start).toBe('Lobby');
    expect(game.metadata.description).toBe('Welcome to the game.');
    expect(Object.keys(game.verbs)).toEqual(['LOOK', 'USE', 'TAKE']);
  });

  it('parses room with objects and interactions', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\nUSE\n\n# Inventory\n',
      'lobby.md': `# Lobby
LOOK: A dimly lit room.

DOOR
  + LOOK: A heavy wooden door.
  + USE:
      You push it open.
      - player -> "Hallway"
`,
    };

    const game = parseGameFiles(files);
    expect(game.rooms['Lobby']).toBeDefined();
    expect(game.objects['Lobby::DOOR']).toBeDefined();

    const lookRoom = game.interactions.find(i => i.verb === 'LOOK' && i.targetGroups.length === 0);
    expect(lookRoom?.narrative).toBe('A dimly lit room.');

    const lookDoor = game.interactions.find(i => i.verb === 'LOOK' && i.targetGroups[0]?.[0] === 'DOOR');
    expect(lookDoor?.narrative).toBe('A heavy wooden door.');

    const useDoor = game.interactions.find(i => i.verb === 'USE' && i.targetGroups[0]?.[0] === 'DOOR');
    expect(useDoor?.narrative).toContain('You push it open.');
    expect(useDoor?.arrows[0]?.subject).toBe('player');
    expect(useDoor?.arrows[0]?.destination).toBe('"Hallway"');
  });

  it('round-trips: serialize then parse', () => {
    // Import serializeGame to test round-trip
    const { serializeGame } = require('../src/lib/serializer');
    const { createGameData, createVerb, createRoom, createRoomObject, objectKey } = require('../src/lib/factory');

    const original = createGameData();
    original.metadata = { title: 'Round Trip', author: 'Test', start: 'Room' };
    original.verbs['LOOK'] = createVerb('LOOK');
    original.rooms['Room'] = createRoom('Room');
    original.objects[objectKey('Room', 'BOX')] = createRoomObject('BOX', 'Room');
    original.interactions.push({
      verb: 'LOOK',
      targetGroups: [['BOX']],
      narrative: 'A wooden box.',
      arrows: [],
      room: 'Room',
      sealedContent: null,
      sealedArrows: [],
      signalChecks: [],
    });

    const files = serializeGame(original);
    const parsed = parseGameFiles(files);

    expect(parsed.metadata.title).toBe('Round Trip');
    expect(parsed.verbs['LOOK']).toBeDefined();
    expect(parsed.objects['Room::BOX']).toBeDefined();

    const lookBox = parsed.interactions.find(i => i.verb === 'LOOK' && i.targetGroups[0]?.[0] === 'BOX');
    expect(lookBox?.narrative).toBe('A wooden box.');
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd /home/chris/dev/addventure/editor
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Wire import in TopBar.svelte**

Add to `TopBar.svelte`:

```typescript
  import JSZip from 'jszip';
  import { parseGameFiles } from '../lib/parser';

  let fileInput: HTMLInputElement;

  async function handleImport() {
    fileInput.click();
  }

  async function onFileSelected(e: Event) {
    const file = (e.currentTarget as HTMLInputElement).files?.[0];
    if (!file) return;

    const files: Record<string, string> = {};

    if (file.name.endsWith('.zip')) {
      const zip = await JSZip.loadAsync(file);
      for (const [path, zipEntry] of Object.entries(zip.files)) {
        if (zipEntry.dir) continue;
        if (!path.endsWith('.md')) continue;
        const filename = path.split('/').pop()!;
        files[filename] = await zipEntry.async('string');
      }
    } else if (file.name.endsWith('.md')) {
      files[file.name] = await file.text();
    }

    if (Object.keys(files).length > 0) {
      const gameData = parseGameFiles(files);
      const name = gameData.metadata.title || file.name.replace(/\.\w+$/, '');
      store.create(name);
      store.mutate((game) => {
        Object.assign(game, gameData);
      });
    }
  }
```

Add hidden file input and wire import button:

```svelte
<input type="file" accept=".zip,.md" bind:this={fileInput} onchange={onFileSelected} style="display:none" />
<button onclick={handleImport}>Import</button>
```

- [ ] **Step 5: Verify in browser**

Export a game as `.zip`, then import it. Verify the game data round-trips correctly — rooms, objects, verbs, and interactions are preserved.

- [ ] **Step 6: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/lib/parser.ts editor/tests/parser.test.ts editor/src/components/TopBar.svelte
git commit -m "feat(editor): add .md parser and zip/file import"
```

---

### Task 14: Source View (CodeMirror)

**Files:**
- Create: `editor/src/components/SourceView.svelte`
- Modify: `editor/src/components/RoomView.svelte`

- [ ] **Step 1: Install CodeMirror**

```bash
cd /home/chris/dev/addventure/editor
npm install @codemirror/state @codemirror/view @codemirror/language @codemirror/commands codemirror @codemirror/lang-markdown
```

- [ ] **Step 2: Write SourceView.svelte**

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { EditorView, basicSetup } from 'codemirror';
  import { EditorState } from '@codemirror/state';
  import { markdown } from '@codemirror/lang-markdown';
  import { ViewPlugin } from '@codemirror/view';

  let { content, onchange }: { content: string; onchange: (value: string) => void } = $props();

  let container: HTMLDivElement;
  let view: EditorView;
  let updating = false;

  const darkTheme = EditorView.theme({
    '&': {
      backgroundColor: 'var(--dark)',
      color: 'var(--text-light)',
      fontFamily: 'var(--font-mono)',
      fontSize: '13px',
    },
    '.cm-content': { caretColor: 'var(--gold)' },
    '.cm-cursor': { borderLeftColor: 'var(--gold)' },
    '.cm-activeLine': { backgroundColor: 'rgba(201, 168, 76, 0.05)' },
    '.cm-selectionBackground': { backgroundColor: 'rgba(201, 168, 76, 0.2) !important' },
    '.cm-gutters': {
      backgroundColor: 'var(--dark-warm)',
      color: 'var(--text-dim)',
      border: 'none',
    },
  });

  onMount(() => {
    const updatePlugin = ViewPlugin.fromClass(class {
      update(update: any) {
        if (update.docChanged && !updating) {
          onchange(update.state.doc.toString());
        }
      }
    });

    view = new EditorView({
      state: EditorState.create({
        doc: content,
        extensions: [basicSetup, markdown(), darkTheme, updatePlugin],
      }),
      parent: container,
    });
  });

  onDestroy(() => {
    view?.destroy();
  });

  // Sync external content changes into editor
  $effect(() => {
    if (view && content !== view.state.doc.toString()) {
      updating = true;
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: content },
      });
      updating = false;
    }
  });
</script>

<div class="source-view" bind:this={container}></div>

<style>
  .source-view {
    flex: 1;
    overflow: hidden;
  }
  .source-view :global(.cm-editor) {
    height: 100%;
  }
</style>
```

- [ ] **Step 3: Wire into RoomView.svelte**

Add source view toggle to `RoomView.svelte`. Add state and logic:

```typescript
  import SourceView from './SourceView.svelte';
  import { serializeGame } from '../lib/serializer';
  import { parseGameFiles } from '../lib/parser';

  let sourceMode = $state(false);

  // Generate source for current room
  let roomSource = $derived(() => {
    if (!game) return '';
    const files = serializeGame(game);
    const filename = roomName.toLowerCase().replace(/\s+/g, '_') + '.md';
    return files[filename] ?? '';
  });

  function handleSourceChange(newSource: string) {
    // Re-parse the single room file and update game data
    // This is a simplified bidirectional sync
    const files = { [roomName.toLowerCase().replace(/\s+/g, '_') + '.md']: newSource };
    const parsed = parseGameFiles(files);

    store.mutate((g) => {
      // Remove old room data
      g.interactions = g.interactions.filter(i => i.room !== roomName);
      for (const key of Object.keys(g.objects)) {
        if (key.startsWith(roomName + '::')) delete g.objects[key];
      }

      // Merge parsed data
      Object.assign(g.rooms, parsed.rooms);
      Object.assign(g.objects, parsed.objects);
      g.interactions.push(...parsed.interactions);
      Object.assign(g.actions, parsed.actions);
    });
  }
```

Replace the view toggle buttons:

```svelte
  <div class="view-toggle">
    <button class:active={!sourceMode} onclick={() => sourceMode = false}>Visual</button>
    <button class:active={sourceMode} onclick={() => sourceMode = true}>Source</button>
  </div>
```

And conditionally render:

```svelte
  {#if sourceMode}
    <SourceView content={roomSource()} onchange={handleSourceChange} />
  {:else}
    <!-- existing visual view content -->
  {/if}
```

- [ ] **Step 4: Verify in browser**

Create a room with objects and interactions. Toggle to Source view — verify the raw `.md` is displayed with syntax highlighting. Edit the source and toggle back to Visual — verify changes sync.

- [ ] **Step 5: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/SourceView.svelte editor/src/components/RoomView.svelte
git commit -m "feat(editor): add CodeMirror source view with bidirectional sync"
```

---

### Task 15: Map View

**Files:**
- Create: `editor/src/components/MapView.svelte`
- Modify: `editor/src/components/MainPanel.svelte`

- [ ] **Step 1: Write MapView.svelte**

A simple canvas-based room graph. Rooms are draggable rectangles, exits are drawn as lines with arrows.

```svelte
<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getRoomExits } from '../lib/helpers';
  import { loadMapPositions, saveMapPositions } from '../lib/persistence';

  let game = $derived(store.game);
  let rooms = $derived(game ? Object.values(game.rooms).filter(r => r.state === null) : []);

  // Position state
  let positions = $state<Record<string, { x: number; y: number }>>({});

  // Load saved positions
  $effect(() => {
    if (store.project) {
      const saved = loadMapPositions(store.project.id);
      // Initialize positions for rooms without saved positions
      const pos = { ...saved };
      let col = 0;
      for (const room of rooms) {
        if (!pos[room.name]) {
          pos[room.name] = { x: 100 + (col % 4) * 200, y: 100 + Math.floor(col / 4) * 120 };
          col++;
        }
      }
      positions = pos;
    }
  });

  let dragging: string | null = null;
  let dragOffset = { x: 0, y: 0 };

  function startDrag(roomName: string, e: MouseEvent) {
    dragging = roomName;
    const pos = positions[roomName];
    dragOffset = { x: e.clientX - (pos?.x ?? 0), y: e.clientY - (pos?.y ?? 0) };
    e.preventDefault();
  }

  function onMouseMove(e: MouseEvent) {
    if (!dragging) return;
    positions[dragging] = {
      x: e.clientX - dragOffset.x,
      y: e.clientY - dragOffset.y,
    };
  }

  function onMouseUp() {
    if (dragging && store.project) {
      saveMapPositions(store.project.id, positions);
    }
    dragging = null;
  }

  function clickRoom(roomName: string) {
    if (!dragging) {
      store.showRoom(roomName);
    }
  }

  // Compute edges
  let edges = $derived(() => {
    if (!game) return [];
    const result: { from: string; to: string; label: string }[] = [];
    for (const room of rooms) {
      const exits = getRoomExits(game, room.name);
      for (const exit of exits) {
        result.push({ from: room.name, to: exit.targetRoom, label: exit.via });
      }
    }
    // Cues as dashed lines
    for (const cue of game.cues) {
      result.push({ from: cue.triggerRoom, to: cue.targetRoom, label: 'cue' });
    }
    return result;
  });

  const NODE_W = 160;
  const NODE_H = 50;
</script>

<div
  class="map-view"
  onmousemove={onMouseMove}
  onmouseup={onMouseUp}
  role="application"
>
  <svg class="edges">
    {#each edges() as edge}
      {#if positions[edge.from] && positions[edge.to]}
        <line
          x1={positions[edge.from].x + NODE_W / 2}
          y1={positions[edge.from].y + NODE_H / 2}
          x2={positions[edge.to].x + NODE_W / 2}
          y2={positions[edge.to].y + NODE_H / 2}
          stroke={edge.label === 'cue' ? 'var(--parchment-dark)' : 'var(--warm-gray)'}
          stroke-width="2"
          stroke-dasharray={edge.label === 'cue' ? '6 4' : 'none'}
          marker-end="url(#arrowhead)"
        />
      {/if}
    {/each}
    <defs>
      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="var(--warm-gray)" />
      </marker>
    </defs>
  </svg>

  {#each rooms as room}
    {#if positions[room.name]}
      <div
        class="room-node"
        class:start={game?.metadata.start === room.name}
        style="left: {positions[room.name].x}px; top: {positions[room.name].y}px; width: {NODE_W}px; height: {NODE_H}px;"
        onmousedown={(e) => startDrag(room.name, e)}
        ondblclick={() => clickRoom(room.name)}
        role="button"
        tabindex="0"
      >
        <span class="room-label">{room.name}</span>
      </div>
    {/if}
  {/each}
</div>

<style>
  .map-view {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: auto;
    cursor: default;
  }
  .edges {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  .room-node {
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--mid-dark);
    border: 2px solid var(--warm-gray);
    border-radius: 8px;
    cursor: grab;
    user-select: none;
  }
  .room-node:hover { border-color: var(--gold-dim); }
  .room-node.start { border-color: var(--gold); }
  .room-node:active { cursor: grabbing; }
  .room-label {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--parchment-light);
    text-align: center;
  }
</style>
```

- [ ] **Step 2: Wire into MainPanel.svelte**

Add the import and render:

```svelte
<script lang="ts">
  import MapView from './MapView.svelte';
  // ... existing imports
</script>

  {:else if store.activeView === 'map'}
    <MapView />
```

- [ ] **Step 3: Verify in browser**

Create multiple rooms with movement arrows between them (`player -> "Room"`). Click the Map View button in the sidebar footer. Verify:
- Rooms appear as draggable nodes
- Edges connect rooms that have movement arrows
- Double-clicking a node navigates to the room editor
- Positions persist after navigating away and back

- [ ] **Step 4: Commit**

```bash
cd /home/chris/dev/addventure
git add editor/src/components/MapView.svelte editor/src/components/MainPanel.svelte
git commit -m "feat(editor): add draggable room map view with exits and cues"
```

---

### Task 16: Integration Test with Example Game

**Files:**
- No new files — this is a verification task

- [ ] **Step 1: Import the example game**

Copy the example game `.md` files and test the round-trip:

```bash
cd /home/chris/dev/addventure
cp -r games/example /tmp/example-test
cd editor
```

In the browser:
- Click "Import"
- Select the `.zip` or navigate to import individual `.md` files from `games/example/`

- [ ] **Step 2: Verify the imported game**

Check that:
- All rooms appear in the sidebar (Control Room, Basement, Cell Block, Epilogue)
- Verbs are listed (LOOK, USE, TAKE)
- Objects appear in each room with their interactions
- Arrows display correctly as badges
- Cues appear in the Signals & Cues section
- Game Summary shows the title and metadata

- [ ] **Step 3: Export and compare**

Export the imported game as `.zip`. Unzip and compare the output `.md` files with the originals. The content should be semantically equivalent (formatting may differ slightly).

- [ ] **Step 4: Build the exported game**

```bash
cd /tmp
unzip ~/Downloads/the-facility.zip
cd the-facility
uv run addventure build .
```

Verify the build succeeds or fails gracefully (the parser may catch differences — fix any serializer issues).

- [ ] **Step 5: Fix any issues found**

Address any serializer, parser, or display bugs found during the integration test. Each fix gets its own commit.

- [ ] **Step 6: Final commit**

```bash
cd /home/chris/dev/addventure
git add editor/
git commit -m "fix(editor): integration test fixes for example game round-trip"
```

---

## Summary

| Task | Component | Key Files |
|------|-----------|-----------|
| 1 | Project scaffolding | `editor/package.json`, `vite.config.ts`, `theme.css` |
| 2 | Data model & factories | `types.ts`, `factory.ts` |
| 3 | Helpers (derived data) | `helpers.ts` |
| 4 | Store & persistence | `store.svelte.ts`, `persistence.ts` |
| 5 | App shell | `App.svelte`, `TopBar`, `Sidebar`, `MainPanel`, `ProjectList` |
| 6 | Game summary view | `GameSummary.svelte` |
| 7 | Sidebar add actions | `Sidebar.svelte`, `store.svelte.ts` |
| 8 | Room view & object cards | `RoomView.svelte`, `ObjectCard.svelte`, `InteractionCard.svelte`, `ArrowBadge.svelte` |
| 9 | Interaction editor | `InteractionEditor.svelte`, `VerbPicker.svelte`, `TargetBuilder.svelte`, `ArrowEditor.svelte` |
| 10 | Signal check editor | `SignalCheckEditor.svelte` |
| 11 | Serializer | `serializer.ts` |
| 12 | Export (.zip) | `export.ts`, `TopBar.svelte` |
| 13 | Import (parser) | `parser.ts`, `TopBar.svelte` |
| 14 | Source view | `SourceView.svelte`, `RoomView.svelte` |
| 15 | Map view | `MapView.svelte` |
| 16 | Integration test | Verification with example game |

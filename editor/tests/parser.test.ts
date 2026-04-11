import { describe, it, expect } from 'vitest';
import { parseGameFiles } from '../src/lib/parser';
import { serializeGame } from '../src/lib/serializer';
import {
  createGameData,
  createVerb,
  createRoom,
  createRoomObject,
  createInventoryObject,
  createInteraction,
  createArrow,
  createAction,
  createSignalCheck,
  objectKey,
  actionKey,
} from '../src/lib/factory';

// ── parseIndex: frontmatter and verbs ─────────────────────────────────────

describe('parseGameFiles — index.md frontmatter', () => {
  it('parses frontmatter metadata', () => {
    const files = {
      'index.md': `---
title: The Facility
author: Test Author
start: Control Room
---

# Verbs
LOOK
USE
`,
    };
    const game = parseGameFiles(files);
    expect(game.metadata['title']).toBe('The Facility');
    expect(game.metadata['author']).toBe('Test Author');
    expect(game.metadata['start']).toBe('Control Room');
  });

  it('parses verbs from # Verbs section', () => {
    const files = {
      'index.md': `# Verbs
LOOK
USE
TAKE
`,
    };
    const game = parseGameFiles(files);
    expect(game.verbs['LOOK']).toBeDefined();
    expect(game.verbs['USE']).toBeDefined();
    expect(game.verbs['TAKE']).toBeDefined();
    expect(game.verbs['LOOK'].name).toBe('LOOK');
  });

  it('parses inventory from # Inventory section', () => {
    const files = {
      'index.md': `# Verbs
LOOK

# Inventory
KEY
LANTERN
`,
    };
    const game = parseGameFiles(files);
    expect(game.inventory['KEY']).toBeDefined();
    expect(game.inventory['LANTERN']).toBeDefined();
  });

  it('parses description text after frontmatter before sections', () => {
    const files = {
      'index.md': `---
title: Test
---

You wake up bound to a chair. The air tastes of rust.

Nobody is coming for you.

# Verbs
LOOK
`,
    };
    const game = parseGameFiles(files);
    expect(game.metadata['description']).toContain('You wake up bound');
    expect(game.metadata['description']).toContain('Nobody is coming');
  });

  it('handles index.md with no frontmatter', () => {
    const files = {
      'index.md': `# Verbs
LOOK
`,
    };
    const game = parseGameFiles(files);
    expect(game.verbs['LOOK']).toBeDefined();
    expect(game.metadata['title']).toBeUndefined();
  });

  it('parses index-level signal checks', () => {
    const files = {
      'index.md': `---
title: Test
---

INTRO_DONE?
  The game begins in earnest.

# Verbs
LOOK
`,
    };
    const game = parseGameFiles(files);
    expect(game.signalChecks).toHaveLength(1);
    expect(game.signalChecks[0].signalNames).toEqual(['INTRO_DONE']);
    expect(game.signalChecks[0].narrative).toBe('The game begins in earnest.');
  });

  it('parses multi-signal checks', () => {
    const files = {
      'index.md': `LAMP_LIT + DOOR_OPEN?
  Both are active.

otherwise?
  Nothing active.

# Verbs
LOOK
`,
    };
    const game = parseGameFiles(files);
    expect(game.signalChecks).toHaveLength(2);
    expect(game.signalChecks[0].signalNames).toEqual(['LAMP_LIT', 'DOOR_OPEN']);
    expect(game.signalChecks[1].signalNames).toEqual([]);
    expect(game.signalChecks[1].narrative).toBe('Nothing active.');
  });
});

// ── parseRoomFile: rooms, objects, and interactions ───────────────────────

describe('parseGameFiles — room file parsing', () => {
  it('creates a room from # Room Name header', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\n',
      'hallway.md': '# Hallway\n',
    };
    const game = parseGameFiles(files);
    expect(game.rooms['Hallway']).toBeDefined();
    expect(game.rooms['Hallway'].name).toBe('Hallway');
    expect(game.rooms['Hallway'].state).toBeNull();
  });

  it('parses LOOK: description at room level', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\n',
      'basement.md': `# Basement
LOOK: Damp walls and flickering lights.
`,
    };
    const game = parseGameFiles(files);
    const lookInteraction = game.interactions.find(
      (i) => i.verb === 'LOOK' && i.room === 'Basement' && i.targetGroups.length === 0,
    );
    expect(lookInteraction).toBeDefined();
    expect(lookInteraction!.narrative).toBe('Damp walls and flickering lights.');
  });

  it('parses room object with keyed interactions', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\nTAKE\n',
      'basement.md': `# Basement
LAMP
+ LOOK: An old oil lamp.
+ TAKE:
  You grab the lamp.
  - LAMP -> player
`,
    };
    const game = parseGameFiles(files);

    // Object should be created
    const lampKey = objectKey('Basement', 'LAMP');
    expect(game.objects[lampKey]).toBeDefined();
    expect(game.objects[lampKey].name).toBe('LAMP');
    expect(game.objects[lampKey].room).toBe('Basement');

    // LOOK interaction
    const lookInteraction = game.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('LAMP')),
    );
    expect(lookInteraction).toBeDefined();
    expect(lookInteraction!.narrative).toBe('An old oil lamp.');

    // TAKE interaction with arrow
    const takeInteraction = game.interactions.find(
      (i) =>
        i.verb === 'TAKE' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('LAMP')),
    );
    expect(takeInteraction).toBeDefined();
    expect(takeInteraction!.narrative).toBe('You grab the lamp.');
    expect(takeInteraction!.arrows).toHaveLength(1);
    expect(takeInteraction!.arrows[0].subject).toBe('LAMP');
    expect(takeInteraction!.arrows[0].destination).toBe('player');
  });

  it('parses multiple target groups in an interaction', () => {
    const files = {
      'index.md': '# Verbs\nUSE\n',
      'room.md': `# Room
FUSE
+ USE + FUSE_BOX: You slot the fuse in.
`,
    };
    const game = parseGameFiles(files);
    const interaction = game.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Room' &&
        i.targetGroups.some((g) => g.includes('FUSE')),
    );
    expect(interaction).toBeDefined();
    expect(interaction!.targetGroups).toHaveLength(2);
  });

  it('parses actions with > prefix', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\n',
      'hallway.md': `# Hallway
> GO_NORTH
  You walk north.
  - player -> "Control Room"
`,
    };
    const game = parseGameFiles(files);
    const key = actionKey('Hallway', 'GO_NORTH');
    expect(game.actions[key]).toBeDefined();
    expect(game.actions[key].narrative).toBe('You walk north.');
    expect(game.actions[key].arrows).toHaveLength(1);
    expect(game.actions[key].arrows[0].subject).toBe('player');
    expect(game.actions[key].arrows[0].destination).toBe('"Control Room"');
  });

  it('parses ## Interactions freeform section', () => {
    const files = {
      'index.md': '# Verbs\nUSE\n',
      'control_room.md': `# Control Room

## Interactions

USE__RESTRAINED + *:
  You strain against the bindings. No use.
`,
    };
    const game = parseGameFiles(files);
    const interaction = game.interactions.find(
      (i) => i.verb === 'USE__RESTRAINED' && i.room === 'Control Room',
    );
    expect(interaction).toBeDefined();
    expect(interaction!.narrative).toBe('You strain against the bindings. No use.');
    expect(interaction!.targetGroups).toEqual([['*']]);
  });

  it('parses sealed fragment blocks', () => {
    const files = {
      'index.md': '# Verbs\nUSE\n',
      'room.md': `# Room
DOOR
+ USE: You step through.
  ::: fragment
  Cold air hits your face.
  - player -> "Outside"
  :::
`,
    };
    const game = parseGameFiles(files);
    const interaction = game.interactions.find(
      (i) => i.verb === 'USE' && i.room === 'Room',
    );
    expect(interaction).toBeDefined();
    expect(interaction!.sealedContent).toBe('Cold air hits your face.');
    expect(interaction!.sealedArrows).toHaveLength(1);
    expect(interaction!.sealedArrows[0].destination).toBe('"Outside"');
  });

  it('parses signal checks inside interactions', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\n',
      'room.md': `# Room
TERMINAL
+ LOOK: A dusty terminal.
  UNLOCKED?
    It glows green.
`,
    };
    const game = parseGameFiles(files);
    const interaction = game.interactions.find(
      (i) => i.verb === 'LOOK' && i.room === 'Room',
    );
    expect(interaction).toBeDefined();
    expect(interaction!.signalChecks).toHaveLength(1);
    expect(interaction!.signalChecks[0].signalNames).toEqual(['UNLOCKED']);
    expect(interaction!.signalChecks[0].narrative).toBe('It glows green.');
  });

  it('parses cue arrows (? -> "Room")', () => {
    const files = {
      'index.md': '# Verbs\nUSE\n',
      'control_room.md': `# Control Room
TERMINAL
+ USE + KEYCARD:
  You slide the keycard.
  - ? -> "Basement"
    A power surge ripples through the basement.
    - COMPARTMENT -> room
`,
    };
    const game = parseGameFiles(files);
    expect(game.cues).toHaveLength(1);
    expect(game.cues[0].targetRoom).toBe('Basement');
    expect(game.cues[0].triggerRoom).toBe('Control Room');
    expect(game.cues[0].narrative).toBe('A power surge ripples through the basement.');
  });

  it('parses multiple rooms from separate files', () => {
    const files = {
      'index.md': '# Verbs\nLOOK\n',
      'basement.md': '# Basement\n',
      'hallway.md': '# Hallway\n',
    };
    const game = parseGameFiles(files);
    expect(game.rooms['Basement']).toBeDefined();
    expect(game.rooms['Hallway']).toBeDefined();
  });

  it('handles comments with //', () => {
    const files = {
      'index.md': `# Verbs
LOOK // this is a comment - should be ignored
USE
`,
    };
    const game = parseGameFiles(files);
    expect(game.verbs['LOOK']).toBeDefined();
    expect(game.verbs['USE']).toBeDefined();
    // "// this is a comment - should be ignored" should not appear as a verb
    expect(Object.keys(game.verbs)).not.toContain('// this is a comment - should be ignored');
  });
});

// ── Round-trip test: serialize → parse → verify ────────────────────────────

describe('round-trip: serialize → parse', () => {
  it('preserves metadata and verbs through a round-trip', () => {
    const game = createGameData();
    game.metadata = { title: 'The Facility', author: 'Test', start: 'Hallway' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');
    game.verbs['TAKE'] = createVerb('TAKE');
    game.rooms['Hallway'] = createRoom('Hallway');

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    expect(parsed.metadata['title']).toBe('The Facility');
    expect(parsed.metadata['author']).toBe('Test');
    expect(parsed.verbs['LOOK']).toBeDefined();
    expect(parsed.verbs['USE']).toBeDefined();
    expect(parsed.verbs['TAKE']).toBeDefined();
    expect(parsed.rooms['Hallway']).toBeDefined();
  });

  it('preserves inventory through a round-trip', () => {
    const game = createGameData();
    game.inventory['KEY'] = createInventoryObject('KEY');
    game.inventory['LANTERN'] = createInventoryObject('LANTERN');
    game.rooms['Hallway'] = createRoom('Hallway');

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    expect(parsed.inventory['KEY']).toBeDefined();
    expect(parsed.inventory['LANTERN']).toBeDefined();
  });

  it('preserves rooms and interactions through a round-trip', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['TAKE'] = createVerb('TAKE');
    game.rooms['Basement'] = createRoom('Basement');

    const lamp = createRoomObject('LAMP', 'Basement');
    game.objects[objectKey('Basement', 'LAMP')] = lamp;

    const lookInteraction = createInteraction('LOOK', 'Basement');
    lookInteraction.targetGroups = [['LAMP']];
    lookInteraction.narrative = 'An old oil lamp.';
    game.interactions.push(lookInteraction);

    const takeInteraction = createInteraction('TAKE', 'Basement');
    takeInteraction.targetGroups = [['LAMP']];
    takeInteraction.narrative = 'You grab the lamp.';
    takeInteraction.arrows.push(createArrow('LAMP', 'player'));
    game.interactions.push(takeInteraction);

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    // Room should be preserved
    expect(parsed.rooms['Basement']).toBeDefined();

    // Object should be preserved
    const lampKey = objectKey('Basement', 'LAMP');
    expect(parsed.objects[lampKey]).toBeDefined();

    // LOOK interaction
    const parsedLook = parsed.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('LAMP')),
    );
    expect(parsedLook).toBeDefined();
    expect(parsedLook!.narrative).toBe('An old oil lamp.');

    // TAKE interaction with arrow
    const parsedTake = parsed.interactions.find(
      (i) =>
        i.verb === 'TAKE' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('LAMP')),
    );
    expect(parsedTake).toBeDefined();
    expect(parsedTake!.narrative).toBe('You grab the lamp.');
    expect(parsedTake!.arrows).toHaveLength(1);
    expect(parsedTake!.arrows[0].subject).toBe('LAMP');
    expect(parsedTake!.arrows[0].destination).toBe('player');
  });

  it('preserves room LOOK description through a round-trip', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Hallway'] = createRoom('Hallway');

    const roomLook = createInteraction('LOOK', 'Hallway');
    roomLook.targetGroups = [];
    roomLook.narrative = 'A dimly lit hallway.';
    game.interactions.push(roomLook);

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    const parsedLook = parsed.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Hallway' &&
        i.targetGroups.length === 0,
    );
    expect(parsedLook).toBeDefined();
    expect(parsedLook!.narrative).toBe('A dimly lit hallway.');
  });

  it('preserves actions through a round-trip', () => {
    const game = createGameData();
    game.rooms['Hallway'] = createRoom('Hallway');

    const action = createAction('GO_NORTH', 'Hallway');
    action.narrative = 'You head north.';
    action.arrows.push(createArrow('player', '"Control Room"'));
    game.actions[actionKey('Hallway', 'GO_NORTH')] = action;

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    const key = actionKey('Hallway', 'GO_NORTH');
    expect(parsed.actions[key]).toBeDefined();
    expect(parsed.actions[key].narrative).toBe('You head north.');
    expect(parsed.actions[key].arrows).toHaveLength(1);
    expect(parsed.actions[key].arrows[0].destination).toBe('"Control Room"');
  });

  it('preserves signal checks inside interactions through a round-trip', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Room'] = createRoom('Room');

    const obj = createRoomObject('TERMINAL', 'Room');
    game.objects[objectKey('Room', 'TERMINAL')] = obj;

    const interaction = createInteraction('LOOK', 'Room');
    interaction.targetGroups = [['TERMINAL']];
    interaction.narrative = 'A dusty terminal.';
    const check = createSignalCheck();
    check.signalNames = ['UNLOCKED'];
    check.narrative = 'It glows green.';
    interaction.signalChecks.push(check);
    game.interactions.push(interaction);

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    const parsedInteraction = parsed.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Room' &&
        i.targetGroups.some((g) => g.includes('TERMINAL')),
    );
    expect(parsedInteraction).toBeDefined();
    expect(parsedInteraction!.signalChecks).toHaveLength(1);
    expect(parsedInteraction!.signalChecks[0].signalNames).toEqual(['UNLOCKED']);
    expect(parsedInteraction!.signalChecks[0].narrative).toBe('It glows green.');
  });

  it('preserves sealed content through a round-trip', () => {
    const game = createGameData();
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Room'] = createRoom('Room');

    const obj = createRoomObject('DOOR', 'Room');
    game.objects[objectKey('Room', 'DOOR')] = obj;

    const interaction = createInteraction('USE', 'Room');
    interaction.targetGroups = [['DOOR']];
    interaction.narrative = 'You step through.';
    interaction.sealedContent = 'Cold air hits your face.';
    interaction.sealedArrows.push(createArrow('player', '"Outside"'));
    game.interactions.push(interaction);

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    const parsedInteraction = parsed.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Room' &&
        i.targetGroups.some((g) => g.includes('DOOR')),
    );
    expect(parsedInteraction).toBeDefined();
    expect(parsedInteraction!.sealedContent).toBe('Cold air hits your face.');
    expect(parsedInteraction!.sealedArrows).toHaveLength(1);
    expect(parsedInteraction!.sealedArrows[0].destination).toBe('"Outside"');
  });

  it('preserves freeform interactions through a round-trip', () => {
    const game = createGameData();
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Control Room'] = createRoom('Control Room');

    const wildcardInteraction = createInteraction('USE__RESTRAINED', 'Control Room');
    wildcardInteraction.targetGroups = [['*']];
    wildcardInteraction.narrative = 'You strain against the bindings.';
    game.interactions.push(wildcardInteraction);

    const files = serializeGame(game);
    const parsed = parseGameFiles(files);

    const parsedInteraction = parsed.interactions.find(
      (i) => i.verb === 'USE__RESTRAINED' && i.room === 'Control Room',
    );
    expect(parsedInteraction).toBeDefined();
    expect(parsedInteraction!.narrative).toBe('You strain against the bindings.');
    expect(parsedInteraction!.targetGroups).toEqual([['*']]);
  });
});

// ── Parsing the example game ───────────────────────────────────────────────

describe('parseGameFiles — example game structure', () => {
  const exampleIndex = `---
title: The Facility
author: Addventure Example
start: Control Room
---

You wake up bound to a chair. Your wrists burn against coarse rope.

# Verbs
USE
TAKE
LOOK

# Inventory
`;

  const exampleControlRoom = `# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  - TERMINAL -> TERMINAL__UNLOCKED
  - KEYCARD -> trash
  - -> OVERRIDE

## Interactions

USE__RESTRAINED + *:
  You strain against the bindings. No use.
`;

  it('parses the example index', () => {
    const files = { 'index.md': exampleIndex };
    const game = parseGameFiles(files);
    expect(game.metadata['title']).toBe('The Facility');
    expect(game.verbs['USE']).toBeDefined();
    expect(game.verbs['TAKE']).toBeDefined();
    expect(game.verbs['LOOK']).toBeDefined();
    expect(game.metadata['description']).toContain('You wake up bound');
  });

  it('parses the example control room', () => {
    const files = {
      'index.md': exampleIndex,
      'control_room.md': exampleControlRoom,
    };
    const game = parseGameFiles(files);

    expect(game.rooms['Control Room']).toBeDefined();

    const terminalKey = objectKey('Control Room', 'TERMINAL');
    expect(game.objects[terminalKey]).toBeDefined();

    // Check LOOK interaction on TERMINAL
    const terminalLook = game.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('TERMINAL')),
    );
    expect(terminalLook).toBeDefined();

    // Check freeform USE__RESTRAINED + *
    const wildcardInteraction = game.interactions.find(
      (i) =>
        i.verb === 'USE__RESTRAINED' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('*')),
    );
    expect(wildcardInteraction).toBeDefined();
    expect(wildcardInteraction!.narrative).toBe('You strain against the bindings. No use.');
  });
});

import { describe, it, expect } from 'vitest';
import {
  serializeGame,
  serializeIndex,
  serializeRoom,
  serializeArrow,
  serializeInteraction,
  serializeSignalCheck,
} from '../src/lib/serializer';
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
import type { GameData } from '../src/lib/types';

// ---- serializeArrow ----

describe('serializeArrow', () => {
  it('serializes an arrow with subject', () => {
    const arrow = createArrow('KEY', 'player');
    expect(serializeArrow(arrow)).toBe('KEY -> player');
  });

  it('serializes an arrow with empty subject', () => {
    const arrow = createArrow('', 'OVERRIDE');
    expect(serializeArrow(arrow)).toBe('-> OVERRIDE');
  });

  it('serializes a player move arrow', () => {
    const arrow = createArrow('player', '"Basement"');
    expect(serializeArrow(arrow)).toBe('player -> "Basement"');
  });

  it('serializes a trash arrow', () => {
    const arrow = createArrow('LAMP', 'trash');
    expect(serializeArrow(arrow)).toBe('LAMP -> trash');
  });

  it('serializes a signal arrow', () => {
    const arrow = createArrow('ESCAPED', 'signal');
    expect(serializeArrow(arrow)).toBe('ESCAPED -> signal');
  });

  it('serializes a cue arrow', () => {
    const arrow = createArrow('?', '"Basement"');
    expect(serializeArrow(arrow)).toBe('? -> "Basement"');
  });
});

// ---- serializeSignalCheck ----

describe('serializeSignalCheck', () => {
  it('serializes a single-signal check', () => {
    const check = createSignalCheck();
    check.signalNames = ['LAMP_LIT'];
    check.narrative = 'The lamp glows.';
    const lines = serializeSignalCheck(check, '');
    expect(lines).toEqual(['LAMP_LIT?', '  The lamp glows.']);
  });

  it('serializes a multi-signal check', () => {
    const check = createSignalCheck();
    check.signalNames = ['LAMP_LIT', 'DOOR_OPEN'];
    check.narrative = 'Both active.';
    const lines = serializeSignalCheck(check, '');
    expect(lines).toEqual(['LAMP_LIT + DOOR_OPEN?', '  Both active.']);
  });

  it('serializes an otherwise check (no signal names)', () => {
    const check = createSignalCheck();
    check.narrative = 'Nothing happened.';
    const lines = serializeSignalCheck(check, '');
    expect(lines).toEqual(['otherwise?', '  Nothing happened.']);
  });

  it('serializes a check with arrows', () => {
    const check = createSignalCheck();
    check.signalNames = ['KEY_FOUND'];
    check.narrative = '';
    check.arrows.push(createArrow('DOOR', 'DOOR__OPEN'));
    const lines = serializeSignalCheck(check, '');
    expect(lines).toEqual(['KEY_FOUND?', '  - DOOR -> DOOR__OPEN']);
  });

  it('respects indentation', () => {
    const check = createSignalCheck();
    check.signalNames = ['FLAG'];
    check.narrative = 'Triggered.';
    const lines = serializeSignalCheck(check, '  ');
    expect(lines).toEqual(['  FLAG?', '    Triggered.']);
  });
});

// ---- serializeInteraction ----

describe('serializeInteraction', () => {
  it('serializes a simple interaction with inline narrative', () => {
    const interaction = createInteraction('LOOK', 'Basement');
    interaction.targetGroups = [['LAMP']];
    interaction.narrative = 'A dusty lamp.';
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + LOOK + LAMP: A dusty lamp.']);
  });

  it('serializes an interaction with empty narrative', () => {
    const interaction = createInteraction('USE', 'Basement');
    interaction.targetGroups = [['DOOR']];
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + USE + DOOR:']);
  });

  it('serializes an interaction with multiline narrative', () => {
    const interaction = createInteraction('USE', 'Basement');
    interaction.targetGroups = [['DOOR']];
    interaction.narrative = 'You push.\nIt moves.';
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + USE + DOOR:', '    You push.', '    It moves.']);
  });

  it('serializes an interaction with arrows', () => {
    const interaction = createInteraction('TAKE', 'Basement');
    interaction.targetGroups = [['KEY']];
    interaction.narrative = 'You grab the key.';
    interaction.arrows.push(createArrow('KEY', 'player'));
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual([
      '  + TAKE + KEY: You grab the key.',
      '    - KEY -> player',
    ]);
  });

  it('serializes an interaction with no target groups (LOOK description-style)', () => {
    const interaction = createInteraction('LOOK', 'Hallway');
    interaction.narrative = 'A long corridor.';
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + LOOK: A long corridor.']);
  });

  it('serializes an interaction with multiple target groups', () => {
    const interaction = createInteraction('USE', 'Basement');
    interaction.targetGroups = [['FUSE'], ['FUSE_BOX']];
    interaction.narrative = 'You slot it in.';
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + USE + FUSE + FUSE_BOX: You slot it in.']);
  });

  it('serializes an interaction with alternation in target group', () => {
    const interaction = createInteraction('USE', 'Basement');
    interaction.targetGroups = [['KEYCARD', 'BADGE']];
    interaction.narrative = 'Access granted.';
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual(['  + USE + KEYCARD | BADGE: Access granted.']);
  });

  it('serializes an interaction with sealed content', () => {
    const interaction = createInteraction('USE', 'Cell Block');
    interaction.targetGroups = [['EXIT_DOOR']];
    interaction.narrative = 'You step out.';
    interaction.sealedContent = 'Cold air hits your face.';
    interaction.sealedArrows.push(createArrow('player', '"Epilogue"'));
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual([
      '  + USE + EXIT_DOOR: You step out.',
      '    ::: fragment',
      '    Cold air hits your face.',
      '    - player -> "Epilogue"',
      '    :::',
    ]);
  });

  it('serializes an interaction with indentation', () => {
    const interaction = createInteraction('LOOK', 'Basement');
    interaction.targetGroups = [['LAMP']];
    interaction.narrative = 'A dusty lamp.';
    const lines = serializeInteraction(interaction, '  ');
    expect(lines).toEqual(['    + LOOK + LAMP: A dusty lamp.']);
  });

  it('serializes an interaction with signal checks', () => {
    const interaction = createInteraction('LOOK', 'Basement');
    interaction.targetGroups = [['TERMINAL']];
    interaction.narrative = 'A terminal.';
    const check = createSignalCheck();
    check.signalNames = ['UNLOCKED'];
    check.narrative = 'It is unlocked.';
    interaction.signalChecks.push(check);
    const lines = serializeInteraction(interaction, '');
    expect(lines).toEqual([
      '  + LOOK + TERMINAL: A terminal.',
      '    UNLOCKED?',
      '      It is unlocked.',
    ]);
  });
});

// ---- serializeIndex ----

describe('serializeIndex', () => {
  it('produces frontmatter from metadata', () => {
    const game = createGameData();
    game.metadata = { title: 'The Facility', author: 'Test Author', start: 'Control Room' };
    game.verbs['LOOK'] = createVerb('LOOK');
    const output = serializeIndex(game);
    expect(output).toContain('---');
    expect(output).toContain('title: The Facility');
    expect(output).toContain('author: Test Author');
    expect(output).toContain('start: Control Room');
  });

  it('includes verbs section with base verbs only', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');
    game.verbs['USE__RESTRAINED'] = createVerb('USE__RESTRAINED'); // state verb, should be skipped
    const output = serializeIndex(game);
    expect(output).toContain('# Verbs\nLOOK\nUSE');
    expect(output).not.toContain('USE__RESTRAINED');
  });

  it('includes inventory section', () => {
    const game = createGameData();
    game.inventory['KEY'] = createInventoryObject('KEY');
    game.inventory['LANTERN'] = createInventoryObject('LANTERN');
    const output = serializeIndex(game);
    expect(output).toContain('# Inventory\nKEY\nLANTERN');
  });

  it('omits description key from frontmatter and puts it as paragraph', () => {
    const game = createGameData();
    game.metadata = {
      title: 'Test',
      description: 'A long description.\n\nSecond paragraph.',
    };
    game.verbs['LOOK'] = createVerb('LOOK');
    const output = serializeIndex(game);
    expect(output).not.toContain('description: A long description');
    expect(output).toContain('A long description.\n\nSecond paragraph.');
  });

  it('includes index-level signal checks', () => {
    const game = createGameData();
    const check = createSignalCheck();
    check.signalNames = ['INTRO_DONE'];
    check.narrative = 'The game begins.';
    game.signalChecks.push(check);
    const output = serializeIndex(game);
    expect(output).toContain('INTRO_DONE?');
    expect(output).toContain('  The game begins.');
  });

  it('produces index.md with no frontmatter when metadata is empty', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    const output = serializeIndex(game);
    expect(output).not.toContain('---');
    expect(output).toContain('# Verbs');
  });
});

// ---- serializeRoom ----

describe('serializeRoom', () => {
  function makeSimpleRoom(): GameData {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');
    game.verbs['TAKE'] = createVerb('TAKE');

    game.rooms['Basement'] = createRoom('Basement');

    const lamp = createRoomObject('LAMP', 'Basement');
    game.objects[objectKey('Basement', 'LAMP')] = lamp;

    // LOOK for the room itself
    const roomLook = createInteraction('LOOK', 'Basement');
    roomLook.targetGroups = [];
    roomLook.narrative = 'Damp walls. A lamp sits on a shelf.';
    game.interactions.push(roomLook);

    // LOOK for the lamp
    const lampLook = createInteraction('LOOK', 'Basement');
    lampLook.targetGroups = [['LAMP']];
    lampLook.narrative = 'An old oil lamp.';
    game.interactions.push(lampLook);

    // TAKE for the lamp
    const lampTake = createInteraction('TAKE', 'Basement');
    lampTake.targetGroups = [['LAMP']];
    lampTake.narrative = 'You grab the lamp.';
    lampTake.arrows.push(createArrow('LAMP', 'player'));
    game.interactions.push(lampTake);

    return game;
  }

  it('starts with room header', () => {
    const game = makeSimpleRoom();
    const output = serializeRoom(game, 'Basement');
    expect(output).toMatch(/^# Basement/);
  });

  it('includes LOOK description for the room', () => {
    const game = makeSimpleRoom();
    const output = serializeRoom(game, 'Basement');
    expect(output).toContain('LOOK: Damp walls. A lamp sits on a shelf.');
  });

  it('includes room objects with their interactions', () => {
    const game = makeSimpleRoom();
    const output = serializeRoom(game, 'Basement');
    expect(output).toContain('LAMP');
    expect(output).toContain('  + LOOK: An old oil lamp.');
    expect(output).toContain('  + TAKE: You grab the lamp.');
    expect(output).toContain('    - LAMP -> player');
  });

  it('produces correct output for a room with a move arrow', () => {
    const game = createGameData();
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Hallway'] = createRoom('Hallway');

    const door = createRoomObject('DOOR', 'Hallway');
    game.objects[objectKey('Hallway', 'DOOR')] = door;

    const useInteraction = createInteraction('USE', 'Hallway');
    useInteraction.targetGroups = [['DOOR']];
    useInteraction.narrative = 'You walk through.';
    useInteraction.arrows.push(createArrow('player', '"Basement"'));
    game.interactions.push(useInteraction);

    const output = serializeRoom(game, 'Hallway');
    expect(output).toContain('  + USE: You walk through.');
    expect(output).toContain('    - player -> "Basement"');
  });

  it('serializes freeform interactions in ## Interactions section', () => {
    const game = createGameData();
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Control Room'] = createRoom('Control Room');

    // Freeform interaction: targets a wildcard
    const wildcardInteraction = createInteraction('USE__RESTRAINED', 'Control Room');
    wildcardInteraction.targetGroups = [['*']];
    wildcardInteraction.narrative = 'You strain against the bindings.';
    game.interactions.push(wildcardInteraction);

    const output = serializeRoom(game, 'Control Room');
    expect(output).toContain('## Interactions');
    expect(output).toContain('USE__RESTRAINED + *: You strain against the bindings.');
  });

  it('serializes actions in the room', () => {
    const game = createGameData();
    game.rooms['Hallway'] = createRoom('Hallway');

    const action = createAction('GO_NORTH', 'Hallway');
    action.narrative = 'You head north.';
    action.arrows.push(createArrow('player', '"Control Room"'));
    game.actions[actionKey('Hallway', 'GO_NORTH')] = action;

    const output = serializeRoom(game, 'Hallway');
    expect(output).toContain('> GO_NORTH');
    expect(output).toContain('  You head north.');
    expect(output).toContain('  - player -> "Control Room"');
  });

  it('does not include interactions from other rooms', () => {
    const game = makeSimpleRoom();

    game.rooms['Hallway'] = createRoom('Hallway');
    const hallwayLook = createInteraction('LOOK', 'Hallway');
    hallwayLook.narrative = 'A long corridor.';
    game.interactions.push(hallwayLook);

    const output = serializeRoom(game, 'Basement');
    expect(output).not.toContain('A long corridor.');
  });
});

// ---- serializeGame ----

describe('serializeGame', () => {
  it('produces index.md and room files', () => {
    const game = createGameData();
    game.metadata = { title: 'Test Game', start: 'Hallway' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Hallway'] = createRoom('Hallway');
    game.rooms['Control Room'] = createRoom('Control Room');
    game.rooms['Basement__FLOODED'] = createRoom('Basement__FLOODED'); // state variant — skip

    const result = serializeGame(game);

    expect(Object.keys(result)).toContain('index.md');
    expect(Object.keys(result)).toContain('hallway.md');
    expect(Object.keys(result)).toContain('control_room.md');
    expect(Object.keys(result)).not.toContain('basement__flooded.md');
  });

  it('index.md contains frontmatter and verbs', () => {
    const game = createGameData();
    game.metadata = { title: 'Test Game', start: 'Hallway' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Hallway'] = createRoom('Hallway');

    const result = serializeGame(game);
    const index = result['index.md'];

    expect(index).toContain('title: Test Game');
    expect(index).toContain('# Verbs');
    expect(index).toContain('LOOK');
    expect(index).toContain('USE');
  });

  it('room files contain room content', () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Hallway'] = createRoom('Hallway');

    const roomLook = createInteraction('LOOK', 'Hallway');
    roomLook.targetGroups = [];
    roomLook.narrative = 'A dimly lit hallway.';
    game.interactions.push(roomLook);

    const result = serializeGame(game);
    expect(result['hallway.md']).toContain('# Hallway');
    expect(result['hallway.md']).toContain('LOOK: A dimly lit hallway.');
  });

  it('handles room names with spaces for filenames', () => {
    const game = createGameData();
    game.rooms['Control Room'] = createRoom('Control Room');
    game.rooms['Cell Block'] = createRoom('Cell Block');

    const result = serializeGame(game);
    expect(Object.keys(result)).toContain('control_room.md');
    expect(Object.keys(result)).toContain('cell_block.md');
  });
});

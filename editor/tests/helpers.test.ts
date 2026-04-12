import { describe, it, expect } from 'vitest';
import {
  displayName,
  getSignalEmissions,
  getSignalConsumers,
  classifyArrow,
  arrowLabel,
  getRoomExits,
  getRoomObjects,
  getRoomInteractions,
  getObjectInteractions,
} from '../src/lib/helpers';
import {
  createGameData,
  createArrow,
  createInteraction,
  createRoomObject,
  createRoom,
  createAction,
  actionKey,
  objectKey,
} from '../src/lib/factory';

// ---- displayName ----

describe('displayName', () => {
  it('upper_words (default): keeps uppercase, replaces underscores with spaces', () => {
    expect(displayName('STEEL_DOOR')).toBe('STEEL DOOR');
  });

  it('upper_words: strips state suffix', () => {
    expect(displayName('STEEL_DOOR__OPEN')).toBe('STEEL DOOR');
  });

  it('upper_words: single word stays uppercase', () => {
    expect(displayName('LAMP')).toBe('LAMP');
  });

  it('title: converts to title case', () => {
    expect(displayName('STEEL_DOOR', 'title')).toBe('Steel Door');
  });

  it('title: strips state suffix', () => {
    expect(displayName('STEEL_DOOR__OPEN', 'title')).toBe('Steel Door');
  });

  it('title: single word', () => {
    expect(displayName('LAMP', 'title')).toBe('Lamp');
  });
});

// ---- getSignalEmissions ----

describe('getSignalEmissions', () => {
  it('returns empty array when no signals are emitted', () => {
    const game = createGameData();
    const interaction = createInteraction('TAKE', 'Basement');
    interaction.arrows.push(createArrow('LAMP', 'player'));
    game.interactions.push(interaction);
    expect(getSignalEmissions(game)).toEqual([]);
  });

  it('finds signals from interaction arrows', () => {
    const game = createGameData();
    const interaction = createInteraction('USE', 'Control Room');
    interaction.arrows.push(createArrow('POWER_ON', 'signal'));
    game.interactions.push(interaction);
    const signals = getSignalEmissions(game);
    expect(signals).toContain('POWER_ON');
    expect(signals).toHaveLength(1);
  });

  it('finds signals from sealed arrows', () => {
    const game = createGameData();
    const interaction = createInteraction('READ', 'Library');
    interaction.sealedArrows.push(createArrow('SECRET_FOUND', 'signal'));
    game.interactions.push(interaction);
    expect(getSignalEmissions(game)).toContain('SECRET_FOUND');
  });

  it('deduplicates signals emitted in multiple places', () => {
    const game = createGameData();
    const i1 = createInteraction('USE', 'Room A');
    const i2 = createInteraction('EXAMINE', 'Room B');
    i1.arrows.push(createArrow('POWER_ON', 'signal'));
    i2.arrows.push(createArrow('POWER_ON', 'signal'));
    game.interactions.push(i1, i2);
    const signals = getSignalEmissions(game);
    expect(signals.filter((s) => s === 'POWER_ON')).toHaveLength(1);
  });
});

// ---- classifyArrow ----

describe('classifyArrow', () => {
  it('classifies destroy arrow (→ trash)', () => {
    expect(classifyArrow(createArrow('CROWBAR', 'trash'))).toBe('destroy');
  });

  it('classifies pickup arrow (→ player)', () => {
    expect(classifyArrow(createArrow('CROWBAR', 'player'))).toBe('pickup');
  });

  it('classifies move arrow (player →)', () => {
    expect(classifyArrow(createArrow('player', 'Basement'))).toBe('move');
  });

  it('classifies signal arrow (→ signal)', () => {
    expect(classifyArrow(createArrow('POWER_ON', 'signal'))).toBe('signal');
  });

  it('classifies cue arrow (? →)', () => {
    expect(classifyArrow(createArrow('?', 'Basement'))).toBe('cue');
  });

  it('classifies reveal arrow (subject → room)', () => {
    expect(classifyArrow(createArrow('KEY', 'room'))).toBe('reveal');
  });

  it('classifies transform arrow (subject has __)', () => {
    expect(classifyArrow(createArrow('DOOR__CLOSED', 'DOOR__OPEN'))).toBe(
      'transform',
    );
  });

  it('classifies reveal_verb arrow (empty subject, uppercase dest)', () => {
    expect(classifyArrow(createArrow('', 'OVERRIDE'))).toBe('reveal_verb');
  });

  it('classifies room_state arrow (room →)', () => {
    expect(classifyArrow(createArrow('room', 'room__FLOODED'))).toBe(
      'room_state',
    );
  });

  it('classifies verb_restore arrow (VERB__STATE → VERB)', () => {
    expect(classifyArrow(createArrow('USE__RESTRAINED', 'USE'))).toBe(
      'verb_restore',
    );
  });
});

// ---- arrowLabel ----

describe('arrowLabel', () => {
  it('labels a destroy arrow (upper_words default)', () => {
    expect(arrowLabel(createArrow('CROWBAR', 'trash'))).toBe('× CROWBAR');
  });

  it('labels a pickup arrow (upper_words)', () => {
    expect(arrowLabel(createArrow('CROWBAR', 'player'))).toBe(
      '↑ CROWBAR → inventory',
    );
  });

  it('labels a move arrow', () => {
    expect(arrowLabel(createArrow('player', 'Basement'))).toBe('→ Basement');
  });

  it('labels a signal arrow', () => {
    expect(arrowLabel(createArrow('ESCAPE', 'signal'))).toBe('⚡ ESCAPE');
  });

  it('labels a cue arrow', () => {
    expect(arrowLabel(createArrow('?', 'Basement'))).toBe('? → Basement');
  });

  it('labels a transform arrow (upper_words)', () => {
    expect(arrowLabel(createArrow('DOOR__CLOSED', 'DOOR__OPEN'))).toBe(
      'DOOR → DOOR OPEN',
    );
  });

  it('labels a transform arrow (title style)', () => {
    expect(arrowLabel(createArrow('DOOR__CLOSED', 'DOOR__OPEN'), 'title')).toBe(
      'Door → Door Open',
    );
  });

  it('labels a reveal_verb arrow', () => {
    expect(arrowLabel(createArrow('', 'OVERRIDE'))).toBe('+ OVERRIDE');
  });
});

// ---- getRoomExits ----

describe('getRoomExits', () => {
  it('finds exits from player arrows in interactions', () => {
    const game = createGameData();
    const interaction = createInteraction('GO_NORTH', 'Hallway');
    interaction.arrows.push(createArrow('player', 'Basement'));
    game.interactions.push(interaction);

    const exits = getRoomExits(game, 'Hallway');
    expect(exits).toHaveLength(1);
    expect(exits[0].targetRoom).toBe('Basement');
    expect(exits[0].via).toBe('GO_NORTH');
  });

  it('returns empty array when room has no exits', () => {
    const game = createGameData();
    const interaction = createInteraction('EXAMINE', 'Basement');
    interaction.arrows.push(createArrow('LAMP', 'player'));
    game.interactions.push(interaction);

    expect(getRoomExits(game, 'Basement')).toEqual([]);
  });

  it('does not include player→player arrows as exits', () => {
    const game = createGameData();
    const interaction = createInteraction('TAKE', 'Basement');
    interaction.arrows.push(createArrow('player', 'player'));
    game.interactions.push(interaction);

    expect(getRoomExits(game, 'Basement')).toEqual([]);
  });
});

// ---- getRoomObjects ----

describe('getRoomObjects', () => {
  it('groups objects by base name', () => {
    const game = createGameData();
    game.objects[objectKey('Basement', 'LAMP')] = createRoomObject(
      'LAMP',
      'Basement',
    );
    game.objects[objectKey('Basement', 'LAMP__LIT')] = createRoomObject(
      'LAMP__LIT',
      'Basement',
    );
    game.objects[objectKey('Basement', 'KEY')] = createRoomObject(
      'KEY',
      'Basement',
    );

    const result = getRoomObjects(game, 'Basement');
    expect(result['LAMP']).toContain('LAMP');
    expect(result['LAMP']).toContain('LAMP__LIT');
    expect(result['KEY']).toEqual(['KEY']);
  });

  it('excludes objects from other rooms', () => {
    const game = createGameData();
    game.objects[objectKey('Hallway', 'KEY')] = createRoomObject(
      'KEY',
      'Hallway',
    );

    const result = getRoomObjects(game, 'Basement');
    expect(result).toEqual({});
  });
});

// ---- getRoomInteractions ----

describe('getRoomInteractions', () => {
  it('returns only interactions for the specified room', () => {
    const game = createGameData();
    const i1 = createInteraction('TAKE', 'Basement');
    const i2 = createInteraction('EXAMINE', 'Hallway');
    const i3 = createInteraction('USE', 'Basement');
    game.interactions.push(i1, i2, i3);

    const result = getRoomInteractions(game, 'Basement');
    expect(result).toHaveLength(2);
    expect(result.every((i) => i.room === 'Basement')).toBe(true);
  });
});

// ---- getObjectInteractions ----

describe('getObjectInteractions', () => {
  it('returns interactions targeting the specified object', () => {
    const game = createGameData();
    const i1 = createInteraction('TAKE', 'Basement');
    i1.targetGroups = [['LAMP']];
    const i2 = createInteraction('EXAMINE', 'Basement');
    i2.targetGroups = [['KEY']];
    const i3 = createInteraction('USE', 'Basement');
    i3.targetGroups = [['LAMP']];
    game.interactions.push(i1, i2, i3);

    const result = getObjectInteractions(game, 'Basement', 'LAMP');
    expect(result).toHaveLength(2);
    expect(result.map((i) => i.verb)).toEqual(['TAKE', 'USE']);
  });
});

// ---- getSignalConsumers ----

describe('getSignalConsumers', () => {
  it('returns record of signal consumers from interaction signal checks', () => {
    const game = createGameData();
    const interaction = createInteraction('EXAMINE', 'Basement');
    const check = {
      signalNames: ['POWER_ON'],
      narrative: 'The lights flicker.',
      arrows: [],
    };
    interaction.signalChecks.push(check);
    game.interactions.push(interaction);

    const consumers = getSignalConsumers(game);
    expect(consumers['POWER_ON']).toBeDefined();
    expect(consumers['POWER_ON'][0].room).toBe('Basement');
  });

  it('returns empty record when no signal checks exist', () => {
    const game = createGameData();
    expect(getSignalConsumers(game)).toEqual({});
  });
});

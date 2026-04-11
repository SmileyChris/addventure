import { describe, it, expect } from 'vitest';
import {
  createGameData,
  createGameProject,
  createRoom,
  createRoomObject,
  createArrow,
  objectKey,
  createVerb,
  createInventoryObject,
  createInteraction,
  createCue,
  createAction,
  createSignalCheck,
} from '../src/lib/factory';

describe('createGameData', () => {
  it('returns empty structure with all required fields', () => {
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
  it('sets name and generates a non-empty id', () => {
    const project = createGameProject('My Adventure');
    expect(project.name).toBe('My Adventure');
    expect(project.id).toBeTruthy();
    expect(typeof project.id).toBe('string');
  });

  it('generates unique IDs for different projects', () => {
    const a = createGameProject('Game A');
    const b = createGameProject('Game B');
    expect(a.id).not.toBe(b.id);
  });

  it('sets lastModified to a recent timestamp', () => {
    const before = Date.now();
    const project = createGameProject('Test');
    const after = Date.now();
    expect(project.lastModified).toBeGreaterThanOrEqual(before);
    expect(project.lastModified).toBeLessThanOrEqual(after);
  });

  it('initializes with empty game data', () => {
    const project = createGameProject('Test');
    expect(project.game.interactions).toEqual([]);
    expect(project.game.rooms).toEqual({});
  });
});

describe('createRoom', () => {
  it('parses a base room with no state', () => {
    const room = createRoom('Basement');
    expect(room.name).toBe('Basement');
    expect(room.base).toBe('Basement');
    expect(room.state).toBeNull();
  });

  it('parses a stated room using double underscore', () => {
    const room = createRoom('Basement__FLOODED');
    expect(room.name).toBe('Basement__FLOODED');
    expect(room.base).toBe('Basement');
    expect(room.state).toBe('FLOODED');
  });

  it('handles multiple underscores correctly (splits on first __)', () => {
    const room = createRoom('Control_Room__LOCKED');
    expect(room.base).toBe('Control_Room');
    expect(room.state).toBe('LOCKED');
  });
});

describe('createRoomObject', () => {
  it('parses a base object with no state', () => {
    const obj = createRoomObject('LAMP', 'Basement');
    expect(obj.name).toBe('LAMP');
    expect(obj.base).toBe('LAMP');
    expect(obj.state).toBeNull();
    expect(obj.room).toBe('Basement');
    expect(obj.discovered).toBe(false);
  });

  it('parses a stated object using double underscore', () => {
    const obj = createRoomObject('LAMP__LIT', 'Basement');
    expect(obj.base).toBe('LAMP');
    expect(obj.state).toBe('LIT');
  });

  it('respects the discovered flag when true', () => {
    const obj = createRoomObject('KEY', 'Hallway', true);
    expect(obj.discovered).toBe(true);
  });

  it('defaults discovered to false', () => {
    const obj = createRoomObject('KEY', 'Hallway');
    expect(obj.discovered).toBe(false);
  });
});

describe('createArrow', () => {
  it('sets signalName to null for non-signal destinations', () => {
    const arrow = createArrow('LAMP', 'player');
    expect(arrow.subject).toBe('LAMP');
    expect(arrow.destination).toBe('player');
    expect(arrow.signalName).toBeNull();
  });

  it('sets signalName to subject when destination is "signal"', () => {
    const arrow = createArrow('LAMP_LIT', 'signal');
    expect(arrow.signalName).toBe('LAMP_LIT');
    expect(arrow.destination).toBe('signal');
  });

  it('sets signalName to null for trash destination', () => {
    const arrow = createArrow('LAMP', 'trash');
    expect(arrow.signalName).toBeNull();
  });
});

describe('objectKey', () => {
  it('creates a composite key as room::name', () => {
    expect(objectKey('Basement', 'LAMP')).toBe('Basement::LAMP');
  });

  it('works with room and object names containing special characters', () => {
    expect(objectKey('Control Room', 'LEVER__PULLED')).toBe(
      'Control Room::LEVER__PULLED',
    );
  });
});

describe('createVerb', () => {
  it('creates a verb with the given name', () => {
    const verb = createVerb('TAKE');
    expect(verb.name).toBe('TAKE');
  });
});

describe('createInventoryObject', () => {
  it('creates an inventory object with the given name', () => {
    const obj = createInventoryObject('LANTERN');
    expect(obj.name).toBe('LANTERN');
  });
});

describe('createInteraction', () => {
  it('creates an interaction with defaults', () => {
    const interaction = createInteraction('TAKE', 'Basement');
    expect(interaction.verb).toBe('TAKE');
    expect(interaction.room).toBe('Basement');
    expect(interaction.targetGroups).toEqual([]);
    expect(interaction.narrative).toBe('');
    expect(interaction.arrows).toEqual([]);
    expect(interaction.sealedContent).toBeNull();
    expect(interaction.sealedArrows).toEqual([]);
    expect(interaction.signalChecks).toEqual([]);
  });
});

describe('createCue', () => {
  it('creates a cue with correct rooms', () => {
    const cue = createCue('Hallway', 'Basement');
    expect(cue.triggerRoom).toBe('Hallway');
    expect(cue.targetRoom).toBe('Basement');
    expect(cue.narrative).toBe('');
    expect(cue.arrows).toEqual([]);
  });
});

describe('createAction', () => {
  it('creates an action with defaults', () => {
    const action = createAction('GO_NORTH', 'Hallway');
    expect(action.name).toBe('GO_NORTH');
    expect(action.room).toBe('Hallway');
    expect(action.narrative).toBe('');
    expect(action.arrows).toEqual([]);
    expect(action.discovered).toBe(false);
  });
});

describe('createSignalCheck', () => {
  it('creates a signal check with empty defaults', () => {
    const check = createSignalCheck();
    expect(check.signalNames).toEqual([]);
    expect(check.narrative).toBe('');
    expect(check.arrows).toEqual([]);
  });
});

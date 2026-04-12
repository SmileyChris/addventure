import { describe, it, expect, beforeEach } from 'vitest';
import { autoCreateFromArrows } from '../src/lib/autocreate';
import {
  createGameData,
  createInteraction,
  createArrow,
  createCue,
  createAction,
  createRoomObject,
  createInventoryObject,
  createRoom,
  createSignalCheck,
  objectKey,
} from '../src/lib/factory';
import type { GameData } from '../src/lib/types';

function makeGame(): GameData {
  return createGameData();
}

function addRoom(game: GameData, name: string) {
  game.rooms[name] = createRoom(name);
}

function addInteractionWithArrow(
  game: GameData,
  verb: string,
  room: string,
  subject: string,
  destination: string,
) {
  const interaction = createInteraction(verb, room);
  interaction.arrows.push(createArrow(subject, destination));
  game.interactions.push(interaction);
}

describe('autoCreateFromArrows', () => {
  let game: GameData;

  beforeEach(() => {
    game = makeGame();
    addRoom(game, 'Basement');
  });

  // Rule 1: Object state transforms
  it('creates a stated RoomObject when THING -> THING__STATE arrow exists', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', 'LAMP', 'LAMP__LIT');

    autoCreateFromArrows(game);

    const key = objectKey('Basement', 'LAMP__LIT');
    expect(game.objects[key]).toBeDefined();
    expect(game.objects[key].name).toBe('LAMP__LIT');
    expect(game.objects[key].room).toBe('Basement');
    expect(game.objects[key].discovered).toBe(false);
  });

  // Rule 2: Auto-inventory when TAKE exists
  it('creates inventory item when OBJECT -> player arrow exists and TAKE verb is present', () => {
    // TAKE is in default game verbs
    addInteractionWithArrow(game, 'TAKE', 'Basement', 'KEY', 'player');

    autoCreateFromArrows(game);

    expect(game.inventory['KEY']).toBeDefined();
    expect(game.inventory['KEY'].name).toBe('KEY');
  });

  it('uses base name for inventory when stated object is picked up', () => {
    addInteractionWithArrow(game, 'TAKE', 'Basement', 'KEY__RUSTY', 'player');

    autoCreateFromArrows(game);

    expect(game.inventory['KEY']).toBeDefined();
    expect(game.inventory['KEY__RUSTY']).toBeUndefined();
  });

  // Rule 3: No auto-inventory when TAKE is missing
  it('does NOT create inventory when TAKE verb is missing', () => {
    delete game.verbs['TAKE'];
    addInteractionWithArrow(game, 'USE', 'Basement', 'KEY', 'player');

    autoCreateFromArrows(game);

    expect(game.inventory['KEY']).toBeUndefined();
  });

  // Rule 4: Verb states from interaction verbs
  it('auto-creates verb state when interaction uses VERB__STATE and base VERB exists', () => {
    const interaction = createInteraction('USE__RESTRAINED', 'Basement');
    game.interactions.push(interaction);

    autoCreateFromArrows(game);

    expect(game.verbs['USE__RESTRAINED']).toBeDefined();
    expect(game.verbs['USE__RESTRAINED'].name).toBe('USE__RESTRAINED');
  });

  it('does NOT auto-create verb state when base verb does not exist', () => {
    const interaction = createInteraction('PUNCH__HARD', 'Basement');
    game.interactions.push(interaction);

    autoCreateFromArrows(game);

    expect(game.verbs['PUNCH__HARD']).toBeUndefined();
    expect(game.verbs['PUNCH']).toBeUndefined();
  });

  // Rule 5: Auto-verbs from -> VERBNAME arrows
  it('creates a new verb when arrow has empty subject and uppercase destination', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'OVERRIDE');

    autoCreateFromArrows(game);

    expect(game.verbs['OVERRIDE']).toBeDefined();
    expect(game.verbs['OVERRIDE'].name).toBe('OVERRIDE');
  });

  it('does not create verb for reserved destinations like trash, player, room, signal', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'trash');
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'player');
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'room');
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'signal');

    autoCreateFromArrows(game);

    // trash/player/room/signal should not appear as verbs
    expect(game.verbs['trash']).toBeUndefined();
    expect(game.verbs['player']).toBeUndefined();
    expect(game.verbs['room']).toBeUndefined();
    expect(game.verbs['signal']).toBeUndefined();
  });

  // Rule 6: Discovered objects from OBJECT -> room
  it('creates a discovered RoomObject when OBJECT -> room arrow exists', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', 'HIDDEN_KEY', 'room');

    autoCreateFromArrows(game);

    const key = objectKey('Basement', 'HIDDEN_KEY');
    expect(game.objects[key]).toBeDefined();
    expect(game.objects[key].discovered).toBe(true);
  });

  it('sets discovered=true on existing object when OBJECT -> room arrow exists', () => {
    const key = objectKey('Basement', 'LAMP');
    game.objects[key] = createRoomObject('LAMP', 'Basement', false);
    addInteractionWithArrow(game, 'USE', 'Basement', 'LAMP', 'room');

    autoCreateFromArrows(game);

    expect(game.objects[key].discovered).toBe(true);
  });

  // Rule 7: Rooms from player movement
  it('creates a room when player -> "RoomName" arrow exists', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', 'player', '"Attic"');

    autoCreateFromArrows(game);

    expect(game.rooms['Attic']).toBeDefined();
    expect(game.rooms['Attic'].name).toBe('Attic');
  });

  // Rule 7 (cues): Cue target rooms
  it('creates a room when cue has ? -> "RoomName" arrow', () => {
    const cue = createCue('Basement', 'Library');
    cue.arrows.push(createArrow('?', '"Library"'));
    game.cues.push(cue);

    autoCreateFromArrows(game);

    expect(game.rooms['Library']).toBeDefined();
    expect(game.rooms['Library'].name).toBe('Library');
  });

  // Rule 8: Verb restore arrow creates verb state
  it('creates verb state when VERB__STATE -> VERB restore arrow exists', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', 'USE__LOCKED', 'USE');

    autoCreateFromArrows(game);

    expect(game.verbs['USE__LOCKED']).toBeDefined();
    expect(game.verbs['USE__LOCKED'].name).toBe('USE__LOCKED');
  });

  it('does NOT create verb state when base verb does not exist in restore arrow', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', 'PUNCH__HARD', 'PUNCH');

    autoCreateFromArrows(game);

    expect(game.verbs['PUNCH__HARD']).toBeUndefined();
  });

  // Idempotency / no duplicates
  it('does not duplicate existing entities when called multiple times', () => {
    game.inventory['KEY'] = createInventoryObject('KEY');
    addInteractionWithArrow(game, 'TAKE', 'Basement', 'KEY', 'player');

    autoCreateFromArrows(game);
    autoCreateFromArrows(game);

    const inventoryKeys = Object.keys(game.inventory).filter((k) => k === 'KEY');
    expect(inventoryKeys).toHaveLength(1);
  });

  it('does not overwrite an existing stated object', () => {
    const key = objectKey('Basement', 'LAMP__LIT');
    game.objects[key] = createRoomObject('LAMP__LIT', 'Basement', true);
    addInteractionWithArrow(game, 'USE', 'Basement', 'LAMP', 'LAMP__LIT');

    autoCreateFromArrows(game);

    // discovered should remain true (not overwritten with false)
    expect(game.objects[key].discovered).toBe(true);
  });

  it('does not create a room if it already exists', () => {
    game.rooms['Attic'] = createRoom('Attic');
    addInteractionWithArrow(game, 'USE', 'Basement', 'player', '"Attic"');

    autoCreateFromArrows(game);

    // Only one Attic room
    expect(Object.keys(game.rooms).filter((r) => r === 'Attic')).toHaveLength(1);
  });

  // Edge cases
  it('handles an empty game gracefully', () => {
    const empty = createGameData();
    expect(() => autoCreateFromArrows(empty)).not.toThrow();
  });

  it('handles interactions with no arrows gracefully', () => {
    const interaction = createInteraction('LOOK', 'Basement');
    game.interactions.push(interaction);

    expect(() => autoCreateFromArrows(game)).not.toThrow();
  });

  it('handles arrows in sealed content', () => {
    const interaction = createInteraction('USE', 'Basement');
    interaction.sealedArrows.push(createArrow('LAMP', 'LAMP__LIT'));
    game.interactions.push(interaction);

    autoCreateFromArrows(game);

    const key = objectKey('Basement', 'LAMP__LIT');
    expect(game.objects[key]).toBeDefined();
  });

  it('handles arrows in signal checks', () => {
    const interaction = createInteraction('USE', 'Basement');
    const check = createSignalCheck();
    check.arrows.push(createArrow('LAMP', 'LAMP__LIT'));
    interaction.signalChecks.push(check);
    game.interactions.push(interaction);

    autoCreateFromArrows(game);

    const key = objectKey('Basement', 'LAMP__LIT');
    expect(game.objects[key]).toBeDefined();
  });

  it('handles arrows in actions', () => {
    game.actions['Basement::GO_NORTH'] = createAction('GO_NORTH', 'Basement');
    game.actions['Basement::GO_NORTH'].arrows.push(createArrow('player', '"Attic"'));

    autoCreateFromArrows(game);

    expect(game.rooms['Attic']).toBeDefined();
  });

  it('does not create verb for lowercase or mixed-case destinations', () => {
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'override');
    addInteractionWithArrow(game, 'USE', 'Basement', '', 'Override');

    autoCreateFromArrows(game);

    expect(game.verbs['override']).toBeUndefined();
    expect(game.verbs['Override']).toBeUndefined();
  });

  it('skips arrows with no room context', () => {
    // Create an action with an empty room string
    game.actions['::orphan'] = createAction('orphan', '');
    game.actions['::orphan'].arrows.push(createArrow('player', '"Nowhere"'));

    autoCreateFromArrows(game);

    // Should not create the room because room is empty
    expect(game.rooms['Nowhere']).toBeUndefined();
  });
});

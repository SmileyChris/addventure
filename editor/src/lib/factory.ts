import type {
  GameProject,
  GameData,
  Verb,
  Room,
  RoomObject,
  InventoryObject,
  Arrow,
  Interaction,
  Cue,
  Action,
  SignalCheck,
} from './types';

export function createGameData(): GameData {
  return {
    metadata: {},
    verbs: {
      LOOK: { name: 'LOOK' },
      USE: { name: 'USE' },
      TAKE: { name: 'TAKE' },
    },
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

function parseBaseState(name: string): { base: string; state: string | null } {
  const idx = name.indexOf('__');
  if (idx === -1) {
    return { base: name, state: null };
  }
  return { base: name.slice(0, idx), state: name.slice(idx + 2) };
}

export function createRoom(name: string): Room {
  const { base, state } = parseBaseState(name);
  return { name, base, state };
}

export function createRoomObject(
  name: string,
  room: string,
  discovered = false,
): RoomObject {
  const { base, state } = parseBaseState(name);
  return { name, base, state, room, discovered };
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

export function objectKey(room: string, name: string): string {
  return `${room}::${name}`;
}

export function actionKey(room: string, name: string): string {
  return `${room}::${name}`;
}

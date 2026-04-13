import type { GameData, Arrow } from './types';
import { createRoom, createRoomObject, createVerb, createInventoryObject, objectKey } from './factory';

export function autoCreateFromArrows(game: GameData): void {
  // Collect all arrows from all sources
  const arrowsWithContext: { arrow: Arrow; room: string; verb: string }[] = [];

  for (const interaction of game.interactions) {
    for (const arrow of interaction.arrows) {
      arrowsWithContext.push({ arrow, room: interaction.room, verb: interaction.verb });
    }
    for (const arrow of interaction.sealedArrows) {
      arrowsWithContext.push({ arrow, room: interaction.room, verb: interaction.verb });
    }
    for (const check of interaction.signalChecks) {
      for (const arrow of check.arrows) {
        arrowsWithContext.push({ arrow, room: interaction.room, verb: interaction.verb });
      }
    }
  }

  for (const cue of game.cues) {
    for (const arrow of cue.arrows) {
      // Cue arrows operate in the target room, not the trigger room
      arrowsWithContext.push({ arrow, room: cue.targetRoom, verb: 'CUE' });
    }
  }

  for (const action of Object.values(game.actions)) {
    for (const arrow of action.arrows) {
      arrowsWithContext.push({ arrow, room: action.room, verb: '' });
    }
  }

  const hasTake = 'TAKE' in game.verbs;

  for (const { arrow, room, verb } of arrowsWithContext) {
    if (!room) continue; // Skip inventory-level interactions for room-specific creation

    // 1. Object state transforms: THING -> THING__STATE
    if (
      arrow.destination.includes('__') &&
      arrow.subject &&
      arrow.destination !== 'signal' &&
      !arrow.destination.startsWith('"') &&
      arrow.destination !== 'trash' &&
      arrow.destination !== 'player' &&
      arrow.destination !== 'room'
    ) {
      const key = objectKey(room, arrow.destination);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(arrow.destination, room, false);
      }
    }

    // 2. Auto-inventory: OBJECT -> player
    if (arrow.destination === 'player' && arrow.subject && arrow.subject !== 'player' && hasTake) {
      const baseName = arrow.subject.split('__')[0];
      if (!game.inventory[baseName]) {
        game.inventory[baseName] = createInventoryObject(baseName);
      }
    }

    // 3. Discovered objects: OBJECT -> room
    if (
      arrow.destination === 'room' &&
      arrow.subject &&
      arrow.subject !== 'player' &&
      arrow.subject !== 'room' &&
      !arrow.subject.startsWith('>') &&
      !arrow.subject.startsWith('?')
    ) {
      const key = objectKey(room, arrow.subject);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(arrow.subject, room, true);
      } else if (!game.objects[key].discovered) {
        game.objects[key].discovered = true;
      }
    }

    // 4. Auto-verbs: -> VERBNAME (empty subject, uppercase destination)
    if (
      arrow.subject === '' &&
      arrow.destination.match(/^[A-Z][A-Z0-9_]*$/) &&
      arrow.destination !== 'trash' &&
      arrow.destination !== 'player' &&
      arrow.destination !== 'room' &&
      arrow.destination !== 'signal'
    ) {
      if (!game.verbs[arrow.destination]) {
        game.verbs[arrow.destination] = createVerb(arrow.destination);
      }
    }

    // 5. Rooms from movement: player -> "RoomName"
    if (
      arrow.subject === 'player' &&
      arrow.destination.startsWith('"') &&
      arrow.destination.endsWith('"')
    ) {
      const roomName = arrow.destination.slice(1, -1);
      if (roomName && !game.rooms[roomName]) {
        game.rooms[roomName] = createRoom(roomName);
      }
    }

    // 6. Cue target rooms: ? -> "RoomName"
    if (
      arrow.subject === '?' &&
      arrow.destination.startsWith('"') &&
      arrow.destination.endsWith('"')
    ) {
      const roomName = arrow.destination.slice(1, -1);
      if (roomName && !game.rooms[roomName]) {
        game.rooms[roomName] = createRoom(roomName);
      }
    }

    // 7. Verb state restore: VERB__STATE -> VERB
    if (arrow.subject.includes('__') && !arrow.destination.includes('__')) {
      const baseVerb = arrow.subject.split('__')[0];
      if (game.verbs[baseVerb] && !game.verbs[arrow.subject]) {
        game.verbs[arrow.subject] = createVerb(arrow.subject);
      }
    }

    void verb; // verb context available for future rules
  }

  // 8. Verb states from interaction verbs
  for (const interaction of game.interactions) {
    if (interaction.verb.includes('__')) {
      const baseVerb = interaction.verb.split('__')[0];
      if (game.verbs[baseVerb] && !game.verbs[interaction.verb]) {
        game.verbs[interaction.verb] = createVerb(interaction.verb);
      }
    }
  }
}

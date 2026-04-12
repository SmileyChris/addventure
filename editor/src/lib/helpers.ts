import type { GameData, Arrow, Interaction } from './types';

/**
 * Format an entity name for display, respecting name_style setting.
 * "upper_words" (default): STEEL_DOOR → "STEEL DOOR"
 * "title": STEEL_DOOR → "Steel Door"
 * Strips state suffix: DOOR__OPEN → "DOOR" or "Door"
 */
export function displayName(name: string, style: string = 'upper_words'): string {
  const base = name.split('__')[0];
  const words = base.replace(/_/g, ' ');
  if (style === 'title') {
    return words
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }
  return words;
}

/** Format a full name including state: DOOR__OPEN → "DOOR OPEN" or "Door Open" */
function displayFullName(name: string, style: string = 'upper_words'): string {
  const words = name.replace(/__/g, ' ').replace(/_/g, ' ');
  if (style === 'title') {
    return words
      .split(' ')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }
  return words;
}

/** Get all signal names emitted in the game (scan all arrows with destination "signal") */
export function getSignalEmissions(game: GameData): string[] {
  const signals = new Set<string>();

  function scanArrows(arrows: Arrow[]) {
    for (const arrow of arrows) {
      if (arrow.destination === 'signal' && arrow.signalName) {
        signals.add(arrow.signalName);
      }
    }
  }

  for (const interaction of game.interactions) {
    scanArrows(interaction.arrows);
    scanArrows(interaction.sealedArrows);
  }

  for (const cue of game.cues) {
    scanArrows(cue.arrows);
  }

  for (const action of Object.values(game.actions)) {
    scanArrows(action.arrows);
  }

  for (const check of game.signalChecks) {
    scanArrows(check.arrows);
  }

  return Array.from(signals);
}

/** Get all signal names consumed (referenced in signal checks) — returns record of signal name → list of {room, context} */
export function getSignalConsumers(
  game: GameData,
): Record<string, { room: string; context: string }[]> {
  const result: Record<string, { room: string; context: string }[]> = {};

  function addConsumer(signalName: string, room: string, context: string) {
    if (!result[signalName]) {
      result[signalName] = [];
    }
    result[signalName].push({ room, context });
  }

  for (const interaction of game.interactions) {
    for (const check of interaction.signalChecks) {
      for (const signalName of check.signalNames) {
        addConsumer(
          signalName,
          interaction.room,
          `${interaction.verb} interaction`,
        );
      }
    }
  }

  for (const check of game.signalChecks) {
    for (const signalName of check.signalNames) {
      addConsumer(signalName, '', 'global signal check');
    }
  }

  return result;
}

/** Get room exits: rooms reachable via player -> "Room" arrows */
export function getRoomExits(
  game: GameData,
  roomName: string,
): { targetRoom: string; via: string }[] {
  const exits: { targetRoom: string; via: string }[] = [];

  for (const interaction of game.interactions) {
    if (interaction.room !== roomName) continue;

    for (const arrow of interaction.arrows) {
      if (
        arrow.subject === 'player' &&
        arrow.destination !== 'player' &&
        arrow.destination !== 'trash' &&
        arrow.destination !== 'signal' &&
        arrow.destination !== 'room' &&
        !arrow.destination.startsWith('room__') &&
        arrow.destination !== roomName
      ) {
        exits.push({
          targetRoom: arrow.destination,
          via: interaction.verb,
        });
      }
    }
  }

  // Also check actions
  for (const action of Object.values(game.actions)) {
    if (action.room !== roomName) continue;

    for (const arrow of action.arrows) {
      if (
        arrow.subject === 'player' &&
        arrow.destination !== 'player' &&
        arrow.destination !== 'trash' &&
        arrow.destination !== 'signal' &&
        arrow.destination !== 'room' &&
        !arrow.destination.startsWith('room__') &&
        arrow.destination !== roomName
      ) {
        exits.push({
          targetRoom: arrow.destination,
          via: action.name,
        });
      }
    }
  }

  return exits;
}

/** Get all objects in a specific room, grouped by base name */
export function getRoomObjects(
  game: GameData,
  roomName: string,
): Record<string, string[]> {
  const result: Record<string, string[]> = {};

  for (const obj of Object.values(game.objects)) {
    if (obj.room !== roomName) continue;

    if (!result[obj.base]) {
      result[obj.base] = [];
    }
    result[obj.base].push(obj.name);
  }

  return result;
}

/** Get interactions for a specific room */
export function getRoomInteractions(
  game: GameData,
  roomName: string,
): Interaction[] {
  return game.interactions.filter((i) => i.room === roomName);
}

/** Get interactions for a specific object (by name, in a room) */
export function getObjectInteractions(
  game: GameData,
  roomName: string,
  objectName: string,
): Interaction[] {
  return game.interactions.filter(
    (i) =>
      i.room === roomName &&
      i.targetGroups.some((group) => group.includes(objectName)),
  );
}

/** Classify an arrow into a human-readable type */
export function classifyArrow(arrow: Arrow): string {
  const { subject, destination } = arrow;

  // Cue: subject is '?'
  if (subject === '?') return 'cue';

  // Signal emission
  if (destination === 'signal') return 'signal';

  // Destroy
  if (destination === 'trash') return 'destroy';

  // Pickup (object goes to player)
  if (destination === 'player') return 'pickup';

  // Move (player moves to another room)
  if (subject === 'player') return 'move';

  // Discover action (subject starts with '>')
  if (subject.startsWith('>')) return 'discover_action';

  // Reveal verb (empty subject, uppercase destination — reveals a new verb)
  if (subject === '' && destination === destination.toUpperCase()) {
    return 'reveal_verb';
  }

  // Room state change
  if (subject === 'room' || subject.startsWith('room__')) return 'room_state';

  // Verb restore: subject has __ and destination is same base without __
  if (subject.includes('__')) {
    const base = subject.split('__')[0];
    if (destination === base) return 'verb_restore';
    return 'transform';
  }

  // Destination has __ → transform
  if (destination.includes('__')) return 'transform';

  // Reveal (object appears in room)
  if (destination === 'room') return 'reveal';

  return 'reveal';
}

/** Get a display label for an arrow */
export function arrowLabel(arrow: Arrow, style: string = 'upper_words'): string {
  const type = classifyArrow(arrow);
  const { subject, destination } = arrow;
  const dn = (n: string) => displayName(n, style);
  const dfn = (n: string) => displayFullName(n, style);

  switch (type) {
    case 'destroy':
      return `\u00d7 ${dn(subject)}`;
    case 'pickup':
      return `\u2191 ${dn(subject)} \u2192 inventory`;
    case 'move':
      return `\u2192 ${dn(destination)}`;
    case 'transform': {
      return `${dn(subject)} \u2192 ${dfn(destination)}`;
    }
    case 'reveal':
      return `${dn(subject)} appears`;
    case 'cue':
      return `? \u2192 ${dn(destination)}`;
    case 'signal':
      return `\u26a1 ${arrow.signalName ?? subject}`;
    case 'reveal_verb':
      return `+ ${destination}`;
    case 'discover_action':
      return `> ${subject.slice(1)}`;
    case 'room_state': {
      return `room \u2192 ${dn(destination)}`;
    }
    case 'verb_restore': {
      return `${dn(subject)} \u2192 ${dn(destination)}`;
    }
    default:
      return `${subject} \u2192 ${destination}`;
  }
}

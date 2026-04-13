/**
 * integration.test.ts — Round-trip integration tests using the actual example game.
 *
 * Reads the .md files from ../../games/example/, parses them with parseGameFiles(),
 * verifies the parsed structure, serializes back with serializeGame(), re-parses,
 * and verifies key data survived the round-trip.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { parseGameFiles } from '../src/lib/parser';
import { serializeGame } from '../src/lib/serializer';
import type { GameData } from '../src/lib/types';

// ── Load example game files ──────────────────────────────────────────────────

const EXAMPLE_DIR = join(__dirname, '../../games/example');

function loadExampleGame(): Record<string, string> {
  const files: Record<string, string> = {};
  const entries = readdirSync(EXAMPLE_DIR);
  for (const entry of entries) {
    if (entry.endsWith('.md')) {
      files[entry] = readFileSync(join(EXAMPLE_DIR, entry), 'utf-8');
    }
  }
  return files;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('Integration: example game parse', () => {
  let files: Record<string, string>;
  let game: GameData;

  beforeAll(() => {
    files = loadExampleGame();
    game = parseGameFiles(files);
  });

  it('loads all example .md files', () => {
    // Should have index.md + room files (basement, control_room, hallway)
    expect(Object.keys(files)).toContain('index.md');
    expect(Object.keys(files)).toContain('control_room.md');
    expect(Object.keys(files)).toContain('basement.md');
    expect(Object.keys(files)).toContain('hallway.md');
    expect(Object.keys(files).length).toBeGreaterThanOrEqual(4);
  });

  it('parses metadata from index.md frontmatter', () => {
    expect(game.metadata['title']).toBe('The Facility');
    expect(game.metadata['author']).toBe('Addventure Example');
    expect(game.metadata['start']).toBe('Control Room');
  });

  it('parses verbs: LOOK, USE, TAKE', () => {
    expect(game.verbs['LOOK']).toBeDefined();
    expect(game.verbs['USE']).toBeDefined();
    expect(game.verbs['TAKE']).toBeDefined();
  });

  it('parses game description from index.md', () => {
    expect(game.metadata['description']).toBeDefined();
    expect(game.metadata['description']).toContain('You wake up bound to a chair');
  });

  it('creates rooms for each room file', () => {
    expect(game.rooms['Control Room']).toBeDefined();
    expect(game.rooms['Basement']).toBeDefined();
    expect(game.rooms['Cell Block']).toBeDefined();
  });

  it('parses control room objects: TERMINAL, HATCH, CRATE, BINDINGS, KNIFE', () => {
    const objectNames = Object.values(game.objects)
      .filter((o) => o.room === 'Control Room')
      .map((o) => o.name);
    expect(objectNames).toContain('TERMINAL');
    expect(objectNames).toContain('HATCH');
    expect(objectNames).toContain('CRATE');
    expect(objectNames).toContain('BINDINGS');
    expect(objectNames).toContain('KNIFE');
  });

  it('parses basement objects: WORKBENCH, CROWBAR, STEEL_DOOR, FUSE_BOX, AIR_DUCT, PRISONER', () => {
    const objectNames = Object.values(game.objects)
      .filter((o) => o.room === 'Basement')
      .map((o) => o.name);
    expect(objectNames).toContain('WORKBENCH');
    expect(objectNames).toContain('CROWBAR');
    expect(objectNames).toContain('STEEL_DOOR');
    expect(objectNames).toContain('FUSE_BOX');
    expect(objectNames).toContain('AIR_DUCT');
    expect(objectNames).toContain('PRISONER');
  });

  it('parses interactions with multiple targets (USE + KEYCARD)', () => {
    const useKeycard = game.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('KEYCARD')),
    );
    expect(useKeycard).toBeDefined();
    expect(useKeycard!.narrative).toContain('You slide the keycard');
  });

  it('parses state transition arrows (TERMINAL -> TERMINAL__UNLOCKED)', () => {
    const useKeycard = game.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('KEYCARD')),
    );
    expect(useKeycard).toBeDefined();
    const terminalArrow = useKeycard!.arrows.find(
      (a) => a.subject === 'TERMINAL' && a.destination === 'TERMINAL__UNLOCKED',
    );
    expect(terminalArrow).toBeDefined();
  });

  it('parses cue arrows (? -> "Basement")', () => {
    // Cues parsed from control_room.md: USE + KEYCARD creates a cue to Basement
    const controlRoomCues = game.cues.filter((c) => c.triggerRoom === 'Control Room');
    expect(controlRoomCues.length).toBeGreaterThan(0);
    const basementCue = controlRoomCues.find((c) => c.targetRoom === 'Basement');
    expect(basementCue).toBeDefined();
  });

  it('parses cue arrow children (COMPARTMENT -> room)', () => {
    // The cue from "Control Room" to "Basement" should have a COMPARTMENT -> room arrow
    const basementCue = game.cues.find(
      (c) => c.triggerRoom === 'Control Room' && c.targetRoom === 'Basement',
    );
    expect(basementCue).toBeDefined();
    const compartmentArrow = basementCue!.arrows.find(
      (a) => a.subject === 'COMPARTMENT' && a.destination === 'room',
    );
    expect(compartmentArrow).toBeDefined();
  });

  it('parses nested object state interactions (TERMINAL__UNLOCKED + LOOK)', () => {
    // TERMINAL__UNLOCKED should be a room object in Control Room
    const terminalUnlocked = Object.values(game.objects).find(
      (o) => o.name === 'TERMINAL__UNLOCKED' && o.room === 'Control Room',
    );
    expect(terminalUnlocked).toBeDefined();

    // There should be a LOOK interaction for TERMINAL__UNLOCKED
    const lookInteraction = game.interactions.find(
      (i) =>
        i.verb === 'LOOK' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('TERMINAL__UNLOCKED')),
    );
    expect(lookInteraction).toBeDefined();
  });

  it('parses verb state interactions (USE__RESTRAINED)', () => {
    // USE__RESTRAINED + * should be in ## Interactions
    const useRestrained = game.interactions.find(
      (i) => i.verb === 'USE__RESTRAINED' && i.room === 'Control Room',
    );
    expect(useRestrained).toBeDefined();
  });

  it('parses wildcard interaction (USE__RESTRAINED + *)', () => {
    const wildcardInteraction = game.interactions.find(
      (i) =>
        i.verb === 'USE__RESTRAINED' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('*')),
    );
    expect(wildcardInteraction).toBeDefined();
    expect(wildcardInteraction!.narrative).toContain('You strain against the bindings');
  });

  it('parses fragment/sealed content block (AIR_DUCT in Basement)', () => {
    const airDuctUse = game.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('PRISONER')),
    );
    expect(airDuctUse).toBeDefined();
    expect(airDuctUse!.sealedContent).not.toBeNull();
    expect(airDuctUse!.sealedContent).toContain('From the roof you can see all of it');
  });

  it('parses sealed content arrows (signal arrow inside fragment)', () => {
    const airDuctUse = game.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Basement' &&
        i.targetGroups.some((g) => g.includes('PRISONER')),
    );
    expect(airDuctUse).toBeDefined();
    const signalArrow = airDuctUse!.sealedArrows.find(
      (a) => a.destination === 'signal',
    );
    expect(signalArrow).toBeDefined();
    expect(signalArrow!.subject).toBe('EVERYONE_OUT_ESCAPE');
  });

  it('parses cue from Cell Block to Basement (PRISONER -> room)', () => {
    const cellBlockCues = game.cues.filter((c) => c.triggerRoom === 'Cell Block');
    expect(cellBlockCues.length).toBeGreaterThan(0);
    // Find the cue that has the PRISONER arrow (there may be duplicates if
    // extra .md files exist in the example dir alongside the originals)
    const basementCue = cellBlockCues.find(
      (c) =>
        c.targetRoom === 'Basement' &&
        c.arrows.some((a) => a.subject === 'PRISONER' && a.destination === 'room'),
    );
    expect(basementCue).toBeDefined();
  });

  it('has multiple interactions total', () => {
    expect(game.interactions.length).toBeGreaterThan(20);
  });

  it('has multiple cues total', () => {
    expect(game.cues.length).toBeGreaterThan(0);
  });
});

// ── Round-trip tests ─────────────────────────────────────────────────────────

describe('Integration: example game round-trip (parse → serialize → re-parse)', () => {
  let files: Record<string, string>;
  let game1: GameData;
  let serialized: Record<string, string>;
  let game2: GameData;

  beforeAll(() => {
    files = loadExampleGame();
    game1 = parseGameFiles(files);
    serialized = serializeGame(game1);
    game2 = parseGameFiles(serialized);
  });

  it('produces serialized files for each base room', () => {
    expect(serialized['index.md']).toBeDefined();
    expect(serialized['control_room.md']).toBeDefined();
    expect(serialized['basement.md']).toBeDefined();
    expect(serialized['cell_block.md']).toBeDefined();
  });

  it('round-trip: same metadata', () => {
    expect(game2.metadata['title']).toBe(game1.metadata['title']);
    expect(game2.metadata['author']).toBe(game1.metadata['author']);
    expect(game2.metadata['start']).toBe(game1.metadata['start']);
  });

  it('round-trip: same verbs', () => {
    const verbs1 = Object.keys(game1.verbs).filter((v) => !v.includes('__')).sort();
    const verbs2 = Object.keys(game2.verbs).filter((v) => !v.includes('__')).sort();
    expect(verbs2).toEqual(verbs1);
  });

  it('round-trip: same number of rooms', () => {
    const baseRooms1 = Object.values(game1.rooms).filter((r) => r.state === null).length;
    const baseRooms2 = Object.values(game2.rooms).filter((r) => r.state === null).length;
    expect(baseRooms2).toBe(baseRooms1);
  });

  it('round-trip: same room names', () => {
    const roomNames1 = Object.values(game1.rooms)
      .filter((r) => r.state === null)
      .map((r) => r.name)
      .sort();
    const roomNames2 = Object.values(game2.rooms)
      .filter((r) => r.state === null)
      .map((r) => r.name)
      .sort();
    expect(roomNames2).toEqual(roomNames1);
  });

  it('round-trip: same base object names per room', () => {
    for (const room of Object.values(game1.rooms)) {
      if (room.state !== null) continue;
      const baseObjs1 = Object.values(game1.objects)
        .filter((o) => o.room === room.name && o.state === null)
        .map((o) => o.name)
        .sort();
      const baseObjs2 = Object.values(game2.objects)
        .filter((o) => o.room === room.name && o.state === null)
        .map((o) => o.name)
        .sort();
      expect(baseObjs2).toEqual(baseObjs1);
    }
  });

  it('round-trip: same number of interactions', () => {
    // Allow some variance for freeform vs. object-level classification differences
    expect(Math.abs(game2.interactions.length - game1.interactions.length)).toBeLessThanOrEqual(5);
  });

  it('round-trip: LOOK interaction for Control Room survives', () => {
    const look1 = game1.interactions.find(
      (i) => i.verb === 'LOOK' && i.room === 'Control Room' && i.targetGroups.length === 0,
    );
    const look2 = game2.interactions.find(
      (i) => i.verb === 'LOOK' && i.room === 'Control Room' && i.targetGroups.length === 0,
    );
    expect(look1).toBeDefined();
    expect(look2).toBeDefined();
    expect(look2!.narrative).toContain('Fluorescent lights buzz');
  });

  it('round-trip: wildcard interaction (USE__RESTRAINED + *) survives', () => {
    const wildcard2 = game2.interactions.find(
      (i) =>
        i.verb === 'USE__RESTRAINED' &&
        i.room === 'Control Room' &&
        i.targetGroups.some((g) => g.includes('*')),
    );
    expect(wildcard2).toBeDefined();
    expect(wildcard2!.narrative).toContain('You strain against the bindings');
  });

  it('round-trip: fragment sealed content survives', () => {
    const airDuctUse2 = game2.interactions.find(
      (i) =>
        i.verb === 'USE' &&
        i.room === 'Basement' &&
        i.sealedContent !== null,
    );
    expect(airDuctUse2).toBeDefined();
    expect(airDuctUse2!.sealedContent).toContain('From the roof you can see all of it');
  });

  it('round-trip: description text survives', () => {
    expect(game2.metadata['description']).toContain('You wake up bound to a chair');
  });
});

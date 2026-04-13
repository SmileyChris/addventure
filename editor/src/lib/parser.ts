/**
 * parser.ts — JavaScript port of the Addventure .md script parser.
 *
 * Converts a map of filename → content strings into a GameData model.
 * Main entry point: parseGameFiles(files)
 */

import type {
  GameData,
  Arrow,
  Interaction,
  Cue,
  Action,
  SignalCheck,
} from './types';
import {
  createGameData,
  createVerb,
  createRoom,
  createRoomObject,
  createInventoryObject,
  createArrow,
  createInteraction,
  createCue,
  createAction,
  createSignalCheck,
  objectKey,
  actionKey,
} from './factory';

// ── Regex helpers ──────────────────────────────────────────────────────────

const NAME_RE = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$/;
const STATED_NAME_RE =
  /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*(?:__[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)?$/;
const OBJECT_REF_RE =
  /^(?:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*(?:__[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)?|\*)$/;

function isName(s: string): boolean {
  return NAME_RE.test(s);
}

function isStatedName(s: string): boolean {
  return STATED_NAME_RE.test(s);
}

function isObjectRef(s: string): boolean {
  return OBJECT_REF_RE.test(s);
}

function splitName(name: string): { base: string; state: string | null } {
  const idx = name.indexOf('__');
  if (idx === -1) return { base: name, state: null };
  return { base: name.slice(0, idx), state: name.slice(idx + 2) };
}

// ── Line helpers ───────────────────────────────────────────────────────────

function getIndent(line: string): number {
  let count = 0;
  for (const ch of line) {
    if (ch === ' ') count++;
    else break;
  }
  return count;
}

function stripTrailingComment(line: string): string {
  const idx = line.indexOf('//');
  if (idx === -1) return line;
  return line.slice(0, idx).trimEnd();
}

function normalizeStructuralLine(line: string): string {
  if (!line.includes(':')) {
    return stripTrailingComment(line).trim();
  }
  const colonIdx = line.indexOf(':');
  const header = line.slice(0, colonIdx);
  const tail = line.slice(colonIdx + 1).trim();
  return `${stripTrailingComment(header).trim()}:${tail}`;
}

function isComment(line: string): boolean {
  return line.trim().startsWith('//');
}

function isHeader(line: string): boolean {
  const s = line.trim();
  return s.startsWith('## ') || s.startsWith('# ');
}

function parseHeader(line: string): { type: string; name: string | null } {
  const s = line.trim();
  const name = s.startsWith('## ') ? s.slice(3).trim() : s.slice(2).trim();
  const lower = name.toLowerCase();
  if (lower === 'verbs' || lower === 'inventory' || lower === 'interactions') {
    return { type: lower, name: null };
  }
  return { type: 'room', name };
}

function isArrow(s: string): boolean {
  return s.includes('->');
}

function parseArrow(text: string): Arrow {
  const [left, right] = text.split('->', 2).map((p) => p.trim());
  const subject = left ?? '';
  const destination = right ?? '';
  return createArrow(subject, destination);
}

function stripMarker(s: string): { marker: string; content: string } {
  if (s.startsWith('+ ')) return { marker: '+', content: s.slice(2) };
  if (s.startsWith('- ')) return { marker: '-', content: s.slice(2) };
  return { marker: '', content: s };
}

function hasColonHeader(s: string): boolean {
  return s.includes(':') && !s.startsWith('//');
}

function isAction(s: string): boolean {
  return s.startsWith('> ');
}

function isSealedFence(s: string): boolean {
  return s === ':::' || s === '::: fragment';
}

function isNarrative(s: string): boolean {
  if (s.startsWith('+ ') || s.startsWith('- ')) return false;
  if (s.includes('->')) return false;
  if (isHeader(s) || isComment(s)) return false;
  if (/^[A-Z][A-Z0-9_]*$/.test(s)) return false;
  return true;
}

// ── Frontmatter parser ─────────────────────────────────────────────────────

function parseFrontmatter(lines: string[]): {
  meta: Record<string, string>;
  nextLine: number;
} {
  if (!lines.length || lines[0].trim() !== '---') {
    return { meta: {}, nextLine: 0 };
  }
  const meta: Record<string, string> = {};
  let i = 1;
  while (i < lines.length) {
    const line = stripTrailingComment(lines[i]).trim();
    if (line === '---') {
      return { meta, nextLine: i + 1 };
    }
    if (line && line.includes(':')) {
      const colonIdx = line.indexOf(':');
      const key = line.slice(0, colonIdx).trim();
      const val = line.slice(colonIdx + 1).trim();
      meta[key] = val;
    }
    i++;
  }
  return { meta, nextLine: i };
}

// ── Signal check parser ────────────────────────────────────────────────────

function isSignalCheckLine(s: string): boolean {
  if (s === 'otherwise?') return true;
  if (s.endsWith('?') && s.length > 1) {
    const namesPart = s.slice(0, -1);
    return namesPart.split('+').every((n) => isName(n.trim()));
  }
  return false;
}

function parseSignalCheckGroup(
  lines: string[],
  startI: number,
  roomName: string,
): { checks: SignalCheck[]; nextLine: number } {
  const checks: SignalCheck[] = [];
  let sawOtherwise = false;
  let i = startI;

  while (i < lines.length) {
    const stripped = stripTrailingComment(lines[i]).trim();
    if (!stripped || isComment(stripped)) {
      i++;
      continue;
    }
    if (isHeader(lines[i])) break;

    let signalNames: string[];
    if (stripped === 'otherwise?') {
      if (sawOtherwise) break; // stop, don't error
      sawOtherwise = true;
      signalNames = [];
      i++;
    } else if (stripped.endsWith('?') && stripped.length > 1) {
      if (sawOtherwise) break;
      const namesPart = stripped.slice(0, -1).trim();
      const parts = namesPart.split('+').map((n) => n.trim());
      if (!parts.every(isName)) break;
      signalNames = parts;
      i++;
    } else {
      break;
    }

    // Parse indented body: narrative + arrows
    const narrativeLines: string[] = [];
    const arrows: Arrow[] = [];
    let blockIndent: number | null = null;

    while (i < lines.length) {
      const line = lines[i];
      const lineStripped = stripTrailingComment(line).trim();
      if (!lineStripped || isComment(lineStripped)) {
        i++;
        continue;
      }
      const ind = getIndent(line);
      if (blockIndent === null) {
        if (ind === 0) break;
        blockIndent = ind;
      }
      if (ind < blockIndent) break;
      if (isHeader(line)) break;

      const { marker, content } = stripMarker(lineStripped);
      if (marker === '-' && isArrow(content)) {
        const arrow = parseArrow(stripTrailingComment(content));
        arrows.push(arrow);
        i++;
      } else if (!marker) {
        narrativeLines.push(lineStripped);
        i++;
      } else {
        i++;
      }
    }

    const check = createSignalCheck();
    check.signalNames = signalNames;
    check.narrative = narrativeLines.join('\n');
    check.arrows = arrows;
    checks.push(check);
  }

  return { checks, nextLine: i };
}

// ── Interaction body parser ────────────────────────────────────────────────

interface InteractionBody {
  narrative: string;
  arrows: Arrow[];
  sealedContent: string | null;
  sealedArrows: Arrow[];
  signalChecks: SignalCheck[];
  nextLine: number;
}

function collectInteractionBody(
  lines: string[],
  startI: number,
  parentIndent: number,
  roomName: string,
  game: GameData,
): InteractionBody {
  let i = startI;
  let narrative = '';
  const arrows: Arrow[] = [];
  let sealedContent: string | null = null;
  const sealedArrows: Arrow[] = [];
  let signalChecks: SignalCheck[] = [];
  let blankLineSeen = false;

  while (i < lines.length) {
    const line = lines[i];
    const lineStripped = line.trim();
    if (!lineStripped || isComment(lineStripped)) {
      if (narrative) blankLineSeen = true;
      i++;
      continue;
    }
    if (getIndent(line) <= parentIndent || isHeader(line)) break;

    const { marker, content } = stripMarker(lineStripped);

    if (marker === '-' && isArrow(content)) {
      const arrow = parseArrow(stripTrailingComment(content));
      arrows.push(arrow);
      blankLineSeen = false;
      const arrowIndent = getIndent(line);
      i++;
      // Parse arrow children (state transitions, cues, -> room, etc.)
      i = parseArrowChildren(lines, i, arrowIndent + 1, roomName, arrow, game);
    } else if (isSealedFence(lineStripped)) {
      if (lineStripped === '::: fragment') {
        i++;
        const result = parseFragmentBlock(lines, i, roomName);
        sealedContent = result.content;
        sealedArrows.push(...result.arrows);
        i = result.nextLine;
      } else {
        i++; // closing ::: outside fragment block context, skip
      }
    } else if (isSignalCheckLine(lineStripped)) {
      const result = parseSignalCheckGroup(lines, i, roomName);
      signalChecks = result.checks;
      i = result.nextLine;
      break;
    } else if (isNarrative(lineStripped)) {
      if (!narrative) {
        narrative = lineStripped;
      } else if (blankLineSeen) {
        narrative += '\n\n' + lineStripped;
      } else {
        narrative += ' ' + lineStripped;
      }
      blankLineSeen = false;
      i++;
    } else {
      // Skip unrecognized lines inside interaction body
      i++;
    }
  }

  return { narrative, arrows, sealedContent, sealedArrows, signalChecks, nextLine: i };
}

function parseFragmentBlock(
  lines: string[],
  startI: number,
  _roomName: string,
): { content: string; arrows: Arrow[]; nextLine: number } {
  const contentLines: string[] = [];
  const arrows: Arrow[] = [];
  let i = startI;
  let baseIndent: number | null = null;
  let blankLineSeen = false;

  while (i < lines.length) {
    const line = lines[i];
    const lineStripped = line.trim();
    if (lineStripped === ':::') {
      i++;
      break;
    }
    if (!lineStripped) {
      if (contentLines.length > 0) blankLineSeen = true;
      i++;
      continue;
    }
    if (isComment(lineStripped)) {
      i++;
      continue;
    }
    if (baseIndent === null) {
      baseIndent = getIndent(line);
    }
    const { marker, content } = stripMarker(lineStripped);
    if (marker === '-' && isArrow(content)) {
      arrows.push(parseArrow(stripTrailingComment(content)));
    } else {
      if (blankLineSeen) {
        contentLines.push('');
        blankLineSeen = false;
      }
      contentLines.push(lineStripped);
    }
    i++;
  }

  return { content: contentLines.join('\n'), arrows, nextLine: i };
}

interface CueResult {
  cue: Cue | null;
  nextLine: number;
}

function parseCueChildren(
  lines: string[],
  startI: number,
  childIndent: number,
  triggerRoom: string,
  game: GameData,
): CueResult {
  // We need the cue's target room from the arrow — but we parse it upstream.
  // This function parses the cue body and returns the cue.
  // The caller should already have the arrow, so we just parse the body here.
  // Since we call it after seeing '? -> "TargetRoom"', we need to read narrative/arrows.
  let i = startI;
  const narrativeLines: string[] = [];
  const cueArrows: Arrow[] = [];

  while (i < lines.length) {
    const line = lines[i];
    const lineStripped = stripTrailingComment(line).trim();
    if (!lineStripped || isComment(lineStripped)) {
      i++;
      continue;
    }
    if (getIndent(line) < childIndent || isHeader(line)) break;

    const { marker, content } = stripMarker(lineStripped);
    if (marker === '-' && isArrow(content)) {
      const arrow = parseArrow(stripTrailingComment(content));
      cueArrows.push(arrow);
      // Register revealed room objects for "-> room" arrows
      if (arrow.destination === 'room' && arrow.subject) {
        const { base, state } = splitName(arrow.subject);
        const key = objectKey(triggerRoom, arrow.subject);
        if (!game.objects[key]) {
          game.objects[key] = createRoomObject(arrow.subject, triggerRoom, true);
        }
      }
      i++;
    } else if (isNarrative(lineStripped)) {
      narrativeLines.push(lineStripped);
      i++;
    } else {
      i++;
    }
  }

  // Note: the cue targetRoom comes from the parent arrow — we return null here
  // and let the caller set it, since we don't have it here.
  // Actually, we need to restructure: the cue creation happens in collectInteractionBody
  // after seeing the ? arrow. We'll handle this differently.
  return { cue: null, nextLine: i };
}

// ── Interaction registration ──────────────────────────────────────────────

function registerInteraction(game: GameData, interaction: Interaction): void {
  game.interactions.push(interaction);
}

// ── Parse inline interaction header ───────────────────────────────────────

function parseInteractionHeader(
  content: string,
  contextEntity: string | null,
  _roomName: string,
): { verb: string; targetGroups: string[][] } {
  // Strip leading + marker if present
  const { content: headerContent } = stripMarker(content);
  const colonIdx = headerContent.indexOf(':');
  const headerPart =
    colonIdx !== -1
      ? headerContent.slice(0, colonIdx).trim()
      : headerContent.trim();

  let verb: string;
  let extraTargets: string[][];

  if (headerPart.includes('+')) {
    const parts = headerPart.split('+').map((p) => p.trim());
    verb = parts[0];
    extraTargets = parts.slice(1).map((p) =>
      p
        .split('|')
        .map((a) => a.trim())
        .filter(Boolean),
    );
  } else {
    verb = headerPart;
    extraTargets = [];
  }

  const targetGroups: string[][] =
    contextEntity !== null ? [[contextEntity], ...extraTargets] : extraTargets;

  return { verb, targetGroups };
}

// ── Parse action ───────────────────────────────────────────────────────────

function parseAction(
  lines: string[],
  startI: number,
  roomName: string,
  game: GameData,
): number {
  const line = lines[startI];
  const stripped = line.trim();
  const name = stripped.slice(2).trim(); // "> NAME"
  const parentIndent = getIndent(line);
  let i = startI + 1;

  const narrativeLines: string[] = [];
  const arrows: Arrow[] = [];

  while (i < lines.length) {
    const bline = lines[i];
    const bstripped = bline.trim();
    if (!bstripped || isComment(bstripped)) {
      i++;
      continue;
    }
    if (getIndent(bline) <= parentIndent || isHeader(bline)) break;

    const { marker, content } = stripMarker(bstripped);
    if (marker === '-' && isArrow(content)) {
      arrows.push(parseArrow(stripTrailingComment(content)));
      i++;
    } else if (isNarrative(bstripped)) {
      narrativeLines.push(bstripped);
      i++;
    } else {
      i++;
    }
  }

  const key = actionKey(roomName, name);
  const action = createAction(name, roomName);
  action.narrative = narrativeLines.join('\n');
  action.arrows = arrows;
  game.actions[key] = action;
  return i;
}

// ── Parse freeform interactions (## Interactions section) ─────────────────

function parseFreeformInteractions(
  lines: string[],
  startI: number,
  roomName: string,
  game: GameData,
): number {
  let i = startI;

  while (i < lines.length) {
    const line = lines[i];
    if (isHeader(line)) break;
    const stripped = normalizeStructuralLine(line);
    if (!stripped || isComment(stripped)) {
      i++;
      continue;
    }

    // Freeform interaction: VERB + TARGETS: narrative (no leading + marker)
    if (hasColonHeader(stripped) && !isArrow(stripped) && !isAction(stripped)) {
      const colonIdx = stripped.indexOf(':');
      const headerPart = stripped.slice(0, colonIdx).trim();
      const afterColon = stripped.slice(colonIdx + 1).trim();

      let verb: string;
      let targetGroups: string[][];

      if (headerPart.includes('+')) {
        const parts = headerPart.split('+').map((p) => p.trim());
        verb = parts[0];
        targetGroups = parts.slice(1).map((p) =>
          p
            .split('|')
            .map((a) => a.trim())
            .filter(Boolean),
        );
      } else {
        verb = headerPart;
        targetGroups = [];
      }

      const interaction = createInteraction(verb, roomName);
      interaction.targetGroups = targetGroups;

      const body = collectInteractionBody(lines, i + 1, 0, roomName, game);
      // Inline narrative from header
      if (afterColon) {
        interaction.narrative = afterColon;
        if (body.narrative) {
          interaction.narrative += '\n' + body.narrative;
        }
      } else {
        interaction.narrative = body.narrative;
      }
      interaction.arrows = body.arrows;
      interaction.sealedContent = body.sealedContent;
      interaction.sealedArrows = body.sealedArrows;
      interaction.signalChecks = body.signalChecks;

      registerInteraction(game, interaction);
      i = body.nextLine;
    } else {
      i++;
    }
  }

  return i;
}

// ── Parse entity block (interactions for a room object) ────────────────────

function parseEntityBlock(
  lines: string[],
  startI: number,
  roomName: string,
  entityName: string,
  entityIndent: number,
  game: GameData,
): number {
  let i = startI;

  while (i < lines.length) {
    const line = lines[i];
    const stripped = normalizeStructuralLine(line);
    if (!stripped || isComment(stripped)) {
      i++;
      continue;
    }
    if (isHeader(line)) break;

    const ind = getIndent(line);
    const { marker, content } = stripMarker(stripped);

    // Must be deeper than entity or + at same level
    if (ind < entityIndent) break;
    if (ind === entityIndent && marker !== '+') break;

    if (marker === '+') {
      if (hasColonHeader(content) && !isArrow(content)) {
        // Inline interaction: + VERB + TARGET: narrative
        const colonIdx = content.indexOf(':');
        const headerPart = content.slice(0, colonIdx).trim();
        const afterColon = content.slice(colonIdx + 1).trim();

        // Parse verb and extra targets from "VERB + TARGET1 + TARGET2"
        let verb: string;
        let extraTargets: string[][];
        if (headerPart.includes('+')) {
          const parts = headerPart.split('+').map((p) => p.trim());
          verb = parts[0];
          extraTargets = parts.slice(1).map((p) =>
            p.split('|').map((a) => a.trim()).filter(Boolean),
          );
        } else {
          verb = headerPart;
          extraTargets = [];
        }
        const targetGroups: string[][] = [[entityName], ...extraTargets];

        const interaction = createInteraction(verb, roomName);
        interaction.targetGroups = targetGroups;

        const body = collectInteractionBody(lines, i + 1, ind, roomName, game);
        if (afterColon) {
          interaction.narrative = afterColon;
          if (body.narrative) {
            interaction.narrative += '\n' + body.narrative;
          }
        } else {
          interaction.narrative = body.narrative;
        }
        interaction.arrows = body.arrows;
        interaction.sealedContent = body.sealedContent;
        interaction.sealedArrows = body.sealedArrows;
        interaction.signalChecks = body.signalChecks;

        registerInteraction(game, interaction);
        i = body.nextLine;
      } else {
        i++;
      }
    } else if (marker === '-') {
      if (isArrow(content)) {
        const arrow = parseArrow(stripTrailingComment(content));
        i++;
        // Parse arrow children (state transitions, cues, -> room, etc.)
        i = parseArrowChildren(lines, i, ind + 1, roomName, arrow, game);
      } else {
        i++;
      }
    } else if (isAction(stripped)) {
      i = parseAction(lines, i, roomName, game);
    } else if (!marker && ind > entityIndent && isStatedName(stripped)) {
      // Nested object (state variant)
      const objName = stripped;
      const key = objectKey(roomName, objName);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(objName, roomName);
      }
      i++;
      i = parseEntityBlock(lines, i, roomName, objName, ind, game);
    } else {
      i++;
    }
  }

  return i;
}

/**
 * Parse children of an arrow line. Mirrors Python's _parse_arrow_children.
 *
 * After parsing an arrow, if the arrow has a state-destination or a
 * `-> room` / `-> "Room"` destination, we parse the nested + blocks
 * (interactions / entity properties) that follow at `childIndent`.
 *
 * Returns the updated line index after consuming all children.
 */
function parseArrowChildren(
  lines: string[],
  startI: number,
  childIndent: number,
  roomName: string,
  arrow: Arrow,
  game: GameData,
): number {
  const dest = arrow.destination;
  const subj = arrow.subject;

  // -> signal: no children
  if (dest === 'signal') return startI;

  // ? -> "Room": cue (handled by caller — but also handle here for completeness)
  if (subj === '?') {
    if (dest.startsWith('"') && dest.endsWith('"')) {
      const targetRoom = dest.slice(1, -1);
      const cueResult = parseCueChildrenFull(lines, startI, childIndent, roomName, targetRoom, game);
      game.cues.push(cueResult.cue);
      return cueResult.nextLine;
    }
    return startI;
  }

  // -> trash: no children
  if (dest === 'trash') return startI;

  // player -> "Room": movement, no children
  if (subj === 'player' && dest.startsWith('"') && dest.endsWith('"')) return startI;

  // -> "Room" (non-player subject): object teleports to another room, parse entity block there
  if (dest.startsWith('"') && dest.endsWith('"')) {
    const targetRoom = dest.slice(1, -1);
    if (subj) {
      const key = objectKey(targetRoom, subj);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(subj, targetRoom);
      }
      return parseEntityBlock(lines, startI, targetRoom, subj, childIndent - 1, game);
    }
    return startI;
  }

  // -> room: subject appears in current room, parse entity block
  if (dest === 'room') {
    if (subj) {
      const key = objectKey(roomName, subj);
      if (!game.objects[key]) {
        game.objects[key] = createRoomObject(subj, roomName, true);
      } else {
        game.objects[key].discovered = true;
      }
      return parseEntityBlock(lines, startI, roomName, subj, childIndent - 1, game);
    }
    return startI;
  }

  // -> VERBNAME (verb reveal, subject is empty string): no children
  if (!subj) return startI;

  // Verb state restore: VERB__STATE -> VERB (e.g. USE__RESTRAINED -> USE)
  // index.md is parsed first so game.verbs has base verbs by this point
  if (dest in game.verbs) return startI;

  // Entity state transform: ENTITY -> ENTITY__STATE
  // dest is a stated name like TERMINAL__UNLOCKED
  if (isStatedName(dest) && dest !== 'room' && dest !== 'player' && dest !== 'trash') {
    const key = objectKey(roomName, dest);
    if (!game.objects[key]) {
      game.objects[key] = createRoomObject(dest, roomName);
    }
    return parseEntityBlock(lines, startI, roomName, dest, childIndent - 1, game);
  }

  return startI;
}

function parseCueChildrenFull(
  lines: string[],
  startI: number,
  childIndent: number,
  triggerRoom: string,
  targetRoom: string,
  game: GameData,
): { cue: Cue; nextLine: number } {
  let i = startI;
  const narrativeLines: string[] = [];
  const cueArrows: Arrow[] = [];

  while (i < lines.length) {
    const line = lines[i];
    const lineStripped = stripTrailingComment(line).trim();
    if (!lineStripped || isComment(lineStripped)) {
      i++;
      continue;
    }
    if (getIndent(line) < childIndent || isHeader(line)) break;

    const { marker, content } = stripMarker(lineStripped);
    if (marker === '-' && isArrow(content)) {
      const arrow = parseArrow(stripTrailingComment(content));
      cueArrows.push(arrow);
      // Register revealed room objects for "-> room" arrows
      if (arrow.destination === 'room' && arrow.subject) {
        const key = objectKey(targetRoom, arrow.subject);
        if (!game.objects[key]) {
          game.objects[key] = createRoomObject(arrow.subject, targetRoom, true);
        }
      }
      i++;
      // Parse sub-entity block for the cue arrow's destination
      if (arrow.destination === 'room' && arrow.subject) {
        i = parseEntityBlock(lines, i, targetRoom, arrow.subject, getIndent(line), game);
      }
    } else if (isNarrative(lineStripped)) {
      narrativeLines.push(lineStripped);
      i++;
    } else {
      i++;
    }
  }

  const cue = createCue(triggerRoom, targetRoom);
  cue.narrative = narrativeLines.join('\n');
  cue.arrows = cueArrows;
  return { cue, nextLine: i };
}

// ── Parse room body ────────────────────────────────────────────────────────

function parseRoomBody(
  lines: string[],
  startI: number,
  roomName: string,
  game: GameData,
): number {
  let i = startI;

  while (i < lines.length && !isHeader(lines[i])) {
    const line = lines[i];
    const stripped = normalizeStructuralLine(line);
    if (!stripped || isComment(stripped)) {
      i++;
      continue;
    }

    const ind = getIndent(line);

    if (isAction(stripped)) {
      i = parseAction(lines, i, roomName, game);
      continue;
    }

    if (ind === 0) {
      const { marker } = stripMarker(stripped);

      if (!marker && hasColonHeader(stripped) && !isArrow(stripped)) {
        // Room-level interaction: LOOK: desc or VERB + TARGET: ...
        const colonIdx = stripped.indexOf(':');
        const headerPart = stripped.slice(0, colonIdx).trim();
        const afterColon = stripped.slice(colonIdx + 1).trim();

        let verb: string;
        let targetGroups: string[][];

        if (headerPart.includes('+')) {
          const parts = headerPart.split('+').map((p) => p.trim());
          verb = parts[0];
          targetGroups = parts.slice(1).map((p) =>
            p
              .split('|')
              .map((a) => a.trim())
              .filter(Boolean),
          );
        } else {
          verb = headerPart;
          targetGroups = [];
        }

        const interaction = createInteraction(verb, roomName);
        interaction.targetGroups = targetGroups;

        const body = collectInteractionBody(lines, i + 1, 0, roomName, game);
        if (afterColon) {
          interaction.narrative = afterColon;
          if (body.narrative) {
            interaction.narrative += '\n' + body.narrative;
          }
        } else {
          interaction.narrative = body.narrative;
        }
        interaction.arrows = body.arrows;
        interaction.sealedContent = body.sealedContent;
        interaction.sealedArrows = body.sealedArrows;
        interaction.signalChecks = body.signalChecks;

        registerInteraction(game, interaction);
        i = body.nextLine;
      } else if (!marker && isStatedName(stripped) && !isArrow(stripped)) {
        // Bare name at indent 0 = room object
        const objName = stripped;
        const key = objectKey(roomName, objName);
        const existing = game.objects[key];
        game.objects[key] = createRoomObject(
          objName,
          roomName,
          existing?.discovered ?? false,
        );
        i++;
        i = parseEntityBlock(lines, i, roomName, objName, 0, game);
      } else {
        i++;
      }
    } else {
      i++;
    }
  }

  return i;
}

// ── Parse index.md ─────────────────────────────────────────────────────────

function parseIndex(content: string, game: GameData): void {
  const lines = content.split('\n');
  const { meta, nextLine } = parseFrontmatter(lines);

  // Copy metadata (exclude description)
  for (const [k, v] of Object.entries(meta)) {
    game.metadata[k] = v;
  }

  let i = nextLine;

  // Collect description and signal checks between frontmatter and first # section
  const descLines: string[] = [];

  while (i < lines.length) {
    const line = lines[i];
    const stripped = stripTrailingComment(line).trim();
    if (isHeader(line)) break;
    if (!stripped || isComment(stripped)) {
      i++;
      continue;
    }
    if (isSignalCheckLine(stripped)) {
      const startRoom = meta['start'] ?? '';
      const result = parseSignalCheckGroup(lines, i, startRoom);
      game.signalChecks = result.checks;
      i = result.nextLine;
      // Consume trailing blank lines before header
      while (i < lines.length && !isHeader(lines[i]) && !stripTrailingComment(lines[i]).trim()) {
        i++;
      }
      break;
    }
    descLines.push(stripped);
    i++;
  }

  if (descLines.length > 0) {
    // Join paragraph blocks separated by blank lines
    game.metadata['description'] = descLines.join('\n\n');
  }

  // Parse # Verbs and # Inventory sections
  while (i < lines.length) {
    const line = stripTrailingComment(lines[i]).trim();
    if (!line || isComment(line)) {
      i++;
      continue;
    }
    if (isHeader(line)) {
      const { type } = parseHeader(line);
      i++;
      if (type === 'verbs') {
        while (i < lines.length && !isHeader(lines[i])) {
          const w = stripTrailingComment(lines[i]).trim();
          if (w && !isComment(w) && isName(w)) {
            game.verbs[w] = createVerb(w);
          }
          i++;
        }
      } else if (type === 'inventory') {
        while (i < lines.length && !isHeader(lines[i])) {
          const w = stripTrailingComment(lines[i]).trim();
          if (w && !isComment(w) && getIndent(lines[i]) === 0 && isName(w)) {
            game.inventory[w] = createInventoryObject(w);
          }
          i++;
        }
      } else {
        // Unknown global section, skip
      }
    } else {
      i++;
    }
  }
}

// ── Parse room .md file ────────────────────────────────────────────────────

function parseRoomFile(content: string, game: GameData): void {
  const lines = content.split('\n');
  let i = 0;

  // Skip frontmatter in room files
  if (lines.length && lines[0].trim() === '---') {
    const result = parseFrontmatter(lines);
    i = result.nextLine;
  }

  let roomName: string | null = null;

  while (i < lines.length) {
    const line = stripTrailingComment(lines[i]).trim();
    if (!line || isComment(line)) {
      i++;
      continue;
    }
    if (isHeader(line)) {
      const { type, name } = parseHeader(line);
      i++;
      if (type === 'room' && name) {
        roomName = name;
        const { base, state } = splitName(name);
        game.rooms[name] = createRoom(name);
        i = parseRoomBody(lines, i, roomName, game);
      } else if (type === 'interactions') {
        if (roomName) {
          i = parseFreeformInteractions(lines, i, roomName, game);
        }
      }
      // else skip unknown section
    } else {
      i++;
    }
  }
}

// ── Main entry point ───────────────────────────────────────────────────────

/**
 * Parse a map of filename → .md content into a GameData model.
 * Parses index.md first, then all other .md files as room files.
 */
export function parseGameFiles(files: Record<string, string>): GameData {
  const game = createGameData();

  const indexContent = files['index.md'];
  if (indexContent) {
    parseIndex(indexContent, game);
  }

  // Sort non-index files alphabetically (matching Python behavior)
  const roomFiles = Object.entries(files)
    .filter(([name]) => name !== 'index.md' && name.endsWith('.md'))
    .sort(([a], [b]) => a.localeCompare(b));

  for (const [, content] of roomFiles) {
    parseRoomFile(content, game);
  }

  return game;
}

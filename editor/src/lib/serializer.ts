import type {
  GameData,
  Arrow,
  Interaction,
  SignalCheck,
} from './types';

/** Convert a room name to a filename: spaces → underscores, lowercase + .md */
function roomNameToFilename(roomName: string): string {
  return roomName.toLowerCase().replace(/ /g, '_') + '.md';
}

/**
 * Serialize a GameData model into a map of filename → .md content strings.
 * Produces `index.md` and one `{room_name}.md` per base room (state === null).
 */
export function serializeGame(game: GameData): Record<string, string> {
  const result: Record<string, string> = {};

  result['index.md'] = serializeIndex(game);

  for (const room of Object.values(game.rooms)) {
    if (room.state !== null) continue; // skip state variants
    const filename = roomNameToFilename(room.name);
    result[filename] = serializeRoom(game, room.name);
  }

  return result;
}

/** Serialize the index.md file (metadata, verbs, inventory) */
export function serializeIndex(game: GameData): string {
  const lines: string[] = [];

  // Frontmatter
  const metaKeys = Object.keys(game.metadata);
  const descriptionText = game.metadata['description'] ?? '';
  const frontmatterKeys = metaKeys.filter((k) => k !== 'description');

  if (frontmatterKeys.length > 0) {
    lines.push('---');
    for (const key of frontmatterKeys) {
      lines.push(`${key}: ${game.metadata[key]}`);
    }
    lines.push('---');
    lines.push('');
  }

  // Description text (after frontmatter, before sections)
  if (descriptionText) {
    lines.push(descriptionText);
    lines.push('');
  }

  // Index-level signal checks (game.signalChecks)
  if (game.signalChecks.length > 0) {
    for (const check of game.signalChecks) {
      lines.push(...serializeSignalCheck(check, ''));
    }
    lines.push('');
  }

  // Verbs section — skip verbs with __ (they're states)
  const baseVerbs = Object.values(game.verbs).filter(
    (v) => !v.name.includes('__'),
  );
  if (baseVerbs.length > 0) {
    lines.push('# Verbs');
    for (const verb of baseVerbs) {
      lines.push(verb.name);
    }
    lines.push('');
  }

  // Inventory section
  lines.push('# Inventory');
  for (const item of Object.values(game.inventory)) {
    lines.push(item.name);

    // Inventory-level interactions (room === "")
    const itemInteractions = game.interactions.filter(
      (i) =>
        i.room === '' &&
        i.targetGroups.some((group) => group.includes(item.name)),
    );
    for (const interaction of itemInteractions) {
      lines.push(...serializeInteraction(interaction, '  '));
    }
  }
  lines.push('');

  return lines.join('\n');
}

/** Serialize a room .md file */
export function serializeRoom(game: GameData, roomName: string): string {
  const lines: string[] = [];

  lines.push(`# ${roomName}`);

  // Room LOOK description: find interaction with verb=LOOK, room=roomName, empty targetGroups
  const lookInteraction = game.interactions.find(
    (i) =>
      i.verb === 'LOOK' &&
      i.room === roomName &&
      i.targetGroups.length === 0,
  );
  if (lookInteraction && lookInteraction.narrative) {
    lines.push(`LOOK: ${lookInteraction.narrative}`);
    lines.push('');
  }

  // Group objects by base name
  const objectsByBase: Record<string, string[]> = {};
  for (const obj of Object.values(game.objects)) {
    if (obj.room !== roomName) continue;
    if (!objectsByBase[obj.base]) {
      objectsByBase[obj.base] = [];
    }
    objectsByBase[obj.base].push(obj.name);
  }

  // Serialize objects (base first, then states)
  const serializedBases = new Set<string>();
  for (const obj of Object.values(game.objects)) {
    if (obj.room !== roomName) continue;
    if (serializedBases.has(obj.base)) continue;
    serializedBases.add(obj.base);

    const allVariants = objectsByBase[obj.base] ?? [];
    // Base first, then states
    const baseVariant = allVariants.find((n) => !n.includes('__')) ?? allVariants[0];
    const stateVariants = allVariants.filter((n) => n !== baseVariant);

    // Emit base object declaration
    lines.push(baseVariant);

    // Interactions for the base object (those that target baseVariant)
    const baseInteractions = game.interactions.filter(
      (i) =>
        i.room === roomName &&
        i.targetGroups.some((group) => group.includes(baseVariant)),
    );
    for (const interaction of baseInteractions) {
      lines.push(...serializeInteraction(interaction, ''));
    }

    // State variants (sub-objects) with their interactions
    for (const stateVariant of stateVariants) {
      lines.push(`  ${stateVariant}`);
      const stateInteractions = game.interactions.filter(
        (i) =>
          i.room === roomName &&
          i.targetGroups.some((group) => group.includes(stateVariant)),
      );
      for (const interaction of stateInteractions) {
        lines.push(...serializeInteraction(interaction, '  '));
      }
    }

    lines.push('');
  }

  // Actions in this room
  const roomActions = Object.values(game.actions).filter(
    (a) => a.room === roomName,
  );
  for (const action of roomActions) {
    lines.push(`> ${action.name}`);
    if (action.narrative) {
      // Indent narrative lines
      for (const narrativeLine of action.narrative.split('\n')) {
        lines.push(`  ${narrativeLine}`);
      }
    }
    for (const arrow of action.arrows) {
      lines.push(`  - ${serializeArrow(arrow)}`);
    }
    lines.push('');
  }

  // Freeform interactions (## Interactions section)
  // These are interactions that don't target any specific object in this room
  // i.e., interactions in this room not already covered by object blocks
  const coveredObjects = new Set<string>();
  for (const obj of Object.values(game.objects)) {
    if (obj.room === roomName) {
      coveredObjects.add(obj.name);
    }
  }

  const freeformInteractions = game.interactions.filter((i) => {
    if (i.room !== roomName) return false;
    if (i.targetGroups.length === 0) return false; // LOOK description handled above
    // Freeform if none of its targets are in room objects
    const allTargets = i.targetGroups.flat();
    if (allTargets.includes('*')) return true; // wildcard = freeform
    return !allTargets.some((t) => coveredObjects.has(t));
  });

  if (freeformInteractions.length > 0) {
    lines.push('## Interactions');
    lines.push('');
    for (const interaction of freeformInteractions) {
      lines.push(...serializeFreeformInteraction(interaction));
      lines.push('');
    }
  }

  return lines.join('\n');
}

/** Serialize an interaction (attached to an object, indented) */
export function serializeInteraction(
  interaction: Interaction,
  indent: string,
): string[] {
  const lines: string[] = [];

  // Build header: + VERB [+ TARGET1 | ALT + TARGET2]: narrative
  const verbPart = interaction.verb;
  const targetPart = interaction.targetGroups
    .map((group) => group.join(' | '))
    .join(' + ');

  const headerBase =
    `${indent}+ ${verbPart}` + (targetPart ? ` + ${targetPart}` : '');

  const narrative = interaction.narrative;
  const isMultilineNarrative = narrative.includes('\n');

  if (!narrative) {
    lines.push(`${headerBase}:`);
  } else if (isMultilineNarrative) {
    lines.push(`${headerBase}:`);
    for (const narrativeLine of narrative.split('\n')) {
      lines.push(`${indent}  ${narrativeLine}`);
    }
  } else {
    lines.push(`${headerBase}: ${narrative}`);
  }

  // Arrows
  for (const arrow of interaction.arrows) {
    lines.push(`${indent}  - ${serializeArrow(arrow)}`);
    // If this is a cue arrow (subject === '?'), it has no children in this model
  }

  // Signal checks
  for (const check of interaction.signalChecks) {
    lines.push(...serializeSignalCheck(check, `${indent}  `));
  }

  // Sealed content
  if (interaction.sealedContent !== null) {
    lines.push(`${indent}  ::: fragment`);
    for (const contentLine of interaction.sealedContent.split('\n')) {
      lines.push(`${indent}  ${contentLine}`);
    }
    for (const arrow of interaction.sealedArrows) {
      lines.push(`${indent}  - ${serializeArrow(arrow)}`);
    }
    lines.push(`${indent}  :::`);
  }

  return lines;
}

/** Serialize a freeform interaction (in ## Interactions section, unindented header) */
function serializeFreeformInteraction(interaction: Interaction): string[] {
  const lines: string[] = [];

  const verbPart = interaction.verb;
  const targetPart = interaction.targetGroups
    .map((group) => group.join(' | '))
    .join(' + ');

  const headerBase = `${verbPart}` + (targetPart ? ` + ${targetPart}` : '');
  const narrative = interaction.narrative;
  const isMultilineNarrative = narrative.includes('\n');

  if (!narrative) {
    lines.push(`${headerBase}:`);
  } else if (isMultilineNarrative) {
    lines.push(`${headerBase}:`);
    for (const narrativeLine of narrative.split('\n')) {
      lines.push(`  ${narrativeLine}`);
    }
  } else {
    lines.push(`${headerBase}: ${narrative}`);
  }

  for (const arrow of interaction.arrows) {
    lines.push(`  - ${serializeArrow(arrow)}`);
  }

  for (const check of interaction.signalChecks) {
    lines.push(...serializeSignalCheck(check, '  '));
  }

  if (interaction.sealedContent !== null) {
    lines.push('  ::: fragment');
    for (const contentLine of interaction.sealedContent.split('\n')) {
      lines.push(`  ${contentLine}`);
    }
    for (const arrow of interaction.sealedArrows) {
      lines.push(`  - ${serializeArrow(arrow)}`);
    }
    lines.push('  :::');
  }

  return lines;
}

/** Serialize a single arrow: "subject -> destination" or "-> destination" */
export function serializeArrow(arrow: Arrow): string {
  if (!arrow.subject) {
    return `-> ${arrow.destination}`;
  }
  return `${arrow.subject} -> ${arrow.destination}`;
}

/** Serialize a signal check */
export function serializeSignalCheck(
  check: SignalCheck,
  indent: string,
): string[] {
  const lines: string[] = [];

  // Header: "SIGNAL_A + SIGNAL_B?" or "otherwise?"
  if (check.signalNames.length === 0) {
    lines.push(`${indent}otherwise?`);
  } else {
    lines.push(`${indent}${check.signalNames.join(' + ')}?`);
  }

  // Narrative (indented)
  if (check.narrative) {
    for (const narrativeLine of check.narrative.split('\n')) {
      lines.push(`${indent}  ${narrativeLine}`);
    }
  }

  // Arrows (indented)
  for (const arrow of check.arrows) {
    lines.push(`${indent}  - ${serializeArrow(arrow)}`);
  }

  return lines;
}

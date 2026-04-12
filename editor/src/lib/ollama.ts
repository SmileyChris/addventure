import type { GameData } from './types';
import { displayName } from './helpers';

const OLLAMA_URL = 'http://localhost:11434';

export interface OllamaModel {
  name: string;
}

/** Fetch available models from Ollama */
export async function listModels(): Promise<string[]> {
  try {
    const res = await fetch(`${OLLAMA_URL}/api/tags`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.models ?? []).map((m: OllamaModel) => m.name);
  } catch {
    return []; // Ollama not running
  }
}

/** Generate text using Ollama */
export async function generate(model: string, prompt: string): Promise<string> {
  const res = await fetch(`${OLLAMA_URL}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      prompt,
      stream: false,
      options: {
        temperature: 0.8,
        num_predict: 200,
      },
    }),
  });
  if (!res.ok) throw new Error(`Ollama error: ${res.status}`);
  const data = await res.json();
  return data.response?.trim() ?? '';
}

/** Build a rich context string from the game's existing narrative */
export function buildGameContext(game: GameData): string {
  const parts: string[] = [];

  // Game metadata
  if (game.metadata.title) parts.push(`Game: "${game.metadata.title}"`);
  if (game.metadata.author) parts.push(`Author: ${game.metadata.author}`);

  // Opening description sets the tone
  if (game.metadata.description) {
    parts.push(`\nOpening narrative:\n"${game.metadata.description.slice(0, 500)}"`);
  }

  // Sample existing room descriptions to establish voice (up to 3)
  const roomDescriptions: string[] = [];
  for (const interaction of game.interactions) {
    if (interaction.verb === 'LOOK' && interaction.targetGroups.length === 0 && interaction.narrative) {
      roomDescriptions.push(`${interaction.room}: "${interaction.narrative.slice(0, 200)}"`);
    }
    if (roomDescriptions.length >= 3) break;
  }
  if (roomDescriptions.length > 0) {
    parts.push(`\nExisting room descriptions (match this tone):\n${roomDescriptions.join('\n')}`);
  }

  // List all rooms for world context
  const roomNames = Object.values(game.rooms).filter(r => r.state === null).map(r => r.name);
  if (roomNames.length > 0) {
    parts.push(`\nRooms in the game: ${roomNames.join(', ')}`);
  }

  return parts.join('\n');
}

/** Build a prompt for generating a room description */
export function roomDescriptionPrompt(roomName: string, objects: string[], game: GameData): string {
  const context = buildGameContext(game);
  const objectList = objects.map(o => displayName(o)).join(', ');

  return `You are writing descriptions for a paper-based text adventure game. Match the tone and style of the existing writing.

${context}

Write a brief atmospheric description (2-3 sentences) for the room "${roomName}". ${objectList ? `The room contains: ${objectList}.` : ''}

Rules:
- Write only the description text, no labels or formatting
- Match the existing narrative voice and atmosphere
- Be evocative but concise — players read this on paper
- Don't mention game mechanics, only describe the fiction`;
}

/** Build a prompt for generating an interaction narrative */
export function interactionPrompt(verb: string, targets: string[], roomName: string, game: GameData, existingNarrative?: string): string {
  const context = buildGameContext(game);
  const targetStr = targets.map(t => displayName(t)).join(' and ');

  // Include nearby interactions for context
  const nearbyNarratives: string[] = [];
  for (const interaction of game.interactions) {
    if (interaction.room === roomName && interaction.narrative && nearbyNarratives.length < 3) {
      nearbyNarratives.push(`${interaction.verb} + ${interaction.targetGroups.flat().map(t => displayName(t)).join(', ')}: "${interaction.narrative.slice(0, 150)}"`);
    }
  }

  let prompt = `You are writing for a paper-based text adventure game. Match the tone of the existing writing.

${context}

${nearbyNarratives.length > 0 ? `Other interactions in "${roomName}":\n${nearbyNarratives.join('\n')}\n` : ''}
The player is in "${roomName}" and performs "${displayName(verb)}" on "${targetStr}".
Write the result (1-2 sentences).

Rules:
- Write only the narrative text, no labels, no formatting
- Match the existing voice
- Be atmospheric but concise — this is printed on paper`;

  if (existingNarrative) {
    prompt += `\n- Improve or rework this draft: "${existingNarrative}"`;
  }

  return prompt;
}

/** Build a prompt for generating sealed/fragment content */
export function sealedContentPrompt(verb: string, targets: string[], roomName: string, game: GameData): string {
  const context = buildGameContext(game);
  const targetStr = targets.map(t => displayName(t)).join(' and ');

  return `You are writing for a paper-based text adventure game. This is sealed content — a dramatic reveal or secret passage of text.

${context}

The player is in "${roomName}" and triggers this sealed content by using "${displayName(verb)}" on "${targetStr}".
Write a dramatic reveal (3-5 sentences). This is hidden content only shown during a key moment.

Rules:
- Write only the narrative, no labels or formatting
- Match the existing voice and atmosphere
- Be dramatic — this is a payoff moment
- Keep it under 5 sentences — space is limited on paper`;
}

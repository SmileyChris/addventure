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

/** Build a prompt for generating a room description */
export function roomDescriptionPrompt(roomName: string, objects: string[], gameTitle: string): string {
  return `You are writing for a text adventure game called "${gameTitle}". Write a brief atmospheric description (2-3 sentences) of a room called "${roomName}". The room contains these objects: ${objects.join(', ')}. Write only the description, no labels or formatting. Keep it evocative but concise.`;
}

/** Build a prompt for generating an interaction narrative */
export function interactionPrompt(verb: string, targets: string[], roomName: string, gameTitle: string): string {
  const targetStr = targets.join(' and ');
  return `You are writing for a text adventure game called "${gameTitle}". The player is in "${roomName}" and uses the action "${verb}" on "${targetStr}". Write a brief result description (1-2 sentences). Write only the narrative text, no labels or formatting. Be atmospheric and concise.`;
}

/** Build a prompt for generating sealed/fragment content */
export function sealedContentPrompt(verb: string, targets: string[], roomName: string, gameTitle: string): string {
  const targetStr = targets.join(' and ');
  return `You are writing for a text adventure game called "${gameTitle}". The player is in "${roomName}" and discovers a hidden passage or secret after using "${verb}" on "${targetStr}". Write a dramatic reveal (3-5 sentences). This is sealed content only revealed during gameplay. Write only the narrative, no labels or formatting.`;
}

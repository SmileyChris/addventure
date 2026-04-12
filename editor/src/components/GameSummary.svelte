<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';
  import { buildGameContext, generate } from '../lib/ollama';
  import GenerateDialog from './GenerateDialog.svelte';

  let showDescriptionGen = $state(false);
  let narratorPreset = $state('');
  let narratorExtra = $state('');
  let buildingVoice = $state(false);

  const NARRATOR_PRESETS = [
    { label: 'Literary Gothic', value: 'Rich, atmospheric prose. Long flowing sentences with dark undertones. Victorian gothic sensibility.' },
    { label: 'Terse Noir', value: 'Short, punchy sentences. Hardboiled detective style. Dry humor. Cynical observations.' },
    { label: 'Whimsical Fantasy', value: 'Playful and wonder-filled. Fairy tale cadence with a modern wink. Warm and inviting.' },
    { label: 'Clinical Sci-Fi', value: 'Precise, technical language. Detached observation. Sterile environments described with cold clarity.' },
    { label: 'Folksy Warmth', value: 'Conversational, homespun tone. Simple language with deep feeling. Like a story told by the fire.' },
    { label: 'Cosmic Horror', value: 'Creeping dread. Sanity-eroding descriptions. Unknowable forces lurking beyond comprehension.' },
    { label: 'Dry Comedy', value: 'Deadpan observations. Absurd situations described matter-of-factly. Understated humor throughout.' },
    { label: 'Sparse Minimalist', value: 'Bare essentials only. No adjectives wasted. Let the player\'s imagination fill the gaps.' },
    { label: 'Lush Romantic', value: 'Sensory-rich prose. Colors, textures, scents. Emotional resonance in every detail.' },
    { label: 'Pulp Adventure', value: 'Breathless pacing. Exclamation points earned. Bold heroes, dastardly villains, exotic locales.' },
  ];

  async function buildVoice() {
    if (!store.settings.ollamaModel) return;
    buildingVoice = true;
    try {
      const gameCtx = store.game ? `Game title: "${store.game.metadata.title ?? 'Untitled'}"` : '';
      const prompt = `You are helping an author define the narrator voice for a paper-based text adventure game.

${gameCtx}

Base style: ${narratorPreset || 'No preset selected'}
${narratorExtra ? `Additional direction from the author: ${narratorExtra}` : ''}

Write a concise narrator voice description (2-3 sentences) that an AI can use as a style guide when generating game text. Include: tone, sentence structure, vocabulary level, perspective (second person), and any distinctive qualities. Write only the voice description, no labels.`;

      const result = await generate(store.settings.ollamaModel, prompt, store.settings.ollamaThinking, 150);
      store.updateSettings({ ...store.settings, narratorVoice: result });
    } catch (e) {
      console.error('Voice build failed:', e);
    } finally {
      buildingVoice = false;
    }
  }

  function signals() {
    if (!store.game) return [];
    return getSignalEmissions(store.game);
  }

  function baseRooms() {
    if (!store.game) return [];
    return Object.values(store.game.rooms).filter((r) => r.state === null);
  }

  function descriptionContext(): string {
    if (!store.game) return '';
    const ctx = buildGameContext(store.game, store.settings.narratorVoice || undefined);
    const rooms = baseRooms().map(r => r.name).join(', ');
    return `You are writing the opening narrative for a paper-based text adventure game.

${ctx}

${rooms ? `The game has these rooms: ${rooms}` : ''}

Write an atmospheric opening description (2-4 paragraphs) that sets the scene and hooks the player. This text is the first thing players read before they begin exploring.

Rules:
- Write only the narrative text, no labels or formatting
- Set the tone and atmosphere for the entire game
- Be evocative — this is printed on paper and should feel literary
- End with something that propels the player into action`;
  }
</script>

<div class="game-summary">
  <h2>Game Summary</h2>
  {#if store.game}
    <form class="meta-form" onsubmit={(e) => e.preventDefault()}>
      <div class="form-grid">
        <!-- Title -->
        <div class="field">
          <label for="meta-title">Title</label>
          <input
            id="meta-title"
            type="text"
            value={store.game.metadata.title ?? ''}
            oninput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              store.mutate((g) => {
                g.metadata.title = val;
              });
              if (store.project && val.trim()) {
                store.project.name = val.trim();
              }
            }}
          />
        </div>

        <!-- Author -->
        <div class="field">
          <label for="meta-author">Author</label>
          <input
            id="meta-author"
            type="text"
            value={store.game.metadata.author ?? ''}
            oninput={(e) =>
              store.mutate((g) => {
                g.metadata.author = (e.target as HTMLInputElement).value;
              })}
          />
        </div>

        <!-- Start Room -->
        <div class="field">
          <label for="meta-start">Start Room</label>
          <select
            id="meta-start"
            value={store.game.metadata.start ?? ''}
            onchange={(e) =>
              store.mutate((g) => {
                g.metadata.start = (e.target as HTMLSelectElement).value;
              })}
          >
            <option value="">— none —</option>
            {#each baseRooms() as room (room.name)}
              <option value={room.name}>{room.name}</option>
            {/each}
          </select>
        </div>

        <!-- Ledger Prefix -->
        <div class="field field-narrow">
          <label for="meta-prefix">Ledger Prefix</label>
          <input
            id="meta-prefix"
            type="text"
            maxlength="1"
            value={store.game.metadata.ledger_prefix ?? ''}
            oninput={(e) =>
              store.mutate((g) => {
                g.metadata.ledger_prefix = (
                  e.target as HTMLInputElement
                ).value.toUpperCase();
              })}
          />
        </div>

        <!-- Name Style -->
        <div class="field">
          <label for="meta-style">Name Style</label>
          <select
            id="meta-style"
            value={store.game.metadata.name_style ?? 'upper_words'}
            onchange={(e) =>
              store.mutate((g) => {
                g.metadata.name_style = (e.target as HTMLSelectElement).value;
              })}
          >
            <option value="upper_words">UPPER WORDS</option>
            <option value="title">Title Case</option>
          </select>
        </div>
      </div>

      <!-- Narrator Voice (shown when AI is enabled) -->
      {#if store.settings.ollamaEnabled}
        <div class="field field-full narrator-field">
          <div class="narrator-header">
            <label>
              <span class="narrator-label">✦ Narrator Voice</span>
              <span class="narrator-hint">Sets the tone for all AI-generated text</span>
            </label>
          </div>

          <div class="narrator-preset-row">
            <select
              value=""
              onchange={(e) => {
                const val = (e.target as HTMLSelectElement).value;
                if (val) {
                  narratorPreset = val;
                  narratorExtra = '';
                }
                (e.target as HTMLSelectElement).value = '';
              }}
            >
              <option value="">Choose a style...</option>
              {#each NARRATOR_PRESETS as preset}
                <option value={preset.value}>{preset.label}</option>
              {/each}
            </select>
          </div>

          <textarea
            rows="2"
            value={narratorExtra}
            oninput={(e) => narratorExtra = (e.target as HTMLTextAreaElement).value}
            placeholder="Extra direction... (e.g. set in the 1920s, noir detective feel)"
          ></textarea>

          <div class="narrator-actions">
            <button
              class="btn-build-voice"
              onclick={buildVoice}
              disabled={buildingVoice || (!narratorPreset && !narratorExtra) || !store.settings.ollamaModel}
            >
              {buildingVoice ? 'Building...' : '✦ Build Voice'}
            </button>
          </div>

          {#if store.settings.narratorVoice}
            <div class="narrator-result">
              <span class="narrator-result-label">Active voice:</span>
              <p class="narrator-result-text">{store.settings.narratorVoice}</p>
              <button class="narrator-clear" onclick={() => store.updateSettings({ ...store.settings, narratorVoice: '' })}>Clear</button>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Description -->
      <div class="field field-full">
        <div class="label-row">
          <label for="meta-description">Description</label>
          {#if store.settings.ollamaEnabled && store.settings.ollamaModel}
            <button class="ai-btn" onclick={() => showDescriptionGen = true} title="Generate with AI">✦ AI</button>
          {/if}
        </div>
        <textarea
          id="meta-description"
          rows="6"
          value={store.game.metadata.description ?? ''}
          oninput={(e) =>
            store.mutate((g) => {
              g.metadata.description = (e.target as HTMLTextAreaElement).value;
            })}
          placeholder="Opening narrative that sets the scene for the player..."
        ></textarea>
      </div>

      {#if showDescriptionGen}
        <GenerateDialog
          context={descriptionContext()}
          label="Opening Description"
          ongenerated={(text) => store.mutate((g) => { g.metadata.description = text; })}
          onclose={() => showDescriptionGen = false}
        />
      {/if}

      <!-- Signal Checks -->
      {#if signals().length > 0}
        <div class="field field-full signals-section">
          <span class="label-text">Signal Checks</span>
          <p class="hint">
            This game uses {signals().length} signal{signals().length === 1
              ? ''
              : 's'}. Signal checks are defined inline in room interactions and
            cannot be edited here — edit them in the room where they occur.
          </p>
          <ul class="signal-list">
            {#each signals() as sig}
              <li><span class="signal-chip">{sig}</span></li>
            {/each}
          </ul>
        </div>
      {/if}
    </form>
  {:else}
    <p class="hint">No game loaded.</p>
  {/if}
</div>

<style>
  .game-summary {
    padding: 2rem;
    max-width: 680px;
  }

  h2 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 1.5rem;
  }

  .meta-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .field-narrow input {
    width: 60px;
  }

  .field-full {
    grid-column: 1 / -1;
  }

  label,
  .label-text {
    font-family: var(--font-title);
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-mid);
  }

  input,
  select,
  textarea {
    background-color: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.9rem;
    padding: 0.4em 0.6em;
    transition: border-color 0.15s;
  }

  input:focus,
  select:focus,
  textarea:focus {
    outline: none;
    border-color: var(--gold-dim);
  }

  textarea {
    resize: vertical;
    width: 100%;
    box-sizing: border-box;
  }

  select {
    cursor: pointer;
  }

  .signals-section {
    border-top: 1px solid var(--warm-gray);
    padding-top: 1rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.85rem;
    margin: 0.4rem 0;
    line-height: 1.5;
  }

  .signal-list {
    list-style: none;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.5rem;
  }

  .signal-chip {
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    padding: 0.2em 0.6em;
    border-radius: 2px;
  }

  .label-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .ai-btn {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    padding: 1px 6px;
    background: none;
    color: var(--gold-dim);
    border: 1px solid var(--gold-dim);
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .ai-btn:hover {
    color: var(--gold);
    border-color: var(--gold);
    background: rgba(201, 168, 76, 0.1);
  }

  /* Narrator Voice */
  .narrator-field {
    background: rgba(201, 168, 76, 0.03);
    border: 1px solid rgba(201, 168, 76, 0.1);
    border-radius: 8px;
    padding: 16px;
  }

  .narrator-header {
    margin-bottom: 10px;
  }

  .narrator-label {
    font-family: var(--font-title);
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
  }

  .narrator-hint {
    display: block;
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-top: 2px;
  }

  .narrator-preset-row {
    margin-bottom: 8px;
  }

  .narrator-preset-row select {
    width: 100%;
    font-size: 0.9rem;
    padding: 6px 10px;
  }

  .narrator-field textarea {
    width: 100%;
    font-size: 0.85rem;
    resize: vertical;
    margin-bottom: 8px;
  }

  .narrator-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
  }

  .btn-build-voice {
    font-family: var(--font-title);
    font-weight: 800;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 6px 14px;
    background: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .btn-build-voice:hover:not(:disabled) {
    background: var(--gold);
    color: var(--black);
  }

  .btn-build-voice:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .narrator-result {
    background: var(--mid-dark);
    border-radius: 6px;
    padding: 10px 12px;
    position: relative;
  }

  .narrator-result-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gold-dim);
    display: block;
    margin-bottom: 4px;
  }

  .narrator-result-text {
    font-size: 0.85rem;
    color: var(--text-light);
    line-height: 1.5;
    margin: 0;
  }

  .narrator-clear {
    position: absolute;
    top: 8px;
    right: 8px;
    font-size: 0.7rem;
    padding: 2px 6px;
    background: none;
    color: var(--text-dim);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
  }

  .narrator-clear:hover {
    color: var(--red-ink);
    border-color: var(--red-ink);
  }
</style>

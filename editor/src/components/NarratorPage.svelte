<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { generate } from '../lib/ollama';

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
</script>

<div class="narrator-page">
  <h2>✦ Narrator Voice</h2>
  <p class="subtitle">Define the tone and style for all AI-generated text across your game.</p>

  <div class="voice-builder">
    <div class="field">
      <label for="narrator-preset">Style Preset</label>
      <select id="narrator-preset" bind:value={narratorPreset}>
        <option value="">Choose a style...</option>
        {#each NARRATOR_PRESETS as preset}
          <option value={preset.value}>{preset.label}</option>
        {/each}
      </select>
      {#if narratorPreset}
        <p class="preset-desc">{narratorPreset}</p>
      {/if}
    </div>

    <div class="field">
      <label for="narrator-extra">Extra Direction</label>
      <textarea
        id="narrator-extra"
        rows="3"
        bind:value={narratorExtra}
        placeholder="e.g. Set in the 1920s, noir detective feel, rural New Zealand backdrop..."
      ></textarea>
    </div>

    <button
      class="btn-build"
      onclick={buildVoice}
      disabled={buildingVoice || (!narratorPreset && !narratorExtra) || !store.settings.ollamaModel}
    >
      {buildingVoice ? 'Building...' : '✦ Build Voice'}
    </button>
  </div>

  {#if store.settings.narratorVoice}
    <div class="active-voice">
      <div class="voice-header">
        <span class="voice-label">Active Voice</span>
        <button class="voice-clear" onclick={() => store.updateSettings({ ...store.settings, narratorVoice: '' })}>Clear</button>
      </div>
      <p class="voice-text">{store.settings.narratorVoice}</p>
    </div>
  {:else}
    <div class="no-voice">
      <p>No narrator voice set. Choose a preset and/or add direction, then click "Build Voice" to generate one.</p>
      <p>The voice guides all AI-generated descriptions — room text, interaction narratives, and sealed content will match this tone.</p>
    </div>
  {/if}
</div>

<style>
  .narrator-page {
    max-width: 640px;
    margin: 0 auto;
    padding: 2rem;
  }

  h2 {
    font-family: var(--font-title);
    font-size: 1.2rem;
    font-weight: 900;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.3rem;
  }

  .subtitle {
    color: var(--text-mid);
    font-size: 0.9rem;
    margin-bottom: 2rem;
  }

  .voice-builder {
    background: rgba(201, 168, 76, 0.03);
    border: 1px solid rgba(201, 168, 76, 0.1);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 1.5rem;
  }

  .field {
    margin-bottom: 1rem;
  }

  .field label {
    display: block;
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-mid);
    margin-bottom: 4px;
  }

  .field select, .field textarea {
    width: 100%;
    font-size: 0.9rem;
  }

  .preset-desc {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-style: italic;
    margin-top: 4px;
  }

  .btn-build {
    font-family: var(--font-title);
    font-weight: 800;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 8px 20px;
    background: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .btn-build:hover:not(:disabled) {
    background: var(--gold);
    color: var(--black);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(201, 168, 76, 0.3);
  }

  .btn-build:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .active-voice {
    background: var(--mid-dark);
    border-radius: 8px;
    padding: 16px;
  }

  .voice-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .voice-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--gold-dim);
  }

  .voice-clear {
    font-size: 0.7rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    padding: 2px 8px;
    background: none;
    color: var(--text-dim);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
  }

  .voice-clear:hover {
    color: var(--red-ink);
    border-color: var(--red-ink);
  }

  .voice-text {
    font-size: 0.9rem;
    color: var(--text-light);
    line-height: 1.6;
  }

  .no-voice {
    color: var(--text-dim);
    font-size: 0.85rem;
    font-style: italic;
    line-height: 1.5;
  }

  .no-voice p + p {
    margin-top: 0.5rem;
  }
</style>

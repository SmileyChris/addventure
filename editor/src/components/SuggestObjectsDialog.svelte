<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { generate, buildGameContext } from '../lib/ollama';
  import { displayName } from '../lib/helpers';

  interface Props {
    roomName: string;
    existingObjects: string[];
    onselected: (items: { name: string; description: string }[]) => void;
    onclose: () => void;
  }

  let { roomName, existingObjects, onselected, onclose }: Props = $props();

  let direction = $state('');
  let loading = $state(false);
  let error = $state('');
  let suggestions = $state<{ name: string; description: string; selected: boolean }[]>([]);

  function focusEl(el: HTMLElement) {
    el.focus();
  }

  async function handleGenerate() {
    const model = store.settings.ollamaModel;
    if (!model || !store.game) return;

    loading = true;
    error = '';
    suggestions = [];

    const ctx = buildGameContext(store.game, store.settings.narratorVoice || undefined);
    const existingList = existingObjects.length > 0
      ? `\nObjects already in this room: ${existingObjects.join(', ')}`
      : '';

    const prompt = `${ctx}
${existingList}

Suggest 6-8 objects that would belong in a room called "${roomName}" in this game.
${direction ? `Author direction: ${direction}` : ''}

Respond with exactly one object per line in this format (example):
RUSTY_KEY: A tarnished brass key with worn teeth
WOODEN_CRATE: A heavy crate nailed shut

Rules:
- Each line is a name, then a colon, then a brief description
- Names are UPPER_CASE_WITH_UNDERSCORES (like SHEARING_TABLE or WOOL_BALE)
- Do NOT use generic names like OBJECT_1 — use descriptive, specific names
- Don't suggest objects already in the room
- Each description should be 5-10 words
- Include a mix of interactive and atmospheric objects
- No numbering, no bullets, no extra text`;

    try {
      const result = await generate(model, prompt, store.settings.ollamaThinking, 400);
      const lines = result.split('\n').filter(l => l.trim());
      const parsed: { name: string; description: string; selected: boolean }[] = [];

      for (const line of lines) {
        // Strip leading numbers, bullets, dashes
        const cleaned = line.replace(/^\s*[\d.\-*•]+\s*/, '');
        const match = cleaned.match(/^([A-Z][A-Z0-9_]*)\s*:\s*(.+)$/);
        if (match) {
          const name = match[1];
          // Skip if already exists
          if (!existingObjects.includes(name)) {
            parsed.push({
              name,
              description: match[2].trim(),
              selected: false,
            });
          }
        }
      }

      if (parsed.length === 0) {
        error = 'No valid suggestions parsed. Try again.';
      } else {
        suggestions = parsed;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Generation failed';
    } finally {
      loading = false;
    }
  }

  function toggleSuggestion(idx: number) {
    suggestions[idx].selected = !suggestions[idx].selected;
  }

  function handleAdd() {
    const selected = suggestions.filter(s => s.selected).map(s => ({ name: s.name, description: s.description }));
    if (selected.length > 0) {
      onselected(selected);
    }
    onclose();
  }

  const selectedCount = $derived(suggestions.filter(s => s.selected).length);

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose();
  }

  const ns = $derived(store.game?.metadata.name_style ?? 'upper_words');
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="overlay" onclick={onclose} onkeydown={handleKeydown} role="dialog" aria-label="Suggest objects">
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div class="dialog" onclick={(e) => e.stopPropagation()} onkeydown={handleKeydown}>
    <h3>Suggest Objects for {roomName}</h3>

    {#if suggestions.length === 0}
      <p class="hint">Describe what kind of room this is, or leave blank for general suggestions.</p>

      <textarea
        class="direction-input"
        rows="2"
        bind:value={direction}
        placeholder="e.g. An old chemistry lab with broken equipment..."
        use:focusEl
        onkeydown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate(); }}
      ></textarea>

      {#if error}
        <p class="error">{error}</p>
      {/if}

      <div class="actions">
        <button class="btn-cancel" onclick={onclose}>Cancel</button>
        <button
          class="btn-generate"
          onclick={handleGenerate}
          disabled={loading}
        >
          {loading ? 'Thinking...' : '✦ Suggest Objects'}
        </button>
      </div>
    {:else}
      <p class="hint">Click to select objects to add to the room.</p>

      <div class="suggestion-list">
        {#each suggestions as suggestion, idx}
          <button
            class="suggestion-item"
            class:selected={suggestion.selected}
            onclick={() => toggleSuggestion(idx)}
          >
            <span class="check">{suggestion.selected ? '✓' : ''}</span>
            <div class="suggestion-info">
              <span class="suggestion-name">{displayName(suggestion.name, ns)}</span>
              <span class="suggestion-desc">{suggestion.description}</span>
            </div>
          </button>
        {/each}
      </div>

      <div class="actions">
        <button class="btn-cancel" onclick={() => { suggestions = []; error = ''; }}>← Back</button>
        <button class="btn-cancel" onclick={onclose}>Cancel</button>
        <button
          class="btn-add"
          onclick={handleAdd}
          disabled={selectedCount === 0}
        >
          Add {selectedCount} object{selectedCount !== 1 ? 's' : ''}
        </button>
      </div>
    {/if}

    <p class="shortcut">Ctrl+Enter to generate · Esc to cancel</p>
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }

  .dialog {
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 12px;
    padding: 24px;
    width: 100%;
    max-width: 520px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  }

  h3 {
    font-family: var(--font-title);
    font-size: 1rem;
    color: var(--gold);
    margin-bottom: 0.5rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }

  .direction-input {
    width: 100%;
    resize: vertical;
    font-family: var(--font-body);
    font-size: 0.95rem;
    padding: 10px 12px;
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 6px;
    color: var(--text-light);
    margin-bottom: 1rem;
  }

  .direction-input::placeholder {
    color: var(--text-dim);
    font-style: italic;
  }

  .direction-input:focus {
    outline: none;
    border-color: var(--gold);
  }

  .error {
    color: var(--red-ink);
    font-size: 0.8rem;
    margin-bottom: 0.75rem;
  }

  .suggestion-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 1rem;
    max-height: 320px;
    overflow-y: auto;
  }

  .suggestion-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    text-align: left;
    padding: 10px 12px;
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 6px;
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .suggestion-item:hover {
    border-color: var(--gold-dim);
    background: var(--dark);
  }

  .suggestion-item.selected {
    border-color: var(--gold);
    background: rgba(201, 168, 76, 0.08);
  }

  .check {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1.5px solid var(--warm-gray);
    border-radius: 4px;
    font-size: 0.75rem;
    color: var(--gold);
    flex-shrink: 0;
  }

  .suggestion-item.selected .check {
    border-color: var(--gold);
    background: rgba(201, 168, 76, 0.15);
  }

  .suggestion-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .suggestion-name {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.85rem;
    color: var(--parchment-light);
  }

  .suggestion-desc {
    font-size: 0.78rem;
    color: var(--text-dim);
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn-cancel {
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    background: var(--mid-dark);
    color: var(--text-mid);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
  }

  .btn-cancel:hover {
    background: var(--warm-gray);
    color: var(--text-light);
  }

  .btn-generate {
    padding: 0.5rem 1.2rem;
    font-size: 0.8rem;
    font-family: var(--font-title);
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: var(--gold);
    color: var(--black);
    border: none;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .btn-generate:hover:not(:disabled) {
    background: var(--gold-bright);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(201, 168, 76, 0.3);
  }

  .btn-generate:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .btn-add {
    padding: 0.5rem 1.2rem;
    font-size: 0.8rem;
    font-family: var(--font-title);
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: var(--gold);
    color: var(--black);
    border: none;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .btn-add:hover:not(:disabled) {
    background: var(--gold-bright);
    transform: translateY(-1px);
  }

  .btn-add:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .shortcut {
    text-align: center;
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-top: 0.75rem;
    font-family: var(--font-mono);
  }
</style>

<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { generate } from '../lib/ollama';

  interface Props {
    /** Base context to include in the prompt */
    context: string;
    /** What kind of content is being generated */
    label: string;
    /** Called with the generated text */
    ongenerated: (text: string) => void;
    /** Called to close the dialog */
    onclose: () => void;
  }

  let { context, label, ongenerated, onclose }: Props = $props();

  let direction = $state('');
  let loading = $state(false);
  let error = $state('');

  function focusEl(el: HTMLElement) {
    el.focus();
  }

  async function handleGenerate() {
    const model = store.settings.ollamaModel;
    if (!model) return;

    loading = true;
    error = '';

    const prompt = `${context}

${direction ? `Author's direction: ${direction}\n` : ''}
Write only the text content. No labels, no formatting, no quotation marks.`;

    try {
      const result = await generate(model, prompt, store.settings.ollamaThinking);
      ongenerated(result);
      onclose();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Generation failed';
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose();
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerate();
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="overlay" onclick={onclose} onkeydown={handleKeydown} role="dialog" aria-label="Generate {label}">
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div class="dialog" onclick={(e) => e.stopPropagation()} onkeydown={handleKeydown}>
    <h3>Generate {label}</h3>
    <p class="hint">Give the AI some direction for what you'd like, or leave blank for a general suggestion.</p>

    <textarea
      class="direction-input"
      rows="3"
      bind:value={direction}
      placeholder="e.g. Dark and foreboding, the facility has been abandoned for years..."
      use:focusEl
    ></textarea>

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn-cancel" onclick={onclose}>Cancel</button>
      <button
        class="btn-generate"
        onclick={handleGenerate}
        disabled={loading || !store.settings.ollamaModel}
      >
        {#if loading}
          Generating…
        {:else}
          ✦ Generate
        {/if}
      </button>
    </div>

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
    max-width: 480px;
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

  .shortcut {
    text-align: center;
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-top: 0.75rem;
    font-family: var(--font-mono);
  }
</style>

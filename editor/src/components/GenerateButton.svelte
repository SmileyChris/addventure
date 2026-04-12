<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { generate } from '../lib/ollama';

  interface Props {
    prompt: string;
    ongenerated: (text: string) => void;
  }

  let { prompt, ongenerated }: Props = $props();

  let loading = $state(false);
  let error = $state(false);

  const isActive = $derived(
    store.settings.ollamaEnabled && !!store.settings.ollamaModel,
  );

  async function handleClick() {
    if (loading || !isActive) return;
    loading = true;
    error = false;
    try {
      const text = await generate(store.settings.ollamaModel, prompt);
      ongenerated(text);
    } catch (e) {
      console.error('Ollama generation error:', e);
      error = true;
      setTimeout(() => {
        error = false;
      }, 1500);
    } finally {
      loading = false;
    }
  }
</script>

{#if isActive}
  <button
    class="generate-btn"
    class:loading
    class:error
    onclick={handleClick}
    disabled={loading}
    title="Generate with AI"
    aria-label="Generate with AI"
  >
    {#if loading}
      <span class="spinner" aria-hidden="true"></span>
    {:else}
      ✦
    {/if}
  </button>
{/if}

<style>
  .generate-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    line-height: 1;
    color: var(--gold-dim);
    background: none;
    border: none;
    padding: 0 2px;
    cursor: pointer;
    transition: color 0.15s;
    min-width: 16px;
    min-height: 16px;
    flex-shrink: 0;
  }

  .generate-btn:hover:not(:disabled) {
    color: var(--gold);
    background: none;
  }

  .generate-btn:disabled {
    cursor: not-allowed;
  }

  .generate-btn.error {
    color: var(--red-ink);
  }

  .spinner {
    display: inline-block;
    width: 8px;
    height: 8px;
    border: 1.5px solid var(--gold-dim);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>

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
      const text = await generate(store.settings.ollamaModel, prompt, store.settings.ollamaThinking);
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
    class="ai-btn"
    class:ai-error={error}
    onclick={handleClick}
    disabled={loading}
    title="Generate with AI"
    aria-label="Generate with AI"
  >
    {#if loading}
      <span class="ai-spinner" aria-hidden="true"></span>
    {:else}
      ✦ AI
    {/if}
  </button>
{/if}

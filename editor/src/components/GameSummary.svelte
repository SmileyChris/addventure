<script lang="ts">
  import { store } from '../lib/store.svelte';
</script>

<div class="game-summary">
  <h2>Game Summary</h2>
  {#if store.game}
    <p class="hint">
      Title: <strong>{store.game.metadata.title ?? 'Untitled'}</strong>
    </p>
    <p class="hint">
      Edit metadata, verbs, inventory, and global settings here.
    </p>
  {:else}
    <p class="hint">No game loaded.</p>
  {/if}
</div>

<style>
  .game-summary {
    padding: 2rem;
  }

  h2 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 1rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
  }

  .hint strong {
    color: var(--text-light);
  }
</style>

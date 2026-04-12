<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';

  function signals() {
    if (!store.game) return [];
    return getSignalEmissions(store.game);
  }

  function baseRooms() {
    if (!store.game) return [];
    return Object.values(store.game.rooms).filter((r) => r.state === null);
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

      <!-- Description -->
      <div class="field field-full">
        <label for="meta-description">Description</label>
        <textarea
          id="meta-description"
          rows="6"
          value={store.game.metadata.description ?? ''}
          oninput={(e) =>
            store.mutate((g) => {
              g.metadata.description = (e.target as HTMLTextAreaElement).value;
            })}
        ></textarea>
      </div>

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
</style>

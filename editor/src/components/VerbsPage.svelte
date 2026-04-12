<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { displayName } from '../lib/helpers';

  function nameStyle(): string {
    return store.game?.metadata.name_style ?? 'upper_words';
  }

  function verbs() {
    if (!store.game) return [];
    return Object.values(store.game.verbs);
  }

  function isStateVerb(name: string) {
    return name.includes('__');
  }

  // Delete verb
  let pendingDelete = $state<string | null>(null);

  function deleteVerb(name: string) {
    if (pendingDelete === name) {
      store.mutate((g) => {
        delete g.verbs[name];
      });
      pendingDelete = null;
    } else {
      pendingDelete = name;
    }
  }

  function cancelDelete() {
    pendingDelete = null;
  }

  // Add verb
  let addingVerb = $state(false);
  let newVerbName = $state('');

  function focusEl(el: HTMLElement) {
    el.focus();
  }

  function normalizeIdentifier(val: string) {
    return val.toUpperCase().replace(/ /g, '_');
  }

  function startAddVerb() {
    addingVerb = true;
    newVerbName = '';
    pendingDelete = null;
  }

  function commitVerb() {
    const name = normalizeIdentifier(newVerbName.trim());
    if (!name) { cancelVerb(); return; }
    if (store.game?.verbs[name]) { cancelVerb(); return; }
    store.addVerb(name);
    cancelVerb();
  }

  function cancelVerb() {
    addingVerb = false;
    newVerbName = '';
  }

  function onVerbKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); commitVerb(); }
    else if (e.key === 'Escape') cancelVerb();
  }
</script>

<div class="verbs-page">
  <div class="page-header">
    <h2>Verbs</h2>
    <p class="hint">
      Verbs are actions players can attempt. Each verb gets a unique ID at build time.
      State verbs (containing <code>__</code>) are automatically created from entity state transitions.
    </p>
  </div>

  {#if store.game}
    <div class="verb-list">
      {#each verbs() as verb (verb.name)}
        <div class="verb-row" class:state-verb={isStateVerb(verb.name)}>
          <div class="verb-info">
            <span class="verb-name">{verb.name}</span>
            <span class="verb-display">{displayName(verb.name, nameStyle())}</span>
          </div>
          <div class="verb-badges">
            {#if isStateVerb(verb.name)}
              <span class="badge badge-state">state</span>
            {/if}
          </div>
          <div class="verb-actions">
            {#if pendingDelete === verb.name}
              <span class="confirm-text">Delete?</span>
              <button class="btn-confirm-delete" onclick={() => deleteVerb(verb.name)}>Yes</button>
              <button class="btn-cancel" onclick={cancelDelete}>No</button>
            {:else}
              <button class="btn-delete" onclick={() => deleteVerb(verb.name)} title="Delete verb">✕</button>
            {/if}
          </div>
        </div>
      {/each}

      {#if verbs().length === 0}
        <p class="empty-message">No verbs yet. Add one below.</p>
      {/if}
    </div>

    <!-- Add form -->
    {#if addingVerb}
      <div class="add-form">
        <input
          type="text"
          placeholder="VERB_NAME…"
          bind:value={newVerbName}
          oninput={(e) => { newVerbName = normalizeIdentifier((e.target as HTMLInputElement).value); }}
          onkeydown={onVerbKeydown}
          onblur={cancelVerb}
          use:focusEl
        />
        <button class="btn-commit" onmousedown={(e) => { e.preventDefault(); commitVerb(); }}>Add</button>
        <button class="btn-cancel" onmousedown={(e) => { e.preventDefault(); cancelVerb(); }}>Cancel</button>
      </div>
    {:else}
      <button class="btn-add-verb" onclick={startAddVerb}>+ Add Verb</button>
    {/if}
  {:else}
    <p class="hint">No game loaded.</p>
  {/if}
</div>

<style>
  .verbs-page {
    padding: 2rem;
    max-width: 700px;
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  h2 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.5rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.85rem;
    line-height: 1.5;
    margin: 0;
  }

  code {
    font-family: var(--font-mono);
    background-color: var(--mid-dark);
    padding: 0.1em 0.3em;
    border-radius: 2px;
    font-size: 0.8em;
    color: var(--parchment);
  }

  /* ── Verb list ──────────────────────── */
  .verb-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 1rem;
  }

  .verb-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    background-color: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    transition: border-color 0.15s;
  }

  .verb-row:hover {
    border-color: var(--parchment-dark);
  }

  .verb-row.state-verb {
    opacity: 0.7;
  }

  .verb-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }

  .verb-name {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--parchment-light);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .verb-display {
    font-family: var(--font-body);
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .verb-badges {
    display: flex;
    gap: 0.3rem;
  }

  .verb-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-shrink: 0;
  }

  /* ── Badges ────────────────────────── */
  .badge {
    font-family: var(--font-title);
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.1em 0.4em;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .badge-state {
    background-color: var(--amber);
    color: var(--black);
  }

  /* ── Buttons ────────────────────────── */
  .btn-delete {
    background: none;
    border: none;
    color: var(--text-dim);
    font-size: 0.75rem;
    padding: 0.2em 0.5em;
    border-radius: 2px;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
    opacity: 0;
  }

  .verb-row:hover .btn-delete {
    opacity: 1;
  }

  .btn-delete:hover {
    color: var(--red-ink);
    background-color: rgba(180, 60, 60, 0.1);
  }

  .confirm-text {
    font-family: var(--font-title);
    font-size: 0.7rem;
    color: var(--red-ink);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .btn-confirm-delete {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2em 0.6em;
    background-color: var(--red-ink);
    color: var(--parchment-light);
    border: none;
    border-radius: 2px;
    cursor: pointer;
  }

  .btn-cancel {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2em 0.6em;
    background: none;
    color: var(--text-dim);
    border: 1px solid var(--warm-gray);
    border-radius: 2px;
    cursor: pointer;
  }

  .btn-cancel:hover {
    color: var(--parchment);
    border-color: var(--parchment-dark);
  }

  /* ── Add form ────────────────────────── */
  .add-form {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background-color: var(--mid-dark);
    border: 1px solid var(--gold-dim);
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .add-form input {
    flex: 1;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    padding: 0.3em 0.5em;
    background-color: var(--dark);
    border: 1px solid var(--warm-gray);
    border-radius: 2px;
    color: var(--text-light);
    min-width: 0;
  }

  .add-form input:focus {
    outline: none;
    border-color: var(--gold);
  }

  .btn-commit {
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.3em 0.8em;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 2px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .btn-commit:hover {
    background-color: var(--gold);
    color: var(--black);
  }

  .btn-add-verb {
    font-family: var(--font-title);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.4em 1em;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
    margin-bottom: 1rem;
  }

  .btn-add-verb:hover {
    background-color: var(--gold);
    color: var(--black);
  }

  .empty-message {
    color: var(--text-dim);
    font-style: italic;
    font-size: 0.85rem;
    padding: 0.5rem 0;
  }
</style>

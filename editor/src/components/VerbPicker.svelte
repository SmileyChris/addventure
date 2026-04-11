<script lang="ts">
  import { store } from '../lib/store.svelte';

  interface Props {
    value: string;
    onchange: (v: string) => void;
  }

  let { value, onchange }: Props = $props();

  let filterText = $state(() => value);
  let open = $state(false);
  let containerEl = $state<HTMLDivElement | null>(null);

  const allVerbs = $derived(store.game ? Object.keys(store.game.verbs) : []);

  const filtered = $derived.by(() => {
    const q = filterText.toUpperCase().trim();
    if (!q) return allVerbs;
    return allVerbs.filter((v) => v.includes(q));
  });

  const showCreate = $derived.by(() => {
    const q = filterText.toUpperCase().trim();
    if (!q) return false;
    return !allVerbs.some((v) => v === q);
  });

  function isStateVerb(verb: string): boolean {
    return verb.includes('__');
  }

  function select(verb: string) {
    filterText = verb;
    open = false;
    onchange(verb);
  }

  function createAndSelect() {
    const name = filterText.toUpperCase().trim();
    if (!name) return;
    store.addVerb(name);
    select(name);
  }

  function handleInput(e: Event) {
    filterText = (e.target as HTMLInputElement).value.toUpperCase();
    open = true;
  }

  function handleFocus() {
    open = true;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      open = false;
    } else if (e.key === 'Enter') {
      if (filtered.length === 1) {
        select(filtered[0]);
      } else if (filtered.length === 0 && showCreate) {
        createAndSelect();
      }
    }
  }

  function handleBlur(e: FocusEvent) {
    // Close if focus leaves the container
    const related = e.relatedTarget as Node | null;
    if (containerEl && related && containerEl.contains(related)) return;
    open = false;
  }
</script>

<div class="verb-picker" bind:this={containerEl}>
  <input
    type="text"
    class="verb-input"
    value={filterText}
    placeholder="VERB"
    oninput={handleInput}
    onfocus={handleFocus}
    onblur={handleBlur}
    onkeydown={handleKeydown}
  />
  {#if open && (filtered.length > 0 || showCreate)}
    <div class="dropdown" role="listbox">
      {#each filtered as verb (verb)}
        <button
          class="dropdown-item"
          role="option"
          aria-selected={verb === value}
          onmousedown={() => select(verb)}
        >
          <span class="verb-name">{verb}</span>
          {#if isStateVerb(verb)}
            <span class="badge-state">state</span>
          {/if}
        </button>
      {/each}
      {#if showCreate}
        <button
          class="dropdown-item create-item"
          role="option"
          aria-selected={false}
          onmousedown={createAndSelect}
        >
          + Create <span class="create-name">{filterText.toUpperCase().trim()}</span>
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .verb-picker {
    position: relative;
    display: inline-block;
    width: 100%;
  }

  .verb-input {
    width: 100%;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 200;
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    margin-top: 2px;
    max-height: 200px;
    overflow-y: auto;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 5px 10px;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: none;
    border-radius: 0;
    color: var(--text-light);
    text-align: left;
    cursor: pointer;
    transition: background-color 0.1s;
  }

  .dropdown-item:hover {
    background: rgba(201, 168, 76, 0.12);
    color: var(--parchment-light);
  }

  .verb-name {
    flex: 1;
    font-family: var(--font-mono);
  }

  .badge-state {
    font-family: var(--font-title);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 1px 5px;
    border-radius: 3px;
    background: rgba(212, 136, 58, 0.25);
    color: var(--amber);
    flex-shrink: 0;
  }

  .create-item {
    color: var(--text-dim);
    border-top: 1px solid var(--warm-gray);
    font-style: italic;
  }

  .create-item:hover {
    color: var(--gold);
  }

  .create-name {
    font-style: normal;
    font-weight: 700;
    color: var(--gold);
  }
</style>

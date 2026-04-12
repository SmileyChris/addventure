<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getObjectInteractions } from '../lib/helpers';
  import { createInteraction, objectKey } from '../lib/factory';
  import InteractionCard from './InteractionCard.svelte';
  import InteractionEditor from './InteractionEditor.svelte';

  interface Props {
    objectName: string;
    roomName: string;
  }

  let { objectName, roomName }: Props = $props();

  let expanded = $state(false);
  let activeState = $state<string | null>(null);
  let editingIdx = $state<number | null>(null);

  const effectiveActiveState = $derived(activeState ?? objectName);

  /** All objects in game with this base name and room */
  const allStates = $derived.by(() => {
    if (!store.game) return [objectName];
    const variants: string[] = [];
    for (const obj of Object.values(store.game.objects)) {
      if (obj.room === roomName && obj.base === objectName) {
        variants.push(obj.name);
      }
    }
    // Sort: base object first (name === base), then alphabetically
    variants.sort((a, b) => {
      if (a === objectName && b !== objectName) return -1;
      if (b === objectName && a !== objectName) return 1;
      return a.localeCompare(b);
    });
    return variants.length > 0 ? variants : [objectName];
  });

  const stateCount = $derived(allStates.length - 1); // exclude base

  const isDiscovered = $derived.by(() => {
    if (!store.game) return false;
    const obj = store.game.objects[`${roomName}:${objectName}`] ??
      Object.values(store.game.objects).find(
        (o) => o.room === roomName && o.name === objectName,
      );
    return obj?.discovered ?? false;
  });

  const interactions = $derived.by(() => {
    if (!store.game) return [];
    return getObjectInteractions(store.game, roomName, effectiveActiveState);
  });

  const totalInteractions = $derived.by(() => {
    if (!store.game) return 0;
    let count = 0;
    for (const state of allStates) {
      count += getObjectInteractions(store.game, roomName, state).length;
    }
    return count;
  });

  function stateSuffix(name: string): string {
    if (name === objectName) return 'base';
    const parts = name.split('__');
    return parts.length > 1 ? parts.slice(1).join('__') : name;
  }

  function toggle() {
    expanded = !expanded;
    if (expanded) {
      activeState = null; // reset to base (via effectiveActiveState) when expanding
    }
  }

  function getInteractionIndex(interaction: (typeof interactions)[number]): number {
    if (!store.game) return -1;
    return store.game.interactions.indexOf(interaction);
  }

  function openEditor(interaction: (typeof interactions)[number]) {
    const idx = getInteractionIndex(interaction);
    if (idx >= 0) editingIdx = idx;
  }

  function deleteObject() {
    if (!store.game) return;
    if (!confirm(`Delete ${objectName} and all its states and interactions?`)) return;
    store.mutate((g) => {
      // Remove all state variants of this object
      for (const key of Object.keys(g.objects)) {
        const obj = g.objects[key];
        if (obj.room === roomName && obj.base === objectName) {
          delete g.objects[key];
        }
      }
      // Remove all interactions targeting this object or its states
      g.interactions = g.interactions.filter((i) => {
        if (i.room !== roomName) return true;
        // Check if any target group references this object or its states
        for (const group of i.targetGroups) {
          for (const target of group) {
            if (target === objectName || target.split('__')[0] === objectName) {
              return false;
            }
          }
        }
        return true;
      });
    });
    expanded = false;
  }

  function addInteraction() {
    if (!store.game) return;
    const targetName = effectiveActiveState;
    const newInteraction = createInteraction('', roomName);
    newInteraction.targetGroups = [[targetName]];
    store.mutate((game) => {
      game.interactions.push(newInteraction);
    });
    // The new interaction is now the last one
    editingIdx = store.game.interactions.length - 1;
  }
</script>

<div class="object-card" class:expanded>
  <!-- Header -->
  <div class="card-header" onclick={toggle} role="button" tabindex="0"
       onkeydown={(e) => e.key === 'Enter' && toggle()}>
    <div class="header-left">
      <span class="toggle-arrow">{expanded ? '▾' : '▸'}</span>
      <span class="object-name">{objectName}</span>
      {#if stateCount > 0}
        <span class="badge badge-states">{stateCount} state{stateCount === 1 ? '' : 's'}</span>
      {/if}
      {#if isDiscovered}
        <span class="badge badge-hidden">hidden</span>
      {/if}
    </div>
    <div class="header-right">
      {#if totalInteractions > 0}
        <span class="interaction-count">{totalInteractions} interaction{totalInteractions === 1 ? '' : 's'}</span>
      {/if}
      {#if expanded}
        <button class="delete-obj-btn" onclick={(e) => { e.stopPropagation(); deleteObject(); }} title="Delete object">✕</button>
      {/if}
    </div>
  </div>

  <!-- Expanded content -->
  {#if expanded}
    <div class="card-body">
      <!-- State tabs -->
      {#if allStates.length > 1}
        <div class="state-tabs">
          {#each allStates as state (state)}
            <button
              class="tab-btn"
              class:active={effectiveActiveState === state}
              onclick={() => (activeState = state)}
            >
              {stateSuffix(state)}
            </button>
          {/each}
          <button class="tab-btn tab-add" title="Add state">+</button>
        </div>
      {/if}

      <!-- Interactions for active state -->
      <div class="interactions-list">
        {#if interactions.length === 0 && editingIdx === null}
          <p class="no-interactions">No interactions for this state.</p>
        {/if}
        {#each interactions as interaction (interaction.verb + JSON.stringify(interaction.targetGroups))}
          {@const idx = getInteractionIndex(interaction)}
          {#if editingIdx === idx}
            <InteractionEditor
              {interaction}
              interactionIndex={idx}
              onclose={() => (editingIdx = null)}
            />
          {:else}
            <InteractionCard {interaction} onclick={() => openEditor(interaction)} />
          {/if}
        {/each}
        <button class="add-btn" onclick={addInteraction}>+ Add interaction</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .object-card {
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
    transition: border-color 0.15s;
  }

  .object-card.expanded {
    border-color: rgba(201, 168, 76, 0.4);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    cursor: pointer;
    user-select: none;
    transition: background-color 0.15s;
  }

  .object-card.expanded .card-header {
    background: rgba(201, 168, 76, 0.06);
  }

  .card-header:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .toggle-arrow {
    font-size: 0.75rem;
    color: var(--text-dim);
    width: 12px;
    flex-shrink: 0;
  }

  .object-name {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--parchment-light);
  }

  .badge {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 3px;
  }

  .badge-states {
    background: rgba(201, 168, 76, 0.25);
    color: var(--gold);
  }

  .badge-hidden {
    background: rgba(212, 136, 58, 0.25);
    color: var(--amber);
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .delete-obj-btn {
    font-size: 0.75rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    padding: 2px 6px;
    background: transparent;
    border: 1px solid var(--warm-gray);
    color: var(--text-dim);
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .delete-obj-btn:hover {
    background: var(--red-ink);
    border-color: var(--red-ink);
    color: var(--parchment-light);
  }

  .interaction-count {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .card-body {
    padding: 0 12px 12px;
    border-top: 1px solid var(--warm-gray);
  }

  .state-tabs {
    display: flex;
    gap: 4px;
    padding: 8px 0 6px;
    border-bottom: 1px solid var(--warm-gray);
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .tab-btn {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    color: var(--text-mid);
    padding: 2px 10px;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    border-bottom: 2px solid transparent;
  }

  .tab-btn:hover {
    color: var(--parchment);
    background: transparent;
  }

  .tab-btn.active {
    color: var(--gold);
    border-bottom-color: var(--gold);
    background: transparent;
  }

  .tab-add {
    color: var(--text-dim);
    font-size: 0.9rem;
    padding: 2px 8px;
  }

  .interactions-list {
    margin-top: 4px;
  }

  .no-interactions {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-style: italic;
    padding: 4px 0 8px;
  }

  .add-btn {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--text-dim);
    padding: 4px 10px;
    border-radius: 4px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    margin-top: 4px;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: transparent;
  }
</style>

<script lang="ts">
  import type { Interaction } from '../lib/types';
  import { displayName } from '../lib/helpers';
  import { store } from '../lib/store.svelte';
  import ArrowBadge from './ArrowBadge.svelte';

  interface Props {
    interaction: Interaction;
    onclick?: () => void;
  }

  let { interaction, onclick }: Props = $props();

  const ns = $derived(store.game?.metadata.name_style ?? 'upper_words');
  const verbLabel = $derived(displayName(interaction.verb, ns));
  const targetLabel = $derived(
    interaction.targetGroups.length === 0
      ? '@ROOM'
      : interaction.targetGroups.map((g) => g.map((t) => displayName(t, ns)).join(' | ')).join(' + '),
  );
  const narrativePreview = $derived(
    interaction.narrative.length > 120
      ? interaction.narrative.slice(0, 120) + '…'
      : interaction.narrative,
  );
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="interaction-card" {onclick}>
  <div class="card-header">
    <span class="verb-label">{verbLabel}</span>
    {#if interaction.targetGroups.length > 0}
      <span class="target-label">+ {targetLabel}</span>
    {:else}
      <span class="target-label target-room">@ROOM</span>
    {/if}
  </div>
  {#if narrativePreview}
    <div class="narrative-preview">{narrativePreview}</div>
  {/if}
  {#if interaction.arrows.length > 0}
    <div class="arrows">
      {#each interaction.arrows as arrow (arrow.subject + arrow.destination)}
        <ArrowBadge {arrow} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .interaction-card {
    background: var(--dark-warm);
    border-radius: 6px;
    margin-bottom: 6px;
    padding: 8px 10px;
    border-left: 3px solid var(--parchment-dark);
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .interaction-card:hover {
    border-left-color: var(--gold);
  }

  .card-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 2px;
  }

  .verb-label {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--gold);
  }

  .target-label {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-dim);
  }

  .target-room {
    color: var(--parchment-dark);
    font-style: italic;
  }

  .narrative-preview {
    font-family: var(--font-body);
    font-size: 0.8rem;
    color: var(--text-dim);
    line-height: 1.4;
    margin-bottom: 4px;
  }

  .arrows {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
  }
</style>

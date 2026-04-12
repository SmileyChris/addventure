<script lang="ts">
  import type { Arrow } from '../lib/types';
  import { classifyArrow, arrowLabel } from '../lib/helpers';
  import { store } from '../lib/store.svelte';

  interface Props {
    arrow: Arrow;
  }

  let { arrow }: Props = $props();

  const nameStyle = $derived(store.game?.metadata.name_style ?? 'upper_words');
  const type = $derived(classifyArrow(arrow));
  const label = $derived(arrowLabel(arrow, nameStyle));
</script>

<span class="arrow-badge badge-{type}">{label}</span>

<style>
  .arrow-badge {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 3px;
    white-space: nowrap;
  }

  .badge-destroy {
    background: rgba(139, 58, 58, 0.25);
    color: var(--red-ink);
  }

  .badge-pickup {
    background: rgba(212, 136, 58, 0.25);
    color: var(--amber);
  }

  .badge-move {
    background: rgba(201, 168, 76, 0.2);
    color: var(--gold);
  }

  .badge-transform {
    background: rgba(212, 197, 169, 0.15);
    color: var(--parchment);
  }

  .badge-reveal {
    background: rgba(74, 122, 74, 0.25);
    color: var(--green-ink);
  }

  .badge-cue {
    background: rgba(184, 168, 138, 0.2);
    color: var(--parchment-dark);
  }

  .badge-signal {
    background: rgba(212, 136, 58, 0.2);
    color: var(--amber);
  }

  .badge-reveal_verb {
    background: rgba(201, 168, 76, 0.2);
    color: var(--gold);
  }

  .badge-discover_action {
    background: rgba(74, 122, 74, 0.2);
    color: var(--green-ink);
  }

  .badge-room_state {
    background: rgba(212, 197, 169, 0.15);
    color: var(--parchment);
  }

  .badge-verb_restore {
    background: rgba(201, 168, 76, 0.2);
    color: var(--gold);
  }
</style>

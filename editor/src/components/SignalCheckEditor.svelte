<script lang="ts">
  import type { SignalCheck, Arrow } from '../lib/types';
  import { createArrow } from '../lib/factory';
  import ArrowEditor from './ArrowEditor.svelte';

  interface Props {
    checks: SignalCheck[];
    onchange: (checks: SignalCheck[]) => void;
    roomName: string;
  }

  let { checks, onchange, roomName }: Props = $props();

  function addCheck() {
    onchange([...checks, { signalNames: [], narrative: '', arrows: [] }]);
  }

  function addOtherwise() {
    // "otherwise" is a check with empty signalNames (the fallback branch)
    onchange([...checks, { signalNames: [], narrative: '', arrows: [] }]);
  }

  function updateCheck(idx: number, field: keyof SignalCheck, value: SignalCheck[keyof SignalCheck]) {
    const updated = checks.map((c, i) => i === idx ? { ...c, [field]: value } : c);
    onchange(updated);
  }

  function removeCheck(idx: number) {
    onchange(checks.filter((_, i) => i !== idx));
  }

  function addArrowToCheck(idx: number) {
    const updated = checks.map((c, i) =>
      i === idx ? { ...c, arrows: [...c.arrows, createArrow('', '')] } : c
    );
    onchange(updated);
  }

  function updateCheckArrow(checkIdx: number, arrowIdx: number, arrow: Arrow) {
    const updated = checks.map((c, i) => {
      if (i !== checkIdx) return c;
      const arrows = c.arrows.map((a, j) => j === arrowIdx ? arrow : a);
      return { ...c, arrows };
    });
    onchange(updated);
  }

  function deleteCheckArrow(checkIdx: number, arrowIdx: number) {
    const updated = checks.map((c, i) => {
      if (i !== checkIdx) return c;
      return { ...c, arrows: c.arrows.filter((_, j) => j !== arrowIdx) };
    });
    onchange(updated);
  }

  function handleSignalNamesInput(idx: number, raw: string) {
    // Parse on spaces and + characters, split into array of non-empty tokens
    const names = raw.split(/[\s+]+/).filter(Boolean);
    updateCheck(idx, 'signalNames', names);
  }
</script>

<div class="signal-checks">
  {#each checks as check, idx (idx)}
    <div class="check-card">
      <!-- Header row -->
      <div class="check-header">
        {#if check.signalNames.length === 0 && checks.some((c, i) => i !== idx && c.signalNames.length === 0)}
          <span class="otherwise-label">otherwise?</span>
        {:else if check.signalNames.length === 0}
          <span class="otherwise-label">otherwise?</span>
        {:else}
          <input
            type="text"
            class="signal-name-input"
            value={check.signalNames.join(' + ')}
            placeholder="SIGNAL_NAME"
            oninput={(e) => handleSignalNamesInput(idx, (e.target as HTMLInputElement).value)}
          />
          <span class="question-mark">?</span>
        {/if}
        <button class="remove-btn" title="Remove branch" onclick={() => removeCheck(idx)}>×</button>
      </div>

      <!-- Narrative -->
      <textarea
        class="check-narrative"
        rows={2}
        value={check.narrative}
        placeholder="Narrative for this branch…"
        oninput={(e) => updateCheck(idx, 'narrative', (e.target as HTMLTextAreaElement).value)}
      ></textarea>

      <!-- Arrows -->
      <div class="check-arrows">
        {#each check.arrows as arrow, arrowIdx (arrowIdx)}
          <ArrowEditor
            {arrow}
            onchange={(a) => updateCheckArrow(idx, arrowIdx, a)}
            ondelete={() => deleteCheckArrow(idx, arrowIdx)}
            {roomName}
          />
        {/each}
        <button class="add-arrow-btn" onclick={() => addArrowToCheck(idx)}>+ Add arrow</button>
      </div>
    </div>
  {/each}

  <!-- Bottom buttons -->
  <div class="check-actions">
    <button class="add-branch-btn" onclick={addCheck}>+ Add signal branch</button>
    <button class="add-branch-btn" onclick={addOtherwise}>+ Add otherwise</button>
  </div>
</div>

<style>
  .signal-checks {
    border-left: 2px solid var(--amber, #c8903c);
    padding-left: 12px;
  }

  .check-card {
    background: var(--mid-dark);
    border-radius: 6px;
    padding: 8px;
    margin-bottom: 12px;
  }

  .check-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
  }

  .signal-name-input {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    flex: 1;
    min-width: 0;
  }

  .question-mark {
    color: var(--amber, #c8903c);
    font-size: 0.9rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .otherwise-label {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--amber, #c8903c);
    flex: 1;
  }

  .remove-btn {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-dim);
    padding: 2px 7px;
    border-radius: 3px;
    flex-shrink: 0;
    cursor: pointer;
    line-height: 1;
    transition: color 0.1s;
  }

  .remove-btn:hover {
    color: var(--red-ink);
    background: rgba(139, 58, 58, 0.15);
  }

  .check-narrative {
    width: 100%;
    font-family: var(--font-body);
    font-size: 0.85rem;
    resize: vertical;
    margin-bottom: 6px;
    box-sizing: border-box;
  }

  .check-arrows {
    margin-top: 4px;
  }

  .add-arrow-btn {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--text-dim);
    padding: 3px 10px;
    border-radius: 4px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    margin-top: 4px;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-arrow-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: transparent;
  }

  .check-actions {
    display: flex;
    gap: 8px;
  }

  .add-branch-btn {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--gold-dim, var(--text-dim));
    padding: 3px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-branch-btn:hover {
    border-color: var(--amber, #c8903c);
    color: var(--amber, #c8903c);
    background: transparent;
  }
</style>

<script lang="ts">
  import type { Interaction, Arrow, SignalCheck } from '../lib/types';
  import { store } from '../lib/store.svelte';
  import { createArrow } from '../lib/factory';
  import VerbPicker from './VerbPicker.svelte';
  import TargetBuilder from './TargetBuilder.svelte';
  import ArrowEditor from './ArrowEditor.svelte';
  import SignalCheckEditor from './SignalCheckEditor.svelte';
  import GenerateButton from './GenerateButton.svelte';
  import { interactionPrompt, sealedContentPrompt } from '../lib/ollama';

  interface Props {
    interaction: Interaction;
    interactionIndex: number;
    onclose: () => void;
  }

  let { interaction, interactionIndex, onclose }: Props = $props();

  function update(fn: (i: Interaction) => void) {
    store.mutate((game) => {
      fn(game.interactions[interactionIndex]);
    });
  }

  function handleVerbChange(v: string) {
    update((i) => { i.verb = v; });
  }

  function handleTargetsChange(groups: string[][]) {
    update((i) => { i.targetGroups = groups; });
  }

  function handleNarrativeInput(e: Event) {
    const val = (e.target as HTMLTextAreaElement).value;
    update((i) => { i.narrative = val; });
  }

  function handleSealedInput(e: Event) {
    const val = (e.target as HTMLTextAreaElement).value;
    update((i) => { i.sealedContent = val; });
  }

  function addSealedContent() {
    update((i) => { i.sealedContent = ''; });
  }

  function removeSealedContent() {
    update((i) => { i.sealedContent = null; });
  }

  function handleArrowChange(arrowIndex: number, newArrow: Arrow) {
    update((i) => { i.arrows[arrowIndex] = newArrow; });
  }

  function handleArrowDelete(arrowIndex: number) {
    update((i) => { i.arrows.splice(arrowIndex, 1); });
  }

  function addArrow() {
    update((i) => { i.arrows.push(createArrow('', '')); });
  }

  function deleteInteraction() {
    store.mutate((game) => {
      game.interactions.splice(interactionIndex, 1);
    });
    onclose();
  }

  function addSignalChecks() {
    update((i) => { i.signalChecks = [{ signalNames: [], narrative: '', arrows: [] }]; });
  }

  function handleSignalChecksChange(checks: SignalCheck[]) {
    update((i) => { i.signalChecks = checks; });
  }
</script>

<div class="interaction-editor">
  <!-- Header -->
  <div class="editor-header">
    <h4 class="editor-title">Edit Interaction</h4>
    <div class="header-actions">
      <button class="delete-interaction-btn" onclick={deleteInteraction}>Delete</button>
      <button class="done-btn" onclick={onclose}>Done</button>
    </div>
  </div>

  <!-- Verb -->
  <div class="field-row">
    <span class="field-label" aria-hidden="true">Verb</span>
    <div class="field-control">
      <VerbPicker value={interaction.verb} onchange={handleVerbChange} />
    </div>
  </div>

  <!-- Targets -->
  <div class="field-row">
    <span class="field-label" aria-hidden="true">Targets</span>
    <div class="field-control">
      <TargetBuilder
        targetGroups={interaction.targetGroups}
        onchange={handleTargetsChange}
        roomName={interaction.room}
      />
    </div>
  </div>

  <!-- Narrative -->
  <div class="field-row field-row-col">
    <div class="label-row">
      <label class="field-label" for="narrative-{interactionIndex}">Narrative</label>
      <GenerateButton
        prompt={interactionPrompt(interaction.verb, interaction.targetGroups.flat(), interaction.room, store.game!, interaction.narrative || undefined, store.settings.narratorVoice || undefined)}
        ongenerated={(text) => update((i) => { i.narrative = text; })}
      />
    </div>
    <textarea
      id="narrative-{interactionIndex}"
      class="narrative-area"
      rows={4}
      value={interaction.narrative}
      oninput={handleNarrativeInput}
      placeholder="Describe what happens…"
    ></textarea>
  </div>

  <!-- Arrows -->
  <div class="field-section">
    <div class="section-label">Arrows</div>
    {#each interaction.arrows as arrow, i (i)}
      <ArrowEditor
        {arrow}
        onchange={(a) => handleArrowChange(i, a)}
        ondelete={() => handleArrowDelete(i)}
        roomName={interaction.room}
      />
    {/each}
    <button class="add-arrow-btn" onclick={addArrow}>+ Add arrow</button>
  </div>

  <!-- Sealed content -->
  <div class="field-section">
    <div class="label-row">
      <div class="section-label">Sealed Content</div>
      {#if interaction.sealedContent !== null}
        <GenerateButton
          prompt={sealedContentPrompt(interaction.verb, interaction.targetGroups.flat(), interaction.room, store.game!)}
          ongenerated={(text) => update((i) => { i.sealedContent = text; })}
        />
      {/if}
    </div>
    {#if interaction.sealedContent === null}
      <button class="add-sealed-btn" onclick={addSealedContent}>+ Add sealed content</button>
    {:else}
      <div class="sealed-block">
        <textarea
          class="sealed-area"
          rows={3}
          value={interaction.sealedContent}
          oninput={handleSealedInput}
          placeholder="Sealed text revealed during play…"
        ></textarea>
        <button class="remove-sealed-btn" onclick={removeSealedContent}>Remove sealed content</button>
      </div>
    {/if}
  </div>

  <!-- Signal checks -->
  <div class="field-section">
    <div class="section-label">Signal Checks</div>
    {#if interaction.signalChecks.length > 0}
      <SignalCheckEditor
        checks={interaction.signalChecks}
        onchange={handleSignalChecksChange}
        roomName={interaction.room}
      />
    {:else}
      <button class="add-sealed-btn" onclick={addSignalChecks}>+ Add signal checks</button>
    {/if}
  </div>
</div>

<style>
  .interaction-editor {
    background: var(--dark-warm);
    border: 1px solid rgba(201, 168, 76, 0.35);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 8px;
  }

  .editor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .editor-title {
    font-family: var(--font-title);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
  }

  .header-actions {
    display: flex;
    gap: 6px;
  }

  .delete-interaction-btn {
    font-size: 0.72rem;
    padding: 3px 10px;
    background: rgba(139, 58, 58, 0.2);
    border-color: rgba(139, 58, 58, 0.5);
    color: var(--red-ink);
  }

  .delete-interaction-btn:hover {
    background: rgba(139, 58, 58, 0.35);
    color: #b05555;
  }

  .done-btn {
    font-size: 0.72rem;
    padding: 3px 10px;
  }

  .field-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .field-row-col {
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
  }

  .label-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .field-label {
    font-family: var(--font-title);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    flex-shrink: 0;
    width: 58px;
  }

  .field-row-col .field-label {
    width: auto;
  }

  .field-control {
    flex: 1;
    min-width: 0;
  }

  .narrative-area,
  .sealed-area {
    width: 100%;
    font-family: var(--font-body);
    font-size: 0.85rem;
    resize: vertical;
  }

  .field-section {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--warm-gray);
  }

  .section-label {
    font-family: var(--font-title);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 6px;
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

  .add-sealed-btn {
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
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-sealed-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: transparent;
  }

  .sealed-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .remove-sealed-btn {
    font-size: 0.7rem;
    padding: 2px 8px;
    background: transparent;
    border-color: var(--warm-gray);
    color: var(--text-dim);
    align-self: flex-start;
  }

  .remove-sealed-btn:hover {
    border-color: rgba(139, 58, 58, 0.5);
    color: var(--red-ink);
    background: rgba(139, 58, 58, 0.1);
  }
</style>

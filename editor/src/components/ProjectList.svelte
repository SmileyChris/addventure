<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { loadProjectIndex, deleteProject } from '../lib/persistence';

  let newGameName = $state('');
  let projects = $state(loadProjectIndex());

  function refreshProjects() {
    projects = loadProjectIndex();
  }

  function handleCreate() {
    const name = newGameName.trim();
    if (!name) return;
    store.create(name);
    newGameName = '';
  }

  function handleOpen(id: string) {
    store.open(id);
  }

  function handleDelete(id: string, name: string) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    deleteProject(id);
    refreshProjects();
  }

  function formatDate(ts: number): string {
    return new Date(ts).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
</script>

<div class="project-list">
  <div class="landing-inner">
    <h1>Addventure Editor</h1>
    <p class="subtitle">Design paper-based text adventures where addition is the parser.</p>

    <div class="new-game-row">
      <input
        type="text"
        placeholder="New game name…"
        bind:value={newGameName}
        onkeydown={(e) => e.key === 'Enter' && handleCreate()}
      />
      <button class="btn-gold" onclick={handleCreate} disabled={!newGameName.trim()}>
        New Game
      </button>
    </div>

    {#if projects.length > 0}
      <div class="projects-section">
        <h2>Recent Projects</h2>
        <ul class="project-items">
          {#each projects.slice().sort((a, b) => b.lastModified - a.lastModified) as entry (entry.id)}
            <li class="project-item">
              <button class="project-open" onclick={() => handleOpen(entry.id)}>
                <span class="project-name">{entry.name}</span>
                <span class="project-date">{formatDate(entry.lastModified)}</span>
              </button>
              <button
                class="btn-delete"
                onclick={() => handleDelete(entry.id, entry.name)}
                title="Delete project"
              >
                ✕
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {:else}
      <p class="no-projects">No saved projects yet. Create one above to get started.</p>
    {/if}
  </div>
</div>

<style>
  .project-list {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background-color: var(--dark);
  }

  .landing-inner {
    width: 100%;
    max-width: 540px;
    padding: 2rem;
  }

  h1 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 2.2rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.4rem;
  }

  .subtitle {
    color: var(--text-mid);
    font-size: 0.95rem;
    margin-bottom: 2rem;
  }

  .new-game-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
  }

  .new-game-row input {
    flex: 1;
  }

  .btn-gold {
    background-color: var(--gold);
    color: var(--black);
    border-color: var(--gold);
  }

  .btn-gold:hover:not(:disabled) {
    background-color: var(--gold-bright);
    color: var(--black);
  }

  .btn-gold:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .projects-section h2 {
    font-family: var(--font-title);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
  }

  .project-items {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .project-item {
    display: flex;
    align-items: stretch;
    gap: 0.4rem;
  }

  .project-open {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    text-align: left;
    background-color: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    padding: 0.6em 1em;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 0.95rem;
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
    color: var(--text-light);
    transition: background-color 0.15s, border-color 0.15s;
  }

  .project-open:hover {
    background-color: var(--mid-dark);
    border-color: var(--gold-dim);
    color: var(--parchment-light);
  }

  .project-name {
    font-weight: 600;
  }

  .project-date {
    font-size: 0.8rem;
    color: var(--text-dim);
  }

  .btn-delete {
    background-color: transparent;
    border: 1px solid var(--warm-gray);
    color: var(--text-dim);
    padding: 0.4em 0.6em;
    font-size: 0.8rem;
    font-family: var(--font-body);
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
  }

  .btn-delete:hover {
    background-color: var(--red-ink);
    border-color: var(--red-ink);
    color: var(--parchment-light);
  }

  .no-projects {
    color: var(--text-dim);
    font-size: 0.9rem;
    font-style: italic;
  }
</style>

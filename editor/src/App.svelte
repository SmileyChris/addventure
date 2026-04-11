<script lang="ts">
  import './styles/theme.css';
  import { store } from './lib/store.svelte';
  import ProjectList from './components/ProjectList.svelte';
  import TopBar from './components/TopBar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import MainPanel from './components/MainPanel.svelte';
</script>

{#if store.project}
  <div class="editor">
    <TopBar />
    <div class="workspace">
      <Sidebar />
      <MainPanel />
    </div>
  </div>
{:else}
  <ProjectList />
{/if}

<style>
  .editor {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .workspace {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
</style>

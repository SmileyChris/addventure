<script lang="ts">
  import './styles/theme.css';
  import { store } from './lib/store.svelte';
  import ProjectList from './components/ProjectList.svelte';
  import TopBar from './components/TopBar.svelte';
  import TabBar from './components/TabBar.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import MainPanel from './components/MainPanel.svelte';
</script>

{#if store.project}
  <div class="editor">
    <TopBar />
    <TabBar />
    <div class="workspace">
      {#if store.activeView === 'editor'}
        <Sidebar />
      {/if}
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

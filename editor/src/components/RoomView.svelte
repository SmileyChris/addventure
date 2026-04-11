<script lang="ts">
  interface Props {
    roomName: string;
  }

  let { roomName }: Props = $props();
</script>

<div class="room-view">
  <h2>{roomName}</h2>
  <p class="hint">
    Edit room objects, interactions, and exits here.
  </p>
</div>

<style>
  .room-view {
    padding: 2rem;
  }

  h2 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 1rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.95rem;
  }
</style>

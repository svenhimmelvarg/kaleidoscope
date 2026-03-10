<script>
  import { api } from "../convex/_generated/api.js";
  import { useQuery } from 'convex-svelte';

  let { notification, relatedNotifications = [], onclick = () => {} } = $props();

  let mainImage = $derived(notification.payload?.output?.images?.[0]);
</script>

{#if mainImage}
  <div class="bentobox" onclick={() => onclick(mainImage)}>
    <div class="bentobox__main">
      <img src={mainImage.uri} alt="Main render" class="bentobox__main-image" />
    </div>
    {#if relatedNotifications.length > 0}
      <div class="bentobox__related">
        {#each relatedNotifications as related}
          {#if related.payload?.output?.images?.[0]}
            {@const img = related.payload.output.images[0]}
            <div class="bentobox__related-item" onclick={(e) => { e.stopPropagation(); onclick(img); }}>
              <img src={img.uri} alt="Related render" class="bentobox__related-image" />
            </div>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .bentobox {
    display: flex;
    flex-direction: row;
    gap: 0.25rem;
    border-radius: 16px;
    overflow: hidden;
    background: #222;
    cursor: pointer;
    transition: transform 0.2s ease;
    flex: 0 0 calc(25% - 0.5rem);
    min-width: 200px;
    max-width: 300px;
    height: 200px;
  }

  .bentobox:hover {
    transform: scale(1.02);
  }

  .bentobox__main {
    flex: 1;
    min-width: 200px;
    height: 100%;
  }

  .bentobox__main-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .bentobox__related {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 0 0 100px;
  }

  .bentobox__related-item {
    flex: 1;
    min-height: 0;
  }

  .bentobox__related-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 8px;
  }
</style>
<script>
  import { imageFileUrl, isVideoDoc } from "./functions/uri_helpers";

  let { 
    mainResult,
    relatedResults = [],
    onclick = () => {}
  } = $props();

  function handleClick() {
    onclick(mainResult);
  }

  function handleRelatedClick(e, related) {
    e.stopPropagation();
    onclick(related);
  }
</script>

{#if mainResult}
  {@const mainIsVideo = isVideoDoc(mainResult)}
  <div class="search-bentobox" onclick={handleClick}>
    <div class="search-bentobox__main">
      {#if mainIsVideo}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video
          src={imageFileUrl(mainResult.image_url)}
          muted
          playsinline
          preload="metadata"
          class="search-bentobox__main-image"
        ></video>
      {:else}
        <img 
          src={imageFileUrl(mainResult.image_url)} 
          alt="Main result" 
          class="search-bentobox__main-image" 
        />
      {/if}
    </div>
    {#if relatedResults.length > 0}
      <div class="search-bentobox__related">
        {#each relatedResults as related}
          {@const relatedIsVideo = isVideoDoc(related)}
          <div class="search-bentobox__related-item" onclick={(e) => handleRelatedClick(e, related)}>
            {#if relatedIsVideo}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video
                src={imageFileUrl(related.image_url)}
                muted
                playsinline
                preload="metadata"
                class="search-bentobox__related-image"
              ></video>
            {:else}
              <img 
                src={imageFileUrl(related.image_url)} 
                alt="Related result" 
                class="search-bentobox__related-image" 
              />
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .search-bentobox {
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

  .search-bentobox:hover {
    transform: scale(1.02);
  }

  .search-bentobox__main {
    flex: 1;
    min-width: 0;
    height: 100%;
  }

  .search-bentobox__main-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .search-bentobox__related {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 0 0 100px;
  }

  .search-bentobox__related-item {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .search-bentobox__related-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 8px;
  }
</style>

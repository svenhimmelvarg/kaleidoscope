<script>
  import { fixImageUrl } from "./functions/uri_helpers";

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
  {@const mainIsVideo = mainResult.type === 'video' || mainResult.content_type?.includes('video') || mainResult.image_url?.endsWith('.mp4')}
  <div class="search-bentobox" onclick={handleClick}>
    <div class="search-bentobox__main">
      <img 
        src={mainIsVideo ? `/images/thumbnails/${mainResult.id}.jpg` : fixImageUrl(mainResult.image_url, mainResult.source)} 
        alt="Main result" 
        class="search-bentobox__main-image" 
      />
    </div>
    {#if relatedResults.length > 0}
      <div class="search-bentobox__related">
        {#each relatedResults as related}
          {@const relatedIsVideo = related.type === 'video' || related.content_type?.includes('video') || related.image_url?.endsWith('.mp4')}
          <div class="search-bentobox__related-item" onclick={(e) => handleRelatedClick(e, related)}>
            <img 
              src={relatedIsVideo ? `/images/thumbnails/${related.id}.jpg` : fixImageUrl(related.image_url, related.source)} 
              alt="Related result" 
              class="search-bentobox__related-image" 
            />
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

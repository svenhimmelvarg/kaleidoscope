Ex
<script lang="ts">
  import { fixImageUrl } from "../functions/uri_helpers.js";
  export let result: any;
  export let isListView: boolean = false;
  export let isDetailOn: boolean = false;
</script>

{#if isListView}
<div class="search-results__item">
  <div class="search-results__item__text">{result.text ? result.text.join(",") : ''}</div>
  <div class="search-results__item__details">
    <div class="search-results__item__schedulers">
      {#each result.schedulers as sched}
        <div class="search-results__item__scheduler">[{sched}]</div>
      {/each}
    </div>
    <div class="search-results__item__loras">
      {#each result.loras as lora}
        <div class="search-results__item__lora">{lora}</div>
      {/each}
    </div>                
  </div>
  <div>
    <img src={fixImageUrl(result.image_url, result.source)} />
  </div>
</div>
{:else}
<div class="search-results__grid-item">
  <div class="search-results__grid-item__image">
    <img src={fixImageUrl(result.image_url, result.source)} alt="Generated image" />
  </div>
  {#if isDetailOn}
  <div class="search-results__grid-item__content">
    <div class="search-results__grid-item__text">{result.text ? result.text.join(",") : ''}</div>
    <div class="search-results__grid-item__details">
      <div class="search-results__grid-item__schedulers">
        {#each result.schedulers as sched}
          <div class="search-results__grid-item__scheduler">[{sched}]</div>
        {/each}
      </div>
      <div class="search-results__grid-item__loras">
        {#each result.loras as lora}
          <div class="search-results__grid-item__lora">{lora}</div>
        {/each}
      </div>
    </div>
  </div>
  {/if}
</div>
{/if}

<style>
  .search-results__item {
    margin-bottom: 1rem;
    padding: 0.5rem;
    border: 1px solid #eee;
    border-radius: 4px;
  }

  .search-results__item__text {
    margin-bottom: 0.5rem;
  }

  .search-results__item__details {
    display: flex;
    gap: 1rem;
  }

  .search-results__item__schedulers,
  .search-results__item__loras {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .search-results__item__scheduler,
  .search-results__item__lora {
    background-color: #f0f0f0;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  .search-results__grid-item {
    border: 1px solid #eee;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .search-results__grid-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  .search-results__grid-item__image {
    width: 100%;
    height: 200px;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f8f9fa;
  }

  .search-results__grid-item__image img {
    max-width: 600px;
    max-height: 100%;
    object-fit: contain;
  }

  .search-results__grid-item__content {
    padding: 1rem;
  }

  .search-results__grid-item__text {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
    line-height: 1.4;
  }

  .search-results__grid-item__details {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .search-results__grid-item__schedulers,
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
  }

  .search-results__grid-item__scheduler,
  .search-results__grid-item__lora {
    background-color: #f0f0f0;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-size: 0.7rem;
  }
</style>
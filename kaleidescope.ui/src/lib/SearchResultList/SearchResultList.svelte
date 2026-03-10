<script lang="ts">
  import { fixImageUrl } from "../functions/uri_helpers";

  
  let results = $props() 

  $effect( ()=>{
    console.log("SearchResultList:effect",results.entries[0])
  })

</script>

<div class="search-results__list">
  {#each results.entries as r }
    <div class="search-results__item">
      <div class="search-results__item__text">{r.text ? r.text.join(",") : ''}</div>
      <div class="search-results__item__details">
        <div class="search-results__item__schedulers">
          {#each r.schedulers as sched}
            <div class="search-results__item__scheduler">[{sched}]</div>
          {/each}
        </div>
        <div class="search-results__item__loras">
          {#each r.loras as lora}
            <div class="search-results__item__lora">{lora}</div>
          {/each}
        </div>                
      </div>
      <div>
        <img src={fixImageUrl(r.image_url, r.source)} />
        
      </div>
    </div>
  {/each}
</div>

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
</style>
<script>
  import { useQuery } from "convex-svelte";
  import { api } from "../convex/_generated/api";
    import { Meilisearch } from 'meilisearch';
      import {getContext} from  'svelte'
  import { fixImageUrl } from "./functions/uri_helpers";
  import { getSearchHost } from "./functions/convex_helpers";

    let {search , onclick = () =>  {}}  = $props() 
    let results  =  $state({ hits: [] })
    let searchParameters =    getContext('search.params')
  const client = new Meilisearch({
    host: getSearchHost(),
    apiKey: 'password'
  });    

    let index = $derived(client.index(searchParameters.indexName))


    function buildFilters(){
         return search.filters.map(f => `${f.attribute} = '${f.value}'`);
    }

    async function runSearch() {
        const searchOptions = {
                facets: search.facets,
                page: search.page,
                hitsPerPage:  3,  // search.pageLimit
                filter: [] 
            };
        const query  = search.q || "";

        let filters = buildFilters() 
        console.log("Main::search:searchOptions",searchOptions, filters ,search  )
              // Only add filter if there are any
        if (filters.length > 0) {
            searchOptions.filter = filters;
        }
        const searchResponse = await index.search(query, searchOptions);        
        results.hits  = searchResponse.hits 
    }

    await runSearch() 

    function convertUrl(url){

    }

</script>
<div class="search-summary">
    <div class="search-summary__list">
    {#each results.hits as h (h.id)}
        <div class="search-summary__item">
            
             <img class="search-summary__image" src='{fixImageUrl(h.image_url, h.source)}'   alt="Generated image" /> 
             <span> [X] </span>
        </div>
    {/each}
    </div>
</div>

<style>
.search-summary {
    margin: 0;
    padding: 0;
}

.search-summary__list {
    display: flex;
    flex-direction: row;
    gap: 1em;
    flex-wrap: wrap;
}

.search-summary__item {
    flex: 0 0 auto;
}

.search-summary__image {
    max-width: 200px;
    max-height: 400px; 
    height: auto;
    object-fit: cover;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out;
}

.search-summary__image:hover {
    transform: scale(1.05);
}
</style>
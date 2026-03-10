<script>
    import {getContext} from 'svelte'
    import {createFilterController} from './controllers/FilterController'
    import {useQuery} from 'convex-svelte'
    import {useConvexClient} from 'convex-svelte'
    import { api } from '../convex/_generated/api';
  import { push } from 'svelte-spa-router';
  import SearchSummaryList from './SearchSummaryList.svelte';

    let { collapsed = false , onUpdate = () => {}  } = $props() 
    let contextSearch =  getContext("search.params")
    const client = useConvexClient() 
    let searchQuery =  useQuery(api.search.getAll, {} )
    let searches =  $derived ( searchQuery.data ?  searchQuery.data :  [] )
    
    const convexClient = getContext("convex.client");
    
    const filterController = createFilterController(convexClient);

    $effect(() => { console.log("Searches:effect:search.params", contextSearch)})
    



    function updateSearch(s) {
        console.log("Searches:updateSearch", s ,contextSearch)
        contextSearch.filters = s.filters 
        contextSearch.facets  = s.facets 
        contextSearch.q  = s.q 
        push("#/search")

    }

    async function _delete (s_id) {
        console.log("Searches:delete:", s_id)
        await filterController._delete(s_id)
    }
</script>
<div class="searches-container">
    <div class="search-list">
        {#each searches as search (search._id)}
            {#if collapsed == false }
            <div class="search-item">
                <div class="search-query">
                    <div> 
                        <div onclick={() => { updateSearch(search.filter ) } }>{search.name}: </div>
                        <div> {search.filter?.q || 'No query'}  </div> 
                        <div onclick={ () =>  { _delete(search._id) }  }> [X]</div>

                    </div>
                    <div>
                        <SearchSummaryList  search={search.filter}  />>
                    </div>
                </div>
                <div class="search-info">

                         
                    <div class="search-filters">

                    </div>
                </div>
            </div>
        {/if}
            <div style="display:flex; justify-content: center">
                <div onclick={() => { updateSearch(search.filter ) ;  onUpdate()  } }>{search.name}: </div>
                <div onclick={ () =>  { _delete(search._id) }  }> [X]</div>

            </div>
        {/each}
    </div>
</div>

<style>
.searches-container {
    padding: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.search-list {
    background-color: rgba(249, 249, 249, 0.8);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.search-query {
    display:flex;
    flex-direction: row ;
    gap: 1em;
}
</style>
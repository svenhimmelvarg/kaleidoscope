<script lang="ts">
  import SearchBar from './SearchBar/SearchBar.svelte';
  import SearchBarAdvanced from './SearchBar/SearchBarAdvanced.svelte'
  import SearchResultList from './SearchResultList/SearchResultList.svelte';
  import SearchResultGrid from './SearchResultGrid/SearchResultGrid.svelte';
  import { Meilisearch } from 'meilisearch';
  import {getContext} from  'svelte'
  import {createFilterController} from './controllers/FilterController';
  import {useConvexClient} from 'convex-svelte'
	

  import { getMeilisearchUrl } from  './functions/convex_helpers'
  import SearchSummaryList from './SearchSummaryList.svelte';
  import Searches from './Searches.svelte';
  import Notifications from './Notifications.svelte';
  import FilterShortcuts from './FilterShortcuts.svelte';
  import { querystring, replace, push } from 'svelte-spa-router';
  import Metrics from './Metrics.svelte';
  import { featureOn } from './growthbook';
  
  let isExperimental = featureOn("experimental");

 let { params = {} }  = $props()

  let results = $state({
    entries: [] as any[],
    facets: {} as Record<string, Record<string, number>>,
    estimatedTotalHits: 0,
    offset: 0,
    limit: 50,
    hasMore: true
  })

  // Infinite scroll state
  let isLoadingMore = $state(false)

  let collapsed: string[] = $state([])

  let sortOptions = $state({
    field: 'created',
    direction: 'desc' // 'asc' for oldest first, 'desc' for newest first
  })

  const searchState: any = getContext('searchState')
  console.log("Search:render", searchState)


  const client = new Meilisearch({
    host:  getMeilisearchUrl(),
    apiKey: 'password'
  });

  // getSearchHost

  // Get Convex client for search saving
  const convexClient = getContext("convex.client")
  const filterController = createFilterController(convexClient);

  let index = $derived(client.index(searchState.indexName))


  let isLoading = $state(false)

  // Initialize Meilisearch client

  function updateUrl(options: { dropId?: boolean, forceId?: string } = {}) {
    const searchParams = new URLSearchParams();
    if (searchState.q) {
      searchParams.set('q', searchState.q);
    }
    if (searchState.customFilters.length > 0) {
      searchParams.set('filters', JSON.stringify(searchState.customFilters));
    }
    
    const qs = searchParams.toString();
    let currentPath = '/search';
    
    let filterPart = params?.filter;
    if (!filterPart || filterPart === 'all') {
      filterPart = 'all';
    }

    const targetId = options.dropId ? null : (options.forceId || params?.id);

    if (targetId) {
      currentPath += `/${filterPart}/${targetId}`;
    } else {
      if (filterPart !== 'all') {
        currentPath += `/${filterPart}`;
      }
    }
    
    replace(`${currentPath}${qs ? `?${qs}` : ''}`);
  }

  function onAssetOpen(id: string) {
    updateUrl({ forceId: id });
  }

  function onAssetClose() {
    updateUrl({ dropId: true });
  }

  function addFilter( kv : {attribute: string, value: string}){
    // Check if filter already exists
    const existingFilterIndex = searchState.customFilters.findIndex(
      (f: any) => f.attribute === kv.attribute && f.value === kv.value
    );
    
    if (existingFilterIndex === -1) {
      // Add new filter
      searchState.customFilters = [...searchState.customFilters, kv];
    } else {
      // Remove filter if it already exists (toggle behavior)
      searchState.customFilters = searchState.customFilters.filter(
        (_: any, index: number) => index !== existingFilterIndex
      );
    }
    
    // Trigger URL update
    updateUrl();
  }
  
  function removeFilter( attribute: string, value: string, expression?: string ){
    const isRouteFilter = searchState.routeFilters.some((f: any) => 
      (attribute && f.attribute === attribute && f.value === value) ||
      (expression && f.expression === expression)
    );

    if (isRouteFilter) {
      const qs = $querystring ? `?${$querystring}` : '';
      if (params?.id) {
        push(`/search/all/${params.id}${qs}`);
      } else {
        push(`/search${qs}`);
      }
    } else {
      searchState.customFilters = searchState.customFilters.filter(
        (f: any) => {
          if (expression) return f.expression !== expression;
          return !(f.attribute === attribute && f.value === value);
        }
      );
      updateUrl();
    }
  }
  
  function buildFilters(){
    let defaultFilters = ["vote != -1", "NOT score < 0", "created EXISTS"];
    
    // Check if the current route is for downvoted items
    const isDownvotedRoute = searchState.routeFilters.some((f: any) => f.expression === 'vote < 0 OR score < 0');
    
    if (isDownvotedRoute) {
      // Remove default filters that hide downvoted content when explicitly searching for it
      defaultFilters = ["created EXISTS"];
    }

    const dynamicFilters = searchState.filters.map((f: any) => {
      if (f?.expression) return f.expression;
      return f?.op ? `${f.attribute} ${f.op} '${f.value}'` : `${f.attribute} = '${f.value}'`;
    });
    const combinedFilters = [...defaultFilters, ...dynamicFilters];
    
    console.log("Search:buildFilters", searchState.filters, combinedFilters);
    return combinedFilters;
  }
  async function search(append: boolean = false) {
    const query  = searchState.q || "";
    const filters = buildFilters();
    
    if (!append) {
      isLoading = true;
      // Reset offset for new searches
      results.offset = 0;
    } else {
      isLoadingMore = true;
    }
    
    try {
      const searchOptions: any = {
        facets: searchState.facets,
        offset: results.offset,
        limit: results.limit,
        sort: [`${sortOptions.field}:${sortOptions.direction}`]
      };
      
      // Only add filter if there are any
      if (filters.length > 0) {
        searchOptions.filter = filters;
      }
      console.log("Main::search:searchOptions",searchOptions, filters )
      const searchResponse = await index.search(query, searchOptions);
      console.log("Main::search:response",searchResponse)
      console.log("Main::search",searchResponse.hits)
      console.log("Main::search:facets",searchResponse.facetDistribution, index)
      
      if (append) {
        // Append new results to existing ones
        results.entries = [...results.entries, ...searchResponse.hits];
      } else {
        // Replace results for new searches
        results.entries = searchResponse.hits;
        results.facets = searchResponse.facetDistribution || {};
        collapsed = [...Object.keys(results.facets)]
      }
      
      results.estimatedTotalHits = searchResponse.estimatedTotalHits || 0;
      results.hasMore = results.entries.length < results.estimatedTotalHits;
      results.offset = results.entries.length;

      console.log(searchResponse)
      return searchResponse ;
    } catch (error) {
      console.error('Search error:', error);
      return [];
    } finally {
      isLoading = false;
      isLoadingMore = false;
    }
  }

  async function onSearch(query: string) {
    console.log('Searching for:', query);
    console.log("Search -", searchState.filters)
    searchState.q = query;
    updateUrl();
  }

  async function loadMore() {
    if (isLoadingMore || !results.hasMore) return;
    console.log('[InfiniteScroll] Loading more results...');
    await search(true);
  }

  // Infinite scroll action
  function infiniteScrollTrigger(node: HTMLElement) {
    const observer = new IntersectionObserver((entries) => {
      const [entry] = entries;
      if (entry.isIntersecting && results.hasMore && !isLoadingMore && !isLoading && results.entries.length > 0) {
        loadMore();
      }
    }, {
      rootMargin: '200px'
    });

    observer.observe(node);

    return {
      destroy() {
        observer.disconnect();
      }
    };
  }

  function saveSearch(name: string){
    filterController.save(name, searchState)
  }

  let count: number = $state(0)
  const increment = () => {
    count += 1
  }

  // Initialize index info on component mount
  const dateFacets  = ["dd","mm","year","dayOfWeek","yy","elapsedMS"]
  const keptFacets = ["loras", "models", "orientation", "samplers", "schedulers", "source"]

  let isListView = $state(false)
  let isDetailOn = $state(false)
  let text = $derived(searchState.q)
  let name = $state('')
  let showMetrics = $state(false)
  let hasWorkflowIdFilter = $derived(
    searchState.filters.some((f: any) => 
      f.attribute === 'workflow_id' || (f.expression && f.expression.includes('workflow_id'))
    )
  )
  
  let hasDateFilter = $derived(
    searchState.filters.some((f: any) => 
      ['dd', 'mm', 'yy', 'week', 'weekday', 'dayOfWeek', 'thisweek_dayOfWeek', 'time_bucket'].includes(f.attribute) || 
      (f.expression && (
        f.expression.includes('dd') || 
        f.expression.includes('mm') || 
        f.expression.includes('yy') || 
        f.expression.includes('week') || 
        f.expression.includes('dayOfWeek')
      ))
    )
  )
  
  // Initialize sortable attributes for the index
  async function initializeSortableAttributes() {
    try {
      await index.updateSortableAttributes(['created']);
      console.log("Sortable attributes updated successfully");
    } catch (error) {
      console.error('Error updating sortable attributes:', error);
    }
  }
  
  // Function to toggle sort direction
  function toggleSortDirection() {
    sortOptions.direction = sortOptions.direction === 'desc' ? 'asc' : 'desc';
    search();
  }
  
  // Function to change sort field
  function changeSortField(field: string) {
    sortOptions.field = field;
    search();
  }
  
  // Track previous filter to avoid infinite loops
  let previousFilter: any = $state(params?.filter)
  let previousQs: any = $state($querystring)

  // Apply initial route filter before the first search
  searchState.applyRouteFilter(params?.filter, $querystring)

  // Initialize sortable attributes and perform initial search
  initializeSortableAttributes();
  search();

  $effect( ()=> {
    console.log("Search:effect", results.entries[0])
  })
  
  // Apply filter shortcuts based on URL param - runs only when filter changes
  $effect(() => {
    const currentFilter = params?.filter
    const currentQs = $querystring
    
    if (currentFilter !== previousFilter || currentQs !== previousQs) {
      previousFilter = currentFilter
      previousQs = currentQs
      searchState.applyRouteFilter(currentFilter, currentQs)
      search()
    }
  })

  let facetCollapsed = $state(true)
  // search() 
  let hideElements = $derived(!!params?.id)
</script>

<div class="layout"> 
  <div class="layout__content">
    <!-- <SearchBar {onSearch} onclick={() => { facetCollapsed = !facetCollapsed}}   text={searchState.q}  /> 
    <SearchBarAdvanced  {onSearch} onclick={() => { facetCollapsed = !facetCollapsed}}   text={searchState.q} />  -->

    <div class="search-container">
      <div class="search-results">
        <FilterShortcuts {params} {onSearch} facets={results.facets} onRemoveFilter={removeFilter} onAddFilter={addFilter} />
        {#if isListView }
        <SearchResultList {results} />
        {:else}
        <!-- {JSON.stringify(searchState)} -->
        <SearchResultGrid {results} {isDetailOn} activeId={params?.id} {onAssetOpen} {onAssetClose} onUpdate={addFilter} />
        {#if hasWorkflowIdFilter || hasDateFilter}
          {#if $isExperimental}
          <div style="text-align: center; margin-top: 1rem;">
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span 
              role="button"
              tabindex="0"
              style="color: grey; cursor: pointer; user-select: none;" 
              onclick={() => showMetrics = !showMetrics}
            >
              metrics
            </span>
          </div>
          {#if showMetrics}
            <Metrics data={results.entries} onclick={() => showMetrics = false} />
          {/if}
          {/if}
        {/if}
        {/if}
        
        <!-- Infinite scroll sentinel and loading indicator -->
        {#if !hideElements}
          <div 
            use:infiniteScrollTrigger 
            class="infinite-scroll-sentinel"
          >
            {#if isLoadingMore}
              <div class="loading-indicator">
                <span>Loading more...</span>
                <div class="loading-spinner"></div>
              </div>
            {:else if !results.hasMore && results.entries.length > 0}
              <div class="no-more-results">No more results</div>
            {/if}
          </div>
        {/if}
      </div>
      
      {#if !facetCollapsed}
      <div class="facetbars">
        
      {#if searchState.filters.length > 0}
        <div class="active-filters">
          <div class="active-filters__header">Active Filters:</div>
          <div class="active-filters__list">
            {#each searchState.filters as filter}
              
              <span class="active-filter">

                {filter.attribute || 'expression'}: {filter.value ? (filter.value.length >= 8 ? filter.value.slice(0, 8) : filter.value) : filter.expression}
                <button class="active-filter__remove" onclick={() => removeFilter(filter.attribute, filter.value, filter.expression)}>×</button>
              </span>
            {/each}
            
          </div>
          <button class="run-again-button" onclick={() => {search();} }>RUN AGAIN</button>
          <div id="searchSaver">
            <div> Save As </div>
            <div> <input bind:value={name} onblur={() => saveSearch(name)} placeholder="Enter search name"> </div>
          </div>

        </div>
      {/if}
      <div style="display:flex;flex-direction:column;gap:0.5em">
       
        <Searches collapsed={true} onUpdate={search}/> 
      </div>
      <div class="facetbar"> <!-- facet side bar -->
      <div class="facetbar facetbar--date"> <!-- date facet side bar -->
          <!-- <div class="facetbar__header">Date Filters</div> -->
          {#each Object.entries(results.facets || {}) as [facetName, facetSummary]}
            {#if dateFacets.includes(facetName)}
             <div class="facetbar__entry">
                <div class="facetbar__entry__name">{facetName}</div>
                 <div class="facetbar__entry__values">
                     <ul class="facetbar__entry__list">
                       {#each Object.entries(facetSummary) as [value, count]}
                         <li
                           class:facetbar__entry__item--active={searchState.filters.some((f: any) => f.attribute === facetName && f.value === value)}
                           onclick={ ()=> addFilter({attribute: facetName, value: value}) }
                           class="facetbar__entry__item"
                         >
                           {value} : ({count})
                         </li>
                       {/each}
                     </ul>
                 </div>
             </div>
            {/if}
          {/each}
      </div>

           {#each Object.entries(results.facets || {}) as [facetName, facetSummary]}
             {#if keptFacets.includes(facetName)}
             <div class="facetbar__entry">
              {#if  collapsed.includes(facetName) }
                <div class="facetbar__entry__name" onclick = { () => {
                  console.log("effect:filter",collapsed.includes(facetName) , facetName, collapsed)
                  if (collapsed.includes(facetName)) {
                    collapsed = [...collapsed.filter( e =>  e!=facetName)]
                  }else{
                    collapsed.push(facetName)
                  }

                }}>{facetName} ({Object.values(facetSummary).length})</div>
              {:else}

                
                <div class="facetbar__entry__name" onclick = { () => {
                  console.log("effect:filter",collapsed.includes(facetName) , facetName, collapsed)
                  if (collapsed.includes(facetName)) {
                    collapsed = [...collapsed.filter( e =>  e!=facetName)]
                  }else{
                    collapsed.push(facetName)
                  }

                }}>{facetName}  
                
              
                </div>
                
                 <div class="facetbar__entry__values">
                     <ul class="facetbar__entry__list">
                       {#each Object.entries(facetSummary).sort((a, b) => (b[1] as number) - (a[1] as number)) as [value, count]}
                         <li
                           class:facetbar__entry__item--active={searchState.filters.some((f: any) => f.attribute === facetName && f.value === value)}
                           onclick={ ()=> addFilter({attribute: facetName, value: value}) }
                           class="facetbar__entry__item"
                         >
                           {value} : ({count})
                         </li>
                       {/each}
                     </ul>
                 </div>
                {/if}
             </div>
             {/if}
           {/each}
       </div>
       </div>
       {/if}
     </div>

   </div>
   <!-- <div class="layout__footer">Footer</div> -->
 </div>

<style>
  .layout {
    display: grid;
    grid-template-rows: auto 1fr auto;
    
    gap: 1rem;
    /* padding: 1rem; */
  }
  
  .layout__header {
    background-color: #f0f0f0;
    padding: 1rem;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
  }
  
  .view-toggle {
    display: flex;
    gap: 0.5rem;
  }
  
  .sort-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .sort-field-select {
    padding: 0.25rem 0.5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    background-color: #fff;
  }
  
  .sort-direction-button {
    padding: 0.25rem 0.5rem;
    border: 1px solid #ccc;
    background-color: #fff;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s ease;
  }
  
  .sort-direction-button:hover {
    background-color: #f0f0f0;
  }

  .view-toggle__button {
    padding: 0.5rem 1rem;
    border: 1px solid #ccc;
    background-color: #fff;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s ease;
  }

  .view-toggle__button:hover {
    background-color: #f0f0f0;
  }

  .view-toggle__button.active {
    background-color: #007bff;
    color: white;
    border-color: #007bff;
  }
  
  .layout__content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .layout__footer {
    background-color: #f0f0f0;
    padding: 1rem;
    border-radius: 4px;
  }

  .search-container {
    display: flex;
    gap: 1rem;
    flex: 1;
  }

  .search-results {
    flex: 1;
  }

  .facetbar {
    width: 250px;
    flex-shrink: 0;
  }

  .facetbar--date {
    margin-top: 1rem;
  }

  .facetbar__header {
    font-weight: bold;
    font-size: 1.1rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #ddd;
  }

  .facetbar__entry {
    margin-bottom: 1rem;
  }

  .facetbar__entry__name {
    font-weight: bold;
    margin-bottom: 0.5rem;
  }

  .facetbar__entry__list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .facetbar__entry__grid {
    display: flex;
    gap: 1em; 
    flex-wrap: wrap;

    padding: 0;
    margin: 0;
  }  

  .facetbar__entry__item {
    padding: 0.25rem 0;
    cursor: pointer;
  }
  
  .facetbar__entry__item:hover {
    background-color: #f0f0f0;
  }
  
  .facetbar__entry__item--active {
    font-weight: bold;
    color: #007bff;
  }
  
  .active-filters {
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: #f8f9fa;
    border-radius: 4px;
  }
  
  .active-filters__header {
    font-weight: bold;
    margin-bottom: 0.5rem;
  }
  
  .active-filters__list {
    display: flex;
    flex-wrap: wrap;
    flex-direction: row;
    gap: 0.5rem;
  }
  
  .active-filter {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.5rem;
    background-color: #e9ecef;
    border-radius: 4px;
    font-size: 0.8rem;
  }
  
  .active-filter__remove {
    margin-left: 0.25rem;
    background: none;
    border: none;
    cursor: pointer;
    font-weight: bold;
    color: #dc3545;
  }


  .search-results__grid {
    /* display: grid;
    grid-template-columns: repeat(4, 1fr); */
    display:flex;
    flex-wrap: wrap;
    
    text-align:left; 
  }

  @media (min-width: 1920px) {
    .search-results__grid {
      grid-template-columns: repeat(6, 1fr);
    }
  }

  @media (min-width: 2560px) {
    .search-results__grid {
      grid-template-columns: repeat(8, 1fr);
    }
  }

  @media (min-width: 3840px) {
    .search-results__grid {
      grid-template-columns: repeat(10, 1fr);
    }
  }

  @media (max-width: 1200px) {
    .search-results__grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  @media (max-width: 900px) {
    .search-results__grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 600px) {
    .search-results__grid {
      grid-template-columns: 1fr;
    }
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
    /* width: 100%;
     height: 200px; */
    max-width: max(100%,1886px)  ;
  
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
  .search-results__grid-item__loras {
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

  .search-summary {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background-color: #f8f9fa;
    border-radius: 4px;
    border-left: 4px solid #007bff;
  }

  .search-summary__stats {
    font-size: 0.9rem;
    color: #495057;
  }

  .infinite-scroll-sentinel {
    padding: 2rem 0;
    text-align: center;
    min-height: 60px;
  }

  .loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: #666;
    font-size: 0.9rem;
  }

  .loading-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #ddd;
    border-top-color: #007bff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .no-more-results {
    color: #999;
    font-size: 0.9rem;
    font-style: italic;
  }

</style>
  


<script lang="ts">
  import Search from './lib/Search.svelte'
  import Collection from './lib/Collection.svelte'
  import Collections from './lib/Collections.svelte'
  import Asset from './lib/Asset.svelte'
  import Searches from './lib/Searches.svelte'
  import Router from 'svelte-spa-router';
  import {setContext,getContext} from 'svelte'
	import { setupConvex ,useConvexClient } from 'convex-svelte';
  import { Meilisearch } from 'meilisearch';

	import { getConvexUrl, getMeilisearchUrl } from './lib/functions/convex_helpers.js';
  import { getWeekString } from './lib/functions/date_helpers.js';
  
 const PUBLIC_CONVEX_URL = import.meta.env.DEV ? window.location.origin : `http://${getConvexUrl()}`;

setupConvex(PUBLIC_CONVEX_URL);
const client = useConvexClient()
  
  const routes = {
    '/': Search,
    '/search' : Search,
    '/search/:filter' : Search,
    '/collections' : Collections,
    '/collection/:name' : Collection,
    '/collection/:name/:id' : Collection,
    '/collections/:name' : Collections,
    '/asset/:id' : Asset,
    '/searches' : Searches
  }



const indexName = import.meta.env.VITE_INDEX_NAME

const searchState = $state({
  indexName: import.meta.env.VITE_INDEX_NAME,
  q: '',
  routeFilters: [] as any[],
  customFilters: [] as any[],
  get filters() {
    return [...this.routeFilters, ...this.customFilters];
  },
  set filters(val) {
    this.customFilters = val;
  },
  facets: ["*"],
  page: 1,
  pageLimit: 50,

  update(partial: any) {
    if (partial.indexName !== undefined) this.indexName = partial.indexName
    if (partial.q !== undefined) this.q = partial.q
    if (partial.filters !== undefined) this.customFilters = partial.filters
    if (partial.facets !== undefined) this.facets = partial.facets
    if (partial.page !== undefined) this.page = partial.page
    if (partial.pageLimit !== undefined) this.pageLimit = partial.pageLimit
  },

  applyRouteFilter(filter: string | undefined, qs?: string) {
    let newQ = '';
    let newCustomFilters = [];
    
    if (qs) {
      const searchParams = new URLSearchParams(qs);
      if (searchParams.has('q')) {
        newQ = searchParams.get('q') || '';
      }
      if (searchParams.has('filters')) {
        try {
          newCustomFilters = JSON.parse(searchParams.get('filters') || '[]');
        } catch (e) {
          console.error("Failed to parse filters from querystring", e);
        }
      }
    }

    this.q = newQ;
    this.customFilters = newCustomFilters;
    this.page = 1;

    let newRouteFilters: any[] = [];
    switch (filter) {
      case 'upvoted':
        newRouteFilters = [{ expression: 'vote > 0 OR score > 0' }]
        break
      case 'downvoted':
        newRouteFilters = [{ expression: 'vote < 0 OR score < 0' }]
        break
      default:
        if (filter && filter.startsWith('thisweek_dayOfWeek:')) {
           const parts = filter.split(':');
           const weekValue = parts[1];
           const dayValue = parts[2];
           
           // Support both new 'week' facet (e.g. 2609) and old 'weekday' facet (e.g. 26093)
           const weekAttribute = weekValue.length === 4 ? 'week' : 'weekday';
           
           newRouteFilters = [
             { attribute: 'dayOfWeek', value: dayValue },
             { attribute: weekAttribute, value: weekValue }
           ];
        } else if (filter && filter.includes(':')) {
           const [key, value] = filter.split(':');
           newRouteFilters = [{ attribute: key, value: value }];
        }
    }
    this.routeFilters = newRouteFilters;
  }
})

setContext("app.indexName", indexName)
setContext('searchState', searchState)
setContext("convex.client", client)
setContext("search.client",new Meilisearch({
  host: getMeilisearchUrl(),
  apiKey: 'password'
})  )


</script>

<div class="app">
  <div class="app__text-logo">K</div>
  <!--div>{PUBLIC_CONVEX_URL}</div--> 
  <!-- <nav class="app__navigation">
    <div class="app__nav-container">      
      <a href="#/search" class="app__nav-link">Search</a>
      <a href="#/collections" class="app__nav-link">Collections</a>
      <a href="#/searches" class="app__nav-link">Saved Searches</a>
    </div>
  </nav> -->

  <main class="app__content">
    <Router {routes} />
  </main>
  
</div>
 
<style>
  /* Apple-inspired navigation design with BEM conventions */
  
  .app {
    /* min-height: 100vh; */
    /* background-color: #f5f5f7; */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width:1880px;
    padding: 0 8px;
  }

  .app__text-logo {
    font-size: 120px;
    line-height: 1;
    color: slategray;
    font-family: ui-rounded, "SF Pro Rounded", "Arial Rounded MT Bold", sans-serif;
    font-weight: 700;
    margin: 0;
    padding: 0;
    display: block;
    margin-right: auto;
  }

  .app__navigation {
    background-color: rgba(255, 255, 255, 0.72);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
   
    position: sticky;
    top: 0;
    z-index: 1000;
  }

  .app__nav-container {
    /* max-width: 1200px; */
    margin: 0 auto;
    /* padding: 0 22px; */
    display: flex;
    align-items: center;
    height: 52px;
  }

  .app__nav-link {
    display: inline-flex;
    align-items: center;
    padding: 0 16px;
    height: 32px;
    border-radius: 16px;
    color: #6b5b54;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    margin-right: 8px;
  }

  .app__nav-link:hover {
    background-color: rgba(0, 0, 0, 0.04);
    color: #4a3f38;
  }

  .app__nav-link:active {
    transform: scale(0.98);
    background-color: rgba(0, 0, 0, 0.08);
  }

  .app__nav-link--active {
    background-color: #e8d5c4;
    color: #6b5b54;
  }

  .app__nav-link--active:hover {
    background-color: #d4b5a0;
    color: #4a3f38;
  }

  .app__content {
    /* max-width: 1200px; */
    /* margin: 0 auto; */
    padding: 14px 12px;
  }

  /* Keep existing logo styles for potential future use */
  .logo {
    height: 6em;
    padding: 1.5em;
    will-change: filter;
    transition: filter 300ms;
  }
  
  .logo:hover {
    filter: drop-shadow(0 0 2em #646cffaa);
  }
  
  .logo.svelte:hover {
    filter: drop-shadow(0 0 2em #ff3e00aa);
  }
  
  .read-the-docs {
    color: #888;
  }
</style>


<script>
  import {useQuery} from 'convex-svelte'
  import {getContext} from 'svelte'
  import { api } from "../convex/_generated/api.js";
  import Collection from './Collection.svelte';
  import { push } from 'svelte-spa-router';
  
  let { params = {}  } = $props()  
  const client = getContext("convex.client")
  const bookmarks = useQuery(api.bookmarks.getAll, {});
  let selectedCollection = $derived( params?.name  ?  params.name  : "default");

  function getNames(entries) {
    const aSet = new Set()
    aSet.add("default")
    entries.forEach((el) => {
        aSet.add(el.name)
    })
    console.log("Collections:getNames", aSet)
    return Array.from(aSet)
  }

  function selectCollection(name) {
    selectedCollection = name;
  }

  $effect(()=>{
    console.log("Collections:effect:", bookmarks , bookmarks.data)
  })
</script>

<div class="collections">
  <div class="collections__header">
    <h2 class="collections__title" onclick={() => {push("#/search")}}>Collections</h2>
  </div>
  {#if bookmarks.isLoading}
    <div class="collections__loading">Loading...</div>
  {:else if bookmarks.error}
    <div class="collections__error">Error: {bookmarks.error}</div>
  {:else}
    <div class="collections__content">
      {#if bookmarks.data}
        <div class="collections__tabs">
          {#each getNames(bookmarks.data) as collection}
            <!-- <button
              class="collections__tab"
              class:collections__tab--active={selectedCollection === collection}
              onclick={() => selectedCollection = collection}
            >
              {collection}
            </button> -->
            <button
              class="collections__tab"
              class:collections__tab--active={selectedCollection === collection}
              onclick = {() => { push(`#/collection/${collection}`)} } 
            >
              {collection}
            </button>


          {/each}
        </div>
        
        <div class="collections__viewer">
          <Collection id={selectedCollection} />
        </div>
      {:else}
        <div class="collections__empty">
          <p class="collections__empty-text">No collections found</p>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  /* Apple-inspired minimalistic design with BEM conventions */
  
  .collections {
    padding: 0;
    width: 100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  .collections__header {
    margin-bottom: 16px;
    padding: 0;
  }

  .collections__title {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    /* color: #1d1d1f; */
    color: #85d1ff; 
    letter-spacing: -0.022em;
  }

  .collections__loading,
  .collections__error {
    padding: 24px 16px;
    text-align: center;
    font-size: 14px;
  }

  .collections__loading {
    color: #86868b;
  }

  .collections__error {
    color: #ff3b30;
  }

  .collections__content {
    width: 100%;
  }

  .collections__tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 24px;
    padding: 0;
    justify-content: center;
  }

  .collections__tab {
    padding: 8px 16px;
    border: none;
    border-radius: 20px;
    background-color: #f2f2f7;
    color: #86868b;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
  }

  .collections__tab:hover {
    background-color: #e5e5ea;
    color: #000;
  }

  .collections__tab:active {
    transform: scale(0.98);
  }

  .collections__tab--active {
    background-color: #7dd3fc;
    color: #0c4a6e;
  }

  .collections__tab--active:hover {
    background-color: #38bdf8;
    color: #0c4a6e;
  }

  .collections__viewer {
    width: 100%;
    min-height: 300px;
  }

  .collections__empty {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 48px 16px;
  }

  .collections__empty-text {
    color: #86868b;
    font-size: 14px;
    font-weight: 400;
  }
</style>
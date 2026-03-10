<script>
  import {useQuery} from 'convex-svelte'
  import {push} from 'svelte-spa-router'
  import {getContext} from 'svelte'
  import { createBookmarkController } from './controllers/BookmarkController.js';
  import { api } from "../convex/_generated/api.js";
  
  let {index, asset  } = $props()
  const client = getContext("convex.client")
  const bookmarks = useQuery(api.bookmarks.getAll, {});
  const bookmarkController = createBookmarkController(client);
  let newCollectionName = $state("");
  let showDropdown = $state(false);

  // Derive active bookmarks for this asset
  let activeBookmarks = $derived.by(() => {
    if (!bookmarks.data || !asset) return [];
    return bookmarks.data.filter(el => 
      el.asset_id && el.asset_id.id === asset.id
    );
  });

  // Derive suggested bookmarks based on input
  let suggestedBookmarks = $derived.by(() => {
    if (!bookmarks.data || !newCollectionName.trim()) return [];
    
    const query = newCollectionName.toLowerCase();
    const activeNames = new Set(activeBookmarks.map(b => b.name));
    
    // Get all unique names in the system
    const allNames = new Set(["default"]); // Ensure default is always an option
    bookmarks.data.forEach(el => allNames.add(el.name));
    
    // Filter to names that match query AND aren't already active
    return Array.from(allNames).filter(name => 
      !activeNames.has(name) && name.toLowerCase().includes(query)
    );
  });

  async function handleRemoveBookmark(bookmark) {
    try {
      await bookmarkController.delete(bookmark._id);
      console.log("Bookmarker:handleRemoveBookmark removed", bookmark.name);
    } catch (error) {
      console.error("Bookmarker:handleRemoveBookmark error removing", error);
    }
  }

  async function handleSuggestionClick(suggestionName) {
    await saveInBookmark(index, suggestionName, asset);
    newCollectionName = "";
    showDropdown = false;
  }

  async function handleInputBlur() {
    // Delay slightly to allow suggestion click to register first
    setTimeout(async () => {
      showDropdown = false;
      if (newCollectionName.trim()) {
        await saveInBookmark(index, newCollectionName.trim(), asset);
        newCollectionName = "";
      }
    }, 200);
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      // Unfocus the input to trigger the save flow
      e.target.blur();
    }
  }

  async function saveInBookmark(index, name, asset){
    try {
      const bookmarkData = {
        indexName: index,
        name: name || "default",
        asset_id: {
          id: asset.id,
          type: asset.type || "image"
        }
      };
      
      const result = await bookmarkController.create(bookmarkData);
      console.log("Bookmarker:saveInBookmark success", result);
      return result;
    } catch (error) {
      console.error("Bookmarker:saveInBookmark error", error);
      throw error;
    }
  }

  async function saveNewCollection() {
    if (newCollectionName.trim()) {
      await saveInBookmark(index, newCollectionName.trim(), asset);
      newCollectionName = "";
    }
  }

  $effect(()=>{
    console.log("Bookmarker:effect:", bookmarks , bookmarks.data)
  })
</script>

<div class="bookmarker">
  {#if bookmarks.isLoading}
    <div class="bookmarker__loading">Loading...</div>
  {:else if bookmarks.error}
    <div class="bookmarker__error">Error: {bookmarks.error}</div>
  {:else}
      {#if bookmarks.data}  
    <div class="bookmarker__content">
        <div class="bookmarker__list">
          {#each activeBookmarks as bookmark}
            <button
              class="bookmarker__item bookmarker__item--active"
              onclick={() => handleRemoveBookmark(bookmark)}
            >
              <span class="bookmarker__item-name">{bookmark.name}</span>
            </button>
          {/each}
          
          <span onclick={()=> {push("#/collections")}} style="cursor: pointer; opacity: 0.6; display: flex; align-items: center;" title="View Collections">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </span>
        </div>
    </div>
    
    <div class="bookmarker__new-collection">
      <input
        type="text"
        class="bookmarker__new-collection-input"
        placeholder="Type to save to new bookmark"
        bind:value={newCollectionName}
        onfocus={() => showDropdown = true}
        onblur={handleInputBlur}
        onkeydown={handleKeydown}
      />
      
      {#if showDropdown && suggestedBookmarks.length > 0}
        <div class="bookmarker__dropdown">
          {#each suggestedBookmarks as suggestion}
            <div 
              class="bookmarker__dropdown-item"
              onpointerdown={(e) => {
                // Use pointerdown instead of click so it fires before input blur
                e.preventDefault();
                handleSuggestionClick(suggestion);
              }}
            >
              {suggestion}
            </div>
          {/each}
        </div>
      {/if}
    </div>    
          {:else}
        <div class="bookmarker__empty">
          <p class="bookmarker__empty-text">No bookmarks found</p>
        </div>
      {/if}

  {/if}
</div>

<style>
  /* Apple-inspired minimalistic design with BEM conventions */
  
  .bookmarker {
    width:100%;
    padding: 0;
    background-color: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  .bookmarker__loading,
  .bookmarker__error {
    padding: 12px 16px;
    font-size: 14px;
    color: #86868b;
    text-align: center;
  }

  .bookmarker__error {
    color: #ff3b30;
  }

  .bookmarker__content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    justify-content:left; 
  }

  .bookmarker__list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .bookmarker__item {
    padding: 0.25rem 0.75rem;
    border: 1px solid rgba(0, 0, 0, 0.04);
    border-radius: 16px;
    background-color: #f5f5f7;
    color: #6b5b54;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
  }

  .bookmarker__item:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.04);
    color: #4a3f38;
  }

  .bookmarker__item:active {
    transform: scale(0.98);
    background-color: rgba(0, 0, 0, 0.08);
  }

  /* Active state mimics a selected or "workflow" facet pill color */
  .bookmarker__item--active {
    background-color: #dce8dc;
    color: #6b5b54;
  }

  .bookmarker__item--active:hover {
    background-color: #c8d5cc;
    color: #4a3f38;
  }

  .bookmarker__item-name {
    display: block;
  }

  .bookmarker__empty {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 32px 16px;
  }

  .bookmarker__empty-text {
    color: #86868b;
    font-size: 14px;
    font-weight: 400;
  }

  .bookmarker__new-collection {
    flex: 1;
    min-width: 120px;
    margin-top: 4px;
    position: relative;

  }

  .bookmarker__new-collection-input {
    /* width: 100%; */ 
    padding: 8px 16px;
    border: none;
    border-radius: 20px;
    background-color: #e9ecef;
    color: #495057;
    font-size: 14px;
    font-weight: 500;
    outline: none;
    transition: all 0.2s ease;
  }

  .bookmarker__new-collection-input::placeholder {
    color: #adb5bd;
  }

  .bookmarker__new-collection-input:focus {
    background-color: #ffffff;
    box-shadow: 0 0 0 2px rgba(107, 91, 84, 0.25);
  }

  /* Dropdown Styles */
  .bookmarker__dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    margin-top: 4px;
    background: #ffffff;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    max-height: 200px;
    overflow-y: auto;
    padding: 4px 0;
    border: 1px solid rgba(0, 0, 0, 0.05);
  }

  .bookmarker__dropdown-item {
    padding: 8px 16px;
    font-size: 14px;
    color: #495057;
    cursor: pointer;
    transition: background-color 0.1s ease;
  }

  .bookmarker__dropdown-item:hover {
    background-color: #f8f9fa;
  }
</style>
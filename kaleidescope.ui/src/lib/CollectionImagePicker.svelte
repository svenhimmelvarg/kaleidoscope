<script>
  import { useQuery } from 'convex-svelte';
  import { getContext } from 'svelte';
  import { api } from "../convex/_generated/api.js";
  import { fixImageUrl } from './functions/uri_helpers';

  let { onSelect = () => {} } = $props();

  const indexName = getContext("app.indexName");
  const mClient = getContext("search.client");
  const bookmarks = useQuery(api.bookmarks.getAll, {});

  let selectedCollection = $state(null);

  function getNames(entries) {
    if (!entries) return [];
    const aSet = new Set();
    aSet.add("default");
    entries.forEach((el) => {
        if (el.name) aSet.add(el.name);
    });
    return Array.from(aSet);
  }

  async function getDocument(assetId) {
    const doc = await mClient.index(indexName).getDocument(assetId);
    return doc;
  }
</script>

{#if bookmarks.isLoading}
  <div style="color:#666; font-size:14px;">Loading collections...</div>
{:else if bookmarks.error}
  <div style="color:red; font-size:14px;">Error: {bookmarks.error}</div>
{:else if bookmarks.data}
  {#if !selectedCollection}
    <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 8px;">
      {#each getNames(bookmarks.data) as name}
        <button 
          style="padding: 6px 12px; border-radius: 16px; border: 1px solid #ccc; background: #f2f2f7; cursor:pointer;"
          onclick={() => selectedCollection = name}
        >
          {name}
        </button>
      {/each}
    </div>
  {:else}
    <div style="margin-bottom: 10px; display: flex; align-items: center; gap: 10px;">
      <button 
        style="padding: 4px 8px; border-radius: 4px; border: 1px solid #ccc; background: #eee; cursor:pointer; font-size: 14px;"
        onclick={() => selectedCollection = null}
      >
        &larr; Back
      </button>
      <span style="font-weight:bold; font-size: 14px;">{selectedCollection}</span>
    </div>

    <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 5px;">
      <!-- Show images in the chosen collection -->
      {#each bookmarks.data.filter(b => (b.name || "default") === selectedCollection).reverse() as entry}
        {#if entry.asset_id && entry.asset_id.id}
          {#await getDocument(entry.asset_id.id)}
            <div style="width:100px;height:100px; background:#eee; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:10px; color:#999;">...</div>
          {:then hit}
            <div>
              <img 
                style="width:100px;height:100px;object-fit:cover;border-radius:4px;cursor:pointer;" 
                src="{fixImageUrl(hit.image_url, hit.source)}"
                alt="Collection item"
                onclick={() => onSelect(hit)}
              />
            </div>
          {:catch}
            <!-- Ignore failed/deleted documents -->
          {/await}
        {/if}
      {/each}
    </div>
  {/if}
{/if}

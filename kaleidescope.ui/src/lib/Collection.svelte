<script>
import {useQuery} from 'convex-svelte'
import { api } from "../convex/_generated/api.js";
import { createBookmarkController } from './controllers/BookmarkController.js';
import { Meilisearch } from 'meilisearch';
import {location, querystring} from 'svelte-spa-router'

import {getContext} from 'svelte'
import { getMeilisearchUrl } from './functions/convex_helpers.js';
import { fixImageUrl } from './functions/uri_helpers';
import Asset from './Asset.svelte';
import Metrics from './Metrics.svelte';
import { featureOn } from './growthbook';

let { params = {} ,  id = 'default'} = $props() 
let isExperimental = featureOn("experimental");
let name = $derived(params.name ||  id );

const index = getContext("app.indexName")
const client = getContext("convex.client")
const bookmarkController = createBookmarkController(client)
const query = $derived(   useQuery(api.bookmarks.getAll, { indexName: index, name }) ) 

const mClient = new Meilisearch({
    host:  getMeilisearchUrl(),
    apiKey: 'password'
});


async function getByPrompt(prompt_id) {
    try {
        const notifications = await client.query(api.notifications.getByPrompt, {
                prompt_id
        });
        console.log("Notifications:", notifications.length )
        return notifications;
    } catch (error) {
        console.log("Notifications:error",error )
        console.error('Error fetching notifications:', error);
        return [];
    }
}



async function getDocument(asset){
    const doc = await mClient.index(index).getDocument(asset.id)
    return doc
}

async function getAncestors(docId) {
    let results = [];
    let currentId = docId;
    let visited = new Set();
    const regex = /([a-f0-9]{32,64})\.(?:png|jpg|jpeg|mp4|webp)$/i;

    while (currentId && !visited.has(currentId)) {
        visited.add(currentId);
        try {
            const doc = await mClient.index(index).getDocument(currentId);
            results.push(doc);
            
            let nextId = null;
            if (doc.inputs) {
                for (let i of doc.inputs) {
                    if (i?.type?.trim() === "image" && i.value) {
                        const match = i.value.match(regex);
                        if (match && match[1]) {
                            nextId = match[1];
                            break;
                        }
                    }
                }
            }
            currentId = nextId;
        } catch (e) {
            console.error("Failed to fetch ancestor:", currentId, e);
            break;
        }
    }
    return results;
}

let selected = $state(null)
let showMetrics = $state(false)
let it = $derived(window.location)
let showTitle = $derived(!window.location.href.includes('collections'));

</script>
<div class="collection">
  
  
<!-- {name} , {JSON.stringify(params,null,2)} -->
{#if query.isLoading}
    <div class="collection__loading">Loading</div>
{:else if query.error}
<div class="collection__error">Error: {query.error}</div>
{:else}

    {#if !selected}

      {#if showTitle}    
      <div class="collections__header">
        <a href="#/collections/{name}"><h2 class="collections__title">{name}</h2></a>
      </div>
      {/if}

    <div style="margin-bottom:20px"></div>

    <div class="collection__container">
        <!-- <h2 class="collection__title">{name}</h2> -->
        <div class="collection__grid">
          
            {#each Array.from(query.data).reverse() as entry }
                {#await getDocument(entry.asset_id)}
                        <div class="collection__item collection__item--loading">
                            Loading doc {entry.asset_id.id}
                        </div>
                {:then doc}
                    
                    <div class="collection__item" onclick={()=>{ 
                        if(selected == entry.asset_id.id){
                          selected = null 
                        }else{
                          selected = entry.asset_id.id
                        }

                    }}>
                        <span>

                        
                        <img
                            class="collection__item-image"
                            src={fixImageUrl(doc.image_url, doc.source)}
                            alt="Generated image"
                            style="height:100%"
                        />
                          {#await getByPrompt(doc.id)}
                            Loading ... 
                          {:then n}
                            {#if n.length > 0}
                              <span style=""> {n.length}</span>
                              
                            {/if}
                          {/await}                           
                        </span>
                        
                    </div>

                {/await}
            {/each}
        </div>
    </div>

    {:else}
                                  
        <div style="display: flex; flex-direction: column; gap: 20px;">
            <Asset params={{ id: selected }} onSelect={()=>{ console.log("Collection:click:asset", selected); selected = null; showMetrics = false;}} />
            
            {#if isExperimental}
                <div style="display: flex; justify-content: center; margin-top: 10px;">
                    <button class="metrics-toggle-btn" onclick={() => showMetrics = !showMetrics}>
                        Metrics
                    </button>
                </div>
                {#if showMetrics}
                    {#await getAncestors(selected)}
                        <div class="collection__loading">Loading metrics...</div>
                    {:then ancestors}
                        {#if ancestors.length > 0}
                            <div style="width: 80%; max-width: 1200px; margin: 0 auto;">
                                <Metrics data={ancestors} />
                            </div>
                        {/if}
                    {/await}
                {/if}
            {/if}
        </div>
    {/if}

{/if}

</div>

<style>
  .collection {
    padding: 1rem;
    width: 100%;
  }

  .collection__loading,
  .collection__error {
    padding: 2rem;
    text-align: center;
    font-size: 1.1rem;
  }

  .collection__error {
    color: #e74c3c;
  }

  .collection__container {
    width: 100%;
  }

  /* .collection__title {
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
    font-weight: 600;
    color: #333;
  } */

    .collections__title {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    /* color: #1d1d1f; */
    color: #85d1ff; 
    letter-spacing: -0.022em;
  }

  .collection__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    grid-auto-rows: minmax(200px, auto);
    gap: 16px;
    width: 100%;
  }

  .collection__item {
    background-color: #fff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
  }

  .collection__item:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  }

  .collection__item--loading {
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f8f9fa;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .collection__item-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .metrics-toggle-btn {
    background-color: #f0f0f0;
    color: #333;
    border: 1px solid #ccc;
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .metrics-toggle-btn:hover {
    background-color: #e0e0e0;
  }
</style>
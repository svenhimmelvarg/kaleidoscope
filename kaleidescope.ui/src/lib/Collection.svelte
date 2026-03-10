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


let { params = {} ,  id = 'default'} = $props() 
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

let selected = $state(null)
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
                                  
        <Asset params={{ id: selected }} onSelect={()=>{ console.log("Collection:click:asset", selected); selected = null}} />
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
</style>
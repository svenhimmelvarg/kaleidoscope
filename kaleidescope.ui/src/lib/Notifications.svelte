<script>
import { getContext }  from 'svelte'
import { api } from "../convex/_generated/api.js";
import {useQuery} from 'convex-svelte'
  import { derived } from 'svelte/store';
import BentoBox from './BentoBox.svelte';


// queryMode  = {pending | doc_id }
let { ids = []  ,queryMode = "pending",  message = "Loading", show = true, onclick= (x = null) => { } ,showTrimmings = false } = $props();


const client = getContext("convex.client")
const mClient = getContext("search.client")
const indexName = getContext("app.indexName")

let docCache = $state({})

async function checkImageStatus(id) {
    if (docCache[id] !== undefined) return docCache[id]
    if (!mClient || !indexName) return true
    try {
        const doc = await mClient.index(indexName).getDocument(id)
        const valid = doc.vote !== -1 && (doc.score === undefined || doc.score >= 0)
        docCache[id] = valid
        return valid
    } catch (e) {
        docCache[id] = true
        return true
    }
}

async function filterRelated(notifications) {
    if (!notifications || notifications.length === 0) return [];
    
    const results = await Promise.all(notifications.map(async (related) => {
        if (related.payload?.output?.images?.[0]) {
            const img = related.payload.output.images[0];
            const isValid = await checkImageStatus(img._id);
            return isValid ? related : null;
        }
        return null;
    }));
    
    return results.filter(n => n !== null);
}

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

function click(img){
  onclick(img._id)
}

async function cancelNotification(notificationId, event) {
    event.stopPropagation();
    try {
        await fetch(`/cancel/${notificationId}`, { method: 'POST' });
    } catch (error) {
        console.error('Failed to cancel notification:', error);
    }
}

// Function to check if a notification is recent (created within the last 10 minutes)
function isNotificationRecent(creationTime) {
    if (!creationTime) return false;
    const tenMinutesInMs = 10 * 60 * 1000;
    const now = Date.now();
    return (now - creationTime) < tenMinutesInMs;
}

function getInputSummary(notification) {
    if (!notification?.payload?.input?.length) return '';

    const input = notification.payload.input[0];
    const keys = Object.keys(input).filter(k => k !== 'id' && k !== '_id');

    for (const key of keys) {
        if (key.startsWith('text')) return '[T]';

        if (key.includes('aspect_ratio') || key.includes('ar')) {
            const value = input[key];
            const ratioMatch = value.match(/(\d+:\d+)/);
            return ratioMatch ? `[${ratioMatch[1]}]` : `[${value}]`;
        }

        if (key.includes('image') || key.includes('img') ||
            (typeof input[key] === 'string' && input[key].startsWith('virtual://'))) {
            return '[IMG]';
        }
    }

    return '';
}

// const query = $derived( ids ?  useQuery(api.notifications.getAll,{ ids}) :  null)
// const query = $derived( ids  ?  useQuery(api.notifications.getByPrompt,{prompt_id : "0" }) :  null)
const query = $derived.by( () => {
  if (!ids) {return null }
  if (queryMode=="pending") { return useQuery(api.notifications.getAll,{ ids}) } 
  if (queryMode=="prompt_id") { return useQuery(api.notifications.getByPrompt,{ prompt_id: ids[0]}) } 

})

$effect(()=> {
console.log("Notifications:query",query?.isLoading, query?.error, query?.data )
})


</script>


    {#if query?.data && query?.data.length > 0 } 

{#if showTrimmings }
<div class="generated-images-header">Renders</div>    
{/if}
<div class="generated-images-grid">

        {#each query.data as n }
            {#key n.status}
            
{#if n.status == "completed"}
                      {#each n.payload?.output?.images as  img}
                          {#await checkImageStatus(img._id) then isValid}
                              {#if isValid}
                                  {@const relatedQuery = useQuery(api.notifications.getRelatedByPrompt, { prompt_id: img._id })}
                                  {#if relatedQuery?.data && relatedQuery.data.length > 0}
                                      {#await filterRelated(relatedQuery.data) then filteredRelated}
                                          {#if filteredRelated.length > 0}
                                            <BentoBox notification={n} relatedNotifications={filteredRelated} onclick={click}/>
                                          {:else}
                                            <img src={img.uri} alt="Generated image" class="generated-image"  onclick={() =>  click(img)}/>
                                          {/if}
                                      {/await}
                                  {:else}
                                    <img src={img.uri} alt="Generated image" class="generated-image"  onclick={() =>  click(img)}/>
                                  {/if}
                              {/if}
                          {/await}
                      {/each}
              {:else if n.status == "pending" && isNotificationRecent(n._creationTime)}
                      <div class="notification" onclick={()=>{ click({_id :  n.prompt_id})}}>
                          <span class="notification__dots">
                              <span class="notification__dot">{n.status}</span>
                              <span class="notification__dot">.</span>
                              <span class="notification__dot">.</span>
                              <span class="notification__dot">.</span>
                          </span>
                          {#if getInputSummary(n)}
                              <span class="notification__summary">{getInputSummary(n)}</span>
                          {/if}
                          <span 
                              class="notification__cancel" 
                              onclick={(e) => cancelNotification(n._id, e)}
                              title="Cancel"
                          >
                              [x]
                          </span>
                      </div>
              {/if}
            {/key}
        {/each}    


</div>
    {/if}

<style>

  .generated-images-header {
    font-size: 2em;
    font-weight: 600;
    /* color: #3a7397cc;  */
    display:flex; 

  }  

  .generated-images-grid {
    /* display: flex;
    flex-wrap: wrap;
    flex-direction:row-reverse; 
    gap: 0.5rem; */
  display: flex;
  flex-wrap: wrap;
  /* flex-direction: row-reverse; */
  gap: 0.5rem;
  padding: 0.5rem;
  /* background: #222; */
  border-radius: 16px;    
  
  }

  .generated-image-container {
    flex: 0 0 calc(25% - 1rem);
    min-width: 200px;
  }

  .generated-image {
    /* width: 100%; */
    height: 200px;
    object-fit: cover;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    background-color: #f8f9fa;
  }

  .notification {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    padding: 1rem;
    border-radius: 8px;
    background-color: #FEFEFE;
    /* box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); */
    /* border: 1px solid rgba(0, 0, 0, 0.05); */

    width:120px;
    height: 120px;
  }
  
  .notification__text {
    font-weight: 500;
    color: #495057;
  }
  
  .notification__dots {
    display: flex;
    gap: 0.1rem;
  }
  
  .notification__dot {
    animation: pulse 1.4s infinite ease-in-out both;
    color: #495057;
  }
  
  .notification__dot:nth-child(1) {
    animation-delay: -0.32s;
  }
  
  .notification__dot:nth-child(2) {
    animation-delay: -0.16s;
  }

  .notification__summary {
    font-size: 0.7rem;
    color: #6c757d;
    font-weight: 600;
    margin-top: 0.25rem;
  }
  
  .notification__cancel {
    cursor: pointer;
    color: #adb5bd;
    font-size: 0.7rem;
    margin-top: 0.25rem;
  }
  
  .notification__cancel:hover {
    color: #495057;
  }

  @keyframes pulse {
    0%, 80%, 100% {
      opacity: 0.3;
      transform: scale(0.8);
    }
    40% {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
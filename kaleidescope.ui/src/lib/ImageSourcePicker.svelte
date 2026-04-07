<script>
  import { getContext } from 'svelte';
  import { fixImageUrl } from "./functions/uri_helpers";
  import CollectionImagePicker from './CollectionImagePicker.svelte';
  import SearchResultGrid from './SearchResultGrid/SearchResultGrid.svelte';
  import { featureOn } from './growthbook';

  let { doc, inputImage, onSelectImage } = $props();
  let isExperimental = featureOn("experimental");

  let hashDocId = $derived.by(() => {
    if (!inputImage || !inputImage.value) return null;
    const releaseFolder = import.meta.env.VITE_RELEASE_FOLDER || 'release';
    const regex = new RegExp(`${releaseFolder}s?\\/([a-f0-9]{32,64})\\.(png|mp4|jpg|jpeg|webp)$`, 'i');
    const match = inputImage.value.match(regex);
    if (match && match[1]) {
      return match[1];
    }
    const hashRegex = /([a-f0-9]{32,64})\.(png|jpg|jpeg|mp4|webp)$/i;
    const hashMatch = inputImage.value.match(hashRegex);
    if (hashMatch && hashMatch[1]) {
      return hashMatch[1];
    }
    return null;
  });

  const indexName = getContext("app.indexName");
  const mClient = getContext("search.client");

  async function getWorkflowResults(docId) {
    try {
      const sourceDoc = await mClient.index(indexName).getDocument(docId);
      if (sourceDoc && sourceDoc.workflow_id) {
        const ret = await mClient.index(indexName).search("", {
          filter: `workflow_id = "${sourceDoc.workflow_id}"`,
          sort: ['created:desc'],
          limit: 50
        });
        return ret.hits;
      }
    } catch (e) {
      console.error("Failed to fetch workflow results for:", docId, e);
    }
    return [];
  }

  let inputTab = $state("input");

  async function getFacetValues(doc,name){
    const ret = await mClient.index(indexName).search("", {
      sort: ['created:desc'],
      limit: 1000,
      attributesToRetrieve: ['inputs']
    });

    const uniqueImages = new Set();
    const images = [];

    ret.hits.forEach(h => {
      const imageInputs = (h.inputs || []).filter(i => i.type && i.type.trim() === 'image');
      imageInputs.forEach(i => {
        if (i.value && /\.(png|jpe?g|webp|gif|bmp|tiff?)$/i.test(i.value)) {
          if (!uniqueImages.has(i.value)) {
            uniqueImages.add(i.value);
            images.push(i.value);
          }
        }
      });
    });
    const releaseFolder = import.meta.env.VITE_RELEASE_FOLDER || 'release';
    const releaseImages = [];
    const otherImages = [];
    
    images.forEach(img => {
      if (img.startsWith(`${releaseFolder}/`)) {
        releaseImages.push(img);
      } else {
        otherImages.push(img);
      }
    });
    
    const finalImages = [...releaseImages, ...otherImages];
    
    console.log("ImageSourcePicker:getFaceValues", name, finalImages)
    return finalImages;
  }

  async function getRecentOutputs(doc, daysOffset) {
    const today = new Date();
    today.setDate(today.getDate() - daysOffset);
    const yy = today.getFullYear();
    const mm = today.getMonth() + 1;
    const dd = today.getDate();

    const ret = await mClient.index(indexName).search("", {
      filter: `yy = ${yy} AND mm = ${mm} AND dd = ${dd}`,
      sort: ['created:desc'],
      limit: 100
    });
    return ret.hits.filter(h => !(h.vote < 0) && !(h.score < 0)).slice(0, 50);
  }

  async function getUpvotedOutputs(doc) {
    const ret = await mClient.index(indexName).search("", {
      filter: `vote >= 1`,
      sort: ['created:desc'],
      limit: 50
    });
    return ret.hits;
  }

</script>

<div>
  <div style="display:flex; gap: 10px; margin-bottom: 10px; cursor:pointer;">
     <div onclick={() => inputTab = 'input'} style="{inputTab === 'input' ? 'font-weight:bold' : ''}">Pick Input</div>
     <div onclick={() => inputTab = 'upvoted'} style="{inputTab === 'upvoted' ? 'font-weight:bold' : ''}">Upvoted</div>
     <div onclick={() => inputTab = 'today'} style="{inputTab === 'today' ? 'font-weight:bold' : ''}">Today</div>
     <div onclick={() => inputTab = 'yesterday'} style="{inputTab === 'yesterday' ? 'font-weight:bold' : ''}">Yesterday</div>
     <div onclick={() => inputTab = 'collections'} style="{inputTab === 'collections' ? 'font-weight:bold' : ''}">Collections</div>
     {#if isExperimental && hashDocId}
        <div onclick={() => inputTab = 'workflow'} style="{inputTab === 'workflow' ? 'font-weight:bold' : ''}">Workflow</div>
     {/if}
  </div>
  
  {#if inputTab === 'input'}
     {#await getFacetValues(doc,'inputs.value')}
        Nothing ...
     {:then images}
         <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 5px;">
         {#each images as i }
         <div>
            <img style="width:100px;height:100px;object-fit:cover;border-radius:4px" src="{`/images/${doc.source}/input/${i}`}"
              onclick = { () => {
                    onSelectImage(i)
                }
              }
            />
          </div>
         {/each}
         </div>
     {/await}
  {:else if inputTab === 'upvoted'}
     {#await getUpvotedOutputs(doc)}
        Loading upvoted...
     {:then hits}
         <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 5px;">
         {#each hits as hit }
         <div>
            <img style="width:100px;height:100px;object-fit:cover;border-radius:4px" src="{fixImageUrl(hit.image_url, doc.source)}"
              onclick = { () => {
                    onSelectImage(`local-output://${hit.id}||${hit.image_url}`)
                }
              }
            />
          </div>
         {/each}
         </div>
     {/await}
  {:else if inputTab === 'today'}
     {#await getRecentOutputs(doc, 0)}
        Loading today...
     {:then hits}
         <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 5px;">
         {#each hits as hit }
         <div>
            <img style="width:100px;height:100px;object-fit:cover;border-radius:4px" src="{fixImageUrl(hit.image_url, doc.source)}"
              onclick = { () => {
                    onSelectImage(`local-output://${hit.id}||${hit.image_url}`)
                }
              }
            />
          </div>
         {/each}
         </div>
     {/await}
  {:else if inputTab === 'yesterday'}
     {#await getRecentOutputs(doc, 1)}
        Loading yesterday...
     {:then hits}
         <div style="display:flex; flex-direction:row; flex-wrap:wrap; gap: 5px;">
         {#each hits as hit }
         <div>
            <img style="width:100px;height:100px;object-fit:cover;border-radius:4px" src="{fixImageUrl(hit.image_url, doc.source)}"
              onclick = { () => {
                    onSelectImage(`local-output://${hit.id}||${hit.image_url}`)
                }
              }
            />
          </div>
         {/each}
         </div>
     {/await}
  {:else if inputTab === 'collections'}
     <CollectionImagePicker 
       onSelect={(hit) => {
         onSelectImage(`local-output://${hit.id}||${hit.image_url}`);
       }} 
     />
  {:else if inputTab === 'workflow' && isExperimental && hashDocId}
     {#await getWorkflowResults(hashDocId)}
        Loading workflow...
     {:then hits}
         {#if hits.length > 0}
            <SearchResultGrid 
              results={{ entries: hits }} 
              isDetailOn={false} 
              onSelect={(r) => onSelectImage(`local-output://${r.id}||${r.image_url}`)} 
            />
         {:else}
            No workflow results found.
         {/if}
     {/await}
  {/if}
</div>
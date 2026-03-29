<script>
  import { getWeekString } from './functions/date_helpers.js';
  import { fixImageUrl } from "./functions/uri_helpers";
  import { getContext } from 'svelte';
  import { useQuery } from 'convex-svelte';
  import { api } from "../convex/_generated/api.js";
  import { Meilisearch } from 'meilisearch';
  import { getMeilisearchUrl, formatFacetValue } from './functions/convex_helpers.js';
  import Bookmarker from './Bookmarker.svelte';
  import {push} from 'svelte-spa-router'
  import InvokeController, {createInvokeController} from './controllers/InvokeController.js';
  import { createAssetController } from './controllers/AssetController.js';
  import Notifications from "./Notifications.svelte";
  import CollectionImagePicker from './CollectionImagePicker.svelte';



  let { params = {} , onUpdate = () => {}  , onSelect = () => {} , onPrev = () => {} , onNext = () => {} , onClose = () => {} , minimal = false, doc: initialDoc = null }  = $props();

  let id = $state( params?.id )
  const indexName = getContext("app.indexName");
  const client = getContext("convex.client");
  const mClient = getContext("search.client");
  const bookmarks = useQuery(api.bookmarks.getAll, {});
  const searchParameters = getContext('search.params');
  let invokeController = createInvokeController();
  let assetController = createAssetController(client);
  let outputs = $state({
    generatedImages:  [],
    isLoading: false,
    elapsedTime: 0,
    notificationIds :  [] ,
    appendNotificationId(nId) {
      this.notificationIds = [...this.notificationIds, nId ]
    }
  });

  let page = $state({
    id :  params?.id,
    previousId : null,
    history : [] ,
    updateId(_id) {
      const index = this.history.indexOf(_id)
      if (index !== -1){
        // Go back to a specific point in history
        this.history = this.history.slice(0, index)
        this.previousId = this.history.length > 0 ? this.history[this.history.length - 1] : null
        this.id = _id
      }else{
        this.previousId = this.id
        this.id = _id
        this.history = [...this.history,this.previousId]
      }
    }
  })

  let docCache = $state({})

  let properties = $state({
    arSquareToggle: false,
    arLandscapeToggle: false,
    arPortraitToggle: false
  })

  function formatElapsedTime(ms) {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${((ms % 60000) / 1000).toFixed(0)}s`;
  }


  function search(args) {

    // Get the search parameters context

    const searchParams = new URLSearchParams();
    searchParams.set('filters', JSON.stringify([args]));

    // Navigate to the search page
    push(`/search?${searchParams.toString()}`);
  }

  function handleFilterClick(args){
    onUpdate(args)
    if (window.location.hash.startsWith('#/asset/')) {
        search(args)
    } else {
        onClose()
    }
  }

  async function getDocument(assetId) {
    if (initialDoc && initialDoc.id === assetId) {
      setTimeout(() => { docCache[assetId] = initialDoc; }, 0);
      return initialDoc;
    }
    const doc = await mClient.index(indexName).getDocument(assetId);
    docCache[assetId] = doc;
    return doc;
  }

  // // Get bookmark collections for this asset
  // function getAssetCollections() {
  //   if (!bookmarks.data || !id) return [];
  //   return bookmarks.data
  //     .filter(bookmark => bookmark.asset_id.id === id)
  //     .map(bookmark => bookmark.name);
  // }

  async function handleTextUpdate(event, text, docId) {
    if (event.key === 'Enter') {
      event.preventDefault();
      const newValue = event.target.innerText;

      try {
        outputs.isLoading = true
        const response = await invokeController.prompt(docId, {
          _id: text._id,
          field: text.key || 'text1',
          value: newValue
        });

        return response.notification_id



        console.log("Asset:notificationIds", response, notificationIds)

        // if (response && response.images) {
        //   outputs.generatedImages = [ ...outputs.generatedImages, ...response.images ];
        //   outputs.elapsedTime = response.elapsed_ms || 0;
        //   outputs.isLoading = false
        // }
        console.log("Asset:handleTextUpdate:effect", outputs, response.images )
      } catch (error) {
        console.error('Error invoking workflow:', error);
      }

      return null

    }

  }

  async function handleUpdate(event, node , docId ) {

    event.preventDefault();


    try {
      outputs.isLoading = true;
      console.log( node )
      const response = await invokeController.prompt(docId, {
        _id: node._id,
        field: node.key,
        value: node.value
      });

      return response.notification_id;
    } catch (error) {
      console.error('Error invoking workflow:', error);
    }

    return null;

  }


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
    
    console.log("Asset:getFaceValues", name, finalImages)
    return finalImages

  }


  let inputTab = $state("input")

  async function getRecentOutputs(doc, daysOffset) {
    const today = new Date();
    today.setDate(today.getDate() - daysOffset);
    const yy = today.getFullYear();
    const mm = today.getMonth() + 1;
    const dd = today.getDate();

    const ret = await mClient.index(indexName).search("", {
      filter: `yy = ${yy} AND mm = ${mm} AND dd = ${dd}`,
      sort: ['created:desc'],
      limit: 50
    });
    return ret.hits;
  }

  async function getUpvotedOutputs(doc) {
    const ret = await mClient.index(indexName).search("", {
      filter: `vote >= 1`,
      sort: ['created:desc'],
      limit: 50
    });
    return ret.hits;
  }

  let collapsed = $state(true)
  let fileInput = $state();
  let err  = $state({ message: null });
  let notificationIds = $state([])
  let currentVote = $state(0);
  let publishStatus = $state({});

  async function imagePrompt(doc,i){
      if (!selectedImageInput) {
        console.error("Asset:imagePrompt: No image input selected");
        return;
      }
      outputs.isLoading = true
      const response = await invokeController.prompt(doc.id,  {
        _id :  selectedImageInput._id,
        field: selectedImageInput.key,
        value: i
      })


      outputs.notificationIds = [...outputs.notificationIds,response.notification_id ]
      console.log("Asset:notificationIds", response, notificationIds)



  }

  async function handleImageInputUpdate(event, doc, i ) {
    const file = event.target.files[0];
    if (!file) return;

    try {
      err.message = JSON.stringify(file.name)
      const result = await assetController.upload(file, doc.source, file.name);
      console.log("Asset:file uploaded:", result);
      outputs.isLoading = true
      err.message = "Asset:file uploaded:"

      const releaseFolder = import.meta.env.VITE_RELEASE_FOLDER || 'release';
      const response = await invokeController.prompt(doc.id,  {
        _id :  i._id,
        field: i.key,
        value: `virtual://${result.storageId}/${doc.source}/input/${releaseFolder}/${file.name}`
      })


      fileInput.value = '';
      outputs.appendNotificationId(response.notification_id)
      return  response.notification_id
    } catch (error) {
      console.error("Asset:file upload error:", error);
    }
  }


  function triggerFileUpload(doc,i ) {
    fileInput.click();
    fileInput.onchange = (e) => handleImageInputUpdate(e, doc, i );
  }


  let showInputValues  = $state(false)
  let selectedImageInput = $state(null)

  // Long press detection for main image
  let mainImageLongPressTimer = $state(null);
  let mainImageIsLongPress = $state(false);

  function handleMainImageStartPress(event) {
    mainImageIsLongPress = false;

    mainImageLongPressTimer = setTimeout(() => {
      mainImageIsLongPress = true;
      collapsed = !collapsed;
    }, 500); // 500ms for long press
  }

  function handleMainImageCancelPress() {
    if (mainImageLongPressTimer) {
      clearTimeout(mainImageLongPressTimer);
      mainImageLongPressTimer = null;
    }
    mainImageIsLongPress = false;
  }

  function handleMainImageEndPress(event) {
    if (mainImageLongPressTimer) {
      clearTimeout(mainImageLongPressTimer);
      mainImageLongPressTimer = null;
    }

    // If it wasn't a long press, handle the regular click
    if (!mainImageIsLongPress) {
       console.log("Asset:image:onSelect");
       if (page.previousId == null){
         onSelect()
       }else{
         page.updateId(page.previousId)
       }
    }

    mainImageIsLongPress = false;
  }

  // Long press detection for input images
  let longPressTimer = $state(null);
  let isLongPress = $state(false);

  function handleStartPress(event, doc, i) {
    isLongPress = false;

    longPressTimer = setTimeout(() => {
      isLongPress = true;
      selectedImageInput = i;
      showInputValues = !showInputValues;
    }, 500); // 500ms for long press
  }

  function handleCancelPress() {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    isLongPress = false;
  }

  function handleEndPress(event, doc, i) {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }

    // If it wasn't a long press, handle the regular click
    if (!isLongPress) {
      if (!selectedImageInput){
        err.message = "Uploading ";
          triggerFileUpload(doc, i);
      }

    }else{
        err.message = "Loading ";

    }

    isLongPress = false;
  }

  async function handleDownload(doc) {
    try {
      const formData = new FormData();
      formData.append('doc', JSON.stringify(doc));

      const response = await fetch(`/download/${doc.id}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        console.error('Download failed:', response.statusText);
        return;
      }

      // Get the blob and create a download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${doc.id}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
    }
  }

  async function handlePublish(doc) {
    publishStatus[doc.id] = 'publishing';
    try {
      const response = await fetch(`/publish/${doc.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(doc.inputs)
      });

      const results = await response.json();

      if (!response.ok) {
        console.error('Publish API request failed:', results);
        publishStatus[doc.id] = 'error';
        return null;
      }

      publishStatus[doc.id] = 'success';

      const githubResult = results[0] || {};
      const hfResult = results[1] || {};

      if (githubResult.status === 'success') {
        console.log('Successfully published workflow to GitHub:', githubResult);
      } else if (githubResult.error) {
        console.error('GitHub publish failed:', githubResult.error);
      }

      if (hfResult.status === 'success') {
        console.log('Successfully published workflow to HuggingFace:', hfResult);
      } else if (hfResult.error) {
        console.error('HuggingFace publish failed:', hfResult.error);
      }

      return {
        github: githubResult,
        huggingface: hfResult
      };
    } catch (error) {
      console.error('Publish error:', error);
      publishStatus[doc.id] = 'error';
      return null;
    }
  }

  async function handleVote(value, doc) {
    const currentDocVote = doc.vote || 0;
    const currentScore = doc.score || 0;
    
    if (value === 1) {
      currentVote = 1;
      await mClient.index(indexName).updateDocuments([{
        id: doc.id,
        vote: 1,
        score: currentScore + 1
      }]);
    } else if (value === -1) {
      if (currentDocVote === 1 && currentScore > 1) {
        currentVote = 1;
        await mClient.index(indexName).updateDocuments([{
          id: doc.id,
          vote: 1,
          score: currentScore - 1
        }]);
      } else if (currentDocVote === 1 && currentScore === 1) {
        currentVote = -1;
        await mClient.index(indexName).updateDocuments([{
          id: doc.id,
          vote: -1,
          score: 0
        }]);
      } else {
        currentVote = -1;
        await mClient.index(indexName).updateDocuments([{
          id: doc.id,
          vote: -1
        }]);
      }
    }
  }

  function handleKeydown(event) {
    console.log('[KeyboardNav] Key pressed:', event.key, '| Active element:', document.activeElement?.tagName, '| isContentEditable:', document.activeElement?.isContentEditable)
    
    // Don't navigate if user is editing text (contenteditable focused)
    if (document.activeElement?.isContentEditable) {
      console.log('[KeyboardNav] Blocked: contenteditable is focused')
      return
    }
    
    // Don't navigate if user is in an input field
    if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
      console.log('[KeyboardNav] Blocked: input field is focused')
      return
    }

    switch (event.key) {
      case 'ArrowLeft':
        console.log('[KeyboardNav] ArrowLeft detected - calling onPrev()')
        event.preventDefault()
        event.stopPropagation()
        onPrev()
        break
      case 'ArrowRight':
        console.log('[KeyboardNav] ArrowRight detected - calling onNext()')
        event.preventDefault()
        event.stopPropagation()
        onNext()
        break
      case 'Escape':
        console.log('[KeyboardNav] Escape detected - calling onClose()')
        event.preventDefault()
        event.stopPropagation()
        onClose()
        break
      case '+':
      case '=':
        console.log('[KeyboardNav] +/= detected - upvoting and calling onNext()')
        event.preventDefault()
        event.stopPropagation()
        getDocument(page.id).then(doc => {
          if (doc) {
            handleVote(1, doc).then(() => {
              onNext()
            })
          }
        })
        break
      case '-':
      case '_':
        console.log('[KeyboardNav] -/_ detected - downvoting and calling onNext()')
        event.preventDefault()
        event.stopPropagation()
        getDocument(page.id).then(doc => {
          if (doc) {
            handleVote(-1, doc).then(() => {
              onNext()
            })
          }
        })
        break
      default:
        console.log('[KeyboardNav] Unhandled key:', event.key)
    }
  }

  let assetContainer = $state(null)

  let touchstartX = $state(0);
  let touchendX = $state(0);
  let touchstartY = $state(0);
  let touchendY = $state(0);

  function handleTouchStart(e) {
    touchstartX = e.changedTouches[0].screenX;
    touchstartY = e.changedTouches[0].screenY;
  }

  function handleTouchEnd(e) {
    touchendX = e.changedTouches[0].screenX;
    touchendY = e.changedTouches[0].screenY;
    handleSwipe();
  }

  function handleSwipe() {
    const swipeDistanceX = touchendX - touchstartX;
    const swipeDistanceY = touchendY - touchstartY;

    if (Math.abs(swipeDistanceX) > Math.abs(swipeDistanceY) && Math.abs(swipeDistanceX) > 50) {
      if (swipeDistanceX < 0) {
        onPrev();
      } else {
        onNext();
      }
    }
  }

  $effect(() => {
    if (assetContainer) {
      console.log('[KeyboardNav] Focusing asset container')
      assetContainer.focus()
      console.log('[KeyboardNav] Asset container focused, activeElement:', document.activeElement?.tagName)
    }
  })
</script>

{#key page.id}
<div bind:this={assetContainer} class="asset" tabindex="-1" onkeydown={handleKeydown} ontouchstart={handleTouchStart} ontouchend={handleTouchEnd}>
    <!-- {JSON.stringify(id)} -->
  {#if page.history.length > 0}
  <div style="display: flex; gap: 0.25rem; overflow-x: auto; padding: 0.5rem; background: #fffbf5; border-radius: 12px; margin-bottom: 0.5rem;">
    {#each page.history as histId}
      {#if docCache[histId]}
        <img 
          src={fixImageUrl(docCache[histId].image_url, docCache[histId].source)} 
          alt="History item" 
          style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px; cursor: pointer;"
          onclick={() => page.updateId(histId)}
        />
      {:else}
        <div style="width: 200px; height: 200px; background: #eee; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; color: #999; cursor: pointer;" onclick={() => page.updateId(histId)}>
          {histId.substring(0, 8)}...
        </div>
      {/if}
    {/each}
  </div>
  {/if}
  {#await getDocument(page.id)}
    <div class="asset__loading">Loading asset...</div>
  {:then doc}

    <div class="asset__container">
      <!-- Pinterest style image cell -->
       {#if !minimal}<div class="generated-images-header">Asset</div>{/if}
      <div class="asset__image-container">
        <img
          class="asset__image"
          src={fixImageUrl(doc.image_url, doc.source)}
          alt="Generated image"
          onpointerdown={(e) => handleMainImageStartPress(e)}
          onpointerup={(e) => handleMainImageEndPress(e)}
          onpointercancel={(e) => handleMainImageCancelPress()}
          onpointerleave={(e) => handleMainImageCancelPress()}
          style="cursor: pointer;"
          title="Click to view, long press for settings"
        />

      </div>
      <div class="asset__settings-toggle"  title="Settings">
        {#if (doc?.inputs != undefined) && doc.inputs.filter((el) => el?.type.includes("res.aspectratio")).length > 0  }
          {@const node =  doc.inputs.filter((el) => el?.type.includes("res.aspectratio"))[0]}
          {@const aspectRatios = doc.inputs.filter((el) => el?.type.includes("res.aspectratio"))[0]._values }
          <div class="asset__aspectratio-select">
                <!-- portrait svg icon -->
                <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"  onclick={() => {
                  properties.arPortraitToggle = !properties.arPortraitToggle
                  properties.arSquareToggle = false
                  properties.arLandscapeToggle = false
                }}>
                  <rect x="6" y="3" width="12" height="18" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
                </svg>
                {#if properties.arPortraitToggle}
                <span>Portrait: </span>
                {#each aspectRatios as ar}

                  {#if ar.includes("Portrait") || ar.includes("Vertical") || ar.includes("Square")}
                  <span class:selected-aspect-ratio={node.value == ar} onclick={async (e) => {
                          let newNode = node
                          node.value = ar
                          node.key= "aspect_ratio"
                          console.log("onclick:", node)
                          const nId = await handleUpdate(e, newNode, doc.id);
                          if (nId!=null){
                            outputs.notificationIds = [...outputs.notificationIds,nId]
                          }

                         } }>{ar.split(" ")[0]}</span>
                  {/if}
                {/each}
                {/if}

                <!-- landscape svg icon -->
                <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" onclick={() => {
                  properties.arLandscapeToggle = !properties.arLandscapeToggle
                  properties.arSquareToggle = false
                  properties.arPortraitToggle = false

                }}>
                  <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
                </svg>
                {#if properties.arLandscapeToggle}
                <span>Lanscape:</span>
                {#each aspectRatios as ar}

                  {#if ar.includes("Landscape") || ar.toLowerCase().includes("wide")}
                    <span class:selected-aspect-ratio={node.value == ar} onclick={async (e) => {
                          let newNode = node
                          node.value = ar
                          node.key= "aspect_ratio"
                          console.log("onclick:", node)
                          const nId = await handleUpdate(e, newNode, doc.id);
                          if (nId!=null){
                            outputs.notificationIds = [...outputs.notificationIds,nId]
                          }

                         } }>{ar.split(" ")[0]}</span>
                  {/if}
                {/each}
                {/if}

                <!-- square svg icon -->
                <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
                </svg>
               {#if properties.arSquareToggle}
                {#each aspectRatios as ar}
                  {#if ar.includes("Square")}
                    <span class:selected-aspect-ratio={node.value == ar} onclick={async (e) => {
                          let newNode = node
                          node.value = ar
                          node.key= "aspect_ratio"
                          const nId = await handleUpdate(e, newNode, doc.id);
                          if (nId!=null){
                            outputs.notificationIds = [...outputs.notificationIds,nId]
                          }

                         } }>{ar.split(" ")[0]}</span>
                  {/if}
                {/each}
                {/if}
          </div>
          {/if}
        <div class="asset__actions-container">
          <svg
            class="asset__settings-icon"
            class:vote-up-active={currentVote === 1}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            xmlns="http://www.w3.org/2000/svg"
            onclick={() => handleVote(1, doc)}
          >
            <circle cx="12" cy="12" r="11"></circle>
            <line x1="12" y1="7" x2="12" y2="17"></line>
            <line x1="7" y1="12" x2="17" y2="12"></line>
          </svg>
          <svg
            class="asset__settings-icon"
            class:vote-down-active={currentVote === -1}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            xmlns="http://www.w3.org/2000/svg"
            onclick={() => handleVote(-1, doc)}
          >
            <circle cx="12" cy="12" r="11"></circle>
            <line x1="7" y1="12" x2="17" y2="12"></line>
          </svg>
          <svg class="asset__settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" onclick={(e) => { e.stopPropagation(); handleDownload(doc); }}>
            <circle cx="12" cy="12" r="11"></circle>
            <path d="M7.5 12.5l4.5 4.5 4.5-4.5"></path>
            <line x1="12" y1="7" x2="12" y2="17"></line>
            <path d="M7.5 17h9"></path>
          </svg>
          <svg class="asset__settings-icon" class:publish-success={publishStatus[doc.id] === 'success'} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg" onclick={() => handlePublish(doc)}>
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </div>


      </div>

      <!-- <div style="text-align:left"><pre>{JSON.stringify(doc,null,2)}</pre></div> -->
      <div>


      </div>





      {#if !collapsed}
      <div class="settings">
      <!-- Bookmark collection pills -->
      <div class="asset__collections">

        <div></div>
        <div class="asset__bookmark-action">
          <Bookmarker index={indexName} asset={{ id: doc.id, type: "image" }} />
        </div>
      </div>



      <div class="asset__facets">


        {#if doc.elapsed_ms}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Elapsed:</div>
            <div class="asset__facet-list">
              <div
                class="asset__facet-pill asset__facet-pill--elapsed"
                title="{doc.elapsed_ms}ms"
              >
                {formatElapsedTime(doc.elapsed_ms)}
              </div>
            </div>
          </div>
        {/if}

        {#if doc.time_bucket}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Time:</div>
            <div class="asset__facet-list">
              <div
                class="asset__facet-pill asset__facet-pill--time"
                onclick={() => handleFilterClick({ attribute: "time_bucket", value: doc.time_bucket})}
              >
                {doc.time_bucket}
              </div>
            </div>
          </div>
        {/if}


        {#if doc.loras && doc.loras.length > 0}
          <div class="asset__facet-group">

            <div class="asset__facet-title">LoRAs:</div>
            <div class="asset__facet-list">
              {#each doc.loras as lora}
                <div
                  class="asset__facet-pill asset__facet-pill--lora"
                  onclick={() => handleFilterClick({ attribute: "loras", value: lora })}
                >
                  {formatFacetValue(lora)}
                </div>
              {/each}
            </div>
          </div>
        {/if}

                {#if doc.workflow_id}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Workflow:</div>
            <div class="asset__facet-list">
              <div
                class="asset__facet-pill asset__facet-pill--workflow"
                onclick={() => handleFilterClick({ attribute: "workflow_id", value: doc.workflow_id})}
              >
                {doc.workflow_id}
              </div>
            </div>
          </div>
        {/if}



        {#if doc.models && doc.models.length > 0}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Models:</div>
            <div class="asset__facet-list">
              {#each doc.models as model}
                <div
                  class="asset__facet-pill asset__facet-pill--model"
                  onclick={() => handleFilterClick({ attribute: "models", value: model })}
                >
                  {formatFacetValue(model)}
                </div>
              {/each}
            </div>
          </div>
        {/if}


        {#if doc.schedulers && doc.schedulers.length > 0}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Schedulers:</div>
            <div class="asset__facet-list">
              {#each doc.schedulers as scheduler}
                <div
                  class="asset__facet-pill asset__facet-pill--scheduler"
                  onclick={() => handleFilterClick({ attribute: "schedulers", value: scheduler })}
                >
                  {scheduler}
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if doc.inputs}
          <div class="asset__facet-group">
            <div class="asset__facet-title">Image Inputs:</div>
            <div class="asset__facet-list" >

                      {#each doc.inputs as i }
                <!-- <div>{JSON.stringify(i,null,2)}  {i.type=="image"}</div> -->
                {#if  i?.type.trim() == "image"}
                  <!-- <div>{i.value}</div> -->
                  <img style="width:100px;height:120px;" src="/images/{doc.source}/input/{i.value}"
                     onclick={() => handleFilterClick({ attribute: "inputs.value", value: i.value })}
                   />
                {/if}
                {/each}
              </div>
            </div>


        {/if}


      </div>
    </div>
    {/if}
      <!-- Inputs -->
       <Notifications ids={[page.id]} queryMode="prompt_id" showTrimmings={true}  onclick={ (_id) =>  { console.log("Asset:notification:onclick", _id ); page.updateId(_id) }}/>
        <!-- {#if outputs.notificationIds.length > 0 }
        <div class="generated-images-header">Renders</div>
        <Notifications ids={outputs.notificationIds} queryMode="prompt_id"  onclick={ (_id) =>  { console.log("Asset:notification:onclick", _id ); page.updateId(_id) }}/>

      {/if} -->
        {#if !minimal}<div class="generated-images-header">Prompts</div>{/if}

       <div class="asset__inputs">
         <!-- <div class="asset__inputs-title">Inputs:</div> -->

         <div class="asset__inputs-content">
             {#if doc.text && doc.text.length > 0}
             <div class="asset__text-inputs">
               {#each doc.text as text}
                 <div class="asset__text-input">
                   {#if text._id && text.value.length > 0 }
                     <!-- <div class="asset__text-input-label">{text._id}:</div> -->
                    <div
                      class="asset__text-input-value editable-text"
                      class:minified-view={minimal}
                      contenteditable="true"
                      onkeydown={async (e) => {
                           const nId = await handleTextUpdate(e, text, doc.id);
                           if (nId!=null){
                             outputs.notificationIds = [...outputs.notificationIds,nId]
                           }

                         } }
                     >{text.value}</div>
                   {:else}
                     <div
                       class="asset__text-input-value editable-text"
                       class:minified-view={minimal}
                       contenteditable="true"
                       onkeydown={ async (e) => {
                           const nId = await handleTextUpdate(e, text, doc.id);
                           if (nId!=null){
                             outputs.notificationIds = [...outputs.notificationIds,nId]
                           }
                         }}
                     >{text}</div>
                   {/if}
                 </div>
               {/each}
             </div>
                       {:else}
             <div class="asset__no-inputs">Text inputs not supports</div>
           {/if}
       </div>


           <div class="asset__inputs-images">
               <!-- {JSON.stringify(doc.inputs,null,2)} -->
               {#each doc.inputs as i }
                 <!-- <div>{JSON.stringify(i,null,2)}  {i.type=="image"}</div> -->
                 {#if  i?.type.trim() == "image"}
                   {@const match = (i.value || '').match(/releases?\/([^/]+)\.png$/)}
                   <div class="input-image-wrapper">
                     <!-- <div>{i.value}</div> -->
                     <img src="/images/{doc.source}/input/{i.value}"
                           onpointerdown={(e) => handleStartPress(e, doc, i)}
                           onpointerup={(e) => handleEndPress(e, doc, i)}
                           onpointercancel={(e) => handleCancelPress()}
                           onpointerleave={(e) => handleCancelPress()}
                           style="cursor: pointer; border-radius:8px;"
                          title="Click to upload new image, long press to toggle input values" />
                     {#if match}
                       <div 
                         class="open-asset-btn"
                         onpointerdown={(e) => e.stopPropagation()}
                         onclick={(e) => { e.stopPropagation(); page.updateId(match[1]); }}
                       >
                         [ Open Asset ]
                       </div>
                     {/if}
                   </div>
                 {/if}

               {/each}

           </div>

           <!-- Hidden file input -->
           <input type="file" accept="image/*" bind:this={fileInput} style="display: none;" />
         </div>



       <!-- {selectedImageInput} {JSON.stringify(showInputValues,null,2)} -->
       {#if showInputValues }

        <div>
          <div style="display:flex; gap: 10px; margin-bottom: 10px; cursor:pointer;">
             <div onclick={() => inputTab = 'input'} style="{inputTab === 'input' ? 'font-weight:bold' : ''}">Pick Input</div>
             <div onclick={() => inputTab = 'upvoted'} style="{inputTab === 'upvoted' ? 'font-weight:bold' : ''}">Upvoted</div>
             <div onclick={() => inputTab = 'today'} style="{inputTab === 'today' ? 'font-weight:bold' : ''}">Today</div>
             <div onclick={() => inputTab = 'yesterday'} style="{inputTab === 'yesterday' ? 'font-weight:bold' : ''}">Yesterday</div>
             <div onclick={() => inputTab = 'collections'} style="{inputTab === 'collections' ? 'font-weight:bold' : ''}">Collections</div>
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
                            imagePrompt(doc, i)
                            selectedImageInput = null
                            showInputValues = !showInputValues
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
                            imagePrompt(doc, `local-output://${hit.id}||${hit.image_url}`)
                            selectedImageInput = null
                            showInputValues = !showInputValues
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
                            imagePrompt(doc, `local-output://${hit.id}||${hit.image_url}`)
                            selectedImageInput = null
                            showInputValues = !showInputValues
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
                            imagePrompt(doc, `local-output://${hit.id}||${hit.image_url}`)
                            selectedImageInput = null
                            showInputValues = !showInputValues
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
                 imagePrompt(doc, `local-output://${hit.id}||${hit.image_url}`);
                 selectedImageInput = null;
                 showInputValues = !showInputValues;
               }} 
             />
          {/if}
       </div>
       {/if}

    </div>
  {:catch error}
    <div class="asset__error">Error: {error.message}</div>
  {/await}
</div>
{/key}

<style>
  .asset {
  /*  width: 80%;*/ 
    /* margin: 0 auto;
    padding: 1rem; 
padding: 1.51rem;*/

  /*  border-bottom: 1px solid #eee;
  border-top: 1px solid #eee;
  border-left: 1px solid #eee;
  border-right: 1px solid #eee;
  border-radius: 16px;    
  background-color: #FFFBF5;  */
  outline: none; /* Remove default browser focus border */
  
  }


  .asset__loading,
  .asset__error {
    padding: 2rem;
    text-align: center;
    font-size: 1.1rem;
  }

  .asset__error {
    color: #e74c3c;
  }

  .asset__container {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    width:fit-content;
  }

  /* Pinterest style image cell */
  .asset__image-container {
    /* width: 95%; */
    border-radius: 16px;
    overflow: hidden;
    /* box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); */ 
    /* background-color: #f8f9fa; */ 
  /*  max-height: 600px; */ 
    display: flex;
    justify-content: left;    
    margin-bottom: 10px;
    padding-bottom: 10px;
  }

  .asset__image {
     max-width: 100%;
    /* height: auto; */
    display: block;
/*    object-fit: cover;
    max-height: 600px;    */
    border-radius: 16px; 
  }

  /* Bookmark collection pills */
  .asset__collections {
    padding: 1rem;
    border-radius: 12px;
  }

  .asset__collections-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
  }

  .asset__collections-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .asset__collection-pill {
    padding: 0.25rem 0.75rem;
    background-color: #007bff;
    color: white;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .asset__collection-pill--empty {
    background-color: #6c757d;
  }

  .asset__aspectratio-select{
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .asset__aspectratio-select span {
    font-size: 0.8rem;
    color: rgba(0, 0, 0, 0.6);
  }

  .aspect-ratio-icon {
    width: 16px;
    height: 16px;
    color: rgba(0, 0, 0, 0.6);
    transition: color 0.2s ease;
  }

  .aspect-ratio-icon:hover {
    color: rgba(0, 0, 0, 0.8);
  }

  .asset__bookmark-action {
    margin-top: 0.5rem;
  }

  /* Settings toggle */
  .settings {
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border: 1px solid rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  margin-top: 1em;
  margin-bottom: 1em;
  background-color: #FCFCFC;

  }

  /* Facets */
  .asset__facets {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .asset__facet-group {
    padding: 1rem;
    border-radius: 12px;
  }

  .asset__facet-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
  }

  .asset__facet-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .asset__facet-pill {
    padding: 0.25rem 0.75rem;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: #f5f5f7;
    color: #6b5b54;
    border: 1px solid rgba(0, 0, 0, 0.04);
  }

  .asset__facet-pill:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    background-color: rgba(0, 0, 0, 0.04);
    color: #4a3f38;
  }

  .asset__facet-pill:active {
    transform: scale(0.98);
    background-color: rgba(0, 0, 0, 0.08);
  }

  .asset__facet-pill--model {
    background-color: #e8d5c4;
    color: #6b5b54;
  }

  .asset__facet-pill--model:hover {
    background-color: #d4b5a0;
    color: #4a3f38;
  }

  .asset__facet-pill--lora {
    background-color: #f0e6dc;
    color: #6b5b54;
  }

  .asset__facet-pill--lora:hover {
    background-color: #e6d5c4;
    color: #4a3f38;
  }

  .asset__facet-pill--scheduler {
    background-color: #e8e0d5;
    color: #6b5b54;
  }

  .asset__facet-pill--scheduler:hover {
    background-color: #d4c8b5;
    color: #4a3f38;
  }

  .asset__facet-pill--workflow {
    background-color: #dce8dc;
    color: #6b5b54;
  }

  .asset__facet-pill--workflow:hover {
    background-color: #c8d5cc;
    color: #4a3f38;
  }

  /* Inputs */
  .asset__inputs {
    /* padding: 1rem; */
/*    border-radius: 12px;
    border: 1px solid #D0DDD0;
    background-color: #D0DDD066;*/ 
    width: 0; 
    min-width: 100%;
  }

  .asset__inputs-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
  }

  .asset__text-inputs {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding-bottom: 1em;

  }

  .asset__text-input {
    display: flex;
    flex-direction: row;
    gap: 0.25rem;
  }

  .asset__text-input-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #6c757d;
  }

  .asset__text-input-value {
    padding: 0.5rem;
    /* border: 1px solid rgba(0, 0, 0, 0.08); */
    border-radius: 8px;
    font-size: 0.9rem;
  }

  .asset__no-inputs {
    color: #6c757d;
    font-style: italic;
  }


  .asset__inputs-images {
    display: flex;
    flex-wrap: wrap;
    gap: 1em;
    max-width: 100%;
    /* overflow: hidden; */
  }

  .input-image-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
  }

  .open-asset-btn {
    position: absolute;
    left: 100%;
    margin-left: 8px;
    white-space: nowrap;
    background-color: #686158;
    color: #F7E8D2;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s 1.5s; /* Delay fading out */
    z-index: 10;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .open-asset-btn:hover {
    background-color: #4a3f38;
    transition: opacity 0.2s 0s; /* Keep visible immediately when hovering the button itself */
  }

  .input-image-wrapper:hover .open-asset-btn {
    opacity: 1;
    pointer-events: auto;
    transition: opacity 0.2s 0s; /* Show immediately when hovering the wrapper */
  }

  .asset__inputs-images img{
    max-width: 100px;
    height: auto;
    flex-shrink: 0;
    object-fit: cover;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  /* Editable text */
  .editable-text {
    padding: 0.5rem;
    border-radius: 8px;
    outline: none;
    transition: background-color 0.2s, border-color 0.2s;
    min-height: 1.2rem;
    background-color: #F0F0D7;
    color: #727D73;
    border: 1px solid transparent;
  }

  .editable-text:hover {
    background-color: #D0DDD0;
  }

  .editable-text:focus {
    border-color: #AAB99A;
    background-color: #D0DDD0;
  }

  /* Generated Components */
  .asset__generated {
    padding: 1rem;
    border-radius: 12px;
  }

  .asset__generated-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.5rem;
  }

  .asset__generated-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .generated-images {
    margin-top: 0.5rem;
  }

  .generated-images-header {
    font-size: 2em;
    font-weight: 600;
    /* color: #3a7397cc; */ 

  }

  .generated-images-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .generated-images h4 {
    font-size: 0.9rem;
    color: #495057;
    margin: 0;
  }

  .generated-images-time {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .time-label {
    font-size: 0.8rem;
    color: #6c757d;
  }

  .time-value {
    font-size: 0.8rem;
    font-weight: 600;
    color: #495057;
    background-color: rgba(0, 0, 0, 0.04);
    padding: 0.2rem 0.5rem;
    border-radius: 12px;
  }

  .generated-images-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;

  /* display: flex;
  flex-wrap: wrap;
  flex-direction: row-reverse;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #222;
  border-radius: 16px; */


  }

  .generated-image-container {
    flex: 0 0 calc(25% - 1rem);
    min-width: 200px;
  }

  .generated-image {
    /* width: 100%; */
    /* height: 200px; */
    max-width: 300px;
    max-height: 400px;
    object-fit: cover;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    background-color: #f8f9fa;
  }

  .asset__no-generated {
    color: #6c757d;
    font-style: italic;
    padding: 1rem;
    text-align: center;
    border-radius: 8px;
  }

  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 1rem;
    border-radius: 8px;
    background-color:#FEFEFE
  }

  .loading-dots {
    display: flex;
    gap: 0.1rem;
  }

  .dot {
    animation: pulse 1.4s infinite ease-in-out both;
  }

  .dot:nth-child(1) {
    animation-delay: -0.32s;
  }

  .dot:nth-child(2) {
    animation-delay: -0.16s;
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

  /* Settings toggle */
  .asset__settings-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    border-radius: 4px;
    transition: background-color 0.2s ease;
    /* margin-left: auto; */
    flex-direction: row;
/*background-color: #F7E8D2; */ 
  padding: 0.25rem;    

  }

  .asset__settings-toggle:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .asset__settings-icon {
    width: 16px;
    height: 16px;
    color: rgba(0, 0, 0, 0.6);
    transition: color 0.2s ease;
  }

  .asset__actions-container {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .asset__settings-toggle:hover .asset__settings-icon {
    color: rgba(0, 0, 0, 0.8);
  }

  .selected-aspect-ratio {
    border: 1px solid rgba(0, 0, 0, 0.3);
    border-radius: 12px;
    padding: 2px 6px;
  }

  .asset__facet-pill--elapsed {
    background-color: #e8f5e9;
    color: #2e7d32;
    font-variant-numeric: tabular-nums;
  }

  .asset__facet-pill--elapsed:hover {
    background-color: #c8e6c9;
    color: #1b5e20;
  }

  .asset__facet-pill--time {
    background-color: #e3f2fd;
    color: #1565c0;
  }

  .asset__facet-pill--time:hover {
    background-color: #bbdefb;
    color: #0d47a1;
  }

  .vote-up-active {
    color: #2e7d32 !important;
  }

  .vote-down-active {
    color: #c62828 !important;
  }

  .publish-success {
    color: #2e7d32 !important;
  }

  .minified-view {
    display: -webkit-box;
    -webkit-line-clamp: 5;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .minified-view:focus {
    display: block;
    -webkit-line-clamp: unset;
    overflow: visible;
    height: auto;
  }
</style>

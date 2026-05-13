<script lang="ts">
  import { imageFileUrl, isVideoDoc } from "../functions/uri_helpers";
  import { createInvokeController } from "../controllers/InvokeController.js";
  import Bookmarker from "../Bookmarker.svelte";
  import { getContext } from "svelte";
  import { jsonToConvex } from "convex/values";
  import Asset from "../Asset.svelte";
  import Notifications from "../Notifications.svelte";
  import { push } from "svelte-spa-router";
  import SearchBentoBox from "../SearchBentoBox.svelte";

  let {
    results,
    items = [],
    groups = [],
    isDetailOn,
    activeId = undefined,
    onAssetOpen = (id: any) => {},
    onAssetClose = () => {},
    onUpdate = () => {},
    onSelect = () => {},
  } = $props();

  const indexName = getContext("app.indexName");

  let showSingle = $state({
    id: undefined,
    result: undefined,
    display: false,

    update({ id, result, display }) {
      this.id = id;
      this.result = result;
      this.display = display;
    },
  });
  let currentIndex = $state(0);

  function goToNext() {
    if (items.length === 0) {
      console.log("[KeyboardNav] goToNext: No results available");
      return;
    }
    const prevIndex = currentIndex;
    currentIndex = (currentIndex + 1) % items.length;
    console.log(
      "[KeyboardNav] goToNext: prevIndex=" +
        prevIndex +
        ", newIndex=" +
        currentIndex +
        ", total=" +
        items.length,
    );
    const nextResult = items[currentIndex];
    showSingle.update({
      id: nextResult.id,
      result: nextResult,
      display: showSingle.display,
    });
    console.log(
      "[KeyboardNav] goToNext: Navigated to asset id=" + nextResult.id,
    );
    onAssetOpen(nextResult.id);
  }

  function goToPrev() {
    if (items.length === 0) {
      console.log("[KeyboardNav] goToPrev: No results available");
      return;
    }
    const prevIndex = currentIndex;
    currentIndex =
      (currentIndex - 1 + items.length) % items.length;
    console.log(
      "[KeyboardNav] goToPrev: prevIndex=" +
        prevIndex +
        ", newIndex=" +
        currentIndex +
        ", total=" +
        items.length,
    );
    const prevResult = items[currentIndex];
    showSingle.update({
      id: prevResult.id,
      result: prevResult,
      display: showSingle.display,
    });
    console.log(
      "[KeyboardNav] goToPrev: Navigated to asset id=" + prevResult.id,
    );
    onAssetOpen(prevResult.id);
  }

  function closeAsset() {
    console.log("[KeyboardNav] closeAsset: Closing asset view");
    showSingle.update({
      id: showSingle.id,
      result: showSingle.result,
      display: false,
    });
    onAssetClose();
    onSelect(showSingle.result);
  }

  function handleWindowKeydown(event: KeyboardEvent) {
    if (!showSingle.display) return;
    
    const target = document.activeElement as HTMLElement | null;

    // Don't navigate if user is editing text
    if (target?.isContentEditable || 
        target?.tagName === 'INPUT' || 
        target?.tagName === 'TEXTAREA') {
      return;
    }

    switch (event.key) {
      case 'ArrowLeft':
        event.preventDefault();
        goToPrev();
        break;
      case 'ArrowRight':
        event.preventDefault();
        goToNext();
        break;
      case 'Escape':
        event.preventDefault();
        closeAsset();
        break;
    }
  }

  let touchstartX = $state(0);
  let touchendX = $state(0);
  let touchstartY = $state(0);
  let touchendY = $state(0);

  function handleTouchStart(e: TouchEvent) {
    if (!showSingle.display) return;
    touchstartX = e.changedTouches[0].screenX;
    touchstartY = e.changedTouches[0].screenY;
  }

  function handleTouchEnd(e: TouchEvent) {
    if (!showSingle.display) return;
    touchendX = e.changedTouches[0].screenX;
    touchendY = e.changedTouches[0].screenY;
    handleSwipe();
  }

  function handleSwipe() {
    const swipeDistanceX = touchendX - touchstartX;
    const swipeDistanceY = touchendY - touchstartY;

    // Only trigger if horizontal swipe is larger than vertical (prevent triggering on scroll)
    // and distance is at least 50px
    if (Math.abs(swipeDistanceX) > Math.abs(swipeDistanceY) && Math.abs(swipeDistanceX) > 50) {
      if (swipeDistanceX < 0) {
        // Swipe left -> Prev
        goToPrev();
      } else {
        // Swipe right -> Next
        goToNext();
      }
    }
  }

  let invokeController = createInvokeController();
  let generatedImages = $state([]);
  let outputs = $state({
    generatedImages: [],
    isLoading: false,
  });

  function toggleShowSingle(r) {
    console.log(
      "[KeyboardNav] toggleShowSingle: Toggling asset id=" +
        r.id +
        ", current display=" +
        showSingle.display,
    );

    // If clicking the same item, toggle. If clicking a different item, ensure it opens.
    const isSameItem = showSingle.id === r.id;
    const newDisplay = isSameItem ? !showSingle.display : true;

    showSingle.update({
      id: r.id,
      result: r,
      display: newDisplay,
    });
    // Find the index of the clicked item in items
    currentIndex = items.findIndex((item) => item.id === r.id);
    if (currentIndex === -1) currentIndex = 0;
    console.log(
      "[KeyboardNav] toggleShowSingle: Set currentIndex=" +
        currentIndex +
        ", total results=" +
        items.length,
    );
    
    if (newDisplay) {
        onAssetOpen(r.id);
    } else {
        onAssetClose();
    }
  }
  function grabFocus(el) {
    console.log("grabFocus", el);
    // el.focus()
  }

  async function handleTextUpdate(event, text) {
    if (event.key === "Enter") {
      event.preventDefault();
      const newValue = event.target.innerText;

      try {
        outputs.isLoading = true;
        const response = await invokeController.prompt(showSingle.result.id, {
          _id: text._id,
          field: text.key || "text1",
          value: newValue,
        });

        if (response && response.images) {
          outputs.generatedImages = [
            ...outputs.generatedImages,
            ...response.images,
          ];
          outputs.isLoading = false;
        }
        console.log(
          "SearchResultGrid:handleTextUpdate:effect",
          outputs,
          response.images,
        );
      } catch (error) {
        console.error("Error invoking workflow:", error);
      }
    }
  }

  $effect(() => {
    console.log(
      "SearchResultGrid:effect:toggleShowSinglez",
      showSingle,
      results.entries,
    );
    console.log("SearchResultGrid:effect:invokeoutputs", outputs);

    if (showSingle.display && showSingle.id) {
      setTimeout(() => {
        const el = document.getElementById(`asset-${showSingle.id}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  });

  $effect(() => {
    if (activeId && (!showSingle.display || showSingle.id !== activeId)) {
      const result = items.find((r: any) => r.id === activeId);
      if (result) {
        showSingle.update({
          id: result.id,
          result: result,
          display: true
        });
        currentIndex = items.findIndex((item: any) => item.id === result.id);
        if (currentIndex === -1) currentIndex = 0;
      }
    } else if (!activeId && showSingle.display) {
        showSingle.update({
          id: showSingle.id,
          result: showSingle.result,
          display: false
        });
    }
  });
</script>

<svelte:window onkeydown={handleWindowKeydown} ontouchstart={handleTouchStart} ontouchend={handleTouchEnd} />

{#key items.length}
    <!--div class="search-results__controls">
       <label class="group-toggle">
         <input type="checkbox" bind:checked={isGroupingEnabled} />
         <span>Group Related Renders</span>
       </label>
    </div-->
    
    <Notifications
      onclick={(_id) => {
        const r = items.find((i) => i.id === _id) || { id: _id };
        toggleShowSingle(r);
      }}/>


    <div class="search-results__grid">
    {#each groups as dateGroup}
      {#if dateGroup.header}
        <div class="search-results__date-header">
          <div>{dateGroup.header}</div>
        </div>
      {/if}

      {#each Object.entries(dateGroup.groupedItems) as [groupKey, groupItems]}
      {#if groupKey !== "ungrouped" && groupItems.length > 1}
        <!-- Render BentoBox for grouped items -->
        {@const mainResult = groupItems[0]}
        {@const relatedResults = groupItems.slice(1)}
        {#if !(showSingle.display && showSingle.id === mainResult.id)}
          <SearchBentoBox
            {mainResult}
            {relatedResults}
            onclick={(result) => toggleShowSingle(result)}
          />
        {/if}
        {#if showSingle.display && showSingle.id === mainResult.id}
          <div id="asset-{mainResult.id}" class="search-results__asset-row">
            <Asset
              minimal={true}
              params={{ id: showSingle.result.id }}
              doc={showSingle.result}
              onSelect={() => {
                toggleShowSingle(showSingle.result);
                onSelect(showSingle.result);
              }}
              onPrev={goToPrev}
              onNext={goToNext}
              onUpdate={onUpdate}
              onClose={closeAsset}
            />
          </div>
        {/if}
      {:else}
        <!-- Render normal grid items -->
        {#each groupItems as r}
          {@const isVideo = isVideoDoc(r)}
          {#if !(showSingle.display && showSingle.id === r.id)}
            <div class="search-results__grid-item">
              <div class="search-results__grid-item__image">
                {#if isVideo}
                  <!-- svelte-ignore a11y_media_has_caption -->
                  <video
                    onclick={(e) => {
                      toggleShowSingle(r);
                      grabFocus(e);
                      onSelect(r);
                    }}
                    src={imageFileUrl(r.image_url)}
                    muted
                    playsinline
                    preload="metadata"
                  ></video>
                {:else}
                  <img
                    onclick={(e) => {
                      toggleShowSingle(r);
                      grabFocus(e);
                      onSelect(r);
                    }}
                    src={imageFileUrl(r.image_url)}
                    alt="Generated image"
                  />
                {/if}
              </div>
              {#if isDetailOn}
                <div class="search-results__grid-item__content">
                  <div class="search-results__grid-item__text">
                    {r.text ? r.text.join(",") : ""}
                  </div>
                  <div class="search-results__grid-item__details">
                    <div class="search-results__grid-item__schedulers">
                      {#each r.schedulers as sched}
                        <div class="search-results__grid-item__scheduler">
                          [{sched}]
                        </div>
                      {/each}
                    </div>
                    <div class="search-results__grid-item__loras">
                      {#each r.loras as lora}
                        <div class="search-results__grid-item_Q_lora">
                          {lora}
                        </div>
                      {/each}
                    </div>
                  </div>
                </div>
              {/if}
            </div>
          {/if}
          {#if showSingle.display && showSingle.id === r.id}
            <div id="asset-{r.id}" class="search-results__asset-row">
              <Asset
                minimal={true}
                params={{ id: showSingle.result.id }}
                doc={showSingle.result}
                onSelect={() => {
                  toggleShowSingle(showSingle.result);
                  onSelect(showSingle.result);
                }}
                onPrev={goToPrev}
                onNext={goToNext}
                onUpdate={onUpdate}
              onClose={closeAsset}
              />
            </div>
          {/if}
        {/each}
      {/if}
      {/each}
    {/each}
  </div>
{/key}

<style>
  .search-results__controls {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 1rem;
    padding: 0 1rem;
  }

  .group-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
    color: #495057;
    background: #f8f9fa;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    border: 1px solid #eee;
    user-select: none;
    transition: all 0.2s ease;
  }

  .group-toggle:hover {
    background: #e9ecef;
  }

  .search-results__grid {
    /* display: grid;
    grid-template-columns: repeat(4, 1fr); */
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    /* gap: 1rem; */ 
  }

  .search-results__date-header {
    grid-column: 1 / -1;
    width: 100%;
    display: flex;
    justify-content: left;
    font-size: 3rem;
    /* border: 1px solid #CCC; */
    /* margin-top: 2rem; */
    /* background-color: #646a6e; */
    /* margin-bottom: 0.5rem; */
    color: #d4d4d4;    
  }

  .search-results__asset-row {
    grid-column: 1 / -1;
    width: 100%;
    display: flex;
    justify-content: left;
    margin-bottom: 1rem;
    margin-top: 1rem;
    padding-bottom: 2rem;
    padding-top: 2rem;
/*    border-bottom: 1px solid #eee;
    border-top: 1px solid #eee*/ 
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
      /* grid-template-columns: repeat(3, 1fr); */
    }
  }

  @media (max-width: 900px) {
    .search-results__grid {
      /* grid-template-columns: repeat(2, 1fr); */
    }
  }

  @media (max-width: 600px) {
    .search-results__grid {
      grid-template-columns: 1fr;
    }
  }

  .search-results__grid-item {
    /* border: 1px solid #eee; */
    /*border-radius: 8px;*/ 
    overflow: hidden;
    transition:
      transform 0.2s ease,
      box-shadow 0.2s ease;
  }

  .search-results__grid-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  .search-results__grid-item__image {
    width: 100%;
    height: 200px;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    /* background-color: #f8f9fa; */
  }

  .search-results__grid-item__image img,
  .search-results__grid-item__image video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    /*border-radius:16px; */
  }

  .search-results__grid-item__imagelarge {
    width: 100%;
    /* height: 200px; */
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f8f9fa;
  }

  .search-results__grid-item__imagelarge img {
    max-width: 100%;
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

  .editable-text {
    border: 1px dashed #ccc;
    padding: 2px 4px;
    border-radius: 3px;
    outline: none;
    transition: border-color 0.2s;
  }

  .editable-text:focus {
    border-color: #007bff;
    background-color: #f8f9fa;
  }

  .generated-images {
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f8f9fa;
    border-radius: 4px;
  }

  .generated-images h4 {
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #495057;
  }

  .generated-image {
    max-width: 200px;
    max-height: 200px;
    object-fit: contain;
    margin-right: 0.5rem;
    margin-bottom: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-top: 0.5rem;
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
    0%,
    80%,
    100% {
      opacity: 0.3;
      transform: scale(0.8);
    }
    40% {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>

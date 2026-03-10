<script>
  import { getContext } from 'svelte';
  import { useQuery } from 'convex-svelte';
  import { api } from "../convex/_generated/api.js";
  import { push } from 'svelte-spa-router';
  import InvokeController, { createInvokeController } from './controllers/InvokeController.js';
  import Notifications from "./Notifications.svelte";

  let { params = {} } = $props();

  const client = getContext("convex.client");
  const invokeController = createInvokeController();

  let notificationId = $state(params?.id);
  let page = $state({
    id: notificationId,
    previousId: null,
    history: [],
    updateId(_id) {
      if (this.history.includes(_id)) {
        const previousId = this.history.pop();
        this.history = [...this.history];
        this.previousId = this.history[this.history.length - 1];
        this.id = previousId;
      } else {
        this.previousId = this.id;
        this.id = _id;
        this.history = [...this.history, this.previousId];
      }
    }
  });

  let outputs = $state({
    isLoading: false,
    notificationIds: [],
    appendNotificationId(nId) {
      this.notificationIds = [...this.notificationIds, nId];
    }
  });

  let properties = $state({
    arSquareToggle: false,
    arLandscapeToggle: false,
    arPortraitToggle: false
  });

  let collapsed = $state(true);
  let fileInput = $state();
  let selectedImageInput = $state(null);
  let showInputValues = $state(false);
  let isLongPress = $state(false);
  let longPressTimer = $state(null);

  async function getNotification(id) {
    const notification = await client.query(api.notifications.get, { notificationId: id });
    return notification;
  }

  function getTextInputs(notification) {
    const input = notification?.payload?.input?.[0] || {};
    const textInputs = [];
    Object.entries(input).forEach(([key, value]) => {
      if (key.startsWith('text')) {
        textInputs.push({ _id: key, key, value });
      }
    });
    return textInputs;
  }

  function getImageInputs(notification) {
    const input = notification?.payload?.input?.[0] || {};
    const imageInputs = [];
    Object.entries(input).forEach(([key, value]) => {
      if (key.includes('image') || key.includes('img') ||
          (typeof value === 'string' && value.startsWith('virtual://'))) {
        imageInputs.push({ _id: key, key, type: 'image', value });
      }
    });
    return imageInputs;
  }

  function getAspectRatio(notification) {
    const input = notification?.payload?.input?.[0] || {};
    let arValue = null;
    Object.entries(input).forEach(([key, value]) => {
      if (key.includes('aspect_ratio') || key.includes('ar')) {
        arValue = value;
      }
    });
    return arValue;
  }

  async function handleTextUpdate(event, text, docId) {
    if (event.key === 'Enter') {
      event.preventDefault();
      const newValue = event.target.innerText;

      try {
        outputs.isLoading = true;
        const response = await invokeController.prompt(docId, {
          _id: text._id,
          field: text.key || 'text1',
          value: newValue
        });
        return response.notification_id;
      } catch (error) {
        console.error('Error invoking workflow:', error);
      }
      outputs.isLoading = false;
    }
    return null;
  }

  async function handleUpdate(event, node, docId) {
    event.preventDefault();
    try {
      outputs.isLoading = true;
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

  async function imagePrompt(doc, i) {
    outputs.isLoading = true;
    const response = await invokeController.prompt(doc.id, {
      _id: selectedImageInput._id,
      field: selectedImageInput.key,
      value: i
    });
    outputs.notificationIds = [...outputs.notificationIds, response.notification_id];
  }

  async function handleImageInputUpdate(event, doc, i) {
    const file = event.target.files[0];
    if (!file) return;

    try {
      outputs.isLoading = true;
      const response = await invokeController.prompt(doc.id, {
        _id: i._id,
        field: i.key,
        value: i.value
      });
      fileInput.value = '';
      outputs.appendNotificationId(response.notification_id);
      return response.notification_id;
    } catch (error) {
      console.error("Error updating image input:", error);
    }
  }

  function triggerFileUpload(doc, i) {
    fileInput.click();
    fileInput.onchange = (e) => handleImageInputUpdate(e, doc, i);
  }

  function handleStartPress(event, doc, i) {
    isLongPress = false;
    longPressTimer = setTimeout(() => {
      isLongPress = true;
      showInputValues = !showInputValues;
    }, 500);
  }

  function handleEndPress(event, doc, i) {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }

    if (!isLongPress) {
      if (!selectedImageInput) {
        triggerFileUpload(doc, i);
      }
    } else {
      selectedImageInput = i;
      showInputValues = !showInputValues;
    }
    isLongPress = false;
  }

  async function handleRefineAll() {
    outputs.isLoading = true;
    const notification = await getNotification(page.id);
    if (notification?.payload?.input) {
      for (const input of notification.payload.input) {
        const keys = Object.keys(input).filter(k => k !== 'id' && k !== '_id');
        for (const key of keys) {
          const response = await invokeController.prompt(notification.prompt_id, {
            _id: input.id || input._id,
            field: key,
            value: input[key]
          });
          if (response?.notification_id) {
            outputs.appendNotificationId(response.notification_id);
          }
        }
      }
    }
    outputs.isLoading = false;
  }
</script>

{#key page.id}
<div class="asset">
  {#await getNotification(page.id)}
    <div class="asset__loading">Loading pending job...</div>
  {:then notification}
    <div class="asset__container">
      <div class="generated-images-header">Refine Pending Job</div>

      <div class="asset__image-container" style="display: flex; align-items: center; justify-content: center; background-color: #f0f0f0; min-height: 200px;">
        <div style="text-align: center; color: #6c757d;">
          <div style="font-size: 3rem; margin-bottom: 0.5rem;">⏳</div>
          <div>Pending Job</div>
          <div style="font-size: 0.8rem;">No output generated yet</div>
        </div>
      </div>

      <div class="asset__settings-toggle" title="Settings">
        {#if getAspectRatio(notification)}
          {@const arValue = getAspectRatio(notification)}
          {@const arValues = ["Square 1:1", "Portrait 4:7", "Portrait 9:16", "Landscape 16:9", "Landscape 21:9"]}
          <div class="asset__aspectratio-select">
            <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
                 onclick={() => { properties.arPortraitToggle = !properties.arPortraitToggle; properties.arSquareToggle = false; properties.arLandscapeToggle = false; }}>
              <rect x="6" y="3" width="12" height="18" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
            </svg>
              {#if properties.arPortraitToggle}
              <span>Portrait: </span>
              {#each aspectRatios as ar}
                {#if ar.includes("Portrait") || ar.includes("Vertical")}
                  <span class:selected-aspect-ratio={arValue == ar}
                        onclick={async (e) => {
                          const nId = await handleUpdate(e, { _id: 'aspect_ratio', key: 'aspect_ratio', value: ar }, notification.prompt_id);
                          if (nId != null) { outputs.notificationIds = [...outputs.notificationIds, nId]; }
                        }}>{ar.split(" ")[0]}</span>
                {/if}
              {/each}
              {/if}

            <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
                 onclick={() => { properties.arLandscapeToggle = !properties.arLandscapeToggle; properties.arSquareToggle = false; properties.arPortraitToggle = false; }}>
              <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
            </svg>
            {#if properties.arLandscapeToggle}
              <span>Landscape:</span>
              {#each arValues as ar}
                {#if ar.includes("Landscape") || ar.toLowerCase().includes("wide")}
                  <span class:selected-aspect-ratio={arValue == ar}
                        onclick={async (e) => {
                          const nId = await handleUpdate(e, { _id: 'aspect_ratio', key: 'aspect_ratio', value: ar }, notification.prompt_id);
                          if (nId != null) { outputs.notificationIds = [...outputs.notificationIds, nId]; }
                        }}>{ar.split(" ")[0]}</span>
                {/if}
              {/each}
            {/if}

            <svg class="aspect-ratio-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
            </svg>
            {#if properties.arSquareToggle}
              {#each arValues as ar}
                {#if ar.includes("Square")}
                  <span class:selected-aspect-ratio={arValue == ar}
                        onclick={async (e) => {
                          const nId = await handleUpdate(e, { _id: 'aspect_ratio', key: 'aspect_ratio', value: ar }, notification.prompt_id);
                          if (nId != null) { outputs.notificationIds = [...outputs.notificationIds, nId]; }
                        }}>{ar.split(" ")[0]}</span>
                {/if}
              {/each}
            {/if}
          </div>
        {/if}

        <div>
          <svg onclick={() => collapsed = !collapsed} class="asset__settings-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5a3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97c0-.33-.03-.65-.07-.97l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.08-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.32-.07.64-.07.97c0 .33.03.65.07.97l-2.11 1.63c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.39 1.06.73 1.69.98l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.25 1.17-.59 1.69-.98l2.49 1c.22.08.49 0 .61-.22l2-3.46c.13-.22.07-.49-.12-.64l-2.11-1.63Z" fill="currentColor"/>
          </svg>
          <svg class="asset__settings-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" onclick={handleRefineAll}>
            <path d="M12 16l-4-4h8l-4 4zm0-12v12" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M5 20h14" stroke="currentColor" stroke-width="2"/>
          </svg>
          <svg class="asset__settings-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" onclick={() => push('#/search')}>
            <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z" stroke="currentColor" stroke-width="2" fill="none"/>
          </svg>
        </div>
      </div>

      {#if !collapsed}
        <div class="settings">
          <div class="asset__facets">
            <div class="asset__facet-group">
              <div class="asset__facet-title">Workflow:</div>
              <div class="asset__facet-list">
                <div class="asset__facet-pill asset__facet-pill--workflow">
                  {notification.workflow_id}
                </div>
              </div>
            </div>

            <div class="asset__facet-group">
              <div class="asset__facet-title">Status:</div>
              <div class="asset__facet-list">
                <div class="asset__facet-pill">
                  {notification.status}
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      <Notifications ids={[page.id]} queryMode="prompt_id" showTrimmings={true}
                     onclick={(_id) => { console.log("Pending:notification:onclick", _id); page.updateId(_id); }}/>

      {#if outputs.notificationIds.length > 0}
        <Notifications ids={outputs.notificationIds} queryMode="prompt_id" showTrimmings={true}
                       onclick={(_id) => { console.log("Pending:refine:notification:onclick", _id); page.updateId(_id); }}/>
      {/if}

      <div class="generated-images-header">Prompts</div>

      <div class="asset__inputs">
        <div class="asset__inputs-content">
          {#if getTextInputs(notification).length > 0}
            <div class="asset__text-inputs">
              {#each getTextInputs(notification) as text}
                <div class="asset__text-input">
                  <div class="asset__text-input-value editable-text"
                       contenteditable="true"
                       onkeydown={async (e) => {
                          const nId = await handleTextUpdate(e, text, notification.prompt_id);
                          if (nId != null) { outputs.notificationIds = [...outputs.notificationIds, nId]; }
                        }}>{text.value}</div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="asset__no-inputs">No text inputs</div>
          {/if}
        </div>

        <div class="asset__inputs-images">
          {#each getImageInputs(notification) as i}
            <img src={i.value.startsWith('virtual://') ? '/images/placeholder.png' : `/images/${i.value}`}
                 onpointerdown={(e) => handleStartPress(e, notification, i)}
                 onpointerup={(e) => handleEndPress(e, notification, i)}
                 onpointercancel={(e) => handleEndPress(e, notification, i)}
                 onpointerleave={(e) => handleEndPress(e, notification, i)}
                 style="cursor: pointer; border-radius:8px;"
                 title="Click to upload new image, long press to toggle input values" />
          {/each}
        </div>

        <input type="file" accept="image/*" bind:this={fileInput} style="display: none;" />
      </div>

      {#if showInputValues}
        <div>
          <div>Pick Input</div>
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
    width: 100%;
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
  }

  .asset__image-container {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    background-color: #f8f9fa;
  }

  .asset__image {
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
  }

  .asset__aspectratio-select {
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
    cursor: pointer;
  }

  .aspect-ratio-icon:hover {
    color: rgba(0, 0, 0, 0.8);
  }

  .settings {
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border: 1px solid rgba(0, 0, 0, 0.03);
    border-radius: 12px;
    margin-top: 1em;
    margin-bottom: 1em;
    background-color: #FCFCFC;
  }

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

  .asset__facet-pill--workflow {
    background-color: #dce8dc;
    color: #6b5b54;
  }

  .generated-images-header {
    font-size: 2em;
    font-weight: 600;
    color: #3a7397cc;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .asset__inputs {
    border-radius: 12px;
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

  .asset__text-input-value {
    padding: 0.5rem;
    border: 1px solid rgba(0, 0, 0, 0.08);
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
    overflow: hidden;
  }

  .asset__inputs-images img {
    max-width: 100px;
    height: auto;
    flex-shrink: 0;
    object-fit: cover;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .editable-text {
    background-color: #FBFBFB;
    padding: 0.5rem;
    border-radius: 8px;
    outline: none;
    transition: border-color 0.2s;
    min-height: 1.2rem;
  }

  .editable-text:focus {
    border-color: #007bff;
    background-color: #f8f9fa;
  }

  .asset__settings-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    border-radius: 4px;
    transition: background-color 0.2s ease;
    flex-direction: row;
  }

  .asset__settings-icon {
    width: 16px;
    height: 16px;
    color: rgba(0, 0, 0, 0.6);
    transition: color 0.2s ease;
    margin-left: 0.5rem;
    cursor: pointer;
  }

  .selected-aspect-ratio {
    border: 1px solid rgba(0, 0, 0, 0.3);
    border-radius: 12px;
    padding: 2px 6px;
  }
</style>

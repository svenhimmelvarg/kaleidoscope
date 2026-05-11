<script>
    import ColorSelector from './ColorSelector.svelte';

    let { text, minimal = false, onUpdate } = $props();
    
    let isEditing = $state(false);
    let showColorSelector = $state(false);
    let el = $state();
    
    let value = $derived(typeof text === 'object' && text !== null ? text.value : text);
    let isHexColor = $derived(/^#([0-9A-Fa-f]{3}){1,2}$/i.test(value?.trim() || ''));

    function handleKeydown(e) {
        onUpdate(e, text);
    }

    function handleColorSelect(color) {
        // Construct a fake event object that mimics an Enter keypress
        const fakeEvent = {
            key: 'Enter',
            preventDefault: () => {},
            target: { innerText: color }
        };
        onUpdate(fakeEvent, text);
        showColorSelector = false;
    }
</script>

{#if !isEditing && isHexColor}
    <div class="color-swatch-container">
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div 
            class="color-swatch" 
            style="background-color: {value.trim()};"
            onclick={() => { showColorSelector = !showColorSelector; }}
            ondblclick={() => {
                isEditing = true;
                showColorSelector = false;
                setTimeout(() => {
                    if (el) el.focus();
                }, 0);
            }}
            title="Click to select a new color, double-click to manually edit"
        ></div>
        
        {#if showColorSelector}
            <ColorSelector startingColor={value.trim()} onSelect={handleColorSelect} />
        {/if}
    </div>
{:else}
    <div
        bind:this={el}
        class="asset__text-input-value editable-text"
        class:minified-view={minimal}
        contenteditable="true"
        onkeydown={handleKeydown}
        onblur={() => isEditing = false}
        onfocus={() => isEditing = true}
    >{value}</div>
{/if}

<style>
  .color-swatch-container {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .color-swatch {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .asset__text-input-value {
    padding: 0.5rem;
    border-radius: 8px;
    font-size: 0.9rem;
  }

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

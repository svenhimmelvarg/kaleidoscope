<script lang="ts">
  export let currentPage: number;
  export let totalPages: number;
  export let goToPage: (page: number) => void;
  export let nextPage: () => void;
  export let prevPage: () => void;
</script>

{#if totalPages > 1}
<div class="paginator">
  <div class="paginator__controls">
    <button
      class="paginator__button"
      disabled={currentPage === 1}
      onclick={prevPage}
    >
      Previous
    </button>
    
    <div class="paginator__pages">
      {#if currentPage > 1}
        <button class="paginator__page" onclick={() => goToPage(1)}>1</button>
        {#if currentPage > 2}
          <span class="paginator__ellipsis">...</span>
        {/if}
      {/if}
      
      {#each Array.from({length: Math.min(11, totalPages - currentPage + 1)}, (_, i) => currentPage + i) as pageNum}
        {#if pageNum === currentPage}
          <span class="paginator__page paginator__page--current">{pageNum}</span>
        {:else}
          <button class="paginator__page" onclick={() => goToPage(pageNum)}>{pageNum}</button>
        {/if}
      {/each}
      
      {#if currentPage + 10 < totalPages}
        <span class="paginator__ellipsis">...</span>
        <button class="paginator__page" onclick={() => goToPage(totalPages)}>{totalPages}</button>
      {/if}
    </div>
    
    <button
      class="paginator__button"
      disabled={currentPage === totalPages}
      onclick={nextPage}
    >
      Next
    </button>
  </div>
</div>
{/if}

<style>
  .paginator {
    margin-top: 2rem;
    padding: 8px 12px;
    background-color: rgba(255, 255, 255, 0.9);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }

  .paginator__controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 4px;
  }

  .paginator__button {
    padding: 6px 12px;
    border: none;
    background-color: transparent;
    cursor: pointer;
    font-size: 13px;
    font-weight: 400;
    color: rgba(0, 0, 0, 0.6);
    transition: color 0.15s ease;
    outline: none;
  }

  .paginator__button:hover:not(:disabled) {
    color: rgba(0, 0, 0, 0.9);
  }

  .paginator__button:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .paginator__pages {
    display: flex;
    gap: 2px;
    align-items: center;
  }

  .paginator__page {
    padding: 6px 8px;
    border: none;
    background-color: transparent;
    cursor: pointer;
    min-width: 28px;
    height: 28px;
    text-align: center;
    font-size: 13px;
    font-weight: 400;
    color: rgba(0, 0, 0, 0.6);
    transition: color 0.15s ease;
    outline: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .paginator__page:hover {
    color: rgba(0, 0, 0, 0.9);
  }

  .paginator__page--current {
    color: rgba(0, 0, 0, 0.9);
    font-weight: 600;
  }

  .paginator__ellipsis {
    padding: 0 6px;
    color: rgba(0, 0, 0, 0.3);
    font-size: 13px;
    font-weight: 400;
  }
</style>
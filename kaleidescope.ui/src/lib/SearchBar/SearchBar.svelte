<script lang="ts">
  import {getContext} from 'svelte'
  let { text = "" , onSearch , onclick=() => {}, execute= () =>{} } = $props()
  const onBlur: () => void = () => {
    onSearch(text)
  };
  let facetCollapsed = $state() 
  const searchParameters = getContext('search.params');
  function check( filters){
    return filters.searchParameters.filters.filter(f => {return f.attribute != "dd" && f.attribute != "mm"}).length > 0
  }
</script>

<div class="search-bar">
    <div class="search-bar__label"> </div>
    <div class="search-bar__input-wrapper">
      <input
        class="search-bar__input"
        bind:value={text}
        onblur={onBlur}
        placeholder="Search..."
        type="search"
      />
    </div>
<div  onclick={()=> {facetCollapsed = !facetCollapsed ; onclick() }}>{ facetCollapsed ?  "+" :  "-"}</div>    
</div>
{#if searchParameters?.filters.filter(f => f.attribute != "dd" && f.attribute != "mm" && f.attribute != "yy").length > 0 }
<div class="date-filters">
  <button
    class="date-filters__button date-filters__button--today"
    onclick={() => {
      console.log("SearchBar:searchParameters", searchParameters.filters);
      let newFilters = searchParameters.filters.filter(f => {return f.attribute != "dd" && f.attribute != "mm"});
      console.log("SearchBar:newFilters", searchParameters.filters, newFilters);
      newFilters = newFilters.concat([
        {attribute: "dd", value: new Date().getDate()},
        {attribute: "mm", value: new Date().getMonth() + 1}
      ]);
      console.log("SearchBar:newFilters:after", newFilters);
      searchParameters.filters = [...newFilters];
      onSearch(text);
    }}
  >
    Today
  </button>

  <button
    class="date-filters__button date-filters__button--week"
    onclick={() => {
      let newFilters = searchParameters.filters.filter(f => {return f.attribute != "dd" && f.attribute != "mm"});
      console.log("SearchBar:newFilters", newFilters);
      newFilters = newFilters.concat([
        {attribute: "dd", "op": ">=", value: new Date().getDate() > 7 ? new Date().getDate() - 7 : 1},
        {attribute: "mm", value: new Date().getMonth() + 1}
      ]);
      searchParameters.filters = [...newFilters];
      onSearch(text);
    }}
  >
    This Week
  </button>

  <button
    class="date-filters__button date-filters__button--month"
    onclick={() => {
      let newFilters = searchParameters.filters.filter(f => {return f.attribute != "dd" && f.attribute != "mm"});
      newFilters = newFilters.concat([
        {attribute: "dd", "op": ">=", value: 1},
        {attribute: "mm", value: new Date().getMonth() + 1}
      ]);
      searchParameters.filters = [...newFilters];
      onSearch(text);
    }}
  >
    Month
  </button>
  {#each searchParameters?.filters.filter(f => f.attribute != "dd" && f.attribute != "mm" && f.attribute != "yy") as f }
      <button class="date-filters__button date-filters__button--filter" style="text-wrap:wrap"
        onclick={()=>{
          let newFilters =  searchParameters.filters.filter( el =>  el.attribute!=f.attribute && el.value!=f.value)
          newFilters = newFilters.concat([
            {attribute: "dd", "op": ">=", value: 1},
            {attribute: "mm", value: new Date().getMonth() + 1}
          ]);
          searchParameters.filters = [...newFilters];
          onSearch(text);          
            }}
      
      >{f.attribute}={f.value.split("/").pop().split(".")[0]} X </button>
  {/each}
</div>
{/if}
<pre>
<!-- {JSON.stringify(searchParameters,null,2)} -->
</pre>
<style>
  .search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background-color: rgba(249, 249, 249, 0.8);
    border-radius: 8px;
    max-width: 400px;
  }

  .search-bar__label {
    font-size: 14px;
    font-weight: 500;
    color: rgba(0, 0, 0, 0.7);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }

  .search-bar__input-wrapper {
    flex: 1;
  }

  .search-bar__input {
    width: 100%;
    padding: 6px 10px;
    font-size: 14px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    border: none;
    outline: none;
    background-color: transparent;
    color: rgba(0, 0, 0, 0.85);
    appearance: none;
    -webkit-appearance: none;
  }

  .search-bar__input:focus {
    background-color: transparent;
  }

  .search-bar__input::placeholder {
    color: rgba(0, 0, 0, 0.4);
  }

  .date-filters {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    padding: 0 12px;
  }

  .date-filters__button {
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: rgba(101, 67, 33, 0.7);
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
  }

  .date-filters__button:hover {
    background-color: rgba(210, 180, 140, 0.1);
    color: rgba(101, 67, 33, 0.9);
  }

  .date-filters__button:active {
    background-color: rgba(188, 143, 143, 0.1);
    transform: scale(0.98);
  }

  .date-filters__button--today {
    color: rgba(139, 69, 19, 0.8);
  }

  .date-filters__button--week {
    color: rgba(128, 70, 27, 0.8);
  }

  .date-filters__button--month {
    color: rgba(105, 25, 25, 0.8);
  }

  .date-filters__button--filter {
    color: rgba(70, 130, 180, 0.8);
  }
</style>

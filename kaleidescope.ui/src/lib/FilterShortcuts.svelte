<script lang="ts">
  import { getContext } from 'svelte';
  import { push, querystring, location } from 'svelte-spa-router';
  import { reduceFacetDistribution } from './functions/indexer_helpers.js';
  import { formatFacetValue } from './functions/convex_helpers.js';
  import { getWeekString } from './functions/date_helpers.js';
  import { featureOn } from './growthbook';
  
  let showHiddenToggleFeature = featureOn("show_hidden_toggle");
  
  const searchState: any = getContext('searchState');

  let { params = {}, onSearch, facets = {}, onRemoveFilter = (attr: string, val: string, expr?: string) => {}, onAddFilter = (kv: any) => {} } = $props();
  
  const weekdayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  
  function getVisibleShortcuts() {
    const shortcuts: Array<{ type: string; value: string; label: string; facet?: string; group: 'date' | 'drilldown' }> = [];
    
    const reduced = reduceFacetDistribution(facets);
    
    if (reduced.vote || reduced.upvoted || reduced.score) {
      shortcuts.push({ type: 'static', value: 'upvoted', label: 'upvoted', group: 'date' });
    }

    const timeShortcuts: any[] = [];
    const drillDownShortcuts: any[] = [];
    
    // 1. Months: up to last 3 months of the current year (or latest available year)
    if (reduced.mm && reduced.yy) {
      // Find the most recent year in the facets
      const years = Object.keys(reduced.yy).map(Number).sort((a, b) => b - a);
      if (years.length > 0) {
        const latestYear = years[0];
        
        // Find months for that year (we assume the mm facet is global, but usually
        // if we are looking at recent data, the highest months are what we want)
        // A more precise way is to just take the highest 3 month numbers
        const monthKeys = Object.keys(reduced.mm)
          .map(Number)
          .sort((a, b) => b - a)
          .slice(0, 3)
          .reverse(); // reverse so it's M-2, M-1, M

        monthKeys.forEach(m => {
          timeShortcuts.push({ 
            type: 'dynamic', 
            facet: 'mm', 
            value: m.toString(), 
            label: monthNames[m - 1] || `M${m}`,
            group: 'date' 
          });
        });
      }
    }
    
    // 2. Weeks: up to last 3 weeks
    let currentWeek = getWeekString(new Date());
    
    // We only want to override the current real-world week if the user has a date-related filter active,
    // otherwise the initial state should just be the current week.
    const hasDateFilter = params.filter && (
      params.filter.startsWith('week:') ||
      params.filter.startsWith('weekday:') ||
      params.filter.startsWith('thisweek_dayOfWeek:')
    );

    // Use 'week' if available, fallback to 'weekday' logic if needed, but week is cleaner
    if (reduced.week) {
      const weekKeys = Object.keys(reduced.week)
        .sort((a, b) => parseInt(b) - parseInt(a))
        .slice(0, 3)
        .reverse(); // W-3, W-2, W-1
        
      if (weekKeys.length > 0 && hasDateFilter) {
        // We will need currentWeek for the dayOfWeek logic
        // The highest week key before slice/reverse was weekKeys[weekKeys.length-1] (since we reversed it)
        currentWeek = weekKeys[weekKeys.length - 1]; 
      }

      weekKeys.forEach(key => {
        // Extract the last 2 digits for a shorter label, e.g., '2609' -> '09'
        const shortLabel = key.length >= 2 ? key.slice(-2) : key;
        timeShortcuts.push({ type: 'dynamic', facet: 'week', value: key, label: `W${shortLabel}`, group: 'date' });
      });
    } else if (reduced.weekday) {
       // Fallback to old weekday logic if 'week' facet is missing
       const weekKeys = Object.keys(reduced.weekday)
        .sort((a, b) => parseInt(b) - parseInt(a))
        .slice(0, 3)
        .reverse();
        
       if (weekKeys.length > 0 && hasDateFilter) {
         currentWeek = weekKeys[weekKeys.length - 1];
       }

       weekKeys.forEach(key => {
         timeShortcuts.push({ type: 'dynamic', facet: 'weekday', value: key, label: `week ${key}`, group: 'date' });
       });
    }
    
    // 3. Days of Week: dynamically derived from the 'weekday' facet for the active week
    if (reduced.weekday && currentWeek) {
      // Extract days that belong to the currentWeek (e.g., '2610') from 'weekday' facet keys (e.g., '26101')
      const daysInWeek = Object.keys(reduced.weekday)
        .filter(k => k.startsWith(currentWeek))
        .sort((a, b) => parseInt(a) - parseInt(b));

      daysInWeek.forEach(key => {
        // 'key' is e.g. '26101' where '1' is Monday.
        // Javascript day 1 = Monday. Our weekdayOrder array has Monday at index 0.
        const dayIndex = parseInt(key.slice(4)) - 1; 
        const dayName = weekdayOrder[dayIndex];
        
        if (dayName) {
          // Route it with the dayName, the router in App.svelte expects "thisweek_dayOfWeek:2610:Monday" 
          // and translates it to filters for dayOfWeek=Monday AND week=2610
          timeShortcuts.push({ type: 'dynamic', facet: 'thisweek_dayOfWeek', value: `${currentWeek}:${dayName}`, label: dayName, group: 'date' });
        }
      });
    } else if (reduced.dayOfWeek) {
      // Fallback if 'weekday' facet isn't available for some reason
      const dayKeys = Object.keys(reduced.dayOfWeek).sort((a, b) => {
        return weekdayOrder.indexOf(a) - weekdayOrder.indexOf(b);
      });
      dayKeys.forEach(key => {
        if (currentWeek) {
          timeShortcuts.push({ type: 'dynamic', facet: 'thisweek_dayOfWeek', value: `${currentWeek}:${key}`, label: key, group: 'date' });
        } else {
          timeShortcuts.push({ type: 'dynamic', facet: 'dayOfWeek', value: key, label: key, group: 'date' });
        }
      });
    }

    // 4. Progressive Drill-Down Facets (Models, Orientation, Time Bucket)
    // Only show these if there's an active filter or custom filter, indicating we've drilled down.
    // reduceFacetDistribution handles dropping facets that no longer have a distribution.
    const hasActiveFilter = !!params.filter || (searchState.customFilters && searchState.customFilters.length > 0);
    
    if (hasActiveFilter) {
      const addTopFacets = (facetName: string, prefixLabel: string, limit: number = 3) => {
        if (reduced[facetName]) {
          const sortedValues = Object.entries(reduced[facetName])
            .sort((a, b) => (b[1] as number) - (a[1] as number))
            .slice(0, limit);
          
          sortedValues.forEach(([val]) => {
            let label = val;
            if (facetName === 'models' || facetName === 'loras') {
               label = formatFacetValue(val);
            }
            
            // Don't add if this is already the active filter or custom filter
            const isActiveFilter = params.filter === `${facetName}:${val}`;
            const isCustomFilter = searchState.customFilters && searchState.customFilters.some((f: any) => f.attribute === facetName && f.value === val);
            
            if (!isActiveFilter && !isCustomFilter) {
               drillDownShortcuts.push({ type: 'dynamic', facet: facetName, value: val, label: `${prefixLabel}${label}`, group: 'drilldown' });
            }
          });
        }
      };

      addTopFacets('models', 'Model: ');
      addTopFacets('loras', 'Lora: ');
      addTopFacets('orientation', '');
      addTopFacets('time_bucket', 'Time: ');
    }
    
    shortcuts.push(...drillDownShortcuts, ...timeShortcuts);
    
    return shortcuts;
  }
  
  let visibleShortcuts = $derived(getVisibleShortcuts());
  

  function handleShortcutClick(shortcut: any) {
    if (shortcut.type === 'static') {
      const filterString = shortcut.value;
      const isActive = params.filter === filterString;
      const qs = $querystring ? `?${$querystring}` : '';
      if (isActive) {
        push(`/search${qs}`);
      } else {
        push(`/search/${filterString}${qs}`);
      }
      return;
    }

    const filterString = `${shortcut.facet}:${shortcut.value}`;
    
    // If it's a primary time/date filter, push it to URL params
    const isDrillDownFacet = ['models', 'loras', 'orientation', 'time_bucket', 'samplers', 'schedulers'].includes(shortcut.facet);
    
    if (!isDrillDownFacet) {
      const isActive = params.filter === filterString;
      const qs = $querystring ? `?${$querystring}` : '';
      if (isActive) {
        push(`/search${qs}`);
      } else {
        push(`/search/${filterString}${qs}`);
      }
    } else {
      // It's a progressive drill down facet, so stack it on the customFilters!
      onAddFilter({ attribute: shortcut.facet, value: shortcut.value });
    }
  }
  function handleClearFilter() {
    const qs = $querystring ? `?${$querystring}` : '';
    if (params?.id) {
      push(`/search/all/${params.id}${qs}`);
    } else {
      push(`/search${qs}`);
    }
  }

  function isShortcutActive(shortcut: any): boolean {
    if (shortcut.type === 'static') {
      return params.filter === shortcut.value;
    } else {
      return params.filter === `${shortcut.facet}:${shortcut.value}`;
    }
  }

  let activeShortcut = $derived(visibleShortcuts.find(isShortcutActive));
  let inactiveShortcuts = $derived(visibleShortcuts.filter(s => !isShortcutActive(s)));

  let dateShortcuts = $derived(inactiveShortcuts.filter(s => s.group === 'date'));
  let drillDownShortcuts = $derived(inactiveShortcuts.filter(s => s.group === 'drilldown'));

  // Logic to populate rows:
  // If there are date shortcuts, they go in row 1, and drill-downs (if any) go in row 2.
  // If there are NO date shortcuts, drill-downs go in row 1, and row 2 is empty.
  let row1Shortcuts = $derived(dateShortcuts.length > 0 ? dateShortcuts : drillDownShortcuts);
  let row2Shortcuts = $derived(dateShortcuts.length > 0 ? drillDownShortcuts : []);

  function getActiveFilterLabel() {
    if (!params.filter) return null;
    if (activeShortcut) return activeShortcut.label;
    if (params.filter.startsWith('thisweek_dayOfWeek:')) {
      const parts = params.filter.split(':');
      return parts[2]; // returns the day string e.g. "Saturday"
    }
    if (params.filter.includes(':')) {
      const parts = params.filter.split(':');
      const facet = parts[0];
      const value = parts.slice(1).join(':');
      if (facet === 'weekday') return `week ${value}`;
      return value;
    }
    return params.filter;
  }

  let activeFilterLabel = $derived(getActiveFilterLabel());

  let searchParamsObj = $derived(new URLSearchParams($querystring || ''));
  let showAdvancedImageInputs = $derived(searchParamsObj.get('advanced') === 'true');
  let showHidden = $derived(searchParamsObj.get('show_hidden') === 'true');

  function toggleAdvanced() {
    const sp = new URLSearchParams($querystring || '');
    if (showAdvancedImageInputs) {
      sp.delete('advanced');
    } else {
      sp.set('advanced', 'true');
    }
    const qs = sp.toString();
    push(`${$location}${qs ? '?' + qs : ''}`);
  }

  function toggleShowHidden() {
    const sp = new URLSearchParams($querystring || '');
    if (showHidden) {
      sp.delete('show_hidden');
    } else {
      sp.set('show_hidden', 'true');
    }
    const qs = sp.toString();
    push(`${$location}${qs ? '?' + qs : ''}`);
  }

  let topInputImages = $derived((() => {
    if (!facets || !facets['inputs.value']) return [];
    return Object.entries(facets['inputs.value'])
      .filter(([val]) => /\.(png|jpe?g|webp|gif|mp4|webm)$/i.test(val))
      .sort((a, b) => (b[1] as number) - (a[1] as number))
      .slice(0, 10)
      .map(([val]) => val);
  })());

  function handleSearchKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      onSearch?.((e.currentTarget as HTMLInputElement).value);
    }
  }
</script>

<div class="filter-shortcuts-container">
  <div class="filter-shortcuts row-1">
    {#each row1Shortcuts as shortcut}
      <button 
        class="filter-shortcuts__pill"
        onclick={() => handleShortcutClick(shortcut)}
      >
        {shortcut.label}
      </button>
    {/each}

    <input
      type="text"
      placeholder="Search..."
      class="filter-shortcuts__pill filter-shortcuts__search"
      bind:value={searchState.q}
      onkeydown={handleSearchKeyDown}
    />

    <button 
      class="filter-shortcuts__icon-btn" 
      class:active={showAdvancedImageInputs}
      onclick={toggleAdvanced} 
      title="Advanced Options"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polygon points="8,10 16,10 12,16" transform={showAdvancedImageInputs ? "rotate(180 12 13)" : ""}></polygon>
      </svg>
    </button>

    {#if $showHiddenToggleFeature}
      <button 
        class="filter-shortcuts__icon-btn" 
        class:active={showHidden}
        onclick={toggleShowHidden} 
        title="Show Hidden"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
          <line x1="1" y1="1" x2="23" y2="23"></line>
        </svg>
      </button>
    {/if}

    {#if activeFilterLabel}
      <button
        class="filter-shortcuts__pill active"
        onclick={handleClearFilter}
        title="Clear filter"
      >
        {activeFilterLabel} &times;
      </button>
    {/if}

    {#if searchState.customFilters}
      {#each searchState.customFilters as filter}
        <button
          class="filter-shortcuts__pill active"
          onclick={() => onRemoveFilter(filter.attribute, filter.value, filter.expression)}
          title="Remove filter"
        >
          {filter.attribute || 'expression'}: {filter.value ? (filter.value.length >= 20 ? filter.value.slice(0, 20) + '...' : filter.value) : filter.expression} &times;
        </button>
      {/each}
    {/if}
  </div>

  {#if showAdvancedImageInputs && topInputImages.length > 0}
    <div class="filter-shortcuts__advanced-images">
      {#each topInputImages as imageName}
        <button 
          class="advanced-image-btn"
          onclick={() => onAddFilter({ attribute: 'inputs.value', value: imageName })}
          title={imageName}
        >
          <img src={`/images/input/${imageName}`} alt={imageName} />
        </button>
      {/each}
    </div>
  {/if}

  {#if row2Shortcuts.length > 0}
    <div class="filter-shortcuts row-2">
      {#each row2Shortcuts as shortcut}
        <button 
          class="filter-shortcuts__pill"
          onclick={() => handleShortcutClick(shortcut)}
        >
          {shortcut.label}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .filter-shortcuts-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 8px;
    padding: 8px 0;
  }

  .filter-shortcuts {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap; /* Important if many pills */
  }

  .filter-shortcuts.row-1 {
    /* Row 1 specific styles if needed */
  }
  
  .filter-shortcuts.row-2 {
    /* Row 2 specific styles if needed */
  }

  .filter-shortcuts__pill {
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    color: rgba(60, 60, 67, 0.6);
    background-color: transparent;
    border: 1px solid rgba(120, 120, 128, 0.16);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
  }

  .filter-shortcuts__pill:hover {
    background-color: rgba(120, 120, 128, 0.08);
    border-color: rgba(120, 120, 128, 0.24);
    color: rgba(60, 60, 67, 0.8);
  }

  .filter-shortcuts__pill.active {
    background-color: rgba(52, 199, 89, 0.15);
    border-color: rgba(52, 199, 89, 0.4);
    color: #248a3d;
  }

  .filter-shortcuts__pill.active:hover {
    background-color: rgba(52, 199, 89, 0.2);
    border-color: rgba(52, 199, 89, 0.5);
  }

  .filter-shortcuts__search {
    width: 150px;
    cursor: text;
  }

  .filter-shortcuts__search:focus {
    border-color: rgba(60, 60, 67, 0.4);
    background-color: rgba(255, 255, 255, 0.5);
  }

  .filter-shortcuts__icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px;
    color: rgba(60, 60, 67, 0.6);
    background-color: transparent;
    border: 1px solid rgba(120, 120, 128, 0.16);
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
  }

  .filter-shortcuts__icon-btn:hover {
    background-color: rgba(120, 120, 128, 0.08);
    border-color: rgba(120, 120, 128, 0.24);
    color: rgba(60, 60, 67, 0.8);
  }
  .filter-shortcuts__icon-btn.active {
    background-color: rgba(52, 199, 89, 0.15);
    border-color: rgba(52, 199, 89, 0.4);
    color: #248a3d;
  }

  .filter-shortcuts__advanced-images {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 4px 0;
    width: 100%;
  }

  .advanced-image-btn {
    flex: 0 0 300px;
    height: 120px;
    padding: 0;
    margin: 0;
    border: 1px solid rgba(120, 120, 128, 0.16);
    border-radius: 12px;
    background-color: transparent;
    cursor: pointer;
    overflow: hidden;
    transition: all 0.2s ease;
    outline: none;
  }

  .advanced-image-btn:hover {
    border-color: rgba(120, 120, 128, 0.4);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .advanced-image-btn img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
</style>

<script lang="ts">
  import { getContext } from 'svelte';
  import { push, querystring, location } from 'svelte-spa-router';
  import { reduceFacetDistribution } from './functions/indexer_helpers.js';
  import { formatFacetValue } from './functions/convex_helpers.js';
  import { getWeekString } from './functions/date_helpers.js';
  import { inputImageUrl } from './functions/uri_helpers.js';
  import { featureOn } from './growthbook';
  
  let showHiddenToggleFeature = featureOn("show_hidden_toggle");
  
  const searchState: any = getContext('searchState');

  let { params = {}, onSearch, facets = {}, onRemoveFilter = (attr: string, val: string, expr?: string) => {}, onAddFilter = (kv: any) => {} } = $props();
  
  type Shortcut = { type: string; value: string; label: string; facet?: string; group: 'date' | 'drilldown' };

  const weekdayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const weekdayShortLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const currentWeek = getWeekString(new Date());
  const todayName = weekdayOrder[(new Date().getDay() + 6) % 7];
  
  function getSortedWeekKeys(reduced: any) {
    if (reduced.week) {
      return Object.keys(reduced.week).sort((a, b) => parseInt(a) - parseInt(b));
    }

    if (reduced.weekday) {
      return Array.from(new Set(Object.keys(reduced.weekday).map(k => k.slice(0, 4))))
        .sort((a: any, b: any) => parseInt(a) - parseInt(b)) as string[];
    }

    return [];
  }
  
  function addSeparator(shortcuts: Shortcut[]) {
    if (shortcuts.length > 0 && shortcuts[shortcuts.length - 1].type !== 'separator') {
      shortcuts.push({ type: 'separator', value: '|', label: '|', group: 'date' });
    }
  }
  
  function buildCurrentWeekDayShortcuts(reduced: any): Shortcut[] {
    if (reduced.weekday) {
      const weekdayDays = Object.keys(reduced.weekday)
        .filter(k => k.startsWith(currentWeek))
        .sort((a, b) => parseInt(a) - parseInt(b))
        .map(key => {
          const dayIndex = parseInt(key.slice(4)) - 1;
          const dayName = weekdayOrder[dayIndex];
          const shortLabel = weekdayShortLabels[dayIndex];

          if (!dayName || !shortLabel) return null;

          return {
            type: 'dynamic',
            facet: 'thisweek_dayOfWeek',
            value: `${currentWeek}:${dayName}`,
            label: dayName === todayName ? 'Today' : shortLabel,
            group: 'date'
          };
        })
        .filter(Boolean) as Shortcut[];

      if (weekdayDays.length > 0) return weekdayDays;
    }

    if (reduced.dayOfWeek && (!reduced.week || reduced.week[currentWeek])) {
      return Object.keys(reduced.dayOfWeek)
        .sort((a, b) => weekdayOrder.indexOf(a) - weekdayOrder.indexOf(b))
        .map(dayName => {
          const dayIndex = weekdayOrder.indexOf(dayName);
          const shortLabel = weekdayShortLabels[dayIndex];

          if (!shortLabel) return null;

          return {
            type: 'dynamic',
            facet: 'thisweek_dayOfWeek',
            value: `${currentWeek}:${dayName}`,
            label: dayName === todayName ? 'Today' : shortLabel,
            group: 'date'
          };
        })
        .filter(Boolean) as Shortcut[];
    }

    return [];
  }

  function parseYearMonth(value: string) {
    const [year, month] = value.split('-').map(Number);

    if (!year || !month) return null;

    return { year, month };
  }

  function buildMonthShortcuts(reduced: any): Shortcut[] {
    if (reduced.ym) {
      return Object.keys(reduced.ym)
        .filter(key => parseYearMonth(key))
        .sort((a, b) => b.localeCompare(a))
        .slice(0, 3)
        .reverse()
        .map(key => {
          const parsed = parseYearMonth(key)!;

          return {
            type: 'dynamic',
            facet: 'ym',
            value: key,
            label: monthNames[parsed.month - 1] || `M${parsed.month}`,
            group: 'date'
          };
        });
    }

    if (reduced.mm) {
      const currentMonth = new Date().getMonth() + 1;

      return Object.keys(reduced.mm)
        .map(Number)
        .sort((a, b) => getRelativeMonthSortValue(b, currentMonth) - getRelativeMonthSortValue(a, currentMonth))
        .slice(0, 3)
        .reverse()
        .map(m => ({
          type: 'dynamic',
          facet: 'mm',
          value: m.toString(),
          label: monthNames[m - 1] || `M${m}`,
          group: 'date'
        }));
    }

    return [];
  }

  function getRelativeMonthSortValue(month: number, currentMonth: number) {
    const inferredYear = month <= currentMonth ? 1 : 0;
    return inferredYear * 12 + month;
  }
  
  function buildTimeShortcuts(reduced: any): Shortcut[] {
    const shortcuts: Shortcut[] = [];
    const weekKeys = getSortedWeekKeys(reduced);
    const previousWeekKeys = weekKeys
      .filter(key => key !== currentWeek)
      .sort((a, b) => parseInt(b) - parseInt(a))
      .slice(0, 3)
      .reverse();
    const monthShortcuts = buildMonthShortcuts(reduced);
    const currentWeekDays = buildCurrentWeekDayShortcuts(reduced);

    if (monthShortcuts.length > 1) {
      shortcuts.push(...monthShortcuts);
    }

    if (previousWeekKeys.length > 0) {
      if (shortcuts.length > 0) addSeparator(shortcuts);

      previousWeekKeys.forEach(key => {
        const shortLabel = key.length >= 2 ? key.slice(-2) : key;
        shortcuts.push({ type: 'dynamic', facet: 'week', value: key, label: `W${shortLabel}`, group: 'date' });
      });
    }

    if (currentWeekDays.length > 0) {
      if (shortcuts.length > 0) addSeparator(shortcuts);
      shortcuts.push(...currentWeekDays);
    }

    return shortcuts;
  }
  
  function getVisibleShortcuts() {
    const shortcuts: Shortcut[] = [];
    
    const reduced = reduceFacetDistribution(facets);
    
    if (reduced.vote || reduced.upvoted || reduced.score) {
      shortcuts.push({ type: 'static', value: 'upvoted', label: 'upvoted', group: 'date' });
    }

    const timeShortcuts: any[] = [];
    const drillDownShortcuts: any[] = [];

    timeShortcuts.push(...buildTimeShortcuts(facets));

    // Progressive Drill-Down Facets (Models, Orientation, Time Bucket)
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
    
    const hasDateShortcut = shortcuts.some(shortcut => shortcut.group === 'date');

    shortcuts.push(...drillDownShortcuts);
    if (hasDateShortcut && timeShortcuts.length > 0) addSeparator(shortcuts);
    shortcuts.push(...timeShortcuts);
    
    return shortcuts;
  }
  
  let visibleShortcuts = $derived(getVisibleShortcuts());
  

  function handleShortcutClick(shortcut: any) {
    if (shortcut.type === 'separator') return;

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
    if (shortcut.type === 'separator') return false;

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

  function formatActiveFacetLabel(facet: string, value: string) {
    if (facet === 'ym') {
      const parsed = parseYearMonth(value);
      return parsed ? monthNames[parsed.month - 1] || value : value;
    }

    if (facet === 'mm') {
      const monthIndex = Number(value) - 1;
      return monthNames[monthIndex] || value;
    }

    if (facet === 'week') {
      const shortLabel = value.length >= 2 ? value.slice(-2) : value;
      return `W${shortLabel}`;
    }

    if (facet === 'weekday') return `week ${value}`;

    return value;
  }

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
      return formatActiveFacetLabel(facet, value);
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
      {#if shortcut.type === 'separator'}
        <span class="filter-shortcuts__separator" aria-hidden="true">|</span>
      {:else}
        <button 
          class="filter-shortcuts__pill"
          onclick={() => handleShortcutClick(shortcut)}
        >
          {shortcut.label}
        </button>
      {/if}
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
          <img src={inputImageUrl(imageName)} alt={imageName} />
        </button>
      {/each}
    </div>
  {/if}

  {#if row2Shortcuts.length > 0}
    <div class="filter-shortcuts row-2">
      {#each row2Shortcuts as shortcut}
        {#if shortcut.type === 'separator'}
          <span class="filter-shortcuts__separator" aria-hidden="true">|</span>
        {:else}
          <button 
            class="filter-shortcuts__pill"
            onclick={() => handleShortcutClick(shortcut)}
          >
            {shortcut.label}
          </button>
        {/if}
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

  .filter-shortcuts__separator {
    color: rgba(60, 60, 67, 0.28);
    font-size: 12px;
    line-height: 1;
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

<script lang="ts">
  import {getContext} from 'svelte'
  import { Meilisearch } from 'meilisearch';
  import { getMeilisearchUrl, formatFacetValue } from '../functions/convex_helpers.js';
  
  let { text = "" , onSearch , onclick=() => {}, execute= () =>{} } = $props()
  
  const searchParameters = getContext('search.params');
  
  // Initialize Meilisearch client
  const client = new Meilisearch({
    host: getMeilisearchUrl(),
    apiKey: 'password'
  });
  
  const index = $derived(client.index(searchParameters.indexName));
  
  // Get week number from date
  function getWeekNumber(date: Date): number {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
    return weekNo;
  }
  
  // Get start and end dates of a week
  function getWeekDates(weekNumber: number, year: number): { start: Date, end: Date } {
    const jan1 = new Date(year, 0, 1);
    const daysOffset = (weekNumber - 1) * 7 - jan1.getDay() + 1;
    const startDate = new Date(year, 0, daysOffset);
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + 6);
    return { start: startDate, end: endDate };
  }
  
  // State for selected week
  let selectedWeek = $state<{week: number, year: number} | null>(null);
  
  // Generate days to display (either last 7 days or selected week's days)
  const displayDays = $derived(() => {
    if (selectedWeek) {
      // Generate days for selected week
      const weekDates = getWeekDates(selectedWeek.week, selectedWeek.year);
      const days = [];
      for (let i = 0; i < 7; i++) {
        const date = new Date(weekDates.start);
        date.setDate(weekDates.start.getDate() + i);
        days.push({
          date: date,
          dd: date.getDate(),
          mm: date.getMonth() + 1,
          yy: date.getFullYear(),
          label: i === 0 ? 'Mon' : i === 1 ? 'Tue' : i === 2 ? 'Wed' : i === 3 ? 'Thu' : i === 4 ? 'Fri' : i === 5 ? 'Sat' : 'Sun'
        });
      }
      return days;
    } else {
      // Generate last 7 days from today
      const days = [];
      const today = new Date();
      for (let i = 0; i < 7; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        days.push({
          date: date,
          dd: date.getDate(),
          mm: date.getMonth() + 1,
          yy: date.getFullYear(),
          label: i === 0 ? 'Today' : i === 1 ? 'Yesterday' : `${date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}`
        });
      }
      return days;
    }
  });
  
  // Store counts for each day
  let dayCounts = $state<Record<string, number>>({});
  let isLoadingCounts = $state(false);
  
  // Store loras and models facet data
  let lorasData = $state<Array<{value: string, count: number}>>([]);
  let modelsData = $state<Array<{value: string, count: number}>>([]);
  let lorasTotal = $state(0);
  let modelsTotal = $state(0);
  let timeBucketsData = $state<Array<{value: string, count: number}>>([]);
  let timeBucketsTotal = $state(0);
  let isLoadingFacets = $state(false);
  
  // Fetch count for a specific day
  async function fetchDayCount(dayInfo: {dd: number, mm: number, yy: number}): Promise<number> {
    try {
      const filter = `dd = ${dayInfo.dd} AND mm = ${dayInfo.mm} AND yy = ${dayInfo.yy}`;
      const response = await index.search('', {
        filter: filter,
        limit: 0
      });
      return response.estimatedTotalHits || 0;
    } catch (error) {
      console.error('Error fetching day count:', error);
      return 0;
    }
  }
  
  // Fetch all day counts
  async function fetchAllDayCounts() {
    isLoadingCounts = true;
    const days = displayDays();
    const counts: Record<string, number> = {};
    
    for (const dayInfo of days) {
      const key = `${dayInfo.dd}-${dayInfo.mm}-${dayInfo.yy}`;
      counts[key] = await fetchDayCount(dayInfo);
    }
    
    dayCounts = counts;
    isLoadingCounts = false;
  }
  
  // Build date filter for displayed days
  function buildDaysFilter(): string | null {
    const days = displayDays();
    if (days.length === 0) return null;
    
    const filters = days.map(day =>
      `dd = ${day.dd} AND mm = ${day.mm} AND yy = ${day.yy}`
    );
    
    return `(${filters.join(' OR ')})`;
  }
  
  // Build filter for a specific selected day
  function buildDayFilter(): string | null {
    if (!selectedDate) return null;
    return `dd = ${selectedDate.dd} AND mm = ${selectedDate.mm} AND yy = ${selectedDate.yy}`;
  }
  
  // Fetch loras and models facet data for displayed days or selected day
  async function fetchFacetData() {
    isLoadingFacets = true;
    try {
      // Use selected day filter if a day is selected, otherwise use days filter
      const filter = selectedDate ? buildDayFilter() : buildDaysFilter();
      const searchOptions: any = {
        facets: ['loras', 'models', 'time_bucket'],
        limit: 0
      };
      
      if (filter) {
        searchOptions.filter = filter;
      }
      
      const response = await index.search('', searchOptions);
      
      const facetDistribution = response.facetDistribution || {};
      
      // Convert loras facet data to array
      const lorasAll = Object.entries(facetDistribution.loras || {})
        .map(([value, count]) => ({ value, count: count as number }))
        .filter(item => item.count > 0)
        .sort((a, b) => b.count - a.count);
      
      lorasTotal = lorasAll.length;
      const loras = lorasAll.slice(0, 4); // Limit to top 4
      
      // Convert models facet data to array
      const modelsAll = Object.entries(facetDistribution.models || {})
        .map(([value, count]) => ({ value, count: count as number }))
        .filter(item => item.count > 0)
        .sort((a, b) => b.count - a.count);
      
       modelsTotal = modelsAll.length;
      const models = modelsAll.slice(0, 4); // Limit to top 4
      
      // Convert time_bucket facet data to array
      const timeBucketsAll = Object.entries(facetDistribution.time_bucket || {})
        .map(([value, count]) => ({ value, count: count as number }))
        .filter(item => item.count > 0)
        .sort((a, b) => b.count - a.count);

      timeBucketsTotal = timeBucketsAll.length;
      const timeBuckets = timeBucketsAll; // Show all (only 5 values)

      lorasData = loras;
      modelsData = models;
      timeBucketsData = timeBuckets;
    } catch (error) {
      console.error('Error fetching facet data:', error);
    } finally {
      isLoadingFacets = false;
    }
  }
  
  // Generate weeks for current year (only weeks that exist)
  const weeksOfYear = $derived(() => {
    const today = new Date();
    const year = today.getFullYear();
    const currentWeek = getWeekNumber(today);
    const weeks = [];
    
    // Show weeks from week 1 up to current week
    for (let i = 1; i <= currentWeek; i++) {
      weeks.push({ week: i, year: year });
    }
    
    return weeks;
  });
  
  // Fetch data on mount
  fetchAllDayCounts();
  fetchFacetData();
  
  // Re-fetch when selections change
  $effect(() => {
    fetchAllDayCounts();
    fetchFacetData();
  });
  
  let selectedDate = $state<{dd: number, mm: number, yy: number} | null>(null);
  let selectedLoras = $state<string[]>([]);
  let selectedModels = $state<string[]>([]);
  let selectedTimeBuckets = $state<string[]>([]);
  
  function handleDateClick(dayInfo: {dd: number, mm: number, yy: number}) {
    // Toggle date selection
    if (selectedDate && selectedDate.dd === dayInfo.dd && selectedDate.mm === dayInfo.mm && selectedDate.yy === dayInfo.yy) {
      selectedDate = null;
    } else {
      selectedDate = dayInfo;
    }
    onSearch(text);
  }
  
  function handleWeekClick(weekInfo: {week: number, year: number}) {
    // Toggle week selection
    if (selectedWeek && selectedWeek.week === weekInfo.week && selectedWeek.year === weekInfo.year) {
      selectedWeek = null;
      selectedDate = null;
    } else {
      selectedWeek = weekInfo;
      selectedDate = null; // Clear day selection when week is selected
    }
    // Re-fetch day counts and facets
    fetchAllDayCounts();
    fetchFacetData();
    onSearch(text);
  }
  
  function handleLoraClick(loraValue: string) {
    const index = selectedLoras.indexOf(loraValue);
    if (index === -1) {
      selectedLoras = [...selectedLoras, loraValue];
    } else {
      selectedLoras = selectedLoras.filter(l => l !== loraValue);
    }
    onSearch(text);
  }
  
  function handleModelClick(modelValue: string) {
    const index = selectedModels.indexOf(modelValue);
    if (index === -1) {
      selectedModels = [...selectedModels, modelValue];
    } else {
      selectedModels = selectedModels.filter(m => m !== modelValue);
    }
    onSearch(text);
  }
   
  function handleTimeBucketClick(timeBucketValue: string) {
    const index = selectedTimeBuckets.indexOf(timeBucketValue);
    if (index === -1) {
      selectedTimeBuckets = [...selectedTimeBuckets, timeBucketValue];
    } else {
      selectedTimeBuckets = selectedTimeBuckets.filter(t => t !== timeBucketValue);
    }
    onSearch(text);
  }
   
  // Update searchParameters filters when selections change
  $effect(() => {
    // Build filter array
    let filters: any[] = [];
    
    // Add date filters
    if (selectedDate) {
      filters.push({attribute: 'dd', value: selectedDate.dd});
      filters.push({attribute: 'mm', value: selectedDate.mm});
      filters.push({attribute: 'yy', value: selectedDate.yy});
    } else if (selectedWeek) {
      // Add week filter (all days in the week)
      const weekDates = getWeekDates(selectedWeek.week, selectedWeek.year);
      for (let i = 0; i < 7; i++) {
        const date = new Date(weekDates.start);
        date.setDate(weekDates.start.getDate() + i);
        filters.push({attribute: 'dd', value: date.getDate()});
        filters.push({attribute: 'mm', value: date.getMonth() + 1});
        filters.push({attribute: 'yy', value: date.getFullYear()});
      }
    }
    
    // Add loras filters
    selectedLoras.forEach(lora => {
      filters.push({ attribute: 'loras', value: lora });
    });
    
    // Add models filters
    selectedModels.forEach(model => {
      filters.push({ attribute: 'models', value: model });
    });
    
    // Add time_bucket filters
    selectedTimeBuckets.forEach(timeBucket => {
      filters.push({ attribute: 'time_bucket', value: timeBucket });
    });
    
    searchParameters.filters = [...filters];
  });
  
  function isDateSelected(dayInfo: {dd: number, mm: number, yy: number}): boolean {
    return selectedDate !== null && selectedDate.dd === dayInfo.dd && selectedDate.mm === dayInfo.mm && selectedDate.yy === dayInfo.yy;
  }
  
  function isWeekSelected(weekInfo: {week: number, year: number}): boolean {
    return selectedWeek !== null && selectedWeek.week === weekInfo.week && selectedWeek.year === weekInfo.year;
  }
  
  function isLoraSelected(loraValue: string): boolean {
    return selectedLoras.includes(loraValue);
  }
  
   function isModelSelected(modelValue: string): boolean {
    return selectedModels.includes(modelValue);
  }
  
  function isTimeBucketSelected(timeBucketValue: string): boolean {
    return selectedTimeBuckets.includes(timeBucketValue);
  }
   
   function getDayCount(dayInfo: {dd: number, mm: number, yy: number}): number {
     const key = `${dayInfo.dd}-${dayInfo.mm}-${dayInfo.yy}`;
     return dayCounts[key] || 0;
   }
</script>

<div class="search-bar-advanced">
  <!-- Date Pills Row -->
  <div class="row">
    <div class="label">{selectedWeek ? 'Week Days:' : 'Last 7 Days:'}</div>
    <div class="pills">
      {#each displayDays().toReversed() as dayInfo}
        <button
          class="pill"
          class:selected={isDateSelected(dayInfo)}
          class:loading={isLoadingCounts}
          onclick={() => handleDateClick(dayInfo)}
        >
          <span class="pill-label">{dayInfo.label}</span>
          <span class="pill-count">
            ({isLoadingCounts ? '...' : getDayCount(dayInfo)})
          </span>
        </button>
      {/each}
    </div>
  </div>
  
  <!-- Loras Pills Row -->
  <div class="row">
    <div class="label">Loras:</div>
    <div class="pills">
      {#if isLoadingFacets}
        <div class="pill">Loading...</div>
      {:else if lorasData.length === 0}
        <div class="pill">No loras</div>
      {:else}
        {#each lorasData as lora}
          <button
            class="pill"
            class:selected={isLoraSelected(lora.value)}
            onclick={() => handleLoraClick(lora.value)}
            title={lora.value}
          >
            <span class="pill-label">{formatFacetValue(lora.value)}</span>
            <span class="pill-count">({lora.count})</span>
          </button>
        {/each}
        {#if lorasTotal > 4}
          <span class="pill more-indicator">... ({lorasTotal - 4} more)</span>
        {/if}
      {/if}
    </div>
  </div>
  
  <!-- Models Pills Row -->
  <div class="row">
    <div class="label">Models:</div>
    <div class="pills">
      {#if isLoadingFacets}
        <div class="pill">Loading...</div>
      {:else if modelsData.length === 0}
        <div class="pill">No models</div>
      {:else}
        {#each modelsData as model}
          <button
            class="pill"
            class:selected={isModelSelected(model.value)}
            onclick={() => handleModelClick(model.value)}
            title={model.value}
          >
            <span class="pill-label">{formatFacetValue(model.value)}</span>
            <span class="pill-count">({model.count})</span>
          </button>
        {/each}
        {#if modelsTotal > 4}
          <span class="pill more-indicator">... ({modelsTotal - 4} more)</span>
        {/if}
       {/if}
     </div>
   </div>
   
   <!-- Time Bucket Pills Row -->
   <div class="row">
     <div class="label">Time:</div>
     <div class="pills">
       {#if isLoadingFacets}
         <div class="pill">Loading...</div>
       {:else if timeBucketsData.length === 0}
         <div class="pill">No time data</div>
       {:else}
         {#each timeBucketsData as timeBucket}
           <button
             class="pill"
             class:selected={isTimeBucketSelected(timeBucket.value)}
             onclick={() => handleTimeBucketClick(timeBucket.value)}
             title={timeBucket.value}
           >
             <span class="pill-label">{timeBucket.value}</span>
             <span class="pill-count">({timeBucket.count})</span>
           </button>
         {/each}
       {/if}
     </div>
   </div>
   
   <!-- Week Selector Row -->
  <div class="divider"></div>
  <div class="week-row">
    <div class="week-header">
      <span class="year">{new Date().getFullYear()}</span>
      <span class="month">[{new Date().getMonth() + 1}]</span>
    </div>
    <div class="weeks">
      {#each weeksOfYear() as weekInfo}
        <button
          class="week-pill"
          class:selected={isWeekSelected(weekInfo)}
          onclick={() => handleWeekClick(weekInfo)}
        >
          [{weekInfo.week}]
        </button>
      {/each}
    </div>
  </div>
</div>

<style>
  .search-bar-advanced {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    background-color: rgba(249, 249, 249, 0.8);
    border-radius: 8px;
    max-width: 100%;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .label {
    font-size: 14px;
    font-weight: 500;
    color: rgba(0, 0, 0, 0.7);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    min-width: 100px;
  }

  .pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    flex: 1;
  }

  .pill {
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 20px;
    color: rgba(101, 67, 33, 0.7);
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
    white-space: nowrap;
  }

  .pill:hover {
    background-color: rgba(210, 180, 140, 0.2);
    border-color: rgba(210, 180, 140, 0.4);
    color: rgba(101, 67, 33, 0.9);
    transform: translateY(-1px);
  }

  .pill:active {
    transform: scale(0.98);
  }

  .pill.selected {
    background-color: rgba(139, 69, 19, 0.15);
    border-color: rgba(139, 69, 19, 0.4);
    color: rgba(139, 69, 19, 1);
    font-weight: 600;
  }

  .pill.selected:hover {
    background-color: rgba(139, 69, 19, 0.2);
  }

  .pill-label {
    margin-right: 4px;
  }

  .pill-count {
    color: rgba(0, 0, 0, 0.5);
    font-size: 12px;
  }

  .more-indicator {
    background-color: rgba(0, 0, 0, 0.05);
    color: rgba(0, 0, 0, 0.4);
    cursor: default;
  }

  .divider {
    height: 1px;
    background-color: rgba(0, 0, 0, 0.1);
    margin: 12px 0;
  }

  .week-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .week-header {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    font-weight: 500;
    color: rgba(0, 0, 0, 0.7);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }

  .year {
    font-size: 16px;
    font-weight: 600;
  }

  .month {
    font-size: 14px;
    color: rgba(0, 0, 0, 0.5);
  }

  .weeks {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .week-pill {
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    color: rgba(101, 67, 33, 0.7);
    cursor: pointer;
    transition: all 0.2s ease;
    outline: none;
    white-space: nowrap;
  }

  .week-pill:hover {
    background-color: rgba(210, 180, 140, 0.2);
    border-color: rgba(210, 180, 140, 0.4);
    color: rgba(101, 67, 33, 0.9);
    transform: translateY(-1px);
  }

  .week-pill:active {
    transform: scale(0.98);
  }

  .week-pill.selected {
    background-color: rgba(139, 69, 19, 0.15);
    border-color: rgba(139, 69, 19, 0.4);
    color: rgba(139, 69, 19, 1);
    font-weight: 600;
  }

  .week-pill.selected:hover {
    background-color: rgba(139, 69, 19, 0.2);
  }
</style>

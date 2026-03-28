<script lang="ts">
  import { Plot, Line, Dot, BarY, ColorLegend } from 'svelteplot';

  let { data = [], onclick = () => {} } = $props<{ data: any[], onclick: () => void }>();

  // Extract elapsed_ms and convert to seconds, filtering out undefined/null values
  let validData = $derived(
    data
      .filter((d) => typeof d.elapsed_ms === 'number' && !isNaN(d.elapsed_ms))
      .map((d) => ({
        ...d,
        seconds: d.elapsed_ms / 1000,
        traced_seconds: (d.traced_elapsed_ms ?? 0) / 1000,
        date: d.created ? new Date(d.created * 1000) : new Date()
      }))
      .sort((a, b) => a.date.getTime() - b.date.getTime())
  );

  let yTicks = $derived(validData.map((d) => d.seconds));

  // Transform validData into a flat structure suitable for BarY with a color grouping dimension
  let barData = $derived(
    validData.flatMap(d => [
      {
        unique_id: `${d._id}_total`,
        date: d.date,
        seconds: d.seconds,
        type: 'Total',
        color: 'rgba(52, 199, 89, 0.8)'
      },
      {
        unique_id: `${d._id}_traced`,
        date: d.date,
        seconds: d.traced_seconds,
        type: 'Traced',
        color: 'rgba(0, 122, 255, 0.8)'
      }
    ])
  );

  // Extract all trace events
  let traceData = $derived(
    data
      .filter((d) => Array.isArray(d.trace))
      .flatMap((d) => {
        const docDate = d.created ? new Date(d.created * 1000) : new Date();
        const docId = d.id || d._id || docDate.getTime().toString();
        return d.trace
          .filter((t: any) => typeof t.elapsed_ms === 'number')
          .map((t: any, idx: number) => ({
            date: docDate,
            doc_id: docId,
            seconds: t.elapsed_ms / 1000,
            series_id: `${t.class_type}_${t.node_id}`,
            unique_id: `${t.class_type}_${t.node_id}_${docDate.getTime()}_${idx}`,
            class_type: t.class_type,
            node_id: t.node_id
          }));
      })
      .sort((a, b) => a.date.getTime() - b.date.getTime()) // Sort chronologically
  );

  let traceYTicks = $derived(traceData.map((d) => d.seconds));
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="metrics-container" {onclick}>
  {#if validData.length === 0}
    <div class="metrics-empty">No valid elapsed_ms data to display</div>
  {:else}
    <Plot
      x={{ axis: null, padding: 0.2 }}
      fx={{ label: 'Time', tickFormat: (d: any) => new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
      y={{ label: 'Elapsed Time (s)', grid: false, ticks: yTicks, axis: 'right' }}
      height={300}
      marginBottom={50}
      marginLeft={80}
      marginTop={30}
      marginRight={30}
    >
      {#snippet footer()}
        <div style="margin-top: 15px; display: flex; justify-content: center; flex-wrap: wrap; padding-bottom: 10px;">
          <ColorLegend />
        </div>
      {/snippet}
      <BarY 
        data={barData} 
        x="type" 
        fx="date"
        y="seconds" 
        fill="type"
        title={(d: any) => `${d.type}: ${d.seconds.toFixed(2)}s (${d.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
      />
    </Plot>
  {/if}
</div>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="metrics-container" {onclick}>
  {#if traceData.length === 0}
    <div class="metrics-empty">No trace events to display</div>
  {:else}
    <Plot
      x={{ label: 'Execution Time', axis: 'bottom', tickRotate: -45, tickFormat: (d: any) => new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
      y={{ label: 'Node Elapsed Time (s)', grid: true, axis: 'left' }}
      height={400}
      marginBottom={100}
      marginLeft={60}
      marginTop={30}
      marginRight={30}
    >
      {#snippet footer()}
        <div style="margin-top: 15px; display: flex; justify-content: center; flex-wrap: wrap; padding-bottom: 10px;">
          <ColorLegend />
        </div>
      {/snippet}
      <BarY 
        data={traceData} 
        x="date" 
        y="seconds" 
        fill="series_id"
        title={(d: any) => `${d.series_id}: ${d.seconds.toFixed(2)}s (${d.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
      />
    </Plot>
  {/if}
</div>

<style>
  .metrics-container {
    margin-top: 1rem;
    padding: 1rem;
    background-color: transparent;
    border: 1px solid rgba(120, 120, 128, 0.16);
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .metrics-container:hover {
    background-color: rgba(120, 120, 128, 0.04);
    border-color: rgba(120, 120, 128, 0.24);
  }
  .metrics-empty {
    text-align: center;
    color: rgba(60, 60, 67, 0.6);
    padding: 2rem;
    font-size: 14px;
    font-weight: 500;
  }
</style>
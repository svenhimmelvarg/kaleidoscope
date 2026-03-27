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

  // Extract trace events where elapsed_ms > 3000ms
  let traceData = $derived(
    data
      .filter((d) => Array.isArray(d.trace))
      .flatMap((d) => {
        const docDate = d.created ? new Date(d.created * 1000) : new Date();
        return d.trace
          .filter((t: any) => typeof t.elapsed_ms === 'number' && t.elapsed_ms > 3000)
          .map((t: any, idx: number) => ({
            date: docDate,
            seconds: t.elapsed_ms / 1000,
            series_id: `${t.class_type}_${t.node_id}`,
            unique_id: `${t.class_type}_${t.node_id}_${docDate.getTime()}_${idx}`,
            class_type: t.class_type,
            node_id: t.node_id
          }));
      })
      .sort((a, b) => b.seconds - a.seconds) // Sort descending by elapsed time
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
      x={{ label: 'Time', grid: true }}
      y={{ label: 'Elapsed Time (s)', grid: false, ticks: yTicks, axis: 'right' }}
      height={300}
      marginBottom={50}
      marginLeft={80}
      marginTop={30}
      marginRight={30}
    >
      <Line 
        data={validData} 
        x="date" 
        y="seconds" 
        stroke="rgba(52, 199, 89, 0.8)" 
        strokeWidth={2} 
      />
      <Dot 
        data={validData} 
        x="date" 
        y="seconds" 
        fill="rgba(52, 199, 89, 1)" 
        stroke="#fff" 
        strokeWidth={1.5}
        r={4}
        title={(d: any) => `Total: ${d.seconds.toFixed(2)}s (${d.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
      />
      <Line 
        data={validData} 
        x="date" 
        y="traced_seconds" 
        stroke="rgba(0, 122, 255, 0.8)" 
        strokeWidth={2} 
      />
      <Dot 
        data={validData} 
        x="date" 
        y="traced_seconds" 
        fill="rgba(0, 122, 255, 1)" 
        stroke="#fff" 
        strokeWidth={1.5}
        r={4}
        title={(d: any) => `Traced: ${d.traced_seconds.toFixed(2)}s (${d.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`}
      />
    </Plot>
  {/if}
</div>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="metrics-container" {onclick}>
  {#if traceData.length === 0}
    <div class="metrics-empty">No trace events &gt; 3 seconds to display</div>
  {:else}
    <Plot
      x={{ label: 'Node Execution', axis: 'bottom', tickRotate: -45, tickFormat: (d: any) => d.split('_').slice(0, -2).join('_') }}
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
        x="unique_id" 
        y="seconds" 
        fill="series_id"
        sort={{ x: "y", reverse: true }}
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
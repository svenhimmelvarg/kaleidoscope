<script>
    let { startingColor = '', onSelect } = $props();
    
    function hslToHex(h, s, l) {
        l /= 100;
        const a = s * Math.min(l, 1 - l) / 100;
        const f = n => {
            const k = (n + h / 30) % 12;
            const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
            return Math.round(255 * color).toString(16).padStart(2, '0');
        };
        return `#${f(0)}${f(8)}${f(4)}`;
    }

    const slCurve = [
        { s: 100, l: 93.9 },  // Lightest
        { s: 52.6, l: 85.1 },
        { s: 39.5, l: 74.7 },
        { s: 41.8, l: 67.6 },
        { s: 42.1, l: 61.4 },
        { s: 42.1, l: 55.3 },
        { s: 43, l: 48.8 },
        { s: 57, l: 42 },
        { s: 100, l: 30.8 }   // Darkest
    ];

    const palette = [];
    for (let h = 0; h < 360; h += 30) {
        for (const shade of slCurve) {
            palette.push(hslToHex(h, shade.s, shade.l));
        }
    }
</script>

<div class="color-selector">
    {#each palette as color}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div 
            class="color-option {color.toLowerCase() === startingColor.toLowerCase() ? 'selected' : ''}"
            style="background-color: {color};"
            onclick={() => onSelect(color)}
            title={color}
        ></div>
    {/each}
    <div class="text-hint">Double-click the color swatch to manually edit the hex code</div>
</div>

<style>
    .color-selector {
        display: grid;
        grid-template-rows: repeat(9, 1fr);
        grid-auto-flow: column;
        gap: 4px;
        padding: 12px;
        background-color: #2b2b2b; /* Darker background to resemble the screenshot */
        border-radius: 8px;
        border: 1px solid #444;
        margin-top: 8px;
        width: max-content;
    }

    .color-option {
        width: 24px;
        height: 24px;
        border-radius: 4px;
        cursor: pointer;
        box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        transition: transform 0.1s;
    }

    .color-option:hover {
        transform: scale(1.15);
        z-index: 10;
        position: relative;
    }

    .color-option.selected {
        outline: 2px solid #fff;
        outline-offset: 1px;
    }

    .text-hint {
        grid-column: 1 / -1;
        width: 100%;
        font-size: 0.75rem;
        color: #aaa;
        text-align: center;
        margin-top: 8px;
    }
</style>
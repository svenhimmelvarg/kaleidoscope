<script>
  import { fixImageUrl } from "./functions/uri_helpers";

  let { doc, onFrameSelect = () => {} } = $props();
  let videoNode = $state();
  
  let showScrubber = $state(false);
  let isScrubbing = $state(false);
  let currentTime = $state(0);
  let duration = $state(0);
  let scrubberContainer = $state();
  
  let thumbnails = $state([]);
  let isGeneratingThumbnails = $state(false);

  // Handle time updates
  function handleTimeUpdate() {
    if (!isScrubbing && videoNode) {
      currentTime = videoNode.currentTime;
    }
  }

  function handleLoadedMetadata() {
    if (videoNode) {
      duration = videoNode.duration;
    }
  }

  async function generateThumbnails() {
    if (!videoNode || isGeneratingThumbnails) return;
    isGeneratingThumbnails = true;
    thumbnails = [];

    const numThumbnails = 8;
    const dur = videoNode.duration;
    if (!dur) {
        isGeneratingThumbnails = false;
        return;
    }

    const offscreenVideo = document.createElement('video');
    offscreenVideo.src = videoNode.src;
    offscreenVideo.crossOrigin = "anonymous";
    offscreenVideo.muted = true;
    
    // Wait for metadata
    await new Promise(resolve => {
      offscreenVideo.addEventListener('loadedmetadata', () => resolve(null), { once: true });
    });

    const canvas = document.createElement('canvas');
    const targetWidth = 60;
    const aspect = offscreenVideo.videoWidth / offscreenVideo.videoHeight || 1;
    canvas.width = targetWidth;
    canvas.height = targetWidth / aspect;
    const ctx = canvas.getContext('2d');

    const step = dur / numThumbnails;

    for (let i = 0; i < numThumbnails; i++) {
      const time = i * step + (step / 2); // get middle of segment
      offscreenVideo.currentTime = time;
      
      await new Promise(resolve => {
        const onSeeked = () => {
          offscreenVideo.removeEventListener('seeked', onSeeked);
          resolve(null);
        };
        offscreenVideo.addEventListener('seeked', onSeeked);
      });

      if (ctx) {
        ctx.drawImage(offscreenVideo, 0, 0, canvas.width, canvas.height);
        thumbnails = [...thumbnails, canvas.toDataURL('image/jpeg', 0.5)];
      }
    }
    isGeneratingThumbnails = false;
  }

  // Scrubber dragging logic
  function calculateTimeFromEvent(e) {
    if (!scrubberContainer || !duration) return 0;
    const rect = scrubberContainer.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const percentage = x / rect.width;
    return percentage * duration;
  }

  function handlePointerDown(e) {
    isScrubbing = true;
    if (videoNode) videoNode.pause();
    scrub(e);
    
    window.addEventListener('pointermove', scrub);
    window.addEventListener('pointerup', handlePointerUp);
  }

  function scrub(e) {
    if (!isScrubbing) return;
    const newTime = calculateTimeFromEvent(e);
    currentTime = newTime;
    if (videoNode) {
      videoNode.currentTime = newTime;
    }
  }

  async function handlePointerUp(e) {
    if (!isScrubbing) return;
    isScrubbing = false;
    window.removeEventListener('pointermove', scrub);
    window.removeEventListener('pointerup', handlePointerUp);
    
    await captureFrame();
  }

  // Frame extraction
  async function captureFrame() {
    if (!videoNode) return;
    
    // Create an off-screen canvas
    const canvas = document.createElement('canvas');
    canvas.width = videoNode.videoWidth;
    canvas.height = videoNode.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Draw current frame to canvas
    ctx.drawImage(videoNode, 0, 0, canvas.width, canvas.height);
    
    // Convert to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      
      // Calculate SHA-256 hash
      let hashHex = "";
      if (window.crypto && crypto.subtle) {
        const buffer = await blob.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      } else {
        hashHex = Math.random().toString(16).substring(2, 15) + Math.random().toString(16).substring(2, 15);
      }
      
      // Create file and pass to callback
      const file = new File([blob], `${hashHex}.jpg`, { type: 'image/jpeg' });
      onFrameSelect(file);
    }, 'image/jpeg', 0.95);
  }

  // Scaffolded for future frame extraction
  export function getCurrentFrame() {
    if (!videoNode) return null;
    return videoNode.currentTime;
  }
</script>

<div class="video-container" class:scrubber-active={showScrubber}>
  <!-- svelte-ignore a11y_media_has_caption -->
  <video
    bind:this={videoNode}
    class="asset__image"
    src={fixImageUrl(doc.image_url, doc.source)}
    controls={!showScrubber}
    autoplay
    ontimeupdate={handleTimeUpdate}
    onloadedmetadata={handleLoadedMetadata}
    style="width: 100%; object-fit: contain; border-radius: 16px; display: block;"
  ></video>

  {#if !showScrubber}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
      class="scrubber-toggle"
      onclick={(e) => { e.stopPropagation(); showScrubber = true; generateThumbnails(); }}
      title="Open Scrubber & Frame Extractor"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="12" y1="8" x2="12" y2="16"></line>
        <line x1="8" y1="12" x2="16" y2="12"></line>
      </svg>
    </div>
  {:else}
    <div class="scrubber-overlay">
      <div 
        class="scrubber-close"
        onclick={(e) => { e.stopPropagation(); showScrubber = false; }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </div>
      
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div 
        class="scrubber-track-container"
        bind:this={scrubberContainer}
        onpointerdown={handlePointerDown}
      >
        <div class="scrubber-filmstrip">
          {#if thumbnails.length === 0}
            <div class="filmstrip-placeholder">Loading frames...</div>
          {:else}
            {#each thumbnails as thumb}
              <img src={thumb} class="filmstrip-frame" draggable="false" alt="frame" />
            {/each}
          {/if}
          <div 
            class="scrubber-playhead" 
            style="left: {duration ? (currentTime / duration) * 100 : 0}%"
          ></div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .video-container {
    position: relative;
    width: 100%;
    border-radius: 16px;
  }

  .scrubber-toggle {
    position: absolute;
    bottom: 24px;
    right: 16px;
    width: 36px;
    height: 36px;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
    opacity: 0.7;
    z-index: 10;
  }

  .scrubber-toggle:hover {
    opacity: 1;
    background: rgba(0, 0, 0, 0.7);
    transform: scale(1.05);
  }

  .scrubber-toggle svg {
    width: 20px;
    height: 20px;
  }

  .scrubber-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 80px;
    background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0) 100%);
    border-bottom-left-radius: 16px;
    border-bottom-right-radius: 16px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 0 16px 16px 16px;
    z-index: 10;
  }

  .scrubber-close {
    position: absolute;
    top: -30px;
    right: 16px;
    width: 28px;
    height: 28px;
    background: rgba(0, 0, 0, 0.6);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    cursor: pointer;
  }
  
  .scrubber-close svg {
    width: 16px;
    height: 16px;
  }

  .scrubber-track-container {
    width: 100%;
    height: 48px;
    display: flex;
    align-items: center;
    cursor: pointer;
    position: relative;
    padding: 4px 0;
  }

  .scrubber-filmstrip {
    width: 100%;
    height: 100%;
    display: flex;
    position: relative;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
  }

  .filmstrip-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ccc;
    font-size: 12px;
  }

  .filmstrip-frame {
    flex: 1;
    height: 100%;
    object-fit: cover;
    pointer-events: none;
    border-right: 1px solid rgba(0, 0, 0, 0.5);
  }

  .filmstrip-frame:last-child {
    border-right: none;
  }

  .scrubber-playhead {
    position: absolute;
    top: -4px;
    bottom: -4px;
    width: 4px;
    background: #ffffff;
    transform: translateX(-50%);
    border-radius: 2px;
    box-shadow: 0 0 4px rgba(0,0,0,0.8);
    pointer-events: none;
  }
</style>

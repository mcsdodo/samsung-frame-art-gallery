<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2 v-if="reframeEnabled">Re-framing Preview</h2>
        <h2 v-else>Preview (Crop: {{ cropPercent }}%, Matte: {{ mattePercent }}%)</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <!-- Reframe info message for multiple images -->
      <div v-if="reframeEnabled && selectedPaths.length > 1" class="info-banner">
        Re-framing uses center crop for multiple images. Select a single image for manual positioning.
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Generating previews...</p>
      </div>

      <!-- Single image reframe mode with drag -->
      <div v-else-if="reframeEnabled && selectedPaths.length === 1" class="reframe-container">
        <div class="reframe-instructions">
          Drag the image to position within the frame. Darkened areas will be cropped.
        </div>
        <div
          class="reframe-canvas"
          ref="viewportRef"
          @mousedown="startDrag"
          @touchstart="startDrag"
        >
          <img
            v-if="originalImageUrl"
            :src="originalImageUrl"
            class="reframe-image"
            :style="canvasImageStyle"
            draggable="false"
            @load="onImageLoad"
          />
          <!-- Frame overlay showing crop boundaries -->
          <div class="crop-overlay">
            <div class="crop-window" :style="cropWindowStyle"></div>
          </div>
        </div>
      </div>

      <!-- Standard preview mode -->
      <div v-else-if="previews.length === 0" class="empty-state">
        <p>No previews available</p>
      </div>

      <div v-else class="previews-container">
        <div v-for="preview in previews" :key="preview.name" class="preview-item">
          <h3>{{ preview.name }}</h3>
          <div class="comparison">
            <div class="image-box">
              <h4>Original</h4>
              <img :src="preview.original_url" :alt="`Original ${preview.name}`" />
            </div>
            <div class="image-box">
              <h4>Processed</h4>
              <img :src="preview.processed_url" :alt="`Processed ${preview.name}`" />
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="secondary" @click="$emit('close')">Cancel</button>
        <button
          class="primary"
          @click="$emit('upload')"
          :disabled="loading || (previews.length === 0 && !reframeEnabled)"
        >
          Upload All
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const emit = defineEmits(['close', 'upload', 'offset-change'])
const props = defineProps({
  previews: {
    type: Array,
    default: () => []
  },
  cropPercent: {
    type: Number,
    default: 0
  },
  mattePercent: {
    type: Number,
    default: 10
  },
  loading: {
    type: Boolean,
    default: false
  },
  reframeEnabled: {
    type: Boolean,
    default: false
  },
  selectedPaths: {
    type: Array,
    default: () => []
  }
})

// Reframe drag state
const viewportRef = ref(null)
const originalImageUrl = ref(null)
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const offsetX = ref(0.5)
const offsetY = ref(0.5)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartOffsetX = ref(0)
const dragStartOffsetY = ref(0)

const TARGET_RATIO = 16 / 9
const CANVAS_WIDTH = 800
const CANVAS_HEIGHT = 500  // Larger than 16:9 to show context

// Calculate image dimensions for the canvas view
const canvasImageStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value

  // Scale image to fit within canvas while showing full image
  let imgDisplayWidth, imgDisplayHeight

  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    // Image is wider - fit to canvas width
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    // Image is taller - fit to canvas height
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  return {
    width: `${imgDisplayWidth}px`,
    height: `${imgDisplayHeight}px`
  }
})

// Calculate crop window position and size
const cropWindowStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value

  // Get displayed image dimensions
  let imgDisplayWidth, imgDisplayHeight
  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  // Calculate crop window size based on image aspect ratio
  let cropWidth, cropHeight

  if (imgRatio > TARGET_RATIO) {
    // Image wider than 16:9 - crop window height = image height, width = height * 16/9
    cropHeight = imgDisplayHeight
    cropWidth = cropHeight * TARGET_RATIO
  } else {
    // Image taller than 16:9 - crop window width = image width, height = width / 16*9
    cropWidth = imgDisplayWidth
    cropHeight = cropWidth / TARGET_RATIO
  }

  // Calculate max offset for crop window positioning
  const maxOffsetX = imgDisplayWidth - cropWidth
  const maxOffsetY = imgDisplayHeight - cropHeight

  // Position crop window based on offset
  const cropLeft = (CANVAS_WIDTH - imgDisplayWidth) / 2 + maxOffsetX * offsetX.value
  const cropTop = (CANVAS_HEIGHT - imgDisplayHeight) / 2 + maxOffsetY * offsetY.value

  return {
    width: `${cropWidth}px`,
    height: `${cropHeight}px`,
    left: `${cropLeft}px`,
    top: `${cropTop}px`
  }
})

// Keep old imageStyle for backwards compatibility (used in drag calculations)
const imageStyle = computed(() => {
  if (!imageNaturalWidth.value || !imageNaturalHeight.value) return {}

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value
  const viewportWidth = 800  // Fixed viewport width
  const viewportHeight = viewportWidth / TARGET_RATIO

  let imgDisplayWidth, imgDisplayHeight

  if (imgRatio > TARGET_RATIO) {
    // Image wider than viewport - fit height, overflow width
    imgDisplayHeight = viewportHeight
    imgDisplayWidth = viewportHeight * imgRatio
  } else {
    // Image taller than viewport - fit width, overflow height
    imgDisplayWidth = viewportWidth
    imgDisplayHeight = viewportWidth / imgRatio
  }

  // Calculate max offset in pixels
  const maxOffsetX = imgDisplayWidth - viewportWidth
  const maxOffsetY = imgDisplayHeight - viewportHeight

  // Apply offset
  const translateX = -maxOffsetX * offsetX.value
  const translateY = -maxOffsetY * offsetY.value

  return {
    width: `${imgDisplayWidth}px`,
    height: `${imgDisplayHeight}px`,
    transform: `translate(${translateX}px, ${translateY}px)`
  }
})

const onImageLoad = (e) => {
  imageNaturalWidth.value = e.target.naturalWidth
  imageNaturalHeight.value = e.target.naturalHeight
}

const startDrag = (e) => {
  e.preventDefault()
  isDragging.value = true

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  dragStartX.value = clientX
  dragStartY.value = clientY
  dragStartOffsetX.value = offsetX.value
  dragStartOffsetY.value = offsetY.value

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging.value) return

  const clientX = e.touches ? e.touches[0].clientX : e.clientX
  const clientY = e.touches ? e.touches[0].clientY : e.clientY

  const deltaX = clientX - dragStartX.value
  const deltaY = clientY - dragStartY.value

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value

  // Get displayed image dimensions (same calc as canvasImageStyle)
  let imgDisplayWidth, imgDisplayHeight
  if (imgRatio > CANVAS_WIDTH / CANVAS_HEIGHT) {
    imgDisplayWidth = CANVAS_WIDTH
    imgDisplayHeight = CANVAS_WIDTH / imgRatio
  } else {
    imgDisplayHeight = CANVAS_HEIGHT
    imgDisplayWidth = CANVAS_HEIGHT * imgRatio
  }

  // Get crop window dimensions
  let cropWidth, cropHeight
  if (imgRatio > TARGET_RATIO) {
    cropHeight = imgDisplayHeight
    cropWidth = cropHeight * TARGET_RATIO
  } else {
    cropWidth = imgDisplayWidth
    cropHeight = cropWidth / TARGET_RATIO
  }

  // Calculate max offset (how far crop window can move)
  const maxOffsetX = imgDisplayWidth - cropWidth
  const maxOffsetY = imgDisplayHeight - cropHeight

  // Calculate new offset (drag moves the crop window, so positive delta = positive offset)
  if (maxOffsetX > 0) {
    offsetX.value = Math.max(0, Math.min(1, dragStartOffsetX.value + deltaX / maxOffsetX))
  }
  if (maxOffsetY > 0) {
    offsetY.value = Math.max(0, Math.min(1, dragStartOffsetY.value + deltaY / maxOffsetY))
  }
}

const stopDrag = () => {
  if (!isDragging.value) return
  isDragging.value = false

  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)

  // Emit offset change to parent
  if (props.selectedPaths.length === 1) {
    emit('offset-change', props.selectedPaths[0], offsetX.value, offsetY.value)
  }
}

// Load original image for reframe mode
const loadOriginalImage = async () => {
  if (!props.reframeEnabled || props.selectedPaths.length !== 1) return

  const path = props.selectedPaths[0]
  originalImageUrl.value = `/api/images/${encodeURIComponent(path)}/thumbnail?size=1200`

  // Reset offset to center
  offsetX.value = 0.5
  offsetY.value = 0.5
}

watch(() => [props.reframeEnabled, props.selectedPaths], loadOriginalImage, { immediate: true })

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 8px;
  max-width: 1400px;
  max-height: 90vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  border: 1px solid #2a2a4e;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #2a2a4e;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.2rem;
  color: white;
}

.close-btn {
  background: transparent;
  border: none;
  color: #aaa;
  font-size: 2rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #aaa;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a4e;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.previews-container {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.preview-item {
  margin-bottom: 2rem;
}

.preview-item:last-child {
  margin-bottom: 0;
}

.preview-item h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: white;
  font-weight: 500;
}

.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.image-box {
  background: #12121f;
  border: 1px solid #2a2a4e;
  border-radius: 4px;
  padding: 0.75rem;
}

.image-box h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #aaa;
  font-weight: 500;
}

.image-box img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 2px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #2a2a4e;
}

.modal-footer button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

.modal-footer button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-footer button.primary {
  background: #4a90d9;
  color: white;
}

.modal-footer button.secondary {
  background: #3a3a5e;
  color: white;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .comparison {
    grid-template-columns: 1fr;
  }

  .modal-content {
    max-height: 95vh;
  }
}

/* Reframe mode styles */
.info-banner {
  background: #2a3a5e;
  color: #8ab4f8;
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  border-bottom: 1px solid #3a4a6e;
}

.reframe-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  overflow: hidden;
}

.reframe-instructions {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.reframe-canvas {
  position: relative;
  width: 800px;
  height: 500px;
  max-width: 100%;
  cursor: grab;
  border-radius: 4px;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.reframe-canvas:active {
  cursor: grabbing;
}

.reframe-image {
  user-select: none;
  pointer-events: none;
  position: relative;
  z-index: 1;
}

.crop-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}

.crop-window {
  position: absolute;
  /* Transparent window showing the crop area */
  background: transparent;
  border: 2px solid #4a90d9;
  border-radius: 2px;
  box-shadow:
    0 0 0 9999px rgba(0, 0, 0, 0.6),
    inset 0 0 0 1px rgba(255, 255, 255, 0.2);
}

/* Corner indicators */
.crop-window::before,
.crop-window::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: #fff;
  border-style: solid;
}

.crop-window::before {
  top: -2px;
  left: -2px;
  border-width: 3px 0 0 3px;
}

.crop-window::after {
  bottom: -2px;
  right: -2px;
  border-width: 0 3px 3px 0;
}
</style>

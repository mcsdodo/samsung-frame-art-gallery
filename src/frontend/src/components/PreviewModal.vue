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
          Drag the image to position the crop area
        </div>
        <div
          class="reframe-viewport"
          ref="viewportRef"
          @mousedown="startDrag"
          @touchstart="startDrag"
        >
          <img
            v-if="originalImageUrl"
            :src="originalImageUrl"
            class="reframe-image"
            :style="imageStyle"
            draggable="false"
            @load="onImageLoad"
          />
          <div class="frame-overlay">
            <div class="frame-outside top"></div>
            <div class="frame-outside bottom"></div>
            <div class="frame-outside left"></div>
            <div class="frame-outside right"></div>
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

// Calculate image dimensions and position
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

  // Convert pixel delta to offset delta (inverted because we're moving the image)
  const viewportWidth = 800
  const viewportHeight = viewportWidth / TARGET_RATIO

  const imgRatio = imageNaturalWidth.value / imageNaturalHeight.value
  let maxOffsetX, maxOffsetY

  if (imgRatio > TARGET_RATIO) {
    const imgDisplayHeight = viewportHeight
    const imgDisplayWidth = viewportHeight * imgRatio
    maxOffsetX = imgDisplayWidth - viewportWidth
    maxOffsetY = 0
  } else {
    const imgDisplayWidth = viewportWidth
    const imgDisplayHeight = viewportWidth / imgRatio
    maxOffsetX = 0
    maxOffsetY = imgDisplayHeight - viewportHeight
  }

  // Calculate new offset (inverted drag direction)
  if (maxOffsetX > 0) {
    offsetX.value = Math.max(0, Math.min(1, dragStartOffsetX.value - deltaX / maxOffsetX))
  }
  if (maxOffsetY > 0) {
    offsetY.value = Math.max(0, Math.min(1, dragStartOffsetY.value - deltaY / maxOffsetY))
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

.reframe-viewport {
  position: relative;
  width: 800px;
  max-width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  cursor: grab;
  border-radius: 4px;
  background: #000;
}

.reframe-viewport:active {
  cursor: grabbing;
}

.reframe-image {
  position: absolute;
  top: 0;
  left: 0;
  user-select: none;
  pointer-events: none;
}

.frame-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.frame-outside {
  position: absolute;
  background: rgba(0, 0, 0, 0.5);
}

.frame-outside.top {
  top: -100%;
  left: 0;
  right: 0;
  height: 100%;
}

.frame-outside.bottom {
  bottom: -100%;
  left: 0;
  right: 0;
  height: 100%;
}

.frame-outside.left {
  left: -100%;
  top: -100%;
  bottom: -100%;
  width: 100%;
}

.frame-outside.right {
  right: -100%;
  top: -100%;
  bottom: -100%;
  width: 100%;
}
</style>

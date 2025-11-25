<template>
  <div
    ref="cardRef"
    class="image-card"
    :class="{ selected, current: isCurrent }"
    @click="$emit('toggle')"
    @dblclick.stop="$emit('preview')"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
    @touchmove="onTouchCancel"
    @touchcancel="onTouchCancel"
  >
    <div class="checkbox" @click.stop="$emit('toggle')">
      <input type="checkbox" :checked="selected" />
    </div>
    <img
      v-if="isVisible && thumbnailUrl && !imgError"
      :src="thumbnailUrl"
      :alt="displayName"
      @error="imgError = true"
      @load="imgLoaded = true"
      :class="{ loaded: imgLoaded }"
    />
    <div v-else class="placeholder">
      <span>{{ displayName.slice(0, 2).toUpperCase() }}</span>
    </div>
    <div class="overlay">
      <span class="name">{{ displayName }}</span>
      <span v-if="isCurrent" class="current-badge">NOW</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, inject, onMounted, onUnmounted, nextTick } from 'vue'

// Get scroll container from parent ImageGrid for proper IntersectionObserver root
const scrollContainer = inject('scrollContainer', ref(null))

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isCurrent: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

const emit = defineEmits(['toggle', 'preview'])

const cardRef = ref(null)
const isVisible = ref(false)
const imgError = ref(false)
const imgLoaded = ref(false)
const longPressTimer = ref(null)
const LONG_PRESS_DELAY = 500

let observer = null

onMounted(() => {
  // Use nextTick to ensure DOM is fully rendered before observing
  nextTick(() => {
    // Use IntersectionObserver with scroll container as root
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            isVisible.value = true
            // Once visible, stop observing (image stays loaded)
            observer?.unobserve(entry.target)
          }
        })
      },
      {
        root: scrollContainer.value, // Use grid container as root
        rootMargin: '200px 0px', // Preload 200px ahead
        threshold: 0
      }
    )

    if (cardRef.value) {
      observer.observe(cardRef.value)
    }
  })
})

onUnmounted(() => {
  if (observer && cardRef.value) {
    observer.unobserve(cardRef.value)
  }
  observer = null
})

const onTouchStart = () => {
  longPressTimer.value = setTimeout(() => {
    emit('preview')
  }, LONG_PRESS_DELAY)
}

const onTouchEnd = () => {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

const onTouchCancel = () => {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
    longPressTimer.value = null
  }
}

const thumbnailUrl = computed(() => {
  if (imgError.value) return null
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/thumbnail`
  }
  // TV artwork - fetch thumbnail from TV
  if (props.image.content_id) {
    return `/api/tv/artwork/${encodeURIComponent(props.image.content_id)}/thumbnail`
  }
  return null
})

const displayName = computed(() => {
  if (props.isLocal) {
    return props.image.name
  }
  return props.image.content_id || 'Unknown'
})
</script>

<style scoped>
.image-card {
  position: relative;
  width: 100%;
  padding-bottom: 100%; /* 1:1 aspect ratio */
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
  background: #2a2a4e;
}

.image-card:hover {
  transform: scale(1.02);
}

.image-card.selected {
  border-color: #4a90d9;
}

.image-card.current {
  border-color: #44ff44;
}

.checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.3s ease;
}

img.loaded {
  opacity: 1;
}

.placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: bold;
  color: #666;
  background: linear-gradient(135deg, #2a2a4e, #1a1a2e);
}

.overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.current-badge {
  background: #44ff44;
  color: black;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
}
</style>

<template>
  <div
    ref="cardRef"
    class="image-card"
    :class="{ selected, current: isCurrent, 'on-tv': onTv }"
    :style="{ aspectRatio: computedAspectRatio }"
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
      <span v-if="isCurrent" class="current-badge">Now showing</span>
      <span v-if="onTv" class="on-tv-badge" title="Already uploaded to the TV">On TV</span>
      <span v-if="image.labels?.length" class="label-chips" :title="image.labels.join(', ')">
        <span class="label-chip">{{ image.labels[0] }}</span>
        <span v-if="image.labels.length > 1" class="label-chip more">+{{ image.labels.length - 1 }}</span>
      </span>
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
  onTv: { type: Boolean, default: false },
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
  // Met images have direct thumbnail URL
  if (props.image.thumbnail) {
    return props.image.thumbnail
  }
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
  // TV artwork uploaded from this app: show the file it came from
  if (props.image.source_path) {
    return props.image.source_path.split('/').pop().replace(/\.jpe?g$/i, '')
  }
  // Met images have title
  if (props.image.title) {
    return props.image.title
  }
  return props.image.content_id || 'Unknown'
})

const computedAspectRatio = computed(() => {
  const w = props.image.width
  const h = props.image.height

  if (!w || !h) {
    return 16 / 9  // Default fallback
  }

  let ratio = w / h

  // Cap extreme ratios to prevent layout issues
  // Min 1:2 (portrait), Max 3:1 (landscape)
  ratio = Math.max(ratio, 0.5)   // No taller than 1:2
  ratio = Math.min(ratio, 3)     // No wider than 3:1

  return ratio
})
</script>

<style scoped>
.image-card {
  position: relative;
  width: 100%;
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  background: var(--surface-3);
  box-shadow: 0 0 0 1px var(--border);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 0 1px var(--border-strong), var(--shadow);
}

.image-card.selected {
  box-shadow: 0 0 0 2px var(--accent), 0 0 0 6px var(--accent-soft);
}

.image-card.current:not(.selected) {
  box-shadow: 0 0 0 2px var(--success);
}

.checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: rgba(10, 11, 15, 0.55);
  backdrop-filter: blur(6px);
  opacity: 0;
  transition: opacity 0.15s;
}

.image-card:hover .checkbox,
.image-card.selected .checkbox {
  opacity: 1;
}

@media (hover: none) {
  .checkbox { opacity: 1; }
}

.checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.3s ease;
}

img.loaded {
  opacity: 1;
}

.image-card.on-tv:not(.selected) img.loaded {
  opacity: 0.5;
}

.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-faint);
  background: linear-gradient(135deg, var(--surface-3), var(--surface-2));
}

.overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24px 10px 8px;
  background: linear-gradient(transparent, rgba(5, 6, 10, 0.85));
  display: flex;
  align-items: center;
  gap: 6px;
}

.name {
  flex: 1;
  min-width: 0;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #f4f5f8;
}

.on-tv-badge,
.current-badge,
.label-chip {
  flex: none;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.on-tv-badge {
  background: var(--accent);
  color: #fff;
}

.current-badge {
  background: var(--success);
  color: #06281c;
}

.label-chips {
  display: flex;
  gap: 4px;
  min-width: 0;
}

.label-chip {
  background: rgba(255, 255, 255, 0.14);
  color: #f4f5f8;
  backdrop-filter: blur(6px);
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

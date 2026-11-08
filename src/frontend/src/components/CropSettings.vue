<template>
  <div class="crop-settings">
    <div v-if="allowReframe" class="reframe-field">
      <label
        class="checkbox-label"
        title="Fill 16:9 frame by cropping the image. Drag to position the crop area."
      >
        <input
          type="checkbox"
          v-model="reframeValue"
          @change="emitChange"
        />
        Re-framing
      </label>
    </div>
    <div v-show="!(reframeValue && allowReframe)" class="crop-field">
      <label title="Remove edges from all sides before adding matte">Crop:</label>
      <input
        type="number"
        v-model.number="cropValue"
        min="0"
        max="50"
        step="1"
        :disabled="reframeValue && allowReframe"
        @input="emitChange"
        title="Percentage of image to crop from each edge"
      />
      <span class="unit">%</span>
    </div>
    <div v-show="!(reframeValue && allowReframe)" class="crop-field">
      <label title="Add white border around the image">Matte:</label>
      <input
        type="number"
        v-model.number="matteValue"
        min="0"
        max="50"
        step="1"
        :disabled="reframeValue && allowReframe"
        @input="emitChange"
        title="Percentage of white border to add around the image"
      />
      <span class="unit">%</span>
    </div>
    <button
      class="preview-btn"
      @click="$emit('preview')"
      :disabled="!hasSelection"
      title="Preview how the image will look after processing"
    >
      Preview
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['change', 'preview'])
const props = defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  },
  allowReframe: {
    type: Boolean,
    default: true
  }
})

const reframeValue = ref(true)  // fill the frame by default; no white matte
const cropValue = ref(0)
const matteValue = ref(10)

const emitChange = () => {
  emit('change', {
    crop: cropValue.value,
    matte: matteValue.value,
    reframe: props.allowReframe ? reframeValue.value : false
  })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/config')
    const data = await res.json()
    if (data.default_crop_percent !== undefined) {
      cropValue.value = data.default_crop_percent
    }
    if (data.default_matte_percent !== undefined) {
      matteValue.value = data.default_matte_percent
    }
    emitChange()
  } catch (e) {
    // Use defaults if config fetch fails
    emitChange()
  }
})
</script>

<style scoped>
.crop-settings {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
}

.reframe-field {
  display: flex;
  align-items: center;
}

.checkbox-label {
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: var(--text-muted);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.crop-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: opacity 0.2s;
}

.crop-field label {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.crop-field input[type="number"] {
  width: 64px;
  height: 32px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: var(--text);
}

.crop-field input[type="number"]:focus {
  outline: none;
  border-color: var(--accent);
}

.crop-field input[type="number"]:disabled {
  background: var(--surface-2);
  color: var(--text-faint);
}

.crop-field .unit {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.preview-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-hover);
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.preview-btn:hover:not(:disabled) {
  background: var(--surface-hover);
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

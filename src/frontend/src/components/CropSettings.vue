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
    <div class="crop-field" :class="{ disabled: reframeValue && allowReframe }">
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
    <div class="crop-field" :class="{ disabled: reframeValue && allowReframe }">
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

const reframeValue = ref(false)
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
  gap: 1rem;
  align-items: center;
}

.reframe-field {
  display: flex;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: #ccc;
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

.crop-field.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.crop-field label {
  font-size: 0.9rem;
  color: #aaa;
}

.crop-field input[type="number"] {
  width: 70px;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.crop-field input[type="number"]:focus {
  outline: none;
  border-color: #4a90d9;
}

.crop-field input[type="number"]:disabled {
  background: #1a1a2e;
  color: #666;
}

.crop-field .unit {
  font-size: 0.9rem;
  color: #aaa;
}

.preview-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #3a3a5e;
  color: white;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.preview-btn:hover:not(:disabled) {
  background: #4a4a6e;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

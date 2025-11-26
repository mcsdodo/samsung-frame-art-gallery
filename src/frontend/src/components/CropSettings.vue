<template>
  <div class="crop-settings">
    <div class="crop-field">
      <label>Crop:</label>
      <input
        type="number"
        v-model.number="cropValue"
        min="0"
        max="50"
        step="1"
        @input="emitChange"
      />
      <span class="unit">%</span>
    </div>
    <button
      class="preview-btn"
      @click="$emit('preview')"
      :disabled="!hasSelection"
    >
      Preview
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['change', 'preview'])
const props = defineProps({
  hasSelection: {
    type: Boolean,
    default: false
  }
})

const cropValue = ref(0)

const emitChange = () => {
  emit('change', cropValue.value)
}
</script>

<style scoped>
.crop-settings {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.crop-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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

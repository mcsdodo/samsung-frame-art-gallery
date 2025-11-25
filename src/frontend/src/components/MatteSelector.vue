<template>
  <div class="matte-selector">
    <div class="matte-field">
      <label>Style:</label>
      <select v-model="style" @change="emitChange">
        <option v-for="s in styles" :key="s" :value="s">{{ formatLabel(s) }}</option>
      </select>
    </div>
    <div class="matte-field">
      <label>Color:</label>
      <select v-model="color" @change="emitChange">
        <option v-for="c in colors" :key="c" :value="c">{{ formatLabel(c) }}</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['change'])

const styles = ref(['none'])
const colors = ref(['neutral'])
const style = ref('none')
const color = ref('neutral')

const formatLabel = (s) => s.charAt(0).toUpperCase() + s.slice(1)

const emitChange = () => {
  emit('change', { style: style.value, color: color.value })
}

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/mattes')
    const data = await res.json()
    styles.value = data.styles || ['none']
    colors.value = data.colors || ['neutral']
  } catch (e) {
    console.error('Failed to load matte options:', e)
  }
})
</script>

<style scoped>
.matte-selector {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.matte-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.matte-field label {
  font-size: 0.9rem;
  color: #aaa;
}

.matte-field select {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  cursor: pointer;
}
</style>

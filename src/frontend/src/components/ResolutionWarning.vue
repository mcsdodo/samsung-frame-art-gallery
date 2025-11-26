<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal">
      <h3>Low Resolution Warning</h3>
      <p>
        The following images may be smaller than your TV's 4K resolution (3840 × 2160)
        and could appear pixelated:
      </p>

      <ul class="image-list">
        <li v-for="img in images" :key="img.object_id">
          <strong>{{ img.title }}</strong>
          <span class="resolution">{{ formatResolution(img) }}</span>
        </li>
      </ul>

      <div class="actions">
        <button class="secondary" @click="$emit('cancel')">Cancel</button>
        <button class="primary" @click="$emit('confirm')">Upload Anyway</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  images: { type: Array, required: true }
})

defineEmits(['confirm', 'cancel'])

const formatResolution = (img) => {
  if (!img.width || !img.height || (img.width === 0 && img.height === 0)) {
    return 'Resolution unknown'
  }
  return `${img.width} × ${img.height}`
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal h3 {
  margin: 0 0 1rem;
  color: #ffaa00;
}

.modal p {
  color: #aaa;
  margin-bottom: 1rem;
}

.image-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.image-list li {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  border-bottom: 1px solid #2a2a4e;
}

.image-list li strong {
  color: white;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 1rem;
}

.resolution {
  color: #ff6666;
  font-family: monospace;
  white-space: nowrap;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.actions button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.actions .secondary {
  background: #3a3a5e;
  color: white;
}

.actions .primary {
  background: #4a90d9;
  color: white;
}
</style>

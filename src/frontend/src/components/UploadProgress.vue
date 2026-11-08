<!-- Progress overlay for a batch upload to the TV: per-image status, stop, and a result summary. -->
<template>
  <div class="upload-overlay">
    <div class="upload-card" role="dialog" aria-live="polite">
      <div class="head">
        <h3>{{ title }}</h3>
        <span class="count">{{ finished }} / {{ items.length }}</span>
      </div>

      <div class="bar"><div class="fill" :class="{ failed: failedCount && done }" :style="{ width: percent + '%' }"></div></div>

      <p v-if="!done && current" class="current">
        <span class="spinner"></span>
        {{ current.name }}
      </p>
      <p v-else-if="done" class="summary">
        <span>{{ doneCount }} uploaded<span v-if="failedCount" class="err">, {{ failedCount }} failed</span><span v-if="skippedCount">, {{ skippedCount }} not sent</span></span>
      </p>

      <ul class="list">
        <li v-for="item in items" :key="item.path" :class="item.status">
          <span class="icon">{{ icons[item.status] }}</span>
          <span class="name">{{ item.name }}</span>
          <span v-if="item.error" class="error" :title="item.error">{{ item.error }}</span>
        </li>
      </ul>

      <div class="actions">
        <button v-if="!done" class="secondary" :disabled="stopping" @click="$emit('stop')">
          {{ stopping ? 'Stopping after this one…' : 'Stop' }}
        </button>
        <button v-else class="primary" @click="$emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, required: true }, // {path, name, status: pending|uploading|done|failed|skipped, error}
  stopping: { type: Boolean, default: false }
})
defineEmits(['stop', 'close'])

const icons = { pending: '○', uploading: '◐', done: '✓', failed: '✕', skipped: '–' }

const doneCount = computed(() => props.items.filter(i => i.status === 'done').length)
const failedCount = computed(() => props.items.filter(i => i.status === 'failed').length)
const skippedCount = computed(() => props.items.filter(i => i.status === 'skipped').length)
const finished = computed(() => doneCount.value + failedCount.value)
const done = computed(() => props.items.every(i => !['pending', 'uploading'].includes(i.status)))
const current = computed(() => props.items.find(i => i.status === 'uploading'))
const percent = computed(() => {
  const total = props.items.length - skippedCount.value
  return total ? Math.round((finished.value / total) * 100) : 100
})
const title = computed(() => {
  if (!done.value) return 'Uploading to TV'
  return failedCount.value ? 'Upload finished with errors' : 'Upload complete'
})
</script>

<style scoped>
.upload-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.upload-card {
  width: min(460px, 100%);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: #1a1a2e;
  border: 1px solid #3a3a5e;
  border-radius: 12px;
  padding: 1.25rem;
  color: #eee;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.head h3 {
  margin: 0;
  font-size: 1.05rem;
}

.count {
  color: #aaa;
  font-variant-numeric: tabular-nums;
}

.bar {
  height: 8px;
  background: #2a2a4e;
  border-radius: 4px;
  overflow: hidden;
}

.fill {
  height: 100%;
  background: #4a90d9;
  transition: width 0.3s ease;
}

.fill.failed {
  background: #d9904a;
}

.current,
.summary {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #ccc;
  min-width: 0;
}

.err {
  color: #ff7b7b;
}

.spinner {
  flex: none;
  width: 14px;
  height: 14px;
  border: 2px solid #333;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  font-size: 0.85rem;
  border-top: 1px solid #2a2a4e;
}

.list li {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding: 0.35rem 0;
  border-bottom: 1px solid #22223a;
  color: #888;
  min-width: 0;
}

.list li.uploading { color: #fff; }
.list li.done { color: #9fd99f; }
.list li.failed { color: #ff7b7b; }

.icon {
  width: 1rem;
  text-align: center;
  flex: none;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.error {
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.actions button {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #3a3a5e;
  cursor: pointer;
}

.actions .primary {
  background: #4a90d9;
  border-color: #4a90d9;
  color: white;
}

.actions .secondary {
  background: transparent;
  color: #ccc;
}

.actions button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>

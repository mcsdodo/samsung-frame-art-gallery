<!-- Add or remove labels on the selected TV artwork; tri-state per label across the selection. -->
<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal label-picker" role="dialog" aria-labelledby="label-picker-title">
      <header class="modal-head">
        <h3 id="label-picker-title">Label {{ count }} artwork{{ count === 1 ? '' : 's' }}</h3>
        <button class="icon-btn" aria-label="Close" @click="$emit('close')">
          <svg viewBox="0 0 20 20"><path d="M6 6l8 8M14 6l-8 8" /></svg>
        </button>
      </header>

      <form class="new-label" @submit.prevent="addNew">
        <input v-model.trim="newLabel" class="input" placeholder="New label, e.g. Nature" maxlength="40" />
        <button class="btn btn-secondary" :disabled="!newLabel">Add</button>
      </form>

      <ul v-if="names.length" class="label-list">
        <li v-for="name in names" :key="name">
          <label class="check-row">
            <input
              type="checkbox"
              :checked="state[name] === 'all'"
              :indeterminate.prop="state[name] === 'some'"
              @change="state[name] = $event.target.checked ? 'all' : 'none'"
            />
            <span class="label-name">{{ name }}</span>
            <span class="label-count">{{ counts[name] || 0 }}</span>
          </label>
        </li>
      </ul>
      <p v-else class="hint">No labels yet. Create one above, for example "Nature" or "Van Gogh".</p>

      <footer class="modal-foot">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button class="btn btn-primary" :disabled="!changed" @click="apply">Save</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

const props = defineProps({
  selected: { type: Array, required: true }, // artwork objects with .labels
  counts: { type: Object, required: true }    // label -> count across all artwork
})
const emit = defineEmits(['apply', 'close'])

const count = computed(() => props.selected.length)
const initial = {}
for (const name of Object.keys(props.counts)) {
  const n = props.selected.filter(a => (a.labels || []).includes(name)).length
  initial[name] = n === 0 ? 'none' : n === props.selected.length ? 'all' : 'some'
}
const state = reactive({ ...initial })
const names = computed(() => Object.keys(state).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' })))
const newLabel = ref('')

const addNew = () => {
  const name = newLabel.value
  if (!name) return
  const existing = Object.keys(state).find(n => n.toLowerCase() === name.toLowerCase())
  state[existing || name] = 'all'
  newLabel.value = ''
}

const changed = computed(() => Object.keys(state).some(n => state[n] !== (initial[n] || 'none')))

const apply = () => {
  const add = Object.keys(state).filter(n => state[n] === 'all' && initial[n] !== 'all')
  const remove = Object.keys(state).filter(n => state[n] === 'none' && (initial[n] || 'none') !== 'none')
  emit('apply', { add, remove })
}
</script>

<style scoped>
.label-picker { width: min(400px, 100%); }

.new-label {
  display: flex;
  gap: 8px;
}
.new-label .input { flex: 1; }

.label-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 280px;
  overflow-y: auto;
}

.check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.check-row:hover { background: var(--surface-3); }
.label-name { flex: 1; }
.label-count {
  font-size: 0.75rem;
  color: var(--text-faint);
  font-variant-numeric: tabular-nums;
}
.hint { margin: 0; color: var(--text-muted); font-size: 0.85rem; }
</style>

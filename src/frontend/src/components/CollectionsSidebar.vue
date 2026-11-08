<template>
  <aside class="collections-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">COLLECTIONS</span>
    </div>

    <button class="new-collection-btn" @click="$emit('create')">
      + New
    </button>

    <div class="collections-list">
      <CollectionCard
        v-for="collection in collections"
        :key="collection.id"
        :collection="collection"
        :selected="selectedId === collection.id"
        @select="$emit('select', collection.id)"
      />
    </div>
  </aside>
</template>

<script setup>
import CollectionCard from './CollectionCard.vue'

defineProps({
  collections: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: [String, Number],
    default: null
  }
})

defineEmits(['select', 'create'])
</script>

<style scoped>
.collections-sidebar {
  width: 200px;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-right: 1px solid var(--border);
  overflow: hidden;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid var(--border);
}

.sidebar-title {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--collection-text-muted);
  text-transform: uppercase;
}

.new-collection-btn {
  margin: 0.75rem;
  padding: 0.6rem 1rem;
  background: var(--collection-accent);
  color: var(--surface-2);
  border: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}

.new-collection-btn:hover {
  background: var(--collection-accent-hover);
}

.collections-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>

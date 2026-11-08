<template>
  <button
    class="collection-card"
    :class="{ selected }"
    @click="$emit('select')"
  >
    <div class="card-thumbnail">
      <img
        v-if="collection.preview_thumbnail"
        :src="collection.preview_thumbnail"
        alt=""
        loading="lazy"
      />
      <div v-else class="placeholder-icon">📁</div>
    </div>
    <div class="card-info">
      <span class="card-name">{{ collection.name }}</span>
      <span class="card-count">{{ collection.item_count }} {{ collection.item_count === 1 ? 'item' : 'items' }}</span>
    </div>
  </button>
</template>

<script setup>
defineProps({
  collection: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select'])
</script>

<style scoped>
.collection-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: none;
  border-radius: 8px;
  border-left: 3px solid transparent;
  cursor: pointer;
  text-align: left;
  color: var(--collection-text-primary);
  transition: all 0.2s ease;
}

.collection-card:hover {
  background: var(--collection-card-bg-hover);
  transform: translateY(-2px);
}

.collection-card.selected {
  border-left-color: var(--collection-accent);
  background: var(--collection-card-bg-selected);
}

.card-thumbnail {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--surface-3);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder-icon {
  font-size: 1.25rem;
  opacity: 0.5;
}

.card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.card-name {
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-count {
  font-size: 0.75rem;
  color: var(--collection-text-secondary);
}
</style>

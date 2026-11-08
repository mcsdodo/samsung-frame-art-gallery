<template>
  <div class="empty-collection">
    <div class="empty-illustration">
      <span class="folder-icon">📂</span>
    </div>
    <h2>This collection is empty</h2>
    <p>Go to Local or Met Museum tab and click '+ Collection' to add artwork here.</p>
    <button class="cta-btn" @click="$emit('go-to-local')">
      Go to Local Images
    </button>
  </div>
</template>

<script setup>
defineEmits(['go-to-local'])
</script>

<style scoped>
.empty-collection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  flex: 1;
}

.empty-illustration {
  margin-bottom: 1.5rem;
}

.folder-icon {
  font-size: 4rem;
  opacity: 0.5;
}

h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: var(--collection-text-primary);
}

p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
  max-width: 280px;
  line-height: 1.5;
}

.cta-btn {
  padding: 0.6rem 1.25rem;
  background: var(--surface-hover);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: var(--surface-hover);
}
</style>

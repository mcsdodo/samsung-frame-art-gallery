<template>
  <div class="empty-collections">
    <div class="empty-illustration">
      <span class="icon">🖼️</span>
      <span class="arrow">→</span>
      <span class="icon">📁</span>
      <span class="arrow">→</span>
      <span class="icon">📺</span>
    </div>
    <h2>Curate your favorite artwork</h2>
    <p>Collect images from Local or Met Museum, then upload them to your TV in one go.</p>
    <button class="cta-btn" @click="$emit('create')">
      + Create First Collection
    </button>
  </div>
</template>

<script setup>
defineEmits(['create'])
</script>

<style scoped>
.empty-collections {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  flex: 1;
}

.empty-illustration {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
  font-size: 2rem;
}

.arrow {
  color: var(--collection-accent);
  font-size: 1.5rem;
}

h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: var(--collection-text-primary);
}

p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
  max-width: 300px;
  line-height: 1.5;
}

.cta-btn {
  padding: 0.75rem 1.5rem;
  background: var(--collection-accent);
  color: var(--surface-2);
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.cta-btn:hover {
  background: var(--collection-accent-hover);
}
</style>

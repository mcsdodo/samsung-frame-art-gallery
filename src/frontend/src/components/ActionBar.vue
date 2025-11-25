<template>
  <div class="action-bar">
    <slot name="left"></slot>
    <div class="actions">
      <slot></slot>
    </div>
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #1a1a2e;
  border-top: 1px solid #2a2a4e;
  gap: 1rem;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

:deep(button) {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

:deep(button:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

:deep(button.primary) {
  background: #4a90d9;
  color: white;
}

:deep(button.secondary) {
  background: #3a3a5e;
  color: white;
}

:deep(button.danger) {
  background: #d94a4a;
  color: white;
}
</style>

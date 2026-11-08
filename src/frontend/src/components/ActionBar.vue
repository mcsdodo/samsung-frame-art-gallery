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
  min-height: var(--actionbar-h);
  padding: 12px 16px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  gap: 12px;
  flex-wrap: wrap;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

:deep(button) {
  height: 36px;
  padding: 0 16px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 550;
  font-size: 0.875rem;
  transition: background 0.15s, opacity 0.15s, border-color 0.15s;
}

:deep(button:disabled) {
  opacity: 0.4;
  cursor: not-allowed;
}

:deep(button.primary) {
  background: var(--accent);
  color: #fff;
}
:deep(button.primary:hover:not(:disabled)) { background: var(--accent-hover); }

:deep(button.secondary) {
  background: var(--surface-3);
  border-color: var(--border-strong);
  color: var(--text);
}
:deep(button.secondary:hover:not(:disabled)) { background: var(--surface-hover); }

:deep(button.danger) {
  background: transparent;
  border-color: rgba(229, 72, 77, 0.45);
  color: var(--danger-text);
}
:deep(button.danger:hover:not(:disabled)) { background: var(--danger-soft); }
</style>

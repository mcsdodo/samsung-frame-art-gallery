<template>
  <div class="bottom-sheet-container">
    <!-- Collapsed bar -->
    <button class="collection-bar" @click="isExpanded = true">
      <span class="bar-label">
        {{ selectedCollection ? selectedCollection.name : 'Select Collection' }}
      </span>
      <span class="bar-icon">▲</span>
    </button>

    <!-- Expanded sheet -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="isExpanded" class="sheet-overlay" @click.self="isExpanded = false">
          <div class="sheet-content">
            <div class="sheet-handle" @click="isExpanded = false">
              <div class="handle-bar"></div>
            </div>

            <h3 class="sheet-title">Your Collections</h3>

            <div class="sheet-list">
              <button
                v-for="collection in collections"
                :key="collection.id"
                class="sheet-item"
                :class="{ selected: selectedId === collection.id }"
                @click="selectAndClose(collection.id)"
                @contextmenu.prevent="showContextMenu($event, collection)"
              >
                <div class="item-thumbnail">
                  <img
                    v-if="collection.preview_thumbnail"
                    :src="collection.preview_thumbnail"
                    alt=""
                  />
                  <span v-else>📁</span>
                </div>
                <div class="item-info">
                  <span class="item-name">{{ collection.name }}</span>
                  <span class="item-count">{{ collection.item_count }} items</span>
                </div>
                <span v-if="selectedId === collection.id" class="item-check">✓</span>
              </button>
            </div>

            <button class="create-btn" @click="$emit('create'); isExpanded = false">
              + Create New Collection
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu.show"
        class="context-menu"
        :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      >
        <button @click="handleRename">Rename</button>
        <button class="danger" @click="handleDelete">Delete</button>
      </div>
      <div v-if="contextMenu.show" class="context-backdrop" @click="contextMenu.show = false"></div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const props = defineProps({
  collections: {
    type: Array,
    default: () => []
  },
  selectedId: {
    type: [String, Number],
    default: null
  },
  selectedCollection: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select', 'create', 'rename', 'delete'])

const isExpanded = ref(false)
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  collection: null
})

const selectAndClose = (id) => {
  emit('select', id)
  isExpanded.value = false
}

const showContextMenu = (event, collection) => {
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.collection = collection
  contextMenu.show = true
}

const handleRename = () => {
  emit('rename', contextMenu.collection)
  contextMenu.show = false
}

const handleDelete = () => {
  emit('delete', contextMenu.collection)
  contextMenu.show = false
}
</script>

<style scoped>
.bottom-sheet-container {
  /* Container for collapsed bar */
}

.collection-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--surface-2);
  border: none;
  border-bottom: 1px solid var(--border);
  color: white;
  cursor: pointer;
}

.bar-label {
  font-weight: 500;
}

.bar-icon {
  font-size: 0.75rem;
  color: var(--collection-accent);
}

/* Sheet overlay and content */
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.sheet-content {
  width: 100%;
  max-height: 70vh;
  background: var(--surface-2);
  border-radius: 16px 16px 0 0;
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
}

.sheet-handle {
  padding: 0.75rem 0;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.handle-bar {
  width: 40px;
  height: 4px;
  background: var(--surface-hover);
  border-radius: 2px;
}

.sheet-title {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: var(--collection-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.sheet-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.sheet-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  text-align: left;
}

.sheet-item.selected {
  background: var(--collection-card-bg-selected);
  border-left: 3px solid var(--collection-accent);
}

.item-thumbnail {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: var(--surface-3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.item-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.item-name {
  font-weight: 500;
}

.item-count {
  font-size: 0.85rem;
  color: var(--collection-text-secondary);
}

.item-check {
  color: var(--collection-accent);
  font-weight: bold;
}

.create-btn {
  width: 100%;
  padding: 0.75rem;
  background: var(--collection-accent);
  color: var(--surface-2);
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

/* Context menu */
.context-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1001;
}

.context-menu {
  position: fixed;
  z-index: 1002;
  background: var(--surface-3);
  border-radius: 8px;
  padding: 0.5rem 0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.context-menu button {
  display: block;
  width: 100%;
  padding: 0.75rem 1.25rem;
  background: none;
  border: none;
  color: white;
  text-align: left;
  cursor: pointer;
}

.context-menu button:hover {
  background: var(--surface-hover);
}

.context-menu button.danger {
  color: var(--danger);
}

/* Transitions */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.3s ease;
}

.sheet-enter-active .sheet-content,
.sheet-leave-active .sheet-content {
  transition: transform 0.3s ease;
}

.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}

.sheet-enter-from .sheet-content,
.sheet-leave-to .sheet-content {
  transform: translateY(100%);
}
</style>

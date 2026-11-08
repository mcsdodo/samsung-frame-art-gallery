<!-- Docked, non-blocking upload progress: collapses to a pill, retries failures, never covers the page. -->
<template>
  <Transition name="dock">
    <section v-if="items.length" class="dock" :class="{ collapsed }" aria-live="polite" aria-label="Uploads">
      <header class="dock-head" @click="collapsed = !collapsed">
        <svg class="ring" viewBox="0 0 36 36" aria-hidden="true">
          <circle cx="18" cy="18" r="15" class="ring-track" />
          <circle cx="18" cy="18" r="15" class="ring-fill" :class="ringTone"
                  :style="{ strokeDashoffset: 94.25 * (1 - percent / 100) }" />
          <text v-if="!busy" x="18" y="22.5" text-anchor="middle" class="ring-icon">{{ c.failed ? '!' : '✓' }}</text>
        </svg>
        <div class="dock-title">
          <strong>{{ title }}</strong>
          <span>{{ subtitle }}</span>
        </div>
        <button class="icon-btn" :aria-label="collapsed ? 'Expand' : 'Collapse'" @click.stop="collapsed = !collapsed">
          <svg viewBox="0 0 20 20" :class="{ flip: !collapsed }"><path d="M5 12.5 10 7.5l5 5" /></svg>
        </button>
        <button v-if="!busy" class="icon-btn" aria-label="Dismiss" @click.stop="clearFinished">
          <svg viewBox="0 0 20 20"><path d="M6 6l8 8M14 6l-8 8" /></svg>
        </button>
      </header>

      <div v-show="!collapsed" class="dock-body">
        <ul class="dock-list">
          <li v-for="item in items" :key="item.id" :class="item.status">
            <img v-if="item.thumb" :src="item.thumb" alt="" loading="lazy" />
            <span v-else class="thumb-ph"></span>
            <div class="row-text">
              <span class="row-name" :title="item.name">{{ item.name }}</span>
              <span class="row-status" :title="item.error">{{ statusText(item) }}</span>
            </div>
            <span v-if="item.status === 'uploading' || item.status === 'retrying'" class="spinner" aria-hidden="true"></span>
            <button v-else-if="item.status === 'failed'" class="chip-btn" @click="retry(item.id)">Retry</button>
            <button v-else-if="item.status === 'pending'" class="icon-btn small" aria-label="Remove from queue" @click="remove(item.id)">
              <svg viewBox="0 0 20 20"><path d="M6 6l8 8M14 6l-8 8" /></svg>
            </button>
            <svg v-else class="done-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 10.5l3.2 3L15 6.5" /></svg>
          </li>
        </ul>
        <footer class="dock-foot">
          <button v-if="c.failed" class="btn btn-secondary btn-sm" @click="retry()">Retry failed ({{ c.failed }})</button>
          <button v-if="c.pending" class="btn btn-ghost btn-sm" @click="cancelPending">Cancel queued</button>
          <button v-if="!busy" class="btn btn-ghost btn-sm" @click="clearFinished">Clear</button>
        </footer>
      </div>
    </section>
  </Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { uploadQueue, retry, remove, cancelPending, clearFinished, MAX_TRIES } from '../stores/uploadQueue.js'

const collapsed = ref(false)
const items = computed(() => uploadQueue.state.items)
const c = uploadQueue.counts
const busy = computed(() => c.value.pending + c.value.active > 0)
const percent = computed(() => {
  const total = c.value.total
  return total ? Math.round(((c.value.done + c.value.failed) / total) * 100) : 0
})
const ringTone = computed(() => (!busy.value && c.value.failed ? 'warn' : !busy.value ? 'ok' : ''))
const title = computed(() => {
  if (busy.value) return `Uploading ${Math.min(c.value.done + c.value.failed + 1, c.value.total)} of ${c.value.total}`
  return c.value.failed ? `${c.value.failed} upload${c.value.failed > 1 ? 's' : ''} failed` : 'Uploads complete'
})
const subtitle = computed(() => {
  const parts = [`${c.value.done} done`]
  if (c.value.failed) parts.push(`${c.value.failed} failed`)
  if (c.value.pending) parts.push(`${c.value.pending} queued`)
  return parts.join(' · ')
})
const statusText = (item) => ({
  pending: 'Queued',
  uploading: item.attempt > 1 ? `Uploading, try ${item.attempt} of ${MAX_TRIES}…` : 'Uploading…',
  retrying: `${item.error} · retrying shortly`,
  done: 'On TV',
  failed: item.error || 'Failed'
})[item.status]
</script>

<style scoped>
.dock {
  position: fixed;
  right: 16px;
  bottom: calc(var(--actionbar-h) + 16px);
  width: min(360px, calc(100vw - 32px));
  max-height: min(60vh, 520px);
  display: flex;
  flex-direction: column;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 900;
  overflow: hidden;
}

.dock-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 12px 12px 14px;
  cursor: pointer;
  user-select: none;
}

.ring {
  width: 34px;
  height: 34px;
  flex: none;
  transform: rotate(-90deg);
}
.ring-track { fill: none; stroke: var(--surface-3); stroke-width: 3.5; }
.ring-fill {
  fill: none;
  stroke: var(--accent);
  stroke-width: 3.5;
  stroke-linecap: round;
  stroke-dasharray: 94.25;
  transition: stroke-dashoffset 0.4s ease;
}
.ring-fill.ok { stroke: var(--success); }
.ring-fill.warn { stroke: var(--warning); }
.ring-icon {
  transform: rotate(90deg);
  transform-origin: 18px 18px;
  fill: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.dock-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.dock-title strong { font-size: 0.9rem; font-weight: 600; }
.dock-title span { font-size: 0.78rem; color: var(--text-muted); }

.icon-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex: none;
}
.icon-btn:hover { background: var(--surface-3); color: var(--text); }
.icon-btn.small { width: 26px; height: 26px; }
.icon-btn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; transition: transform 0.2s; }
.icon-btn svg.flip { transform: rotate(180deg); }

.dock-body {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--border);
}

.dock-list {
  list-style: none;
  margin: 0;
  padding: 6px;
  overflow-y: auto;
}

.dock-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
}
.dock-list li:hover { background: var(--surface-3); }

.dock-list img,
.thumb-ph {
  width: 44px;
  height: 28px;
  object-fit: cover;
  border-radius: 4px;
  flex: none;
  background: var(--surface-3);
}

.row-text { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.row-name { font-size: 0.82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row-status { font-size: 0.72rem; color: var(--text-faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
li.uploading .row-status, li.retrying .row-status { color: var(--accent-text); }
li.done .row-status { color: var(--success); }
li.failed .row-status { color: var(--danger); }
li.pending { opacity: 0.7; }

.done-icon { width: 18px; height: 18px; fill: none; stroke: var(--success); stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; flex: none; }

.chip-btn {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: var(--text);
  font-size: 0.75rem;
  cursor: pointer;
  flex: none;
}
.chip-btn:hover { border-color: var(--accent); }

.spinner {
  width: 16px;
  height: 16px;
  flex: none;
  border: 2px solid var(--surface-3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.dock-foot {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
}
.dock-foot:empty { display: none; }

.dock-enter-active, .dock-leave-active { transition: opacity 0.2s, transform 0.2s; }
.dock-enter-from, .dock-leave-to { opacity: 0; transform: translateY(12px); }

@media (max-width: 767px) {
  .dock { right: 16px; left: 16px; width: auto; }
}
</style>

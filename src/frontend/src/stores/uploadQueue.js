// Background upload queue shared by every tab: one image per request, automatic retry, and
// state for the docked progress widget. Panels enqueue and carry on; nothing blocks the UI.
import { reactive, computed } from 'vue'

const AUTO_RETRIES = 2                 // extra attempts before an item is marked failed
export const MAX_TRIES = AUTO_RETRIES + 1
const RETRY_DELAYS_MS = [3000, 8000]   // the TV often recovers from a timeout within seconds
const PERMANENT = /not found|access denied|no tv configured/i

const state = reactive({ items: [], running: false })
let nextId = 1

/**
 * jobs: [{ name, thumb?, endpoint, body }] — body is the JSON for a single image.
 * display: show the last job of this batch on the TV once it is uploaded.
 */
export function enqueue(jobs, { display = false } = {}) {
  jobs.forEach((job, i) => {
    state.items.push({
      id: nextId++,
      name: job.name,
      thumb: job.thumb || null,
      endpoint: job.endpoint,
      body: { ...job.body, display: display && i === jobs.length - 1 },
      status: 'pending', // pending | uploading | retrying (waiting to retry) | done | failed
      attempt: 0,        // tries made so far, including the one in flight
      error: ''
    })
  })
  run()
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

async function uploadOnce(item) {
  try {
    const res = await fetch(item.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item.body)
    })
    const data = await res.json().catch(() => ({}))
    const result = data.results?.[0]
    if (res.ok && result?.success) return null
    return result?.error || data.detail || `HTTP ${res.status}`
  } catch (e) {
    return e.message || 'Network error'
  }
}

async function run() {
  if (state.running) return
  state.running = true
  let uploaded = 0
  try {
    let item
    while ((item = state.items.find(i => i.status === 'pending'))) {
      item.status = 'uploading'
      item.error = ''
      for (;;) {
        item.attempt++
        const error = await uploadOnce(item)
        if (!error) {
          item.status = 'done'
          uploaded++
          break
        }
        item.error = error
        const retryNo = item.attempt - 1
        if (retryNo >= AUTO_RETRIES || PERMANENT.test(error)) {
          item.status = 'failed'
          break
        }
        item.status = 'retrying'
        await sleep(RETRY_DELAYS_MS[retryNo])
        item.status = 'uploading'
      }
    }
  } finally {
    state.running = false
    if (uploaded) window.dispatchEvent(new Event('tv-uploads-finished'))
  }
}

export function retry(id) {
  state.items.filter(i => i.status === 'failed' && (id == null || i.id === id))
    .forEach(i => { i.status = 'pending'; i.attempt = 0; i.error = '' })
  run()
}

/** Drop everything not yet started; the image currently uploading finishes. */
export function cancelPending() {
  state.items = state.items.filter(i => i.status !== 'pending')
}

export function remove(id) {
  state.items = state.items.filter(i => i.id !== id || ['uploading', 'retrying'].includes(i.status))
}

export function clearFinished() {
  state.items = state.items.filter(i => !['done', 'failed'].includes(i.status))
}

export const uploadQueue = {
  state,
  counts: computed(() => {
    const c = { pending: 0, active: 0, done: 0, failed: 0, total: state.items.length }
    for (const i of state.items) {
      if (i.status === 'pending') c.pending++
      else if (i.status === 'done') c.done++
      else if (i.status === 'failed') c.failed++
      else c.active++
    }
    return c
  })
}

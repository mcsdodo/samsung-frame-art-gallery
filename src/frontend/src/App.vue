<template>
  <div class="app">
    <header class="header">
      <h1>Samsung Frame Art Gallery</h1>
      <div class="status" :class="{ connected: tvStatus.connected }">
        <span class="status-dot"></span>
        {{ tvStatus.connected ? 'TV Connected' : 'TV Disconnected' }}
      </div>
    </header>
    <main class="main">
      <p>Loading...</p>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const tvStatus = ref({ connected: false })

onMounted(async () => {
  try {
    const res = await fetch('/api/tv/status')
    tvStatus.value = await res.json()
  } catch (e) {
    console.error('Failed to get TV status:', e)
  }
})
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1a1a2e;
  color: white;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff4444;
}

.status.connected .status-dot {
  background: #44ff44;
}

.main {
  padding: 1rem;
}
</style>

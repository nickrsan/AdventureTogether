<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'

interface EventItem {
  id: number
  title: string
  slug: string
  description: string
  hashtag: string
  start_time: string
  end_time: string
  is_active: boolean
}

const events = ref<EventItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const fetchEvents = async () => {
  try {
    loading.value = true
    const res = await fetch('/api/events/')
    if (res.ok) {
      const data = await res.json()
      events.value = data.results || data
    } else {
      // Fallback empty list
      events.value = []
    }
  } catch (err: any) {
    error.value = 'Failed to load scavenger hunt events.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchEvents()
})
</script>

<template>
  <div class="home-container">
    <section class="hero-section">
      <h1 class="hero-title">AdventureTogether</h1>
      <p class="hero-subtitle">
        Collaborative open data scavenger hunts. Map OpenStreetMap amenities, submit photos to Wikimedia Commons,
        and link entities in Wikidata with your team.
      </p>
    </section>

    <section class="events-section">
      <div class="section-header">
        <h2 class="section-title">Active & Upcoming Hunts</h2>
      </div>

      <div v-if="loading" class="status-msg">Loading events...</div>
      <div v-else-if="error" class="status-msg error-msg">{{ error }}</div>
      <div v-else-if="events.length === 0" class="card empty-card">
        <h3>No active hunts right now</h3>
        <p>Stay tuned or host your own scavenger hunt event!</p>
      </div>

      <div v-else class="events-grid">
        <div v-for="event in events" :key="event.id" class="card event-card">
          <div class="event-card-header">
            <h3 class="event-card-title">{{ event.title }}</h3>
            <span class="badge badge-primary">#{{ event.hashtag }}</span>
          </div>
          <p class="event-description">{{ event.description }}</p>
          <div class="event-actions">
            <RouterLink :to="`/events/${event.id}/map`" class="btn btn-primary">
              View Map
            </RouterLink>
            <RouterLink :to="`/events/${event.id}/join`" class="btn btn-outline">
              Join Team
            </RouterLink>
            <RouterLink :to="`/events/${event.id}/host/builder`" class="btn btn-secondary">
              Host Builder
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-container {
  max-width: var(--max-content-width);
  margin: 0 auto;
  padding: var(--space-8) var(--space-4);
  width: 100%;
}

.hero-section {
  text-align: center;
  margin-bottom: var(--space-10);
}

.hero-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin-bottom: var(--space-2);
}

.hero-subtitle {
  font-size: var(--font-size-lg);
  color: var(--color-text-muted);
  max-width: 700px;
  margin: 0 auto;
}

.section-header {
  margin-bottom: var(--space-6);
}

.section-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
}

.events-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
}

.event-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.event-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-2);
}

.event-card-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.event-description {
  color: var(--color-text-muted);
  margin-bottom: var(--space-4);
  flex-grow: 1;
}

.event-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.empty-card {
  text-align: center;
  padding: var(--space-10);
  color: var(--color-text-muted);
}

.status-msg {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-text-muted);
}

.error-msg {
  color: var(--color-danger);
}
</style>

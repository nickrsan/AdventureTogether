<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import L from 'leaflet'
import { api, type EventData, type QuestData } from '../api'

const route = useRoute()
const eventId = route.params.id as string

const event = ref<EventData | null>(null)
const quests = ref<QuestData[]>([])

// Quest Form State
const questTitle = ref('')
const questDescription = ref('')
const criteriaType = ref<'osm_tags' | 'wikimedia_commons' | 'wikidata_entry'>('osm_tags')
const pointsReward = ref(10)

// Criteria builders
const osmAmenity = ref('restaurant')
const osmRequiredKey = ref('opening_hours')
const wikiCategory = ref('')
const wikidataProperty = ref('P18')

const targetCoords = ref<{ lat: number; lng: number } | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const successMsg = ref<string | null>(null)

let map: L.Map | null = null
let perimeterLayer: L.GeoJSON | null = null
let currentMarker: L.Marker | null = null
let questsLayerGroup: L.LayerGroup | null = null

const initMap = async () => {
  const mapElement = document.getElementById('builder-map')
  if (!mapElement) return

  map = L.map('builder-map').setView([37.7749, -122.4194], 14)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map)

  questsLayerGroup = L.layerGroup().addTo(map)

  // Map click handler to set quest point target
  map.on('click', (e: L.LeafletMouseEvent) => {
    targetCoords.value = { lat: e.latlng.lat, lng: e.latlng.lng }
    if (currentMarker) {
      currentMarker.setLatLng(e.latlng)
    } else if (map) {
      currentMarker = L.marker(e.latlng, {
        draggable: true,
        title: 'New Quest Target'
      }).addTo(map)

      currentMarker.on('dragend', () => {
        const pos = currentMarker?.getLatLng()
        if (pos) targetCoords.value = { lat: pos.lat, lng: pos.lng }
      })
    }
  })

  // Load Event and existing quests
  await loadEventData()
}

const loadEventData = async () => {
  try {
    event.value = await api.getEvent(eventId)
    quests.value = await api.getQuests(eventId)

    // Render Event Bounding Polygon
    if (event.value && event.value.bounding_polygon && map) {
      if (perimeterLayer) map.removeLayer(perimeterLayer)

      perimeterLayer = L.geoJSON(event.value.bounding_polygon, {
        style: {
          color: '#2563eb',
          weight: 3,
          dashArray: '6, 6',
          fillColor: '#3b82f6',
          fillOpacity: 0.1
        }
      }).addTo(map)

      map.fitBounds(perimeterLayer.getBounds(), { padding: [30, 30] })
    }

    renderExistingQuests()
  } catch (err: any) {
    error.value = 'Failed to load event boundary.'
  }
}

const renderExistingQuests = () => {
  if (!map || !questsLayerGroup) return
  questsLayerGroup.clearLayers()

  quests.value.forEach(q => {
    if (q.target_geometry && q.target_geometry.type === 'Point') {
      const [lng, lat] = q.target_geometry.coordinates
      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: '#16a34a',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 0.8
      }).bindPopup(`<b>${q.title}</b><br/>${q.description}<br/>Reward: ${q.points_reward} pts`)
      questsLayerGroup?.addLayer(marker)
    }
  })
}

const handleSaveQuest = async () => {
  if (!questTitle.value.trim()) {
    error.value = 'Quest title is required.'
    return
  }
  if (!questDescription.value.trim()) {
    error.value = 'Quest description is required.'
    return
  }

  // Construct validation rules payload
  let validationRules: Record<string, any> = {}
  if (criteriaType.value === 'osm_tags') {
    validationRules = {
      required_tags: {
        [osmAmenity.value.trim() ? 'amenity' : '']: osmAmenity.value.trim(),
        [osmRequiredKey.value.trim()]: '*'
      }
    }
    delete validationRules.required_tags['']
  } else if (criteriaType.value === 'wikimedia_commons') {
    validationRules = { category: wikiCategory.value.trim() }
  } else if (criteriaType.value === 'wikidata_entry') {
    validationRules = { property: wikidataProperty.value.trim() }
  }

  // Target geometry GeoJSON Point if selected
  const targetGeometry = targetCoords.value
    ? {
        type: 'Point',
        coordinates: [targetCoords.value.lng, targetCoords.value.lat]
      }
    : null

  try {
    loading.value = true
    error.value = null

    const created = await api.createQuest({
      event: Number(eventId),
      title: questTitle.value.trim(),
      description: questDescription.value.trim(),
      criteria_type: criteriaType.value,
      validation_rules: validationRules,
      target_geometry: targetGeometry,
      points_reward: pointsReward.value
    })

    successMsg.value = `Quest "${created.title}" added successfully!`
    quests.value.push(created)
    renderExistingQuests()

    // Reset form
    questTitle.value = ''
    questDescription.value = ''
    if (currentMarker && map) {
      map.removeLayer(currentMarker)
      currentMarker = null
    }
    targetCoords.value = null
  } catch (err: any) {
    error.value = err.message || 'Failed to create quest.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initMap()
})
</script>

<template>
  <div class="host-builder-view">
    <div class="builder-sidebar card">
      <h2 class="sidebar-title">Quest Builder</h2>
      <p v-if="event" class="sidebar-subtitle">{{ event.title }} (#{{ event.hashtag }})</p>

      <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
      <div v-if="error" class="alert alert-danger">{{ error }}</div>

      <div class="form-group">
        <label class="form-label" for="questTitle">Quest Title</label>
        <input
          id="questTitle"
          v-model="questTitle"
          type="text"
          class="form-input"
          placeholder="e.g. Map Restaurant Opening Hours"
        />
      </div>

      <div class="form-group">
        <label class="form-label" for="questDesc">Description & Instructions</label>
        <textarea
          id="questDesc"
          v-model="questDescription"
          rows="2"
          class="form-textarea"
          placeholder="e.g. Verify and add opening hours to restaurants."
        ></textarea>
      </div>

      <div class="form-group">
        <label class="form-label" for="criteriaType">Verification Criteria</label>
        <select id="criteriaType" v-model="criteriaType" class="form-select">
          <option value="osm_tags">OpenStreetMap Tag Rule</option>
          <option value="wikimedia_commons">Wikimedia Commons Photo</option>
          <option value="wikidata_entry">Wikidata Entry</option>
        </select>
      </div>

      <!-- OSM Criteria Inputs -->
      <div v-if="criteriaType === 'osm_tags'" class="criteria-box">
        <div class="form-group">
          <label class="form-label">Target Feature (amenity=)</label>
          <input v-model="osmAmenity" type="text" class="form-input" placeholder="restaurant, cafe, bench" />
        </div>
        <div class="form-group">
          <label class="form-label">Required Tag Key</label>
          <input v-model="osmRequiredKey" type="text" class="form-input" placeholder="opening_hours, wheelchair, etc." />
        </div>
      </div>

      <!-- Wikimedia Criteria Inputs -->
      <div v-if="criteriaType === 'wikimedia_commons'" class="criteria-box">
        <div class="form-group">
          <label class="form-label">Wikimedia Category</label>
          <input v-model="wikiCategory" type="text" class="form-input" placeholder="e.g. Murals in San Francisco" />
        </div>
      </div>

      <!-- Wikidata Criteria Inputs -->
      <div v-if="criteriaType === 'wikidata_entry'" class="criteria-box">
        <div class="form-group">
          <label class="form-label">Target Wikidata Property</label>
          <input v-model="wikidataProperty" type="text" class="form-input" placeholder="P18 (image), P625, etc." />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Points Reward</label>
        <input v-model.number="pointsReward" type="number" min="1" class="form-input" />
      </div>

      <div class="target-location-hint">
        <p class="hint-text">
          📍 <strong>Target Location:</strong>
          <span v-if="targetCoords">{{ targetCoords.lat.toFixed(4) }}, {{ targetCoords.lng.toFixed(4) }}</span>
          <span v-else>Click map to pin a quest point (optional)</span>
        </p>
      </div>

      <button class="btn btn-primary btn-block" :disabled="loading" @click="handleSaveQuest">
        {{ loading ? 'Saving...' : 'Add Quest Challenge' }}
      </button>

      <div class="existing-quests-section">
        <h3>Existing Quests ({{ quests.length }})</h3>
        <ul class="quests-list">
          <li v-for="q in quests" :key="q.id" class="quest-item">
            <strong>{{ q.title }}</strong>
            <span class="badge badge-primary">{{ q.criteria_type }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="builder-map-container">
      <div id="builder-map" class="map-viewport"></div>
    </div>
  </div>
</template>

<style scoped>
.host-builder-view {
  display: flex;
  height: calc(100vh - var(--header-height));
  gap: var(--space-4);
  padding: var(--space-4);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.builder-sidebar {
  width: 420px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-1);
}

.sidebar-subtitle {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-4);
}

.criteria-box {
  background-color: var(--color-bg-subtle);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
}

.target-location-hint {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary-border);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
  font-size: var(--font-size-xs);
}

.btn-block {
  width: 100%;
}

.builder-map-container {
  flex: 1;
  height: 100%;
}

.existing-quests-section {
  margin-top: var(--space-6);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-4);
}

.quests-list {
  list-style: none;
  margin-top: var(--space-2);
}

.quest-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-sm);
}

.alert {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
  font-size: var(--font-size-xs);
}

.alert-success {
  background-color: var(--color-success-light);
  color: var(--color-success);
  border: 1px solid var(--color-success-border);
}

.alert-danger {
  background-color: var(--color-danger-light);
  color: var(--color-danger);
  border: 1px solid var(--color-danger-border);
}
</style>

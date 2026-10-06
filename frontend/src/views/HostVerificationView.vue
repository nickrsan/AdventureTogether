<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api, type SubmissionData, type EventData } from '../api'

const route = useRoute()
const eventId = route.params.id as string

const event = ref<EventData | null>(null)
const submissions = ref<SubmissionData[]>([])
const loading = ref(false)
const harvesting = ref(false)
const error = ref<string | null>(null)
const notification = ref<string | null>(null)

// Filter state
const filterStatus = ref<'all' | 'pending' | 'verified'>('all')
const filterPlatform = ref<string>('all')

const loadSubmissions = async () => {
  try {
    loading.value = true
    event.value = await api.getEvent(eventId)
    submissions.value = await api.getSubmissions(eventId)
  } catch (err: any) {
    error.value = 'Failed to load submissions for this event.'
  } finally {
    loading.value = false
  }
}

const filteredSubmissions = computed(() => {
  return submissions.value.filter((s) => {
    if (filterStatus.value === 'pending' && s.is_verified) return false
    if (filterStatus.value === 'verified' && !s.is_verified) return false
    if (filterPlatform.value !== 'all' && s.platform !== filterPlatform.value) return false
    return true
  })
})

const handleVerifyToggle = async (submission: SubmissionData) => {
  const newVerifiedState = !submission.is_verified
  try {
    const updated = await api.verifySubmission(submission.id, 'Host')
    submission.is_verified = updated.is_verified
    submission.verified_by_username = updated.verified_by_username
    submission.verified_at = updated.verified_at

    notification.value = updated.is_verified
      ? `Submission #${submission.external_id} marked as verified!`
      : `Submission #${submission.external_id} marked as pending.`

    setTimeout(() => {
      notification.value = null
    }, 3000)
  } catch (err: any) {
    error.value = 'Failed to update verification status.'
  }
}

const handleTriggerHarvest = async () => {
  try {
    harvesting.value = true
    const res = await fetch('/api/submissions/trigger_harvest/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event: eventId })
    })
    if (res.ok) {
      notification.value = 'Harvesting cycle complete! Staged new submissions.'
      await loadSubmissions()
    } else {
      error.value = 'Harvest cycle encountered an issue.'
    }
  } catch (err) {
    error.value = 'Could not trigger harvest.'
  } finally {
    harvesting.value = false
  }
}

const getPlatformIcon = (platform: string) => {
  if (platform === 'osm') return '🗺️ OSM'
  if (platform === 'commons') return '📸 Commons'
  if (platform === 'wikidata') return '📊 Wikidata'
  return platform
}

onMounted(() => {
  loadSubmissions()
})
</script>

<template>
  <div class="host-verification-view">
    <header class="verification-header">
      <div class="header-left">
        <h2 class="page-title">Host Verification Portal</h2>
        <p v-if="event" class="page-subtitle">{{ event.title }} (#{{ event.hashtag }})</p>
      </div>

      <div class="header-actions">
        <button
          class="btn btn-secondary"
          :disabled="harvesting"
          @click="handleTriggerHarvest"
        >
          {{ harvesting ? 'Harvesting...' : '🔄 Poll External APIs Now' }}
        </button>
      </div>
    </header>

    <div v-if="notification" class="alert alert-success">{{ notification }}</div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <!-- Filter Bar -->
    <div class="card filter-bar">
      <div class="filter-group">
        <label class="filter-label">Verification Status:</label>
        <select v-model="filterStatus" class="form-select filter-select">
          <option value="all">All Submissions</option>
          <option value="pending">Pending Only</option>
          <option value="verified">Verified Only</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">Source Platform:</label>
        <select v-model="filterPlatform" class="form-select filter-select">
          <option value="all">All Platforms</option>
          <option value="osm">OpenStreetMap</option>
          <option value="commons">Wikimedia Commons</option>
          <option value="wikidata">Wikidata</option>
        </select>
      </div>

      <div class="filter-stats">
        <span>Showing <strong>{{ filteredSubmissions.length }}</strong> of {{ submissions.length }}</span>
      </div>
    </div>

    <!-- Submissions Table -->
    <div class="card table-card">
      <div v-if="loading" class="status-box">Loading harvested submissions...</div>
      <div v-else-if="filteredSubmissions.length === 0" class="empty-state">
        <p>No submissions found matching criteria.</p>
      </div>

      <table v-else class="submissions-table">
        <thead>
          <tr>
            <th style="width: 120px;">Platform</th>
            <th>ID / Changeset</th>
            <th>Contributor</th>
            <th>Matched Quest</th>
            <th>Assigned Team</th>
            <th>Diff Preview</th>
            <th style="width: 140px; text-align: center;">Verified</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="sub in filteredSubmissions" :key="sub.id" :class="{ 'row-verified': sub.is_verified }">
            <td>
              <span class="badge badge-primary">{{ getPlatformIcon(sub.platform) }}</span>
            </td>
            <td>
              <a :href="sub.external_url" target="_blank" class="external-link">
                #{{ sub.external_id }} ↗
              </a>
            </td>
            <td>
              <strong>{{ sub.author_username }}</strong>
            </td>
            <td>
              <span v-if="sub.quest_title" class="badge badge-success">{{ sub.quest_title }}</span>
              <span v-else class="text-muted">Uncategorized</span>
            </td>
            <td>
              <span v-if="sub.team_name" class="team-badge">{{ sub.team_name }}</span>
              <span v-else class="text-muted">Individual</span>
            </td>
            <td>
              <div class="diff-preview">
                <template v-if="sub.diff_payload && sub.diff_payload.modified_tags_list">
                  <div
                    v-for="(tags, idx) in sub.diff_payload.modified_tags_list.slice(0, 2)"
                    :key="idx"
                    class="tag-pill-container"
                  >
                    <span v-for="(v, k) in tags" :key="k" class="tag-pill">
                      <code>{{ k }}={{ v }}</code>
                    </span>
                  </div>
                </template>
                <template v-else-if="sub.diff_payload && sub.diff_payload.title">
                  <span class="media-preview">{{ sub.diff_payload.title }}</span>
                </template>
                <template v-else>
                  <code class="diff-json">{{ JSON.stringify(sub.diff_payload).substring(0, 60) }}...</code>
                </template>
              </div>
            </td>
            <td style="text-align: center;">
              <button
                :class="['btn', sub.is_verified ? 'btn-primary' : 'btn-outline']"
                @click="handleVerifyToggle(sub)"
              >
                {{ sub.is_verified ? '✓ Verified' : 'Verify' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.host-verification-view {
  max-width: var(--max-content-width);
  margin: 0 auto;
  padding: var(--space-8) var(--space-4);
  width: 100%;
}

.verification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-4);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

.page-subtitle {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.filter-bar {
  display: flex;
  gap: var(--space-6);
  align-items: center;
  margin-bottom: var(--space-6);
  padding: var(--space-4);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.filter-select {
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-sm);
  width: auto;
}

.filter-stats {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.table-card {
  overflow-x: auto;
  padding: var(--space-4);
}

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.submissions-table th {
  text-align: left;
  padding: var(--space-3);
  border-bottom: 2px solid var(--color-border);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-semibold);
}

.submissions-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.row-verified {
  background-color: var(--color-success-light);
}

.external-link {
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-mono);
}

.team-badge {
  background-color: var(--color-bg-subtle);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
}

.diff-preview {
  max-width: 300px;
}

.tag-pill-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
}

.tag-pill {
  background-color: var(--color-bg-subtle);
  border: 1px solid var(--color-border-strong);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
}

.diff-json {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.text-muted {
  color: var(--color-text-muted);
  font-style: italic;
}

.alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
  font-size: var(--font-size-sm);
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

.empty-state, .status-box {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-muted);
}
</style>

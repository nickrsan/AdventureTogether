/**
 * Composable for Privacy-Preserving Foreground Geolocation Sharing.
 * Strictly transmits coordinates while the application is active in the foreground.
 */

import { ref, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import { api } from '../api'

export type VisibilityTier = 'nobody' | 'team' | 'quest'

export function useGeolocation(eventId: number | string) {
  const coords = ref<{ lat: number; lng: number } | null>(null)
  const accuracy = ref<number | null>(null)
  const isForeground = ref<boolean>(document.visibilityState === 'visible')
  const visibility = ref<VisibilityTier>(
    (localStorage.getItem('privacy_visibility') as VisibilityTier) || 'team'
  )
  const isTracking = ref<boolean>(false)
  const error = ref<string | null>(null)
  const lastPingTime = ref<Date | null>(null)

  let watchId: number | null = null
  let heartbeatTimer: any = null

  const userIdentifier = localStorage.getItem('participant_id') || `user-${Math.random().toString(36).substring(2, 9)}`
  const displayName = localStorage.getItem('participant_name') || 'Anonymous Mapper'

  /**
   * Transmits a location ping to the backend API if foregrounded.
   */
  const sendPing = async () => {
    if (!coords.value || !isForeground.value || !isTracking.value) return

    try {
      await api.pingLocation({
        event: eventId,
        user_identifier: userIdentifier,
        display_name: displayName,
        longitude: coords.value.lng,
        latitude: coords.value.lat,
        visibility: visibility.value,
        is_foreground: isForeground.value
      })
      lastPingTime.value = new Date()
    } catch (err: any) {
      // Non-fatal ping error
    }
  }

  /**
   * Updates privacy visibility scope and persists preference.
   */
  const setVisibility = (tier: VisibilityTier) => {
    visibility.value = tier
    localStorage.setItem('privacy_visibility', tier)
    if (coords.value && isForeground.value) {
      sendPing()
    }
  }

  /**
   * Handles visibility changes (pauses transmission on backgrounding).
   */
  const handleVisibilityChange = () => {
    isForeground.value = document.visibilityState === 'visible'
    if (isForeground.value) {
      sendPing()
    }
  }

  /**
   * Starts geolocation watch and periodic heartbeat.
   */
  const startTracking = () => {
    if (!navigator.geolocation) {
      error.value = 'Geolocation is not supported by your browser.'
      return
    }

    isTracking.value = true
    error.value = null

    watchId = navigator.geolocation.watchPosition(
      (position) => {
        coords.value = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        }
        accuracy.value = position.coords.accuracy

        // Send initial ping upon acquiring coordinates
        if (isForeground.value) {
          sendPing()
        }
      },
      (err) => {
        error.value = `Geolocation error: ${err.message}`
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 5000
      }
    )

    // Heartbeat every 10 seconds while foregrounded
    heartbeatTimer = setInterval(() => {
      if (isForeground.value && isTracking.value) {
        sendPing()
      }
    }, 10000)
  }

  /**
   * Stops geolocation tracking and clears timer.
   */
  const stopTracking = () => {
    isTracking.value = false
    if (watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId)
      watchId = null
    }
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  if (getCurrentInstance()) {
    onMounted(() => {
      document.addEventListener('visibilitychange', handleVisibilityChange)
      startTracking()
    })

    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      stopTracking()
    })
  }

  return {
    coords,
    accuracy,
    isForeground,
    visibility,
    isTracking,
    error,
    lastPingTime,
    setVisibility,
    startTracking,
    stopTracking
  }
}

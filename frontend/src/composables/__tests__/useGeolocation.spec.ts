import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useGeolocation } from '../useGeolocation'

describe('useGeolocation Composable', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('initializes with default privacy visibility and foreground state', () => {
    const { visibility, isForeground, setVisibility } = useGeolocation(1)

    expect(visibility.value).toBe('team')
    expect(isForeground.value).toBe(true)

    // Update visibility to whole quest
    setVisibility('quest')
    expect(visibility.value).toBe('quest')
    expect(localStorage.getItem('privacy_visibility')).toBe('quest')
  })
})

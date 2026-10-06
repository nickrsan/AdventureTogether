/**
 * Composable for generating mobile deep links into external mapping tools
 * (StreetComplete and EveryDoor) centered on the participant's location.
 */

export interface DeepLinkTargets {
  streetCompleteUrl: string
  everyDoorUrl: string
  osmWebEditorUrl: string
  osmWebViewUrl: string
}

export function useDeepLinks() {
  /**
   * Generates custom scheme deep links centered on given coordinates.
   */
  const getDeepLinks = (lat: number, lng: number, zoom: number = 18): DeepLinkTargets => {
    const formattedLat = lat.toFixed(6)
    const formattedLng = lng.toFixed(6)

    return {
      // Direct deep link to StreetComplete survey quests
      streetCompleteUrl: `streetcomplete://#map=${zoom}/${formattedLat}/${formattedLng}`,

      // Direct deep link to EveryDoor POI / amenity editor
      everyDoorUrl: `everydoor://?lat=${formattedLat}&lon=${formattedLng}&zoom=${zoom}`,

      // Fallback web links to OpenStreetMap iD Web Editor & Browser View
      osmWebEditorUrl: `https://www.openstreetmap.org/edit#map=${zoom}/${formattedLat}/${formattedLng}`,
      osmWebViewUrl: `https://www.openstreetmap.org/#map=${zoom}/${formattedLat}/${formattedLng}`
    }
  }

  /**
   * Attempts to open the mobile deep link, falling back to web URL if unsupported.
   */
  const launchDeepLink = (deepLinkUrl: string, fallbackUrl?: string) => {
    // Open in window / iframe
    window.location.href = deepLinkUrl
    if (fallbackUrl) {
      setTimeout(() => {
        // If page is still visible after 1.5 seconds, user might not have app installed
        if (document.visibilityState === 'visible') {
          window.open(fallbackUrl, '_blank')
        }
      }, 1500)
    }
  }

  return {
    getDeepLinks,
    launchDeepLink
  }
}

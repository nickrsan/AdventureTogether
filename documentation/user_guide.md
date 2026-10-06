# AdventureTogether - End-User & Host Guide

Welcome to **AdventureTogether**, an event-based scavenger hunt platform created to empower communities to collaboratively improve open geospatial and knowledge datasets (OpenStreetMap, Wikimedia Commons, and Wikidata).

---

## 1. Participant Experience

### 1.1 Finding & Joining Hunts
1. Open the AdventureTogether web application on your mobile device or desktop.
2. Select an active hunt from the home screen or follow an invite link provided by your event organizer.
3. On the **Team Management** page:
   - Enter your **Display Name** (e.g. `Alex the Mapper`).
   - If your teammates already created a team, enter the 6-character **Team Join Code** (e.g. `EXPLOR42`) and tap **Join Team**.
   - Alternatively, select **Create New Team**, provide a group name (e.g. `Mission Cartographers`), and share the generated join code with your squad.

### 1.2 Foreground GPS & Privacy Controls
AdventureTogether protects your privacy and device battery through strict foreground tracking:
- **Foreground Only**: Coordinates are transmitted exclusively while the web tab is open and visible on your screen. When you switch apps or lock your phone, coordinate transmissions are immediately paused.
- **Privacy Tiers**:
  - **Nobody**: Your location is private and never visible to other participants.
  - **Team Only** *(Default)*: Your live marker and last-seen timestamp are shared exclusively with your teammates.
  - **Whole Quest**: Your marker is visible to all participants in the active hunt.
- **20-Minute Decay**: All locations expire from active views after 20 minutes without indefinite history retention.

### 1.3 Deep Linking into Mobile Mapping Tools
To contribute data to OpenStreetMap without tedious manual searching:
1. Tap any quest target on the interactive map or check your location.
2. Under **Mapping Tool Deep Links** in the sidebar:
   - Tap **🚀 Open in StreetComplete** (`streetcomplete://`) to resolve nearby quest surveys.
   - Tap **📍 Open in EveryDoor** (`everydoor://`) for comprehensive node and tag editing.
   - Or tap **🌐 Open OSM Web iD Editor** for desktop web editing.
3. When saving your edits in StreetComplete, EveryDoor, or iD, ensure the event's designated hashtag is included in the changeset comment (e.g. `#SFMapHunt2026`).

---

## 2. Event Host Experience

### 2.1 Creating Hunts & Drawing Bounding Perimeters
1. In the Django Admin or Host Portal, create a new event.
2. Provide:
   - **Title & Description**: Detailed instructions and rules for the hunt.
   - **Start & End Time**: The active time window for the event.
   - **Hashtag**: The unique tag to identify contributions across platforms (e.g. `SFMapHunt2026`).
   - **Bounding Perimeter**: GeoJSON polygon defining the geographic boundaries of the event.

### 2.2 Quest Builder & Criteria Configuration
1. Open `/events/<id>/host/builder` to access the interactive **Quest Builder**.
2. Select your verification criteria:
   - **OpenStreetMap Tag Rule**: Specify required features (e.g. `amenity=restaurant`) and tag requirements (e.g. `opening_hours=*` or `wheelchair=yes`).
   - **Wikimedia Commons Photo**: Target uploads with designated categories or photo hashtags.
   - **Wikidata Entry**: Target Wikidata statements and property links (e.g. `P18` image property).
3. Optionally click on the map within the blue perimeter boundary to pin a specific target coordinate.
4. Assign a point value (e.g. 10–25 points) and tap **Add Quest Challenge**.

### 2.3 Verification Dashboard & Review Workflow
1. Navigate to `/events/<id>/host/verify` to open the **Host Verification Portal**.
2. The background harvester automatically polls OSM, Wikimedia Commons, and Wikidata for contributions tagged with the event hashtag.
3. For each submission:
   - Inspect the **Diff Preview** to review added/modified tags and coordinates.
   - Click the external link (e.g. `#1456789 ↗`) to view the live changeset on OpenStreetMap or Wikimedia.
   - Check the **Verify** button. Verifying a submission automatically awards quest points to the participant's team.

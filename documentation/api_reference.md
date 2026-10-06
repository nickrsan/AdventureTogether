# AdventureTogether - Developer API Reference

## Architectural Overview
AdventureTogether is built using **Django 5**, **GeoDjango**, **Django REST Framework (DRF)**, **PostgreSQL/PostGIS**, and **django-q2**. It exposes RESTful JSON and GeoJSON APIs.

- **Base Endpoint**: `/api/`
- **Spatial Reference System**: EPSG:4326 (WGS 84, Longitude / Latitude)
- **Task Broker**: PostgreSQL ORM via `django-q2` (Zero-Redis stack)

---

## 1. System & Health

### `GET /api/health/`
Returns current API status and active database engine.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "AdventureTogether Backend API",
  "database_connected": true,
  "database_engine": "django.contrib.gis.db.backends.postgis",
  "version": "1.0.0"
}
```

---

## 2. Events API (`/api/events/`)

### `GET /api/events/`
Lists all scavenger hunt events.
- Query Parameters: `format=geojson` (optional, returns FeatureCollection)

### `POST /api/events/`
Creates a new scavenger hunt event.

**Payload**:
```json
{
  "title": "Mission District Hunt",
  "description": "Map amenities in the Mission.",
  "hashtag": "MissionHunt2026",
  "bounding_polygon": {
    "type": "Polygon",
    "coordinates": [[
      [-122.43, 37.76],
      [-122.40, 37.76],
      [-122.40, 37.79],
      [-122.43, 37.79],
      [-122.43, 37.76]
    ]]
  },
  "start_time": "2026-10-04T12:00:00Z",
  "end_time": "2026-10-04T18:00:00Z"
}
```

### `GET /api/events/<id>/geojson/`
Returns the event bounding perimeter formatted as a GeoJSON Feature.

---

## 3. Teams API (`/api/teams/`)

### `GET /api/teams/?event=<event_id>`
Lists teams registered for an event with member counts and current scores.

### `POST /api/teams/`
Creates a new team. Automatically generates a unique 6-character `join_code`.

**Payload**:
```json
{
  "event": 1,
  "name": "Urban Explorers"
}
```

### `POST /api/teams/join/`
Allows a participant to join a team via join code.

**Payload**:
```json
{
  "join_code": "EXPLOR42",
  "user_identifier": "device-uuid-12345",
  "display_name": "Alice"
}
```

---

## 4. Quests API (`/api/quests/`)

### `GET /api/quests/?event=<event_id>`
Lists active quests for an event. Supports `format=geojson`.

### `POST /api/quests/`
Creates a new quest. Rejects target geometries outside the event's bounding perimeter.

**Payload**:
```json
{
  "event": 1,
  "title": "Map Restaurant Opening Hours",
  "description": "Add opening_hours tag to 5 restaurants.",
  "criteria_type": "osm_tags",
  "validation_rules": {
    "required_tags": {
      "amenity": "restaurant",
      "opening_hours": "*"
    },
    "target_count": 5
  },
  "target_geometry": {
    "type": "Point",
    "coordinates": [-122.4194, 37.7749]
  },
  "points_reward": 20
}
```

---

## 5. Location Sharing API (`/api/locations/`)

### `POST /api/locations/ping/`
Ingests an ephemeral foreground location ping.

**Payload**:
```json
{
  "event": 1,
  "user_identifier": "device-uuid-12345",
  "display_name": "Alice",
  "longitude": -122.4194,
  "latitude": 37.7749,
  "visibility": "team",
  "is_foreground": true
}
```

### `GET /api/locations/active/?event=<event_id>&user_identifier=<user_id>`
Returns active participant locations within the **20-minute decay window**, filtered according to privacy matrix permissions (`nobody`, `team`, `quest`).

---

## 6. Submissions & Verification API (`/api/submissions/`)

### `GET /api/submissions/?event=<event_id>&is_verified=<bool>&quest=<quest_id>`
Lists submissions harvested from OSM, Wikimedia Commons, or Wikidata.

### `POST /api/submissions/<id>/verify/`
Host endpoint to verify a submission and award quest points.

**Payload**:
```json
{
  "is_verified": true,
  "verified_by_username": "HostMaster"
}
```

### `POST /api/submissions/trigger_harvest/`
Manually triggers background polling for an event.

**Payload**:
```json
{
  "event": 1
}
```

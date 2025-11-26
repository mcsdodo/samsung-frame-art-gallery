# TV Detection & Selection Design

## Overview

Add automatic Samsung TV discovery via SSDP and a UI for selecting which TV to control. Replaces hardcoded `TV_IP` environment variable with persistent user selection.

## Requirements

- Discover Samsung TVs on local network using SSDP
- Show connection modal on first startup (no TV configured)
- Display discovered TVs with model name + IP
- Allow manual IP entry as fallback
- Persist selection across app restarts (Docker volume)
- Auto-select if only one TV found
- Header icon to access TV settings anytime
- Toast notifications for connection errors

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/services/tv_discovery.py` | SSDP scanner for Samsung TVs |
| `src/services/tv_settings.py` | Load/save TV selection to JSON |
| `src/frontend/src/components/TvConnectionModal.vue` | TV selection UI |

### New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tv/discover` | GET | Trigger SSDP scan, return found TVs |
| `/api/tv/settings` | GET | Get current TV selection |
| `/api/tv/settings` | POST | Save TV selection |

### Modified Files

| File | Changes |
|------|---------|
| `src/services/tv_client.py` | Add `configure(ip)` class method, remove singleton hardcoding |
| `src/api/tv.py` | Add new endpoints |
| `docker-compose.yml` | Add `./data:/app/data` volume mount |
| Frontend header | Add TV icon with status indicator |

## SSDP Discovery

### Protocol

1. Send UDP multicast `M-SEARCH` to `239.255.255.250:1900`
2. Search target: `urn:samsung.com:device:RemoteControlReceiver:1`
3. Wait 3 seconds for responses
4. Parse response headers for `LOCATION` URL
5. Fetch device XML to extract `friendlyName`

### Response Format

```json
GET /api/tv/discover

{
  "tvs": [
    {
      "ip": "192.168.0.105",
      "name": "[TV] Samsung Frame (55)",
      "model": "UE55LS003AU"
    }
  ],
  "scan_duration_ms": 3200
}
```

## Persistence

### Storage

- File: `/app/data/tv_settings.json` (inside container)
- Docker mount: `./data:/app/data`

### Format

```json
{
  "selected_tv_ip": "192.168.0.105",
  "selected_tv_name": "Samsung Frame 55\"",
  "manual_entry": false
}
```

### API

```json
GET /api/tv/settings

{
  "selected_tv_ip": "192.168.0.105",
  "selected_tv_name": "Samsung Frame 55\"",
  "manual_entry": false,
  "configured": true
}
```

```json
POST /api/tv/settings

{
  "ip": "192.168.0.105",
  "name": "Samsung Frame 55\"",
  "manual_entry": false
}
```

## Frontend UI

### TvConnectionModal.vue

- **Trigger:** Opens on app load if `configured: false`, or via header icon
- **Auto-scan:** Triggers `/api/tv/discover` when modal opens
- **TV list:** Clickable cards showing name + IP
- **Rescan button:** Re-triggers discovery
- **Manual entry:** Text input + "Connect" button below divider
- **Auto-select:** If one TV found, auto-connect after 2 seconds with cancel option

### Header

- TV icon button to open modal
- Status dot: green (connected), red (disconnected)
- Tooltip shows current TV name

### Toast Notifications

- Connection failure: "Could not connect to [TV name]. Check that the TV is on." + Settings button
- Successful switch: "Connected to [TV name]"

## TVClient Refactoring

### Changes

```python
class TVClient:
    _instance: Optional["TVClient"] = None
    _current_ip: Optional[str] = None

    def __init__(self, ip: str):
        self._ip = ip
        self._tv = None
        # ...

    @classmethod
    def get_instance(cls) -> Optional["TVClient"]:
        return cls._instance

    @classmethod
    def configure(cls, ip: str) -> "TVClient":
        """Set or switch the TV. Clears old connection."""
        if cls._instance and cls._current_ip != ip:
            cls._instance._tv = None
            cls._instance._thumbnail_cache.clear()
        cls._instance = cls(ip)
        cls._current_ip = ip
        return cls._instance
```

### Startup Flow

1. Load `/app/data/tv_settings.json`
2. If `selected_tv_ip` exists, call `TVClient.configure(ip)`
3. If no settings, endpoints return 503 "No TV configured"

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No TVs found | Empty list, show manual entry option |
| Network timeout | Return empty list with error message |
| TV unreachable on save | Return 400, don't persist |
| TV offline during use | Toast notification, APIs return 503 |
| Multiple TVs same name | Differentiate by IP in parentheses |
| TV IP changes (DHCP) | User rescans and reselects |

## Docker Networking

SSDP requires UDP multicast. Two options:

1. **Host networking (simpler):** `network_mode: host` in docker-compose
2. **Bridge with multicast:** Configure Docker network for multicast routing

Document both in README, recommend host mode for simplicity.

## Validation

- Manual IP: Check IPv4 format before submission
- Before saving: Attempt connection to verify TV responds

# TV Detection & Selection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add automatic Samsung TV discovery via SSDP and UI for selecting which TV to control.

**Architecture:** SSDP scanner discovers TVs on network, settings persisted to JSON file in Docker volume, connection modal shows on startup if unconfigured, TVClient refactored to support runtime IP switching.

**Tech Stack:** Python (FastAPI, socket for SSDP), Vue 3 (Composition API), Docker volumes

---

## Task 1: Add Docker Volume for Persistent Settings

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add data volume mount**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8080:8080"
    volumes:
      - c:\_dev\dezoomify-processor\output\:/images:ro
      - thumbnails:/thumbnails
      - ./data:/app/data
    environment:
      - TV_IP=${TV_IP:-192.168.0.105}
    restart: unless-stopped

volumes:
  thumbnails:
```

**Step 2: Create data directory**

```bash
mkdir -p data
```

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: add data volume mount for persistent settings"
```

---

## Task 2: Create TV Settings Service

**Files:**
- Create: `src/services/tv_settings.py`

**Step 1: Create the settings service**

```python
import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

_LOGGER = logging.getLogger(__name__)

SETTINGS_FILE = Path("/app/data/tv_settings.json")


@dataclass
class TVSettings:
    selected_tv_ip: Optional[str] = None
    selected_tv_name: Optional[str] = None
    manual_entry: bool = False

    @property
    def configured(self) -> bool:
        return self.selected_tv_ip is not None


def load_settings() -> TVSettings:
    """Load TV settings from disk."""
    if not SETTINGS_FILE.exists():
        _LOGGER.info("No TV settings file found, using defaults")
        return TVSettings()

    try:
        data = json.loads(SETTINGS_FILE.read_text())
        return TVSettings(
            selected_tv_ip=data.get("selected_tv_ip"),
            selected_tv_name=data.get("selected_tv_name"),
            manual_entry=data.get("manual_entry", False)
        )
    except Exception as e:
        _LOGGER.error(f"Failed to load TV settings: {e}")
        return TVSettings()


def save_settings(settings: TVSettings) -> None:
    """Save TV settings to disk."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2))
    _LOGGER.info(f"Saved TV settings: {settings.selected_tv_ip}")
```

**Step 2: Commit**

```bash
git add src/services/tv_settings.py
git commit -m "feat: add TV settings persistence service"
```

---

## Task 3: Create SSDP Discovery Service

**Files:**
- Create: `src/services/tv_discovery.py`

**Step 1: Create the discovery service**

```python
import socket
import logging
import re
from typing import Optional
from dataclasses import dataclass
import urllib.request
import xml.etree.ElementTree as ET

_LOGGER = logging.getLogger(__name__)

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_TIMEOUT = 3

SEARCH_REQUEST = """M-SEARCH * HTTP/1.1\r
HOST: 239.255.255.250:1900\r
MAN: "ssdp:discover"\r
MX: 2\r
ST: urn:samsung.com:device:RemoteControlReceiver:1\r
\r
"""


@dataclass
class DiscoveredTV:
    ip: str
    name: str
    model: Optional[str] = None


def _parse_ssdp_response(response: str) -> Optional[str]:
    """Extract LOCATION URL from SSDP response."""
    for line in response.split("\r\n"):
        if line.upper().startswith("LOCATION:"):
            return line.split(":", 1)[1].strip()
    return None


def _fetch_device_info(location_url: str) -> Optional[dict]:
    """Fetch device description XML and extract name/model."""
    try:
        with urllib.request.urlopen(location_url, timeout=2) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {"upnp": "urn:schemas-upnp-org:device-1-0"}

        device = root.find(".//upnp:device", ns)
        if device is None:
            return None

        friendly_name = device.findtext("upnp:friendlyName", "", ns)
        model_name = device.findtext("upnp:modelName", "", ns)
        manufacturer = device.findtext("upnp:manufacturer", "", ns)

        # Only return Samsung devices
        if "samsung" not in manufacturer.lower():
            return None

        return {
            "name": friendly_name or model_name or "Samsung TV",
            "model": model_name
        }
    except Exception as e:
        _LOGGER.debug(f"Failed to fetch device info from {location_url}: {e}")
        return None


def _extract_ip_from_url(url: str) -> Optional[str]:
    """Extract IP address from URL like http://192.168.0.105:9197/dmr"""
    match = re.search(r"http://(\d+\.\d+\.\d+\.\d+)", url)
    return match.group(1) if match else None


def discover_tvs() -> list[DiscoveredTV]:
    """Discover Samsung TVs on the network using SSDP."""
    _LOGGER.info("Starting SSDP discovery...")
    discovered = {}

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(SSDP_TIMEOUT)

        # Send discovery request
        sock.sendto(SEARCH_REQUEST.encode(), (SSDP_ADDR, SSDP_PORT))

        # Collect responses
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                response = data.decode("utf-8", errors="ignore")

                location = _parse_ssdp_response(response)
                if location:
                    ip = _extract_ip_from_url(location)
                    if ip and ip not in discovered:
                        device_info = _fetch_device_info(location)
                        if device_info:
                            discovered[ip] = DiscoveredTV(
                                ip=ip,
                                name=device_info["name"],
                                model=device_info.get("model")
                            )
                            _LOGGER.info(f"Found TV: {device_info['name']} at {ip}")
            except socket.timeout:
                break

    except Exception as e:
        _LOGGER.error(f"SSDP discovery failed: {e}")
    finally:
        sock.close()

    _LOGGER.info(f"Discovery complete, found {len(discovered)} TV(s)")
    return list(discovered.values())
```

**Step 2: Commit**

```bash
git add src/services/tv_discovery.py
git commit -m "feat: add SSDP discovery service for Samsung TVs"
```

---

## Task 4: Refactor TVClient for Dynamic IP

**Files:**
- Modify: `src/services/tv_client.py`

**Step 1: Update TVClient class**

Replace the entire file with:

```python
import logging
import threading
import time
from typing import Optional
from samsungtvws import SamsungTVWS

from src.services.tv_thumbnail_cache import TVThumbnailCache
from src.services.tv_settings import load_settings

_LOGGER = logging.getLogger(__name__)

TV_TIMEOUT = 30


class TVClient:
    _instance: Optional["TVClient"] = None
    _current_ip: Optional[str] = None

    def __init__(self, ip: str):
        self._ip = ip
        self._tv: Optional[SamsungTVWS] = None
        self._api_version: Optional[str] = None
        self._lock = threading.Lock()
        self._thumbnail_cache = TVThumbnailCache()

    @classmethod
    def get_instance(cls) -> Optional["TVClient"]:
        """Get current TVClient instance, or None if not configured."""
        return cls._instance

    @classmethod
    def configure(cls, ip: str) -> "TVClient":
        """Configure TVClient with a new IP. Clears old connection if switching."""
        if cls._instance is not None and cls._current_ip != ip:
            _LOGGER.info(f"Switching TV from {cls._current_ip} to {ip}")
            cls._instance._tv = None
            cls._instance._thumbnail_cache.clear()

        cls._instance = cls(ip)
        cls._current_ip = ip
        _LOGGER.info(f"TVClient configured for {ip}")
        return cls._instance

    @classmethod
    def initialize_from_settings(cls) -> Optional["TVClient"]:
        """Initialize TVClient from saved settings."""
        settings = load_settings()
        if settings.configured:
            return cls.configure(settings.selected_tv_ip)
        _LOGGER.info("No TV configured in settings")
        return None

    @property
    def ip(self) -> str:
        return self._ip

    def _get_tv(self) -> SamsungTVWS:
        if self._tv is None:
            self._tv = SamsungTVWS(self._ip, timeout=TV_TIMEOUT)
        return self._tv

    def get_api_version(self) -> str:
        """Get and cache TV API version."""
        if self._api_version is None:
            tv = self._get_tv()
            self._api_version = tv.art().get_api_version()
            _LOGGER.info(f"TV API version: {self._api_version}")
        return self._api_version

    def _is_new_api(self) -> bool:
        """Check if TV uses new API (4.0+) which requires SSL for thumbnails."""
        try:
            version = self.get_api_version()
            major = int(version.split('.')[0])
            return major >= 4
        except Exception as e:
            _LOGGER.warning(f"Could not determine API version: {e}, assuming new API")
            return True

    def get_status(self) -> dict:
        try:
            tv = self._get_tv()
            supported = tv.art().supported()
            api_version = self.get_api_version()
            return {
                "connected": True,
                "art_mode_supported": supported,
                "tv_ip": self._ip,
                "api_version": api_version,
                "uses_ssl_thumbnails": self._is_new_api()
            }
        except Exception as e:
            self._tv = None
            self._api_version = None
            return {"connected": False, "error": str(e), "tv_ip": self._ip}

    def get_artwork_list(self) -> list:
        tv = self._get_tv()
        return tv.art().available() or []

    def get_current_artwork(self) -> dict:
        tv = self._get_tv()
        return tv.art().get_current() or {}

    def set_current_artwork(self, content_id: str) -> bool:
        tv = self._get_tv()
        tv.art().select_image(content_id)
        return True

    def delete_artwork(self, content_id: str) -> bool:
        tv = self._get_tv()
        tv.art().delete(content_id)
        self._thumbnail_cache.invalidate(content_id)
        return True

    def upload_artwork(self, image_data: bytes, matte: str = "none",
                       matte_color: str = "neutral", display: bool = False) -> dict:
        tv = self._get_tv()
        result = tv.art().upload(image_data, matte=matte, portrait_matte=matte)
        if display and result:
            content_id = result.get("content_id")
            if content_id:
                tv.art().select_image(content_id)
        return result or {}

    def _fetch_thumbnail_from_tv(self, content_id: str) -> Optional[bytes]:
        """Fetch thumbnail from TV using appropriate API based on TV version."""
        tv = self._get_tv()

        if self._is_new_api():
            thumbnails = tv.art().get_thumbnail_list([content_id])
            if thumbnails:
                data = list(thumbnails.values())[0]
                return bytes(data) if isinstance(data, bytearray) else data
        else:
            data = tv.art().get_thumbnail(content_id)
            if data:
                return bytes(data) if isinstance(data, bytearray) else data

        return None

    def get_thumbnail(self, content_id: str, retries: int = 2) -> Optional[bytes]:
        """Get thumbnail with caching, request serialization, and retry logic."""
        cached = self._thumbnail_cache.get(content_id)
        if cached:
            return cached

        data = None
        last_error = None

        for attempt in range(retries + 1):
            try:
                with self._lock:
                    data = self._fetch_thumbnail_from_tv(content_id)
                    if data:
                        break
            except Exception as e:
                last_error = e
                _LOGGER.warning(f"Thumbnail fetch attempt {attempt + 1} failed for {content_id}: {e}")
                if attempt < retries:
                    time.sleep(0.5)
                    self._tv = None

        if data:
            self._thumbnail_cache.set(content_id, data)
            return data

        if last_error:
            _LOGGER.error(f"All thumbnail fetch attempts failed for {content_id}: {last_error}")
            raise last_error

        return None

    def get_matte_options(self) -> dict:
        return {
            "styles": ["none", "modernthin", "modern", "flexible"],
            "colors": ["neutral", "antique", "warm", "cold"]
        }

    def clear_thumbnail_cache(self) -> None:
        """Clear all cached thumbnails."""
        self._thumbnail_cache.clear()


def get_tv_client() -> Optional[TVClient]:
    """Get current TVClient instance."""
    return TVClient.get_instance()
```

**Step 2: Commit**

```bash
git add src/services/tv_client.py
git commit -m "refactor: make TVClient configurable for dynamic IP switching"
```

---

## Task 5: Add TV Settings and Discovery API Endpoints

**Files:**
- Modify: `src/api/tv.py`

**Step 1: Add imports and new request models at top of file**

After existing imports, add:

```python
from src.services.tv_settings import load_settings, save_settings, TVSettings
from src.services.tv_discovery import discover_tvs
```

Add new request model after existing models:

```python
class TVSettingsRequest(BaseModel):
    ip: str
    name: str = "Samsung TV"
    manual_entry: bool = False
```

**Step 2: Add new endpoints before the existing @router.get("/status")**

```python
@router.get("/settings")
async def get_tv_settings():
    """Get current TV settings."""
    settings = load_settings()
    return {
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name,
        "manual_entry": settings.manual_entry,
        "configured": settings.configured
    }


@router.post("/settings")
async def set_tv_settings(request: TVSettingsRequest):
    """Save TV settings and reconfigure client."""
    from src.services.tv_client import TVClient

    # Try to connect to verify TV is reachable
    try:
        client = TVClient.configure(request.ip)
        status = await asyncio.to_thread(client.get_status)
        if not status.get("connected"):
            raise HTTPException(
                status_code=400,
                detail=f"Could not connect to TV at {request.ip}: {status.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to TV: {e}")

    # Save settings
    settings = TVSettings(
        selected_tv_ip=request.ip,
        selected_tv_name=request.name,
        manual_entry=request.manual_entry
    )
    save_settings(settings)

    return {
        "success": True,
        "selected_tv_ip": settings.selected_tv_ip,
        "selected_tv_name": settings.selected_tv_name
    }


@router.get("/discover")
async def discover_samsung_tvs():
    """Discover Samsung TVs on the network."""
    import time
    start = time.time()

    tvs = await asyncio.to_thread(discover_tvs)

    return {
        "tvs": [{"ip": tv.ip, "name": tv.name, "model": tv.model} for tv in tvs],
        "scan_duration_ms": int((time.time() - start) * 1000)
    }
```

**Step 3: Update get_status endpoint to handle unconfigured state**

Replace the existing `get_status` function:

```python
@router.get("/status")
async def get_status():
    client = get_tv_client()
    if client is None:
        return {"connected": False, "configured": False, "error": "No TV configured"}
    status = await asyncio.to_thread(client.get_status)
    status["configured"] = True
    return status
```

**Step 4: Commit**

```bash
git add src/api/tv.py
git commit -m "feat: add TV settings and discovery API endpoints"
```

---

## Task 6: Initialize TVClient on App Startup

**Files:**
- Modify: `src/main.py`

**Step 1: Read current main.py**

Check current content and add initialization.

**Step 2: Add TVClient initialization in startup**

Add after existing imports:

```python
from src.services.tv_client import TVClient
```

In the startup event or lifespan, add:

```python
# Initialize TV client from saved settings
TVClient.initialize_from_settings()
```

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: initialize TVClient from saved settings on startup"
```

---

## Task 7: Create TV Connection Modal Component

**Files:**
- Create: `src/frontend/src/components/TvConnectionModal.vue`

**Step 1: Create the modal component**

```vue
<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Connect to TV</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <!-- Scanning state -->
        <div v-if="scanning" class="scanning">
          <div class="spinner"></div>
          <p>Scanning for Samsung TVs...</p>
        </div>

        <!-- TV List -->
        <div v-else-if="tvs.length > 0" class="tv-list">
          <div
            v-for="tv in tvs"
            :key="tv.ip"
            class="tv-card"
            :class="{ selected: selectedIp === tv.ip, connecting: connecting && selectedIp === tv.ip }"
            @click="selectTV(tv)"
          >
            <div class="tv-icon">📺</div>
            <div class="tv-info">
              <div class="tv-name">{{ tv.name }}</div>
              <div class="tv-ip">{{ tv.ip }}</div>
            </div>
            <div v-if="connecting && selectedIp === tv.ip" class="connecting-indicator">
              <div class="spinner small"></div>
            </div>
          </div>

          <button class="rescan-btn" @click="scan" :disabled="scanning">
            Rescan
          </button>
        </div>

        <!-- No TVs found -->
        <div v-else class="no-tvs">
          <p>No Samsung TVs found on your network.</p>
          <button class="rescan-btn" @click="scan">Scan Again</button>
        </div>

        <!-- Manual entry -->
        <div class="manual-entry">
          <div class="divider">
            <span>or enter IP manually</span>
          </div>
          <div class="manual-form">
            <input
              v-model="manualIp"
              type="text"
              placeholder="192.168.0.100"
              :disabled="connecting"
              @keyup.enter="connectManual"
            />
            <button @click="connectManual" :disabled="!manualIp || connecting">
              Connect
            </button>
          </div>
        </div>

        <!-- Error message -->
        <div v-if="error" class="error">
          {{ error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['close', 'connected'])

const tvs = ref([])
const scanning = ref(false)
const connecting = ref(false)
const selectedIp = ref(null)
const manualIp = ref('')
const error = ref(null)

const scan = async () => {
  scanning.value = true
  error.value = null
  tvs.value = []

  try {
    const res = await fetch('/api/tv/discover')
    const data = await res.json()
    tvs.value = data.tvs || []

    // Auto-select if only one TV found
    if (tvs.value.length === 1) {
      setTimeout(() => selectTV(tvs.value[0]), 500)
    }
  } catch (e) {
    error.value = 'Failed to scan for TVs'
  } finally {
    scanning.value = false
  }
}

const selectTV = async (tv) => {
  if (connecting.value) return

  selectedIp.value = tv.ip
  connecting.value = true
  error.value = null

  try {
    const res = await fetch('/api/tv/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip: tv.ip,
        name: tv.name,
        manual_entry: false
      })
    })

    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Connection failed')
    }

    emit('connected', tv)
  } catch (e) {
    error.value = e.message || 'Failed to connect to TV'
    selectedIp.value = null
  } finally {
    connecting.value = false
  }
}

const connectManual = async () => {
  if (!manualIp.value || connecting.value) return

  // Basic IP validation
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipRegex.test(manualIp.value)) {
    error.value = 'Please enter a valid IP address'
    return
  }

  connecting.value = true
  selectedIp.value = manualIp.value
  error.value = null

  try {
    const res = await fetch('/api/tv/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip: manualIp.value,
        name: 'Samsung TV',
        manual_entry: true
      })
    })

    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Connection failed')
    }

    emit('connected', { ip: manualIp.value, name: 'Samsung TV' })
  } catch (e) {
    error.value = e.message || 'Failed to connect to TV'
    selectedIp.value = null
  } finally {
    connecting.value = false
  }
}

onMounted(() => {
  scan()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border-radius: 12px;
  width: 90%;
  max-width: 450px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #2a2a4e;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: white;
}

.close-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.scanning {
  text-align: center;
  padding: 2rem 0;
  color: #888;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #2a2a4e;
  border-top-color: #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner.small {
  width: 20px;
  height: 20px;
  border-width: 2px;
  margin: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tv-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tv-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #2a2a4e;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.tv-card:hover {
  background: #3a3a5e;
}

.tv-card.selected {
  background: #4a90d9;
}

.tv-card.connecting {
  opacity: 0.7;
  pointer-events: none;
}

.tv-icon {
  font-size: 2rem;
}

.tv-info {
  flex: 1;
}

.tv-name {
  color: white;
  font-weight: 500;
}

.tv-ip {
  color: #888;
  font-size: 0.85rem;
}

.tv-card.selected .tv-ip {
  color: rgba(255, 255, 255, 0.7);
}

.rescan-btn {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  border: 1px solid #4a90d9;
  color: #4a90d9;
  border-radius: 6px;
  cursor: pointer;
  align-self: center;
}

.rescan-btn:hover:not(:disabled) {
  background: rgba(74, 144, 217, 0.1);
}

.rescan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-tvs {
  text-align: center;
  padding: 2rem 0;
  color: #888;
}

.manual-entry {
  margin-top: 1.5rem;
}

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #2a2a4e;
}

.manual-form {
  display: flex;
  gap: 0.75rem;
}

.manual-form input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: #2a2a4e;
  border: 1px solid #3a3a5e;
  border-radius: 6px;
  color: white;
  font-size: 1rem;
}

.manual-form input:focus {
  outline: none;
  border-color: #4a90d9;
}

.manual-form button {
  padding: 0.75rem 1.5rem;
  background: #4a90d9;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  font-weight: 500;
}

.manual-form button:hover:not(:disabled) {
  background: #5a9fe9;
}

.manual-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.9rem;
}
</style>
```

**Step 2: Commit**

```bash
git add src/frontend/src/components/TvConnectionModal.vue
git commit -m "feat: add TV connection modal component"
```

---

## Task 8: Integrate Modal into App.vue

**Files:**
- Modify: `src/frontend/src/App.vue`

**Step 1: Add import**

In script section, add import:

```javascript
import TvConnectionModal from './components/TvConnectionModal.vue'
```

**Step 2: Add state variables**

After existing refs:

```javascript
const showTvModal = ref(false)
const tvName = ref('')
```

**Step 3: Add modal handlers**

```javascript
const handleTvConnected = (tv) => {
  showTvModal.value = false
  tvName.value = tv.name
  tvStatus.value = { connected: true }
  // Refresh TV panel
  tvPanel.value?.loadArtwork()
}

const openTvSettings = () => {
  showTvModal.value = true
}
```

**Step 4: Update onMounted**

Replace the onMounted content:

```javascript
onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)

  try {
    const res = await fetch('/api/tv/settings')
    const settings = await res.json()

    if (!settings.configured) {
      showTvModal.value = true
    } else {
      tvName.value = settings.selected_tv_name || ''
      // Check actual connection status
      const statusRes = await fetch('/api/tv/status')
      tvStatus.value = await statusRes.json()
    }
  } catch (e) {
    console.error('Failed to get TV settings:', e)
    showTvModal.value = true
  }
})
```

**Step 5: Update header in template**

Replace the status div in header:

```html
<div class="header-right">
  <button class="tv-settings-btn" @click="openTvSettings" :title="tvName || 'TV Settings'">
    <span class="tv-icon">📺</span>
    <span class="status-dot" :class="{ connected: tvStatus.connected }"></span>
  </button>
</div>
```

**Step 6: Add modal to template**

After ImagePreview component, add:

```html
<!-- TV Connection Modal -->
<TvConnectionModal
  v-if="showTvModal"
  @close="showTvModal = false"
  @connected="handleTvConnected"
/>
```

**Step 7: Add styles**

Add to style section:

```css
.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tv-settings-btn {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: background 0.2s;
}

.tv-settings-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tv-icon {
  font-size: 1.5rem;
}

.tv-settings-btn .status-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
}
```

**Step 8: Commit**

```bash
git add src/frontend/src/App.vue
git commit -m "feat: integrate TV connection modal into App"
```

---

## Task 9: Add Toast Notifications

**Files:**
- Modify: `src/frontend/src/App.vue`

**Step 1: Add toast state**

```javascript
const toast = ref({ show: false, message: '', type: 'info' })

const showToast = (message, type = 'info') => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, 4000)
}
```

**Step 2: Update handleTvConnected to show toast**

```javascript
const handleTvConnected = (tv) => {
  showTvModal.value = false
  tvName.value = tv.name
  tvStatus.value = { connected: true }
  showToast(`Connected to ${tv.name}`, 'success')
  tvPanel.value?.loadArtwork()
}
```

**Step 3: Add toast template after modals**

```html
<!-- Toast Notification -->
<div v-if="toast.show" class="toast" :class="toast.type">
  {{ toast.message }}
  <button v-if="toast.type === 'error'" class="toast-action" @click="showTvModal = true">
    Settings
  </button>
</div>
```

**Step 4: Add toast styles**

```css
.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  background: #2a2a4e;
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 1001;
  animation: slideUp 0.3s ease;
}

.toast.success {
  background: #2d5a3d;
}

.toast.error {
  background: #5a2d2d;
}

.toast-action {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}
```

**Step 5: Commit**

```bash
git add src/frontend/src/App.vue
git commit -m "feat: add toast notifications for TV connection status"
```

---

## Task 10: Test End-to-End

**Step 1: Rebuild and restart**

```bash
docker-compose build app
docker-compose up -d app
```

**Step 2: Test discovery endpoint**

```bash
curl http://localhost:8080/api/tv/discover
```

Expected: JSON with `tvs` array (may be empty if no TVs on network)

**Step 3: Test settings endpoints**

```bash
# Get settings (should show configured: false initially)
curl http://localhost:8080/api/tv/settings

# Set settings
curl -X POST http://localhost:8080/api/tv/settings \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.0.105", "name": "Test TV", "manual_entry": true}'

# Verify saved
curl http://localhost:8080/api/tv/settings
```

**Step 4: Test UI**

1. Open http://localhost:8080 in browser
2. Should see connection modal on first load
3. Enter TV IP manually and connect
4. Modal should close, TV icon should show green dot
5. Click TV icon to reopen modal

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete TV detection and selection feature"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Add Docker volume mount for settings |
| 2 | Create TV settings persistence service |
| 3 | Create SSDP discovery service |
| 4 | Refactor TVClient for dynamic IP |
| 5 | Add API endpoints for settings/discovery |
| 6 | Initialize TVClient on startup |
| 7 | Create TV connection modal component |
| 8 | Integrate modal into App.vue |
| 9 | Add toast notifications |
| 10 | Test end-to-end |

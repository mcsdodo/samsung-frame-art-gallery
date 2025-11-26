# Samsung TV WebSocket API - Complete Documentation

## Table of Contents
1. [Main API Classes](#main-api-classes)
2. [Art Mode Methods (Sync)](#art-mode-methods-sync)
3. [Art Mode Methods (Async)](#art-mode-methods-async)
4. [Remote Control Methods](#remote-control-methods)
5. [REST API Methods](#rest-api-methods)
6. [Common Usage Patterns](#common-usage-patterns)
7. [Error Handling](#error-handling)
8. [TV Compatibility & API Versions](#tv-compatibility--api-versions)

---

## Main API Classes

### SamsungTVWS (Synchronous Remote Control)
**Location:** `samsungtvws/remote.py`

Main class for controlling Samsung TVs synchronously.

```python
from samsungtvws import SamsungTVWS

tv = SamsungTVWS(
    host='192.168.1.100',
    token=None,              # Optional: reuse saved token
    token_file='token.txt',  # Optional: save token to file
    port=8001,               # Default: 8001
    timeout=None,            # Optional: connection timeout
    key_press_delay=1,       # Default: delay between key presses
    name="SamsungTvRemote"   # Default: remote name
)
```

**Parameters:**
- `host` (str): IP address of the TV
- `token` (str, optional): Authentication token
- `token_file` (str, optional): Path to save/load token
- `port` (int): WebSocket port (default: 8001, art mode typically uses 8002)
- `timeout` (float, optional): Connection timeout in seconds
- `key_press_delay` (float): Delay between key presses (default: 1 second)
- `name` (str): Remote control name displayed on TV

### SamsungTVAsyncArt (Asynchronous Art Mode)
**Location:** `samsungtvws/async_art.py`

Async version of art mode control with event listening support.

```python
from samsungtvws.async_art import SamsungTVAsyncArt

tv = SamsungTVAsyncArt(
    host='192.168.1.100',
    token=None,
    token_file='token.txt',
    port=8002,               # Art mode typically uses port 8002
    timeout=None,
    key_press_delay=1,
    name="SamsungTvRemote"
)

# Must call before using
await tv.start_listening()
```

### SamsungTVWSAsyncRemote (Asynchronous Remote Control)
**Location:** `samsungtvws/async_remote.py`

Async version for regular remote control.

```python
from samsungtvws.async_remote import SamsungTVWSAsyncRemote

tv = SamsungTVWSAsyncRemote(
    host='192.168.1.100',
    token_file='token.txt',
    port=8002,
)

await tv.start_listening()
```

---

## Art Mode Methods (Sync)

All synchronous art methods are in `SamsungTVArt` class accessed via:
```python
tv = SamsungTVWS('192.168.1.100', port=8002, token_file='token.txt')
art = tv.art()  # Get art object, or tv.art(timeout) for custom timeout
```

### Connection & Device Info

#### `supported() -> bool`
Check if Art Mode is supported on this TV.

```python
is_supported = tv.art().supported()
# Returns: True if Frame TV with Art Mode support
```

#### `get_device_info() -> dict`
Get detailed device information.

```python
info = tv.art().get_device_info()
# Returns: {'device': {...}, 'version': '...'}
```

#### `get_api_version() -> str`
Get the Art API version.

```python
version = tv.art().get_api_version()
# Returns: "4.3.4.0" (2022+) or "2.03" (2021 and earlier)
```

**Note:** API differs significantly between old (2021-) and new (2022+) versions.

---

### Image/Artwork Management

#### `available(category=None) -> list`
Get list of available artwork on the TV.

```python
# Get all available art
all_art = tv.art().available()

# Get specific category
my_photos = tv.art().available('MY-C0002')  # My Photos
favourites = tv.art().available('MY-C0004')  # Favourites
store_art = tv.art().available('MY-C0008')   # Store Art
```

**Category IDs:**
- `'MY-C0002'`: My Photos (uploaded images)
- `'MY-C0004'`: Favourites
- `'MY-C0008'`: Store Art

#### `get_current() -> dict`
Get information about currently displayed artwork.

```python
current = tv.art().get_current()
# Returns: {'content_id': 'SAM-F0123', 'name': '...', ...}
```

#### `select_image(content_id, category=None, show=True) -> None`
Select and display a piece of artwork.

```python
# Display immediately
tv.art().select_image('SAM-F0206')

# Select but don't show if not already in art mode
tv.art().select_image('SAM-F0206', show=False)

# With category specification
tv.art().select_image('MY-F0001', category='MY-C0002')
```

#### `upload(file, matte="shadowbox_polar", portrait_matte="shadowbox_polar", file_type="png", date=None) -> str`
Upload an image to the TV.

```python
# From file path
content_id = tv.art().upload('image.png')

# From binary data
with open('image.jpg', 'rb') as f:
    content_id = tv.art().upload(f.read(), file_type='jpg')

# With custom matte and date
content_id = tv.art().upload(
    'image.png',
    matte='modern_neutral',
    portrait_matte='modern_neutral',
    date='2024:01:15 10:30:00'
)

# Longer timeout for large files
content_id = tv.art(30).upload('large_image.png')
```

**Parameters:**
- `file` (str or bytes): File path or binary image data
- `matte` (str): Matte frame style for landscape (format: `{style}_{color}` or `none`)
- `portrait_matte` (str): Matte frame style for portrait orientation
- `file_type` (str): Image format - 'png', 'jpg', 'jpeg', 'bmp' (auto-detected from path)
- `date` (str): Image date in format "YYYY:MM:DD HH:MM:SS" (default: current time)

**Returns:** `content_id` (str) - Unique identifier for uploaded image

#### `delete(content_id) -> bool`
Delete a single artwork from the TV.

```python
success = tv.art().delete('MY-F0001')
```

#### `delete_list(content_ids) -> bool`
Delete multiple artworks.

```python
success = tv.art().delete_list(['MY-F0001', 'MY-F0002', 'MY-F0003'])
```

---

### Thumbnail Operations

#### `get_thumbnail(content_id_list=[], as_dict=False) -> bytes or dict or list`
Get thumbnail image data for artwork(s).

```python
# Single thumbnail as binary
thumb = tv.art().get_thumbnail('SAM-F0206')  # Returns bytes

# Single thumbnail as dict
thumb_dict = tv.art().get_thumbnail('SAM-F0206', as_dict=True)
# Returns: {'SAM-F0206.jpg': b'...binary...'}

# Multiple thumbnails as dict
thumbs = tv.art().get_thumbnail(['SAM-F0206', 'SAM-F0207'], as_dict=True)
# Returns: {'SAM-F0206.jpg': b'...', 'SAM-F0207.jpg': b'...'}
```

#### `get_thumbnail_list(content_id_list=[]) -> dict`
Get thumbnails (new API method, 2022+).

```python
thumbs = tv.art().get_thumbnail_list(['SAM-F0206', 'SAM-F0207'])
# Returns: {'SAM-F0206.jpg': b'...', 'SAM-F0207.jpg': b'...'}
```

---

### Art Mode Control

#### `get_artmode() -> str`
Get current art mode status.

```python
status = tv.art().get_artmode()
# Returns: 'on' or 'off'
```

#### `set_artmode(mode) -> None`
Turn art mode on or off.

```python
tv.art().set_artmode('on')
tv.art().set_artmode('off')
```

---

### Display Settings

#### `get_brightness() -> int or dict`
Get brightness level (0-100).

#### `set_brightness(value) -> dict`
Set brightness level (0-100).

#### `get_color_temperature() -> int or dict`
Get color temperature setting.

#### `set_color_temperature(value) -> dict`
Set color temperature.

#### `get_artmode_settings(setting='') -> dict`
Get various art mode settings.

```python
all_settings = tv.art().get_artmode_settings()
brightness = tv.art().get_artmode_settings('brightness')
color_temp = tv.art().get_artmode_settings('color_temperature')
motion_sens = tv.art().get_artmode_settings('motion_sensitivity')
motion_timer = tv.art().get_artmode_settings('motion_timer')
```

---

### Matte (Frame) Management

#### `get_matte_list(include_colour=False) -> list or tuple`
Get available matte frame styles from the TV.

```python
# Get matte types only
matte_types = tv.art().get_matte_list()
# Returns: [{'matte_type': 'none'}, {'matte_type': 'modern_neutral'}, ...]

# Get mattes and colors
matte_types, matte_colors = tv.art().get_matte_list(True)
```

**Matte Format:** `{style}_{color}` (e.g., `modern_neutral`, `flexible_apricot`)

**Common Styles:**
- `none` - No matte
- `modernthin` - Modern thin frame
- `modern` - Modern frame
- `modernwide` - Modern wide frame
- `flexible` - Flexible frame
- `shadowbox` - Shadow box style
- `panoramic` - Panoramic style

**Common Colors:**
- `neutral`, `antique`, `warm`, `polar`, `sand`
- `seafoam`, `sage`, `burgandy`, `navy`, `apricot`
- `byzantine`, `lavender`, `black`

#### `change_matte(content_id, matte_id=None, portrait_matte=None) -> None`
Change the matte frame on existing artwork.

```python
# Change landscape matte
tv.art().change_matte('SAM-F0206', 'modern_neutral')

# Change both landscape and portrait mattes
tv.art().change_matte('SAM-F0206', 'modern_neutral', 'modern_neutral')

# Remove matte
tv.art().change_matte('SAM-F0206', 'none')
```

---

### Slideshow Control

#### `get_slideshow_status() -> dict` (New API, 2022+)
```python
status = tv.art().get_slideshow_status()
# Returns: {'value': 'off', 'type': 'slideshow', 'category_id': 'MY-C0002'}
```

#### `set_slideshow_status(duration=0, type=True, category=2) -> dict` (New API, 2022+)
```python
# Enable random slideshow every 5 minutes
tv.art().set_slideshow_status(duration=5, type=True, category=2)

# Enable sequential slideshow every 10 minutes
tv.art().set_slideshow_status(duration=10, type=False, category=2)

# Disable slideshow
tv.art().set_slideshow_status(duration=0)
```

**Parameters:**
- `duration` (int): Minutes between changes (0 = off)
- `type` (bool): `True` for shuffled, `False` for sequential
- `category` (int): 2=My Photos, 4=Favourites, 8=Store

#### `get_auto_rotation_status() -> dict` (Old API, 2021-)
#### `set_auto_rotation_status(duration=0, type=True, category=2) -> dict` (Old API, 2021-)

Same parameters as slideshow methods.

---

### Photo Filters

#### `get_photo_filter_list() -> list`
```python
filters = tv.art().get_photo_filter_list()
# Returns: [{'id': 'FILTER_1', 'name': 'Sepia'}, ...]
```

#### `set_photo_filter(content_id, filter_id) -> None`
```python
tv.art().set_photo_filter('SAM-F0206', 'FILTER_1')
```

---

### Favorites

#### `set_favourite(content_id, status='on') -> dict`
```python
tv.art().set_favourite('SAM-F0206', 'on')   # Add to favorites
tv.art().set_favourite('SAM-F0206', 'off')  # Remove from favorites
```

---

### Rotation

#### `get_rotation() -> int`
```python
rotation = tv.art().get_rotation()
# Returns: 0 (unknown), 1 (landscape), 2 (portrait)
```

---

## Art Mode Methods (Async)

All async methods have identical signatures but must be awaited:

```python
from samsungtvws.async_art import SamsungTVAsyncArt

tv = SamsungTVAsyncArt('192.168.1.100', port=8002, token_file='token.txt')
await tv.start_listening()

# All methods must be awaited
await tv.supported()
await tv.get_api_version()
await tv.available('MY-C0002')
await tv.get_current()
await tv.select_image('SAM-F0206')
await tv.upload(file_data, file_type='png')
await tv.delete('MY-F0001')
await tv.get_thumbnail('SAM-F0206')
await tv.get_matte_list(True)
await tv.change_matte('SAM-F0206', 'modern_neutral')
# ... etc
```

### Additional Async-Only Methods

#### `start_listening() -> None`
**Required** before using async TV.

#### `close() -> None`
Close websocket connection.

#### `on() -> bool`
Check if TV is powered on.

#### `is_artmode() -> bool`
Check if TV is on AND in art mode.

#### `set_callback(trigger, callback)`
Register callback for art mode events.

```python
async def on_image_change(event, response):
    print(f'Image changed: {response}')

tv.set_callback('slideshow_image_changed', on_image_change)  # New API
tv.set_callback('auto_rotation_image_changed', on_image_change)  # Old API
tv.set_callback('image_selected', on_image_change)
```

**Common Events:**
- `slideshow_image_changed` (new API)
- `auto_rotation_image_changed` (old API)
- `image_selected`
- `favorite_changed`
- `art_mode_changed`
- `wakeup`
- `go_to_standby`

---

## Remote Control Methods

### Sending Keys

```python
tv.send_key("KEY_POWER")
tv.send_key("KEY_UP", times=3)
tv.hold_key("KEY_POWER", 2)  # Hold for 2 seconds
```

### Available Keys
```
KEY_POWER, KEY_HOME, KEY_MENU, KEY_SOURCE
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ENTER, KEY_RETURN
KEY_CHUP, KEY_CHDOWN, KEY_CH_LIST
KEY_VOLUP, KEY_VOLDOWN, KEY_MUTE
KEY_0 through KEY_9
KEY_RED, KEY_GREEN, KEY_YELLOW, KEY_BLUE
KEY_GUIDE, KEY_TOOLS, KEY_INFO
KEY_MUTI_VIEW (rotate on 2023 and earlier)
```

### App Management

```python
apps = tv.app_list()
tv.run_app('3201606009684')  # Launch by app ID
tv.open_browser('https://www.youtube.com')
```

---

## REST API Methods

```python
info = tv.rest_device_info()
is_on = tv.rest_power_state()
```

---

## Error Handling

```python
from samsungtvws import exceptions

try:
    tv.art().get_current()
except exceptions.ConnectionFailure as e:
    print(f"Could not connect: {e}")
except exceptions.ResponseError as e:
    print(f"API error: {e}")
except exceptions.HttpApiError as e:
    print(f"HTTP error: {e}")
```

---

## TV Compatibility & API Versions

### Detecting API Version

```python
api_version = tv.art().get_api_version()
version_num = int(api_version.replace('.', ''))

if version_num < 4000:
    # 2021 and earlier (Old API)
    # Use: get_thumbnail, get_auto_rotation_status
else:
    # 2022 and later (New API)
    # Use: get_thumbnail_list, get_slideshow_status
```

### Model Year Compatibility

| Year | API Version | Notes |
|------|-------------|-------|
| 2021 | 2.x | Old API, limited features |
| 2022 | 4.0+ | New API, full Art Mode |
| 2023 | 4.1+ | Enhanced settings |
| 2024 | 4.3+ | Additional sensors |

### Port Configuration

```python
# Remote control
tv = SamsungTVWS('192.168.1.100', port=8001)

# Art mode (most Frame TVs)
tv = SamsungTVWS('192.168.1.100', port=8002)
```

---

## Complete Example

```python
from samsungtvws.async_art import SamsungTVAsyncArt
import asyncio

async def main():
    tv = SamsungTVAsyncArt('192.168.1.100', port=8002, token_file='token.txt')
    await tv.start_listening()

    try:
        # Check support
        if not await tv.supported():
            print("Art Mode not supported")
            return

        # Get API version
        version = await tv.get_api_version()
        print(f"API: {version}")

        # Get available mattes from TV
        mattes = await tv.get_matte_list()
        print(f"Available mattes: {mattes}")

        # Upload image with matte
        content_id = await tv.upload(
            'photo.jpg',
            matte='modern_neutral',
            portrait_matte='modern_neutral'
        )
        print(f"Uploaded: {content_id}")

        # Display it
        await tv.select_image(content_id)

    finally:
        await tv.close()

asyncio.run(main())
```

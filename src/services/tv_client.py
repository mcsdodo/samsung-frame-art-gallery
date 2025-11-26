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

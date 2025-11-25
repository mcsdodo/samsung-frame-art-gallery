import os
from typing import Optional
from samsungtvws import SamsungTVWS

TV_IP = os.environ.get("TV_IP", "192.168.0.105")
TV_TIMEOUT = 10

class TVClient:
    _instance: Optional["TVClient"] = None

    def __init__(self):
        self._tv: Optional[SamsungTVWS] = None

    @classmethod
    def get_instance(cls) -> "TVClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_tv(self) -> SamsungTVWS:
        if self._tv is None:
            self._tv = SamsungTVWS(TV_IP, timeout=TV_TIMEOUT)
        return self._tv

    def get_status(self) -> dict:
        try:
            tv = self._get_tv()
            supported = tv.art().supported()
            return {"connected": True, "art_mode_supported": supported, "tv_ip": TV_IP}
        except Exception as e:
            self._tv = None
            return {"connected": False, "error": str(e), "tv_ip": TV_IP}

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

    def get_thumbnail(self, content_id: str) -> bytes:
        tv = self._get_tv()
        return tv.art().get_thumbnail(content_id)

    def get_matte_options(self) -> dict:
        return {
            "styles": ["none", "modernthin", "modern", "flexible"],
            "colors": ["neutral", "antique", "warm", "cold"]
        }


def get_tv_client() -> TVClient:
    return TVClient.get_instance()

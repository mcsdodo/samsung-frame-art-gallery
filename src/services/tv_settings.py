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

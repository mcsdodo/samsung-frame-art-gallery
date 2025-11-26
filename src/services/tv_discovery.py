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

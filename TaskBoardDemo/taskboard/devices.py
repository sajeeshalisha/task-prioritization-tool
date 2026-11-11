"""Works out which device a test case runs on from the text around it."""
import re

# Most important device first. This order is also the priority order for "Get Started".
DEVICE_ORDER = ("watchOS", "iOS", "macOS", "visionOS")

_PATTERNS = {
    "watchOS": re.compile(r"\b(watchos|apple watch|watch)\b", re.IGNORECASE),
    "iOS": re.compile(r"\b(ios|iphone|ipad)\b", re.IGNORECASE),
    "macOS": re.compile(r"\b(macos|macbook|mac)\b", re.IGNORECASE),
    "visionOS": re.compile(r"\b(visionos|vision pro)\b", re.IGNORECASE),
}


def device_in(text):
    """The most important device `text` mentions ("iOS + macOS - Sync" gives "iOS"), or ""."""
    for device in DEVICE_ORDER:
        if _PATTERNS[device].search(text or ""):
            return device
    return ""

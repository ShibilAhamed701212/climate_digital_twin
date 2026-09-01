from __future__ import annotations

import re
from pathlib import Path

from disaster_intelligence.domain.errors import ValidationError

ALLOWED_LAYER_NAMES = frozenset({"buildings", "roads", "amenities", "zonal", "relief"})
_LAYER_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_storage_name(name: str) -> str:
    """Reject path separators and parent segments; keep a single leaf filename."""
    if not name or name.strip() != name:
        raise ValidationError("Invalid storage name", "BAD_REQUEST")
    normalized = name.replace("\\", "/")
    if "/" in normalized or "\x00" in name:
        raise ValidationError("Storage name must be a file name, not a path", "BAD_REQUEST")
    leaf = Path(name).name
    if leaf != name or leaf in {".", ".."}:
        raise ValidationError("Storage name must be a file name, not a path", "BAD_REQUEST")
    return leaf


def safe_layer_name(name: str) -> str:
    if name not in ALLOWED_LAYER_NAMES and not _LAYER_RE.fullmatch(name):
        raise ValidationError("Invalid layer name", "BAD_REQUEST")
    if ".." in name or "/" in name or "\\" in name:
        raise ValidationError("Invalid layer name", "BAD_REQUEST")
    return name

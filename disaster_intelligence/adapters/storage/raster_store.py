from __future__ import annotations

from pathlib import Path

from disaster_intelligence.domain.paths import safe_storage_name


class FilesystemRasterStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, name: str, data: bytes) -> str:
        path = self._root / safe_storage_name(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def path_for(self, name: str) -> str:
        return str(self._root / safe_storage_name(name))

    def exists(self, uri: str) -> bool:
        return Path(uri).exists()

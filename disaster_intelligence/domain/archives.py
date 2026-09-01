from __future__ import annotations

import zipfile
from pathlib import Path

from disaster_intelligence.domain.errors import ValidationError


def safe_extract_zip(archive: Path, dest: Path, *, max_files: int = 32) -> list[Path]:
    """Extract zip members into dest using basenames only (no path traversal)."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_res = dest.resolve()
    written: list[Path] = []
    with zipfile.ZipFile(archive) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        if len(members) > max_files:
            raise ValidationError("Zip contains too many files")
        for info in members:
            name = Path(info.filename)
            if name.is_absolute() or ".." in name.parts:
                raise ValidationError("Zip path traversal rejected")
            target = (dest_res / name.name).resolve()
            if not str(target).startswith(str(dest_res)):
                raise ValidationError("Zip extract escaped destination")
            with zf.open(info) as src, target.open("wb") as out:
                out.write(src.read())
            written.append(target)
    return written

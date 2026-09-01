from __future__ import annotations

import struct
from pathlib import Path

from disaster_intelligence.domain.errors import ValidationError

TIFF_LE = b"II*\x00"
TIFF_BE = b"MM\x00*"
MAX_UPLOAD_MAGIC_READ = 16
MAX_TIFF_DIM = 8192
MAX_TIFF_PIXELS = 16_000_000


def sniff_tiff_magic(data: bytes) -> bool:
    return data[:4] == TIFF_LE or data[:4] == TIFF_BE


def validate_upload_bytes(
    data: bytes,
    filename: str,
    max_bytes: int,
) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".tif", ".tiff", ".cog"}:
        raise ValidationError("Only .tif, .tiff, or .cog uploads are allowed", "UNSUPPORTED_MEDIA")
    if len(data) > max_bytes:
        raise ValidationError("Upload exceeds size limit", "PAYLOAD_TOO_LARGE")
    if len(data) < 8 or not sniff_tiff_magic(data):
        raise ValidationError("File is not a valid GeoTIFF/TIFF", "INVALID_GEOTIFF")


def write_uint8_tiff(path: Path, array: list[list[int]], *, width: int, height: int) -> None:
    """Write an uncompressed little-endian uint8 grayscale TIFF (single strip)."""
    if width <= 0 or height <= 0 or width > MAX_TIFF_DIM or height > MAX_TIFF_DIM:
        raise ValidationError("TIFF dimensions are invalid", "INVALID_GEOTIFF")
    if width * height > MAX_TIFF_PIXELS:
        raise ValidationError("TIFF exceeds in-memory encoder limits", "PAYLOAD_TOO_LARGE")
    strip = bytes(array[r][c] for r in range(height) for c in range(width))
    ifd_count = 10
    header_size = 8
    ifd_size = 2 + ifd_count * 12 + 4
    strip_offset = header_size + ifd_size
    entries = [
        (256, 3, 1, width),
        (257, 3, 1, height),
        (258, 3, 1, 8),
        (259, 3, 1, 1),
        (262, 3, 1, 1),
        (273, 4, 1, strip_offset),
        (277, 3, 1, 1),
        (278, 3, 1, height),
        (279, 4, 1, len(strip)),
        (339, 3, 1, 1),
    ]
    buf = bytearray()
    buf += TIFF_LE
    buf += struct.pack("<I", 8)
    buf += struct.pack("<H", ifd_count)
    for tag, typ, count, value in entries:
        buf += struct.pack("<HHII", tag, typ, count, value)
    buf += struct.pack("<I", 0)
    buf += strip
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(buf))


def read_uint8_tiff(path: Path) -> tuple[list[list[int]], int, int]:
    data = path.read_bytes()
    if not sniff_tiff_magic(data):
        raise ValidationError("Not a TIFF", "INVALID_GEOTIFF")
    if data[:4] != TIFF_LE:
        raise ValidationError(
            "Only little-endian TIFF is supported without rasterio", "INVALID_GEOTIFF"
        )
    if len(data) < 8:
        raise ValidationError("TIFF header truncated", "INVALID_GEOTIFF")
    ifd = struct.unpack_from("<I", data, 4)[0]
    if ifd < 8 or ifd + 2 > len(data):
        raise ValidationError("TIFF IFD offset is out of range", "INVALID_GEOTIFF")
    count = struct.unpack_from("<H", data, ifd)[0]
    tags: dict[int, int] = {}
    for i in range(count):
        off = ifd + 2 + i * 12
        if off + 12 > len(data):
            raise ValidationError("TIFF IFD is truncated", "INVALID_GEOTIFF")
        tag, typ, n, value = struct.unpack_from("<HHII", data, off)
        tags[tag] = value
        _ = typ, n
    compression = tags.get(259, 1)
    if compression != 1:
        raise ValidationError(
            "Only uncompressed TIFF is supported without rasterio", "INVALID_GEOTIFF"
        )
    spp = tags.get(277, 1)
    if spp != 1:
        raise ValidationError("Only single-band uint8 TIFF is supported", "INVALID_GEOTIFF")
    bits = tags.get(258, 8)
    if bits != 8:
        raise ValidationError("Only 8-bit TIFF is supported without rasterio", "INVALID_GEOTIFF")
    width = tags.get(256, 0)
    height = tags.get(257, 0)
    strip_off = tags.get(273, 0)
    nbytes = tags.get(279, 0)
    if width <= 0 or height <= 0 or strip_off <= 0:
        raise ValidationError("TIFF is missing required tags", "INVALID_GEOTIFF")
    if width > MAX_TIFF_DIM or height > MAX_TIFF_DIM or width * height > MAX_TIFF_PIXELS:
        raise ValidationError(
            "TIFF dimensions exceed in-memory decoder limits", "PAYLOAD_TOO_LARGE"
        )
    expected = width * height
    if nbytes <= 0:
        nbytes = expected
    if nbytes < expected:
        raise ValidationError("TIFF strip is shorter than width*height", "INVALID_GEOTIFF")
    if strip_off + expected > len(data):
        raise ValidationError("TIFF strip offset is out of range", "INVALID_GEOTIFF")
    raw = data[strip_off : strip_off + expected]
    rows: list[list[int]] = []
    for r in range(height):
        start = r * width
        rows.append([raw[start + c] for c in range(width)])
    return rows, width, height


def write_float32_vv_vh(
    path: Path,
    vv: list[list[float]],
    vh: list[list[float]],
    *,
    west: float = 0.0,
    north: float = 0.0,
    xres: float = 1.0,
    yres: float = 1.0,
) -> None:
    """Uncompressed LE GeoTIFF, 2-sample float32, interleaved VV then VH per pixel."""
    height = len(vv)
    width = len(vv[0]) if vv else 0
    if height <= 0 or width <= 0 or height != len(vh) or width != len(vh[0]):
        raise ValidationError("VV and VH must be the same non-empty shape", "WRONG_INPUT_CHANNELS")
    if width > MAX_TIFF_DIM or height > MAX_TIFF_DIM or width * height > MAX_TIFF_PIXELS:
        raise ValidationError("TIFF dimensions exceed encoder limits", "PAYLOAD_TOO_LARGE")
    ifd_count = 13
    header_size = 8
    ifd_size = 2 + ifd_count * 12 + 4
    strip_offset = header_size + ifd_size
    nbytes = width * height * 8
    bits_packed = struct.unpack("<I", struct.pack("<HH", 32, 32))[0]
    fmt_packed = struct.unpack("<I", struct.pack("<HH", 3, 3))[0]
    scale_off = strip_offset + nbytes
    tie_off = scale_off + 24
    entries = [
        (256, 3, 1, width),
        (257, 3, 1, height),
        (258, 3, 2, bits_packed),
        (259, 3, 1, 1),
        (262, 3, 1, 2),
        (273, 4, 1, strip_offset),
        (277, 3, 1, 2),
        (278, 3, 1, height),
        (279, 4, 1, nbytes),
        (284, 3, 1, 1),
        (339, 3, 2, fmt_packed),
        (33550, 12, 3, scale_off),
        (33922, 12, 6, tie_off),
    ]
    buf = bytearray()
    buf += TIFF_LE
    buf += struct.pack("<I", 8)
    buf += struct.pack("<H", ifd_count)
    for tag, typ, count, value in entries:
        buf += struct.pack("<HHII", tag, typ, count, value)
    buf += struct.pack("<I", 0)
    for r in range(height):
        for c in range(width):
            buf += struct.pack("<ff", float(vv[r][c]), float(vh[r][c]))
    buf += struct.pack("<ddd", float(xres), float(abs(yres)), 0.0)
    buf += struct.pack("<dddddd", 0.0, 0.0, 0.0, float(west), float(north), 0.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(buf))


def _ifd_entries(data: bytes) -> dict[int, tuple[int, int, int]]:
    if data[:4] != TIFF_LE:
        raise ValidationError(
            "Only little-endian TIFF is supported without rasterio", "INVALID_GEOTIFF"
        )
    ifd = struct.unpack_from("<I", data, 4)[0]
    if ifd < 8 or ifd + 2 > len(data):
        raise ValidationError("TIFF IFD offset is out of range", "INVALID_GEOTIFF")
    count = struct.unpack_from("<H", data, ifd)[0]
    tags: dict[int, tuple[int, int, int]] = {}
    for i in range(count):
        off = ifd + 2 + i * 12
        if off + 12 > len(data):
            raise ValidationError("TIFF IFD is truncated", "INVALID_GEOTIFF")
        tag, typ, n, value = struct.unpack_from("<HHII", data, off)
        tags[tag] = (typ, n, value)
    return tags


def read_float32_vv_vh(path: Path) -> tuple[list[list[float]], list[list[float]], dict[str, float]]:
    data = path.read_bytes()
    if not sniff_tiff_magic(data):
        raise ValidationError("Not a TIFF", "INVALID_GEOTIFF")
    tags = _ifd_entries(data)
    compression = tags.get(259, (3, 1, 1))[2]
    if compression != 1:
        raise ValidationError(
            "Compressed Sentinel-1 GeoTIFF requires rasterio; this decoder is uncompressed only",
            "INVALID_GEOTIFF",
        )
    spp = tags.get(277, (3, 1, 1))[2]
    if spp != 2:
        raise ValidationError("Expected 2-channel VV/VH TIFF", "WRONG_INPUT_CHANNELS")
    _bits_typ, bits_n, bits_val = tags.get(258, (3, 1, 8))
    bits = bits_val if bits_n == 1 else struct.unpack_from("<H", struct.pack("<I", bits_val), 0)[0]
    if bits != 32:
        raise ValidationError("Expected 32-bit float VV/VH TIFF", "INVALID_GEOTIFF")
    width = tags.get(256, (3, 1, 0))[2]
    height = tags.get(257, (3, 1, 0))[2]
    strip_off = tags.get(273, (4, 1, 0))[2]
    if width <= 0 or height <= 0 or strip_off <= 0:
        raise ValidationError("TIFF is missing required tags", "INVALID_GEOTIFF")
    if width > MAX_TIFF_DIM or height > MAX_TIFF_DIM or width * height > MAX_TIFF_PIXELS:
        raise ValidationError("TIFF dimensions exceed decoder limits", "PAYLOAD_TOO_LARGE")
    expected = width * height * 8
    if strip_off + expected > len(data):
        raise ValidationError("TIFF strip offset is out of range", "INVALID_GEOTIFF")
    vv: list[list[float]] = []
    vh: list[list[float]] = []
    pos = strip_off
    for _r in range(height):
        row_vv: list[float] = []
        row_vh: list[float] = []
        for _c in range(width):
            a, b = struct.unpack_from("<ff", data, pos)
            row_vv.append(a)
            row_vh.append(b)
            pos += 8
        vv.append(row_vv)
        vh.append(row_vh)
    geo = {"west": 0.0, "north": 0.0, "xres": 1.0, "yres": 1.0, "width": float(width), "height": float(height)}
    if 33550 in tags:
        off = tags[33550][2]
        if off + 24 <= len(data):
            xres, yres, _z = struct.unpack_from("<ddd", data, off)
            geo["xres"] = float(xres)
            geo["yres"] = float(yres)
    if 33922 in tags:
        off = tags[33922][2]
        if off + 48 <= len(data):
            _i, _j, _k, west, north, _z = struct.unpack_from("<dddddd", data, off)
            geo["west"] = float(west)
            geo["north"] = float(north)
    return vv, vh, geo


def read_uint8_window(
    path: Path, x0: int, y0: int, x1: int, y1: int
) -> tuple[list[list[int]], int, int]:
    """Read a window without allocating unused columns (rows still decoded from the strip)."""
    rows, width, height = read_uint8_tiff(path)
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValidationError("TIFF window is empty", "INVALID_GEOTIFF")
    window = [row[x0:x1] for row in rows[y0:y1]]
    return window, x1 - x0, y1 - y0


def iter_uint8_row_chunks(path: Path, chunk_rows: int = 256) -> list[tuple[int, list[list[int]]]]:
    """Chunked row groups for streaming-style mask processing."""
    rows, _width, height = read_uint8_tiff(path)
    size = max(1, chunk_rows)
    out: list[tuple[int, list[list[int]]]] = []
    for start in range(0, height, size):
        out.append((start, rows[start : start + size]))
    return out

"""Download official EO checkpoints into MODEL_WEIGHTS_DIR (never from unofficial mirrors)."""

from __future__ import annotations

import argparse
import hashlib
import ssl
import sys
import urllib.request
import zipfile
from pathlib import Path

UNET_URL = (
    "https://huggingface.co/Governor6191/sar-flood-extent-unet-resnet34/resolve/main/model.pt"
)
UNET_PAGE = "https://huggingface.co/Governor6191/sar-flood-extent-unet-resnet34"
CHANGEFORMER_URL = (
    "https://github.com/wgcban/ChangeFormer/releases/download/v0.1.0/"
    "CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_"
    "multi_infer_False_shuffle_AB_False_embed_dim_256.zip"
)

_CTX = ssl.create_default_context()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "climate-digital-twin-die/2.1"},
    )
    print(f"GET {url}")
    with urllib.request.urlopen(req, context=_CTX, timeout=600) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")


def _weights_root(explicit: str) -> Path:
    if explicit:
        return Path(explicit)
    preferred = Path(r"D:\ClimateDigitalTwin\models")
    if preferred.parent.exists():
        return preferred
    return Path("models/eo")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="")
    parser.add_argument("--skip-changeformer", action="store_true")
    args = parser.parse_args()
    root = _weights_root(args.dir)
    unet = root / "flood" / "unet" / "model.pt"
    try:
        _download(UNET_URL, unet)
    except Exception as exc:
        print(f"U-Net download failed: {exc}", file=sys.stderr)
        return 1
    if unet.stat().st_size < 1_000_000:
        print("U-Net file too small; refusing to register", file=sys.stderr)
        return 1
    print(f"U-Net sha256={_sha256(unet)}")
    print(f"source={UNET_PAGE} license=MIT")
    if not args.skip_changeformer:
        zpath = root / "change" / "changeformer" / "official.zip"
        try:
            _download(CHANGEFORMER_URL, zpath)
            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(zpath.parent)
            print(f"ChangeFormer extracted under {zpath.parent}")
            ckpt = next(zpath.parent.rglob("*.pt"), None)
            if ckpt is not None:
                print(f"ChangeFormer checkpoint {ckpt} sha256={_sha256(ckpt)}")
        except Exception as exc:
            print(f"ChangeFormer download skipped/failed: {exc}", file=sys.stderr)
    print("SegFormer/Mask2Former: no compatible flood/EO checkpoint (not downloaded).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

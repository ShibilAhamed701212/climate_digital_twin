#!/usr/bin/env python
"""Direct U-Net inference verification."""
import os
import sys
import time
import numpy as np

# Set environment before imports
os.environ['MODEL_WEIGHTS_UNET'] = 'models/checkpoints/flood/unet-sen1floods11-resnet34.pt'
os.environ['MODEL_FLOOD'] = 'unet'
os.environ['MODEL_FLOOD_FALLBACK'] = 'none'
os.environ['MODEL_DEVICE'] = 'cpu'

# Add project root to path
sys.path.insert(0, os.getcwd())

from disaster_intelligence.inference.unet import UNetFloodRunner

# Create synthetic VV/VH data (sigma0 dB, typical range)
np.random.seed(42)
height, width = 512, 512

# VV: typically around -12 dB for water, -7 dB for land
# VH: typically around -18 dB for water, -12 dB for land
vv = np.random.normal(-10, 3, (height, width)).astype(np.float32)
vh = np.random.normal(-15, 3, (height, width)).astype(np.float32)

print(f"VV stats: mean={vv.mean():.2f}, std={vv.std():.2f}, min={vv.min():.2f}, max={vv.max():.2f}")
print(f"VH stats: mean={vh.mean():.2f}, std={vh.std():.2f}, min={vh.min():.2f}, max={vh.max():.2f}")

# Convert to list format
vv_list = vv.tolist()
vh_list = vh.tolist()

# Run inference
runner = UNetFloodRunner()
start = time.perf_counter()
mask = runner.mask_from_vv_vh(vv_list, vh_list)
elapsed = time.perf_counter() - start

print(f"\n=== U-Net Inference Results ===")
print(f"Model ID: {runner.model_id}")
print(f"Device: {runner.device}")
print(f"Runtime: {runner.runtime_name}")
print(f"Checkpoint SHA256: {runner.checkpoint_sha256}")
print(f"Fallback used: {runner.fallback_used}")
print(f"Fallback reason: {runner.fallback_reason}")
print(f"Processing time: {runner.processing_ms:.2f} ms")
print(f"Wall time: {elapsed*1000:.2f} ms")

mask_arr = np.array(mask, dtype=np.uint8)
water_pixels = int(mask_arr.sum())
total_pixels = mask_arr.size
water_fraction = water_pixels / total_pixels

print(f"Mask shape: {mask_arr.shape}")
print(f"Water pixels: {water_pixels}")
print(f"Total pixels: {total_pixels}")
print(f"Water fraction: {water_fraction:.4f}")

provenance = runner.provenance()
print(f"\n=== Provenance ===")
for k, v in provenance.items():
    print(f"  {k}: {v}")

# Verify expected values
expected_sha256 = "45d57e0087f2d3054da8f05cf2a655e2a8f4294417a29334d30addb7950dede9"
assert runner.checkpoint_sha256 == expected_sha256, f"SHA256 mismatch: {runner.checkpoint_sha256}"
assert runner.model_id == "unet-sen1floods11-resnet34", f"Model ID mismatch: {runner.model_id}"
assert runner.fallback_used == False, f"Fallback was used: {runner.fallback_reason}"
assert provenance['sensor'] == 'sentinel-1', f"Sensor mismatch: {provenance['sensor']}"
assert provenance['polarization'] == 'VV+VH', f"Polarization mismatch: {provenance['polarization']}"
assert provenance['fallback_used'] == 'false', f"Fallback used in provenance: {provenance['fallback_used']}"

print("\n=== ALL ASSERTIONS PASSED ===")
print("U-Net checkpoint verified and inference successful!")
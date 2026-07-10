"""Model tests using torch guard — safe on Windows.

All torch-dependent tests run in subprocesses to avoid C++ SEH crashes.
"""

import os
import subprocess
import sys

import pytest

from tests.helpers.torch_guard import safe_import_torch

_TORCH_OK = safe_import_torch()
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

_MODEL_TESTS = {
    "lstm": """
import torch
from models.lstm.model import LSTMModel
model = LSTMModel(n_features=10, n_targets=1)
x = torch.randn(32, 10, 10)
out = model(x)
assert out.shape == (32, 1), f"Expected (32,1), got {out.shape}"
print("LSTM OK:", out.shape)
""",
    "transformer": """
import torch
from models.transformer.model import TransformerModel
model = TransformerModel(n_features=10, n_targets=1, d_model=64, nhead=4)
x = torch.randn(32, 10, 10)
out = model(x)
assert out.shape == (32, 1), f"Expected (32,1), got {out.shape}"
print("Transformer OK:", out.shape)
""",
    "patchtst": """
import torch
from models.patchtst.model import PatchTSTModel
model = PatchTSTModel(n_features=10, n_targets=1, d_model=64)
x = torch.randn(32, 10, 10)
out = model(x)
print("PatchTST OK:", out.shape)
""",
    "timemixer": """
import torch
from models.timemixer.model import TimeMixerModel
model = TimeMixerModel(n_features=10, n_targets=1, d_model=64)
x = torch.randn(32, 10, 10)
out = model(x)
print("TimeMixer OK:", out.shape)
""",
    "itransformer": """
import torch
from models.itransformer.model import ITransformerModel
model = ITransformerModel(n_features=10, n_targets=1, d_model=64)
x = torch.randn(32, 10, 10)
out = model(x)
print("iTransformer OK:", out.shape)
""",
    "registry": """
from models.registry import ModelRegistry
registry = ModelRegistry()
models_list = registry.list_models()
assert isinstance(models_list, list)
print("ModelRegistry OK:", len(models_list), "models")
""",
}


def test_torch_availability():
    assert _TORCH_OK, "torch not available (probe failed)"


@pytest.mark.skipif(not _TORCH_OK, reason="torch unavailable (C++ crash guard)")
@pytest.mark.parametrize("model_name,code", list(_MODEL_TESTS.items()))
def test_model_in_subprocess(model_name, code):
    setup = f"import sys; sys.path.insert(0, {_PROJECT_ROOT!r})\n"
    result = subprocess.run(
        [sys.executable, "-c", setup + code],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=_PROJECT_ROOT,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        pytest.fail(f"{model_name} failed (exit {result.returncode}):\n{result.stderr}")

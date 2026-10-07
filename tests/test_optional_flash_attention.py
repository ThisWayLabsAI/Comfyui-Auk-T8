from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_seedvr_style_stub_does_not_block_torch_attention():
    root = Path(__file__).resolve().parents[1]
    script = r"""
import importlib
import importlib.util
import importlib.machinery
import sys
import types
from pathlib import Path
import torch

root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    "auk_flash_stub_test", root / "__init__.py",
    submodule_search_locations=[str(root)],
)
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)

# Reproduce SeedVR2's missing/broken FlashAttention compatibility placeholder.
stub = types.ModuleType("flash_attn")
stub.__spec__ = importlib.machinery.ModuleSpec("flash_attn", None)
stub.__path__ = []
stub.flash_attn_func = None
stub.flash_attn_varlen_func = None
sys.modules["flash_attn"] = stub

modules = importlib.import_module("auk_flash_stub_test.auk_core.model.modules")
assert not modules.FLASH_ATTN_AVAILABLE
assert modules.AttnProcessor().attn_backend == "torch"
assert modules.JointAttnProcessor().attn_backend == "torch"
attention = modules.Attention(modules.AttnProcessor(), dim=8, heads=2, dim_head=4)
audio_features = torch.randn(1, 5, 8)
output = attention(audio_features)
assert output.shape == audio_features.shape
assert torch.isfinite(output).all()
for processor in (modules.AttnProcessor, modules.JointAttnProcessor):
    try:
        processor(attn_backend="flash_attn")
    except RuntimeError as error:
        assert "unavailable or incomplete" in str(error)
    else:
        raise AssertionError("Explicit FlashAttention must reject the stub")

# Import the actual inference entrypoint without allocating model weights.
importlib.import_module("auk_flash_stub_test.auk_core.infer.infer_auk")
assert sys.modules["flash_attn"] is stub
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(root)],
        capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr

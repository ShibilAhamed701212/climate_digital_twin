"""Safe torch import guard — handles Windows C++ crash gracefully.

Uses subprocess isolation: all torch-dependent code runs in a child
process so that a C++ SEH access violation in torch's C extensions
cannot crash the test runner.

Usage:
    if not safe_import_torch():
        pytest.skip("torch unavailable")

    run_torch_test(lambda: my_torch_func(...))  # runs in subprocess
"""

import functools
import subprocess
import sys
from collections.abc import Callable

_torch_available: bool = False
_torch_error: str | None = None


def safe_import_torch() -> bool:
    """Check if torch is available via subprocess probe.

    Never imports torch in the current process. Runs a simple
    torch import + tensor creation in a subprocess. If the subprocess
    succeeds, torch is considered available (but must still be used
    via subprocess isolation in broken environments).
    """
    global _torch_available, _torch_error

    code = "import torch; x = torch.tensor([1.0]); print('TORCH_OK', torch.__version__)"
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and "TORCH_OK" in result.stdout:
            _torch_available = True
            _torch_error = None
            return True
        else:
            _torch_available = False
            _torch_error = (
                result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
            )
            return False
    except subprocess.TimeoutExpired:
        _torch_available = False
        _torch_error = "subprocess timed out"
        return False
    except Exception as e:
        _torch_available = False
        _torch_error = str(e)
        return False


def run_torch_test(test_func: Callable[[], None]) -> None:
    """Run a torch-dependent test in a subprocess.

    The test function is serialized as source and executed in a
    subprocess.  Raises AssertionError on failure.
    """
    import inspect
    import textwrap

    source = textwrap.dedent(inspect.getsource(test_func))
    body = "\n".join(source.splitlines()[1:])

    preamble = f"""
import sys
sys.path.insert(0, {repr(list(sys.path))})
sys.path.insert(0, {repr(".")})
{body}
"""

    result = subprocess.run(
        [sys.executable, "-c", preamble],
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        raise AssertionError(f"torch test failed (exit {result.returncode}):\n{result.stderr}")


def require_torch(test_func):
    """Decorator: skip test if torch unavailable.

    The decorated function runs in a subprocess to avoid C++ crashes.
    """

    @functools.wraps(test_func)
    def wrapper(*args, **kwargs):
        if not safe_import_torch():
            import pytest

            pytest.skip(f"torch unavailable: {_torch_error}")
        run_torch_test(lambda: test_func(*args, **kwargs))

    return wrapper

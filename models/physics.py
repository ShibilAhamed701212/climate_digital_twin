"""Physics Validation Layer — Safety Constraints for Climate Predictions.

Ensures model predictions satisfy basic physical constraints before they
are returned to callers. This is a **SAFETY LAYER**, not an intelligence
layer. It does NOT improve forecast accuracy — it only guarantees that
predictions are physically plausible.

Physics Validation
    ≠
Physics Simulation

What this module does:
  - Clamp rainfall to [0, rainfall_upper]
  - Ensure Tmin ≤ Tmax by swapping if violated
  - Clamp temperatures to [temp_lower, temp_upper]

What this module does NOT do:
  - No seasonal adjustments
  - No climatology
  - No interpolation or smoothing
  - No statistical or AI-based correction
  - No conservation equations
  - No scenario or what-if modelling
  - No physics simulation
"""

import logging

import torch

logger = logging.getLogger(__name__)


# Default physical bounds for climate variables.
# These are intentionally conservative — they prevent obviously impossible
# values without constraining legitimate climate variation.
_DEFAULT_RAINFALL_UPPER: float = 500.0  # mm/day — extreme tropical rainfall
_DEFAULT_TEMP_LOWER: float = -10.0  # °C
_DEFAULT_TEMP_UPPER: float = 55.0  # °C


class PhysicsValidator:
    """Validates and corrects climate predictions to satisfy physical constraints.

    Operates on prediction tensors of shape ``(batch, n_targets)`` where
    columns follow the ``target_names`` order (default: Rainfall, MaxTemp, MinTemp).

    The validator is:
      - **Deterministic** — same input always produces same output
      - **Idempotent** — applying validation twice yields the same result
      - **Stateless** — no internal state changes between calls
      - **Thread-safe** — all operations are pure tensor computations
      - **Model-agnostic** — works with any forecasting model's output

    Parameters
    ----------
    rainfall_upper : float
        Maximum allowable rainfall in mm/day (default: 500.0).
    temp_lower : float
        Minimum allowable temperature in °C (default: -10.0).
    temp_upper : float
        Maximum allowable temperature in °C (default: 55.0).
    target_names : list of str, optional
        Ordered list of target variable names. If ``None``, defaults to
        ``["Rainfall", "MaxTemp", "MinTemp"]``. The validator uses
        index-based column lookups derived from this list.

    Examples
    --------
    >>> import torch
    >>> v = PhysicsValidator()
    >>> preds = torch.tensor([[-5.0, 30.0, 35.0]])  # negative rain, Tmin > Tmax
    >>> corrected = v.validate(preds)
    >>> corrected[0, 0] >= 0  # rainfall clamped
    tensor(True)
    >>> corrected[0, 1] >= corrected[0, 2]  # Tmax >= Tmin (swapped)
    tensor(True)
    """

    def __init__(
        self,
        rainfall_upper: float = _DEFAULT_RAINFALL_UPPER,
        temp_lower: float = _DEFAULT_TEMP_LOWER,
        temp_upper: float = _DEFAULT_TEMP_UPPER,
        target_names: list[str] | None = None,
    ) -> None:
        self.rainfall_upper = rainfall_upper
        self.temp_lower = temp_lower
        self.temp_upper = temp_upper

        if target_names is None:
            target_names = ["Rainfall", "MaxTemp", "MinTemp"]
        self.target_names = target_names

        # Build column index mapping from variable name to column position.
        self._col_index: dict[str, int] = {name: idx for idx, name in enumerate(target_names)}

    @staticmethod
    def _resolve_idx(n_cols: int, default_idx: int) -> int | None:
        """Return *default_idx* if it is valid for *n_cols*, else ``None``."""
        return default_idx if default_idx < n_cols else None

    def validate(self, predictions: torch.Tensor) -> torch.Tensor:
        """Validate and correct a batch of predictions in-place.

        Applies the following corrections in order:

        1. Clamp rainfall (column 0) to ``[0, rainfall_upper]``.
        2. If the tensor has 3+ columns, ensure ``Tmax >= Tmin`` (cols 1, 2)
           by swapping values if violated.
        3. Clamp temperature columns to ``[temp_lower, temp_upper]``.

        Corrections are applied per-column based on how many targets the
        tensor contains.  A 1-column tensor only gets rainfall clipping;
        a 2-column tensor gets rainfall + temperature clipping without
        the Tmin/Tmax swap; a 3-column tensor gets the full treatment.

        Parameters
        ----------
        predictions : torch.Tensor
            Tensor of shape ``(batch, n_targets)`` or ``(n_targets,)``.
            Must be a floating-point tensor.

        Returns
        -------
        torch.Tensor
            Corrected tensor with the same shape and dtype as the input.

        Raises
        ------
        TypeError
            If ``predictions`` is not a floating-point tensor.
        ValueError
            If ``predictions`` is not 1-D or 2-D.

        Examples
        --------
        >>> v = PhysicsValidator()
        >>> batch = torch.tensor([[-1.0, 40.0, 25.0], [10.0, 30.0, 22.0]])
        >>> result = v.validate(batch)
        >>> result[0, 0]  # rainfall clamped to 0
        tensor(0.)
        >>> result.shape == batch.shape
        True
        """
        if not predictions.is_floating_point():
            raise TypeError(f"Expected floating-point tensor, got {predictions.dtype}")
        if predictions.ndim not in (1, 2):
            raise ValueError(f"Expected 1-D or 2-D tensor, got {predictions.ndim}-D")

        # Work with a 2D view to avoid branching logic in corrections.
        orig_shape = predictions.shape
        flat = predictions.unsqueeze(0) if predictions.ndim == 1 else predictions

        n_cols: int = flat.shape[1]

        # Resolve which columns exist in this tensor.
        rain_idx: int | None = self._resolve_idx(n_cols, self._col_index.get("Rainfall", 0))
        tmax_idx: int | None = self._resolve_idx(n_cols, self._col_index.get("MaxTemp", 1))
        tmin_idx: int | None = self._resolve_idx(n_cols, self._col_index.get("MinTemp", 2))

        # 1. Clamp rainfall to [0, rainfall_upper].
        if rain_idx is not None:
            flat[:, rain_idx] = flat[:, rain_idx].clamp(min=0.0, max=self.rainfall_upper)

        # 2. Ensure Tmax >= Tmin by swapping where violated (only possible
        #    when both temperature columns exist).
        if tmax_idx is not None and tmin_idx is not None:
            tmax_vals = flat[:, tmax_idx].clone()
            tmin_vals = flat[:, tmin_idx].clone()
            swap_mask = tmax_vals < tmin_vals
            if swap_mask.any():
                flat[:, tmax_idx] = torch.where(swap_mask, tmin_vals, tmax_vals)
                flat[:, tmin_idx] = torch.where(swap_mask, tmax_vals, tmin_vals)

        # 3. Clamp temperature columns to [temp_lower, temp_upper].
        for temp_idx in (tmax_idx, tmin_idx):
            if temp_idx is not None:
                flat[:, temp_idx] = flat[:, temp_idx].clamp(
                    min=self.temp_lower, max=self.temp_upper
                )

        return flat.view(orig_shape)

    def validate_single(
        self, rainfall: float, max_temp: float, min_temp: float
    ) -> tuple[float, float, float]:
        """Validate a single set of climate variable predictions.

        Convenience wrapper around :meth:`validate` for scalar inputs.
        Returns corrected ``(rainfall, max_temp, min_temp)``.

        Parameters
        ----------
        rainfall : float
            Predicted rainfall in mm.
        max_temp : float
            Predicted maximum temperature in °C.
        min_temp : float
            Predicted minimum temperature in °C.

        Returns
        -------
        tuple of (float, float, float)
            Corrected ``(rainfall, max_temp, min_temp)``.
        """
        tensor = torch.tensor([[rainfall, max_temp, min_temp]], dtype=torch.float32)
        corrected = self.validate(tensor)
        return (
            float(corrected[0, 0]),
            float(corrected[0, 1]),
            float(corrected[0, 2]),
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"rainfall_upper={self.rainfall_upper}, "
            f"temp_lower={self.temp_lower}, "
            f"temp_upper={self.temp_upper})"
        )

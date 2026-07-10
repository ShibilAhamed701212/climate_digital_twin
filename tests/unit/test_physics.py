"""Unit tests for models/physics.py — PhysicsValidator.

Tests cover:
  - Rainfall constraints (negative, zero, valid, upper bound)
  - Temperature constraints (Tmin vs Tmax swap, lower bound, upper bound)
  - General behaviour (batches, 1-D, idempotence, determinism, errors)
"""

import pytest

try:
    import torch
except (ImportError, OSError):
    pytest.skip("torch not available or DLL failure", allow_module_level=True)

from models.physics import PhysicsValidator

# ──────────────────────────────────────────────
# Rainfall validation
# ──────────────────────────────────────────────


class TestRainfallValidation:
    """Rainfall must be in [0, rainfall_upper]."""

    def test_negative_rainfall_clamped_to_zero(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-5.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 0.0

    def test_negative_rainfall_batch(self):
        v = PhysicsValidator()
        preds = torch.tensor(
            [
                [-1.0, 30.0, 20.0],
                [-100.0, 25.0, 18.0],
                [10.0, 35.0, 22.0],
            ]
        )
        result = v.validate(preds)
        assert result[0, 0] == 0.0
        assert result[1, 0] == 0.0
        assert result[2, 0] == 10.0  # unchanged

    def test_zero_rainfall_unchanged(self):
        v = PhysicsValidator()
        preds = torch.tensor([[0.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 0.0

    def test_valid_rainfall_unchanged(self):
        v = PhysicsValidator()
        preds = torch.tensor([[25.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 25.0

    def test_rainfall_at_upper_bound_unchanged(self):
        v = PhysicsValidator(rainfall_upper=500.0)
        preds = torch.tensor([[500.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 500.0

    def test_rainfall_above_upper_bound_clamped(self):
        v = PhysicsValidator(rainfall_upper=500.0)
        preds = torch.tensor([[999.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 500.0

    def test_rainfall_custom_upper_bound(self):
        v = PhysicsValidator(rainfall_upper=200.0)
        preds = torch.tensor([[250.0, 30.0, 20.0]])
        result = v.validate(preds)
        assert result[0, 0] == 200.0


# ──────────────────────────────────────────────
# Temperature validation
# ──────────────────────────────────────────────


class TestTemperatureConstraint:
    """Tmax must be >= Tmin. Both must be within [temp_lower, temp_upper]."""

    def test_valid_temperatures_unchanged(self):
        v = PhysicsValidator()
        preds = torch.tensor([[10.0, 35.0, 22.0]])
        result = v.validate(preds)
        assert result[0, 1] == 35.0  # Tmax
        assert result[0, 2] == 22.0  # Tmin

    def test_tmin_greater_than_tmax_swapped(self):
        v = PhysicsValidator()
        preds = torch.tensor([[10.0, 25.0, 35.0]])  # Tmin=35 > Tmax=25
        result = v.validate(preds)
        assert result[0, 1] == 35.0  # Tmax gets the higher value
        assert result[0, 2] == 25.0  # Tmin gets the lower value

    def test_tmin_greater_than_tmax_batch(self):
        v = PhysicsValidator()
        preds = torch.tensor(
            [
                [10.0, 30.0, 20.0],  # valid
                [10.0, 20.0, 30.0],  # Tmin > Tmax
                [10.0, 35.0, 40.0],  # Tmin > Tmax
            ]
        )
        result = v.validate(preds)
        assert result[0, 1] == 30.0 and result[0, 2] == 20.0
        assert result[1, 1] == 30.0 and result[1, 2] == 20.0  # swapped
        assert result[2, 1] == 40.0 and result[2, 2] == 35.0  # swapped

    def test_equal_temperatures_unchanged(self):
        v = PhysicsValidator()
        preds = torch.tensor([[10.0, 30.0, 30.0]])
        result = v.validate(preds)
        assert result[0, 1] == 30.0
        assert result[0, 2] == 30.0

    def test_temperature_at_lower_bound(self):
        v = PhysicsValidator(temp_lower=-10.0)
        preds = torch.tensor([[10.0, -10.0, -10.0]])
        result = v.validate(preds)
        assert result[0, 1] == -10.0
        assert result[0, 2] == -10.0

    def test_temperature_below_lower_bound_clamped(self):
        v = PhysicsValidator(temp_lower=-10.0)
        preds = torch.tensor([[10.0, -20.0, -30.0]])
        result = v.validate(preds)
        assert result[0, 1] == -10.0
        assert result[0, 2] == -10.0

    def test_temperature_at_upper_bound(self):
        v = PhysicsValidator(temp_upper=55.0)
        preds = torch.tensor([[10.0, 55.0, 40.0]])
        result = v.validate(preds)
        assert result[0, 1] == 55.0
        assert result[0, 2] == 40.0

    def test_temperature_above_upper_bound_clamped(self):
        v = PhysicsValidator(temp_upper=55.0)
        preds = torch.tensor([[10.0, 60.0, 65.0]])
        result = v.validate(preds)
        assert result[0, 1] == 55.0
        assert result[0, 2] == 55.0

    def test_custom_temperature_bounds(self):
        v = PhysicsValidator(temp_lower=-5.0, temp_upper=45.0)
        preds = torch.tensor([[10.0, 50.0, -10.0]])
        result = v.validate(preds)
        assert result[0, 1] == 45.0
        assert result[0, 2] == -5.0


# ──────────────────────────────────────────────
# Combined constraints
# ──────────────────────────────────────────────


class TestCombinedValidation:
    """Multiple constraint violations handled in a single pass."""

    def test_negative_rain_and_tmin_gt_tmax(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-5.0, 20.0, 30.0]])
        result = v.validate(preds)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 30.0
        assert result[0, 2] == 20.0

    def test_all_violations_single_batch(self):
        v = PhysicsValidator()
        preds = torch.tensor(
            [
                [-1.0, 20.0, 30.0],  # neg rain, Tmin>Tmax
                [600.0, 35.0, 25.0],  # excess rain
                [10.0, 70.0, 80.0],  # temp above upper, Tmin>Tmax
            ]
        )
        result = v.validate(preds)
        # Row 0
        assert result[0, 0] == 0.0
        assert result[0, 1] == 30.0
        assert result[0, 2] == 20.0
        # Row 1
        assert result[1, 0] == 500.0
        assert result[1, 1] == 35.0
        assert result[1, 2] == 25.0
        # Row 2
        assert result[2, 0] == 10.0
        assert result[2, 1] == 55.0
        assert result[2, 2] == 55.0


# ──────────────────────────────────────────────
# General behaviour
# ──────────────────────────────────────────────


class TestGeneralBehaviour:
    """Determinism, idempotence, shape handling, errors."""

    def test_already_valid_predictions_unchanged(self):
        v = PhysicsValidator()
        preds = torch.tensor([[25.0, 32.0, 20.0]])
        result = v.validate(preds)
        assert torch.equal(result, preds)

    def test_idempotent(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-5.0, 35.0, 40.0], [600.0, 20.0, 15.0]])
        once = v.validate(preds)
        twice = v.validate(once)
        assert torch.equal(once, twice)

    def test_idempotent_single(self):
        v = PhysicsValidator()
        preds = torch.tensor([-1.0, 30.0, 25.0])
        once = v.validate(preds)
        twice = v.validate(once)
        assert torch.equal(once, twice)

    def test_deterministic(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-5.0, 35.0, 40.0]])
        r1 = v.validate(preds.clone())
        r2 = v.validate(preds.clone())
        assert torch.equal(r1, r2)

    def test_deterministic_multiple_calls(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-1.0, 20.0, 30.0]])
        results = [v.validate(preds.clone()) for _ in range(10)]
        assert all(torch.equal(results[0], r) for r in results[1:])

    def test_1d_tensor(self):
        v = PhysicsValidator()
        preds = torch.tensor([-5.0, 30.0, 25.0])
        result = v.validate(preds)
        assert result.shape == (3,)
        assert result[0] == 0.0
        assert result[1] == 30.0
        assert result[2] == 25.0

    def test_1d_tensor_with_swap(self):
        v = PhysicsValidator()
        preds = torch.tensor([10.0, 20.0, 35.0])
        result = v.validate(preds)
        assert result[1] == 35.0
        assert result[2] == 20.0

    def test_batch_of_one(self):
        v = PhysicsValidator()
        batch = torch.tensor([[-5.0, 30.0, 25.0]])
        single = torch.tensor([-5.0, 30.0, 25.0])
        batch_result = v.validate(batch)
        single_result = v.validate(single)
        assert batch_result[0, 0] == single_result[0]

    def test_large_batch(self):
        v = PhysicsValidator()
        batch_size = 128
        preds = torch.randn(batch_size, 3) * 50
        result = v.validate(preds)
        assert result.shape == (batch_size, 3)
        assert (result[:, 0] >= 0).all()
        assert (result[:, 1] >= result[:, 2]).all()

    def test_custom_target_names(self):
        v = PhysicsValidator(target_names=["Rain", "High", "Low"])
        preds = torch.tensor([[-5.0, 30.0, 35.0]])
        result = v.validate(preds)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 35.0
        assert result[0, 2] == 30.0

    def test_preserves_dtype(self):
        v = PhysicsValidator()
        preds = torch.tensor([[-5.0, 30.0, 25.0]], dtype=torch.float64)
        result = v.validate(preds)
        assert result.dtype == torch.float64

    def test_preserves_shape(self):
        v = PhysicsValidator()
        preds = torch.randn(16, 3)
        result = v.validate(preds)
        assert result.shape == preds.shape


# ──────────────────────────────────────────────
# Input validation errors
# ──────────────────────────────────────────────


class TestInputValidation:
    """Invalid inputs raise appropriate errors."""

    def test_non_float_tensor_raises(self):
        v = PhysicsValidator()
        preds = torch.tensor([[1, 2, 3]])
        try:
            v.validate(preds)
            pytest.fail("Expected TypeError")
        except TypeError:
            pass

    def test_3d_tensor_raises(self):
        v = PhysicsValidator()
        preds = torch.randn(4, 3, 2)
        try:
            v.validate(preds)
            pytest.fail("Expected ValueError")
        except ValueError:
            pass

    def test_0d_tensor_raises(self):
        v = PhysicsValidator()
        preds = torch.tensor(5.0)
        try:
            v.validate(preds)
            pytest.fail("Expected ValueError")
        except ValueError:
            pass


# ──────────────────────────────────────────────
# validate_single convenience method
# ──────────────────────────────────────────────


class TestValidateSingle:
    """Convenience wrapper for scalar validation."""

    def test_valid_returns_unchanged(self):
        v = PhysicsValidator()
        result = v.validate_single(25.0, 32.0, 20.0)
        assert result == (25.0, 32.0, 20.0)

    def test_corrects_negative_rainfall(self):
        v = PhysicsValidator()
        rain, tmax, tmin = v.validate_single(-5.0, 30.0, 20.0)
        assert rain == 0.0
        assert tmax == 30.0
        assert tmin == 20.0

    def test_corrects_tmin_gt_tmax(self):
        v = PhysicsValidator()
        rain, tmax, tmin = v.validate_single(10.0, 25.0, 35.0)
        assert rain == 10.0
        assert tmax == 35.0
        assert tmin == 25.0

    def test_returns_float_tuple(self):
        v = PhysicsValidator()
        result = v.validate_single(10.0, 30.0, 20.0)
        assert isinstance(result, tuple)
        assert all(isinstance(v, float) for v in result)


# ──────────────────────────────────────────────
# Representation
# ──────────────────────────────────────────────


class TestRepresentation:
    def test_repr_contains_bounds(self):
        v = PhysicsValidator(rainfall_upper=300.0, temp_lower=-5.0, temp_upper=50.0)
        r = repr(v)
        assert "300.0" in r
        assert "-5.0" in r
        assert "50.0" in r

    def test_repr_is_valid_python(self):
        v = PhysicsValidator()
        r = repr(v)
        assert r.startswith("PhysicsValidator(")
        assert r.endswith(")")

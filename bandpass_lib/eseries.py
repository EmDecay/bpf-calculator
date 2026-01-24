"""
E-series component matching for standard resistor/capacitor values.
Reference: IEC 60063 (Preferred number series for resistors and capacitors)
"""
from dataclasses import dataclass
import math

# E-series normalized values (1.0-10.0 range), geometric progression
E_SERIES: dict[str, list[float]] = {
    'E12': [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2],
    'E24': [
        1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
        3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1
    ],
    'E96': [
        1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24,
        1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58,
        1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00,
        2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55,
        2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24,
        3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
        4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23,
        5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
        6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
        8.66, 8.87, 9.09, 9.31, 9.53, 9.76
    ],
}


@dataclass
class ESeriesMatch:
    """Result of E-series component matching."""
    target: float                           # Original target value
    single_value: float                     # Closest single E-series value
    single_error_pct: float                 # Error percentage for single
    parallel: tuple[float, float] | None    # Parallel combo (V1, V2) if better
    parallel_value: float | None            # Resulting parallel value
    parallel_error_pct: float | None        # Error percentage for parallel


def _normalize(value: float) -> tuple[float, int]:
    """Extract mantissa (1.0-10.0) and decade exponent. E.g. 4700 -> (4.7, 3)"""
    if value <= 0:
        raise ValueError("Value must be positive")
    decade = math.floor(math.log10(value))
    return value / (10 ** decade), decade

def _denormalize(mantissa: float, decade: int) -> float:
    """Reconstruct value from mantissa and decade."""
    return mantissa * (10 ** decade)

def _error_pct(actual: float, target: float) -> float:
    """Calculate percentage error."""
    return abs(actual - target) / target * 100


def find_closest_single(target: float, series: str = 'E24') -> tuple[float, float]:
    """Find closest single E-series value. Returns (matched_value, error_pct)."""
    if series not in E_SERIES:
        raise ValueError(f"Unknown series '{series}'. Use E12, E24, or E96.")
    _, decade = _normalize(target)
    series_values = E_SERIES[series]
    best_value, best_error = None, float('inf')
    # Check all values in current decade
    for sv in series_values:
        candidate = _denormalize(sv, decade)
        err = _error_pct(candidate, target)
        if err < best_error:
            best_error, best_value = err, candidate
    # Check boundary values in adjacent decades
    for candidate in [_denormalize(series_values[0], decade + 1),
                      _denormalize(series_values[-1], decade - 1)]:
        err = _error_pct(candidate, target)
        if err < best_error:
            best_error, best_value = err, candidate
    return best_value, best_error


def find_parallel_combo(
    target: float, series: str = 'E24', ratio_limit: float = 10.0
) -> tuple[tuple[float, float], float, float] | None:
    """
    Find parallel combination closest to target. Rp = R1*R2/(R1+R2)
    Returns ((V1, V2), parallel_value, error_pct) or None if no valid combo.
    """
    if series not in E_SERIES:
        raise ValueError(f"Unknown series '{series}'. Use E12, E24, or E96.")
    _, decade = _normalize(target)
    # Build candidate values spanning relevant decades
    candidates = [_denormalize(sv, d) for d in range(decade - 1, decade + 3)
                  for sv in E_SERIES[series]]
    best_combo, best_value, best_error = None, None, float('inf')
    for v1 in candidates:
        if v1 <= target:
            continue  # V1 must be > target for parallel to work
        # Calculate V2 needed: V2 = V1*target/(V1-target)
        v2_needed = v1 * target / (v1 - target)
        if v2_needed <= 0:
            continue
        v2, _ = find_closest_single(v2_needed, series)
        # Check ratio constraint
        if max(v1, v2) / min(v1, v2) > ratio_limit:
            continue
        parallel_val = (v1 * v2) / (v1 + v2)
        err = _error_pct(parallel_val, target)
        if err < best_error:
            best_error, best_value, best_combo = err, parallel_val, (v1, v2)
    return (best_combo, best_value, best_error) if best_combo else None


def match_component(
    target: float, series: str = 'E24', ratio_limit: float = 10.0
) -> ESeriesMatch:
    """Find best E-series match. Returns both single and parallel options."""
    single_val, single_err = find_closest_single(target, series)
    parallel_result = find_parallel_combo(target, series, ratio_limit)
    if parallel_result:
        combo, par_val, par_err = parallel_result
        return ESeriesMatch(target, single_val, single_err, combo, par_val, par_err)
    return ESeriesMatch(target, single_val, single_err, None, None, None)

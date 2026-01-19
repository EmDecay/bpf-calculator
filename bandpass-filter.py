#!/usr/bin/env python3
"""
Coupled Resonator Bandpass Filter Calculator

Calculates component values for coupled resonator bandpass filters with
Top-C (series) or Shunt-C (parallel) coupling topologies.

Supports Butterworth and Chebyshev responses with 2-9 resonators.

Written by Matt N3AR (with AI coding assistance)

References:
- Matthaei, Young, Jones "Microwave Filters, Impedance-Matching Networks..."
- Zverev "Handbook of Filter Synthesis" (1967)
- Cohn "Direct-Coupled-Resonator Filters" (1957)
"""

import argparse
import math
import sys

from bandpass_lib import (
    calculate_bandpass_filter,
    calculate_butterworth_g_values,
    get_chebyshev_g_values,
    calculate_resonator_components,
    calculate_coupling_coefficients,
    CHEBYSHEV_G_VALUES,
    display_results,
)


BUTTERWORTH_BANDPASS_EXPLANATION = """
Butterworth Bandpass Filter Explained
=====================================

A bandpass filter allows signals within a specific frequency range to pass through
while blocking frequencies outside that range. This calculator designs "coupled
resonator" filters - a series of LC tank circuits connected by coupling capacitors.

The Butterworth response provides the flattest possible passband - signals within
your frequency range pass through with minimal amplitude variation. The tradeoff
is a gentler transition at the band edges compared to Chebyshev filters.

Coupled resonator filters use LC "tanks" (parallel inductor-capacitor pairs) tuned
to the center frequency. The coupling capacitors between tanks determine the
bandwidth and shape of the response. More resonators give steeper skirts
but require more components.

Key parameters:
  - Center frequency (f0): The middle of your passband
  - Bandwidth (BW): The width of the passband (3dB points)
  - Fractional BW: BW/f0 - keep below 40% for accurate results

Component Q requirement: Inductors must have unloaded Q greater than (f0/BW)*2
for acceptable insertion loss. Air-core inductors typically achieve Q of 100-300.

Choose Butterworth when you need the smoothest passband response and can tolerate
a gentler rolloff at the band edges.
"""


CHEBYSHEV_BANDPASS_EXPLANATION = """
Chebyshev Bandpass Filter Explained
===================================

A bandpass filter allows signals within a specific frequency range to pass through
while blocking frequencies outside that range. This calculator designs "coupled
resonator" filters - a series of LC tank circuits connected by coupling capacitors.

The Chebyshev response trades passband flatness for steeper rolloff at the band
edges. Small "ripples" in the passband allow much sharper rejection of out-of-band
signals compared to Butterworth filters of the same order.

The "ripple" parameter controls this tradeoff:
  - 0.1 dB: Nearly flat passband, moderate rolloff improvement
  - 0.5 dB: Good balance of flatness and rolloff (recommended)
  - 1.0 dB: Maximum rolloff steepness, noticeable passband variation

Coupled resonator filters use LC "tanks" tuned to the center frequency. The
coupling capacitors between tanks determine bandwidth and response shape. More
resonators give steeper skirts but require more components and tighter tolerances.

Key parameters:
  - Center frequency (f0): The middle of your passband
  - Bandwidth (BW): The width of the passband (3dB points)
  - Fractional BW: BW/f0 - keep below 40% for accurate results

Component Q requirement: Inductors must have unloaded Q greater than (f0/BW)*2
for acceptable insertion loss. Chebyshev filters are more sensitive to component
Q than Butterworth.

Important: Chebyshev filters with equal source/load impedances require an ODD
number of resonators (3, 5, 7, or 9). For even resonator counts, use Butterworth.

Choose Chebyshev when you need sharp rejection of nearby interfering signals and
can tolerate small passband ripple.
"""


# Physical limits for validation
MAX_FREQUENCY_HZ = 1e12  # 1 THz - physical upper limit
MAX_IMPEDANCE_OHMS = 1e6  # 1 MOhm - practical upper limit
SHUNT_C_FBW_LIMIT = 0.10  # Shunt-C topology bandwidth limit
GENERAL_FBW_LIMIT = 0.40  # Narrowband approximation limit


def parse_frequency(freq_str: str) -> float:
    """
    Parse frequency string with optional unit suffix.

    Supported formats:
        - Plain number: 14200000 (Hz)
        - With Hz suffix: 14.2MHz, 500kHz, 1GHz
        - Case insensitive: 14.2mhz, 14.2MHZ

    Args:
        freq_str: Frequency string to parse

    Returns:
        Frequency in Hz

    Raises:
        ValueError: If string cannot be parsed or is NaN/Infinity
    """
    freq_str = freq_str.strip()
    freq_str_lower = freq_str.lower()

    suffixes = [('ghz', 1e9), ('mhz', 1e6), ('khz', 1e3), ('hz', 1)]

    for suffix, mult in suffixes:
        if freq_str_lower.endswith(suffix):
            num_part = freq_str[:-len(suffix)].strip()
            result = float(num_part) * mult
            if not math.isfinite(result):
                raise ValueError(f"Invalid frequency value: {freq_str}")
            return result

    result = float(freq_str)
    if not math.isfinite(result):
        raise ValueError(f"Invalid frequency value: {freq_str}")
    return result


def parse_impedance(z_str: str) -> float:
    """
    Parse impedance string with optional unit suffix.

    Supported formats:
        - Plain number: 50
        - With ohm suffix: 50ohm, 1kohm
        - Unicode omega: 50Ω

    Args:
        z_str: Impedance string to parse

    Returns:
        Impedance in Ohms

    Raises:
        ValueError: If string cannot be parsed or is NaN/Infinity
    """
    z_str = z_str.strip().lower()
    for omega_char in ['ω', 'Ω']:
        z_str = z_str.replace(omega_char, 'ohm')

    multipliers = {'mohm': 1e6, 'kohm': 1e3, 'ohm': 1}

    for suffix, mult in multipliers.items():
        if z_str.endswith(suffix):
            result = float(z_str[:-len(suffix)].strip()) * mult
            if not math.isfinite(result):
                raise ValueError(f"Invalid impedance value: {z_str}")
            return result

    result = float(z_str)
    if not math.isfinite(result):
        raise ValueError(f"Invalid impedance value: {z_str}")
    return result


def validate_and_compute_frequencies(args) -> tuple[float, float, float, float]:
    """
    Validate frequency inputs and compute center frequency + bandwidth.

    Two valid input combinations:
    1. -f (center) + -b (bandwidth)
    2. --fl (low cutoff) + --fh (high cutoff)

    For cutoff method, computes:
        f0 = sqrt(f_low * f_high)  [geometric mean]
        bw = f_high - f_low

    Args:
        args: Parsed argparse namespace

    Returns:
        Tuple (f0_hz, bw_hz, f_low_hz, f_high_hz)

    Raises:
        ValueError: If inputs invalid or incomplete
    """
    has_center_bw = args.frequency is not None and args.bandwidth is not None
    has_low_high = args.f_low is not None and args.f_high is not None
    has_partial_center = (args.frequency is not None) != (args.bandwidth is not None)
    has_partial_cutoff = (args.f_low is not None) != (args.f_high is not None)

    # Check for valid combination
    if has_center_bw and has_low_high:
        raise ValueError("Specify either (-f + -b) OR (--fl + --fh), not both")

    if not has_center_bw and not has_low_high:
        if has_partial_center:
            raise ValueError("Both -f and -b are required together")
        if has_partial_cutoff:
            raise ValueError("Both --fl and --fh are required together")
        raise ValueError("Specify frequency as (-f + -b) or (--fl + --fh)")

    if has_center_bw:
        f0 = parse_frequency(args.frequency)
        bw = parse_frequency(args.bandwidth)
        f_low = f0 - bw / 2
        f_high = f0 + bw / 2
    else:
        f_low = parse_frequency(args.f_low)
        f_high = parse_frequency(args.f_high)

        if f_low >= f_high:
            raise ValueError("Lower frequency must be less than upper frequency")

        # Geometric mean for center frequency
        f0 = math.sqrt(f_low * f_high)
        bw = f_high - f_low

    return f0, bw, f_low, f_high


def validate_inputs(f0: float, bw: float, z0: float, n_resonators: int,
                    filter_type: str, ripple: float, coupling: str) -> list[str]:
    """
    Validate all input parameters.

    Checks:
        - Positive values for f0, bw, z0
        - Upper bounds for f0, z0
        - Pole count in allowed set
        - Bandwidth constraints (warning only)
        - Ripple in allowed set for Chebyshev

    Args:
        f0: Center frequency in Hz
        bw: Bandwidth in Hz
        z0: Impedance in Ohms
        n_resonators: Number of resonators
        filter_type: 'butterworth' or 'chebyshev'
        ripple: Passband ripple in dB
        coupling: 'top' or 'shunt'

    Returns:
        List of warning messages

    Raises:
        ValueError: If any input is invalid
    """
    warnings = []

    if f0 <= 0:
        raise ValueError("Center frequency must be positive")
    if f0 > MAX_FREQUENCY_HZ:
        raise ValueError(f"Center frequency exceeds {MAX_FREQUENCY_HZ/1e12:.0f} THz limit")
    if bw <= 0:
        raise ValueError("Bandwidth must be positive")
    if bw >= f0:
        raise ValueError("Bandwidth must be less than center frequency")
    if z0 <= 0:
        raise ValueError("Impedance must be positive")
    if z0 > MAX_IMPEDANCE_OHMS:
        raise ValueError(f"Impedance exceeds {MAX_IMPEDANCE_OHMS/1e6:.0f} MOhm limit")
    if not 2 <= n_resonators <= 9:
        raise ValueError("Resonators must be between 2 and 9")

    # Chebyshev requires odd resonator count for equal terminations
    if filter_type == 'chebyshev' and n_resonators % 2 == 0:
        raise ValueError(
            f"Chebyshev requires odd resonator count (3, 5, 7, 9) for equal terminations. "
            f"Got {n_resonators}. Use Butterworth for even counts."
        )

    # Check fractional bandwidth
    fbw = bw / f0
    if fbw <= 0:
        raise ValueError("Fractional bandwidth must be positive")

    # Bandwidth constraint warnings
    if coupling == 'shunt' and fbw > SHUNT_C_FBW_LIMIT:
        warnings.append(f"FBW ({fbw*100:.1f}%) exceeds {SHUNT_C_FBW_LIMIT*100:.0f}% limit for Shunt-C topology")
        warnings.append("Consider using Top-C (-c top) for wide bandwidth designs")
    elif fbw > GENERAL_FBW_LIMIT:
        warnings.append(f"FBW ({fbw*100:.1f}%) exceeds {GENERAL_FBW_LIMIT*100:.0f}% recommended limit")
        warnings.append("Results may be inaccurate; consider transmission-line design")

    if filter_type == 'chebyshev' and ripple not in [0.1, 0.5, 1.0]:
        raise ValueError("Ripple must be 0.1, 0.5, or 1.0 dB")

    return warnings


def verify_calculations() -> bool:
    """Verify core calculations against known values."""
    print("Verifying Butterworth g-values...")

    expected = {
        3: [1.00000, 2.00000, 1.00000],
        5: [0.61803, 1.61803, 2.00000, 1.61803, 0.61803],
        7: [0.44504, 1.24698, 1.80194, 2.00000, 1.80194, 1.24698, 0.44504],
        9: [0.34730, 1.00000, 1.53209, 1.87939, 2.00000, 1.87939, 1.53209, 1.00000, 0.34730],
    }

    all_pass = True
    for n, exp_vals in expected.items():
        calc_vals = calculate_butterworth_g_values(n)
        for i, (calc, exp) in enumerate(zip(calc_vals, exp_vals)):
            if abs(calc - exp) > 0.0001:
                print(f"  FAIL: n={n}, g{i+1}: calculated {calc:.5f}, expected {exp:.5f}")
                all_pass = False

    if all_pass:
        print("  All Butterworth g-values verified within 0.0001")

    print("\nVerifying Chebyshev g-value lookup...")
    for ripple in [0.1, 0.5, 1.0]:
        for n in [3, 5, 7, 9]:
            g = get_chebyshev_g_values(n, ripple)
            if len(g) != n:
                print(f"  FAIL: ripple={ripple}, n={n}: got {len(g)} values")
                all_pass = False
    if all_pass:
        print("  All Chebyshev lookups successful")

    print("\nVerifying resonator calculation (resonance check)...")
    test_f0 = 7e6
    test_z0 = 50
    L, C = calculate_resonator_components(test_f0, test_z0)
    calc_f0 = 1 / (2 * math.pi * math.sqrt(L * C))
    error_ppm = abs(calc_f0 - test_f0) / test_f0 * 1e6
    if error_ppm < 1:
        print(f"  Resonance verified: error = {error_ppm:.3f} ppm")
    else:
        print(f"  FAIL: Resonance error = {error_ppm:.3f} ppm (should be < 1 ppm)")
        all_pass = False

    print("\nVerifying coupling coefficients (k < 1 for valid designs)...")
    g = calculate_butterworth_g_values(5)
    k = calculate_coupling_coefficients(g, 0.05)
    if all(ki < 1 for ki in k):
        print(f"  All coupling coefficients < 1: {[f'{ki:.4f}' for ki in k]}")
    else:
        print(f"  FAIL: Some k >= 1: {k}")
        all_pass = False

    print("\n" + "=" * 50)
    if all_pass:
        print("ALL VERIFICATIONS PASSED")
    else:
        print("SOME VERIFICATIONS FAILED")
    print("=" * 50)

    return all_pass


def main():
    parser = argparse.ArgumentParser(
        description='Coupled Resonator Bandpass Filter Calculator',
        epilog='''Examples:
  %(prog)s -t butterworth -f 14.2MHz -b 500kHz -c top -n 5
  %(prog)s -t chebyshev --fl 14MHz --fh 14.35MHz -c shunt -r 0.5 -n 7
  %(prog)s -t butterworth -f 7.1MHz -b 300kHz -c top -z 50 --explain''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Filter type (required unless --verify)
    parser.add_argument('-t', '--type',
                        choices=['butterworth', 'chebyshev'],
                        help='Filter type: butterworth (any n) or chebyshev (odd n only)')

    # Frequency input method 1: center + bandwidth
    parser.add_argument('-f', '--frequency',
                        help='Center frequency (e.g., 14.2MHz, 7.1MHz)')
    parser.add_argument('-b', '--bandwidth',
                        help='3dB bandwidth (e.g., 500kHz, 1MHz)')

    # Frequency input method 2: lower/upper cutoff
    parser.add_argument('--fl', '--f-low', dest='f_low',
                        help='Lower cutoff frequency (e.g., 14MHz)')
    parser.add_argument('--fh', '--f-high', dest='f_high',
                        help='Upper cutoff frequency (e.g., 14.35MHz)')

    # Coupling topology (required unless --verify or --explain)
    parser.add_argument('-c', '--coupling',
                        choices=['top', 'shunt'],
                        help='Coupling topology: top (series) or shunt (parallel)')

    # Other parameters
    parser.add_argument('-z', '--impedance', default='50',
                        help='System impedance (default: 50 ohms)')
    parser.add_argument('-n', '--resonators', type=int, default=2,
                        choices=range(2, 10),
                        help='Number of resonators (LC tanks): 2-9 (default: 2)')
    parser.add_argument('-r', '--ripple', type=float, default=0.5,
                        help='Passband ripple for Chebyshev: 0.1, 0.5, or 1.0 dB (default: 0.5). '
                             'Note: Chebyshev requires odd resonator count (3,5,7,9)')
    parser.add_argument('--q-safety', type=float, default=2.0,
                        help='Q safety factor multiplier (default: 2.0). '
                             'Crystal filters: 1.5, LC filters: 2.0, lossy inductors: 3.0+')

    # Output options
    parser.add_argument('--raw', action='store_true',
                        help='Output raw values in scientific notation')
    parser.add_argument('--explain', action='store_true',
                        help='Explain how the selected filter type works')
    parser.add_argument('--verify', action='store_true',
                        help='Run calculation verification tests')

    args = parser.parse_args()

    # Handle --verify
    if args.verify:
        success = verify_calculations()
        sys.exit(0 if success else 1)

    # Handle --explain (exit early)
    if args.explain:
        if args.type is None:
            parser.error('--explain requires -t/--type')
        if args.type == 'butterworth':
            print(BUTTERWORTH_BANDPASS_EXPLANATION)
        else:
            print(CHEBYSHEV_BANDPASS_EXPLANATION)
        sys.exit(0)

    # Validate required arguments for calculation
    if args.type is None:
        parser.error('the following arguments are required: -t/--type')
    if args.coupling is None:
        parser.error('the following arguments are required: -c/--coupling')

    # Parse and validate
    try:
        f0, bw, f_low, f_high = validate_and_compute_frequencies(args)
        z0 = parse_impedance(args.impedance)
        if args.q_safety <= 0:
            raise ValueError("Q safety factor must be positive")
        warnings = validate_inputs(f0, bw, z0, args.resonators, args.type, args.ripple, args.coupling)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print warnings to stderr
    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    # Calculate filter
    try:
        result = calculate_bandpass_filter(
            f0=f0,
            bw=bw,
            z0=z0,
            n_resonators=args.resonators,
            filter_type=args.type,
            coupling=args.coupling,
            ripple_db=args.ripple if args.type == 'chebyshev' else 0.5,
            q_safety=args.q_safety
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Override f_low/f_high with user-computed values (geometric mean vs arithmetic)
    result['f_low'] = f_low
    result['f_high'] = f_high

    # Display results
    display_results(result, raw=args.raw)


if __name__ == '__main__':
    main()

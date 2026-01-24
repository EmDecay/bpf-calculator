#!/usr/bin/env python3
"""
Coupled Resonator Bandpass Filter Calculator

Calculates component values for coupled resonator bandpass filters with
Top-C (series) or Shunt-C (parallel) coupling topologies.

Supports Butterworth, Chebyshev, and Bessel responses with 2-9 resonators.

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
number of resonators (3, 5, 7, or 9). This is due to prototype g-value mathematics:
even-order Chebyshev produces unequal termination impedances, requiring impedance
transformers for matched 50-ohm systems. For even resonator counts, use Butterworth.

Choose Chebyshev when you need sharp rejection of nearby interfering signals and
can tolerate small passband ripple.
"""


BESSEL_BANDPASS_EXPLANATION = """
Bessel (Thomson) Bandpass Filter Explained
==========================================

A bandpass filter allows signals within a specific frequency range to pass through
while blocking frequencies outside that range. This calculator designs "coupled
resonator" filters - a series of LC tank circuits connected by coupling capacitors.

The Bessel filter (also called Thomson filter) is designed for maximally-flat
group delay, which means all frequencies within the passband experience the same
time delay. This results in linear phase response - the filter preserves the
shape of signals passing through it.

This makes Bessel bandpass filters ideal for:
  - Pulse and transient applications where waveform shape matters
  - Digital communications where timing relationships must be preserved
  - SSB/CW reception where phase coherence affects audio quality
  - Any application where overshoot and ringing are unacceptable

The tradeoff is that Bessel filters have the gentlest rolloff of the three types.
They don't attenuate unwanted frequencies as aggressively as Butterworth or
Chebyshev filters. If sharp selectivity is your priority, choose one of those.

Coupled resonator filters use LC "tanks" tuned to the center frequency. The
coupling capacitors between tanks determine bandwidth and response shape. More
resonators give steeper skirts but require more components.

Key parameters:
  - Center frequency (f0): The middle of your passband
  - Bandwidth (BW): The width of the passband (3dB points)
  - Fractional BW: BW/f0 - keep below 40% for accurate results

Component Q requirement: Inductors must have unloaded Q greater than (f0/BW)*2
for acceptable insertion loss.

Choose Bessel when signal integrity and waveform preservation are more important
than sharp frequency selectivity.
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


def resolve_filter_type(alias: str) -> str:
    """Convert short aliases to full filter type names."""
    return {'bw': 'butterworth', 'b': 'butterworth',
            'ch': 'chebyshev', 'c': 'chebyshev',
            'bs': 'bessel'}.get(alias, alias)


def resolve_coupling(alias: str) -> str:
    """Convert short aliases to full coupling type names."""
    return {'t': 'top', 's': 'shunt'}.get(alias, alias)


def main():
    parser = argparse.ArgumentParser(
        description='Coupled Resonator Bandpass Filter Calculator',
        epilog='''Examples:
  %(prog)s bw top -f 14.2MHz -b 500kHz -n 5        # positional args
  %(prog)s ch shunt --fl 14MHz --fh 14.35MHz -n 7  # short aliases
  %(prog)s bw t -f 7.1MHz -b 300kHz --format json  # JSON output
  %(prog)s bw top -f 14.2MHz -b 500kHz -q          # quiet mode
  %(prog)s -t butterworth -c top -f 14.2MHz -b 500kHz  # flags only''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional arguments (optional, fall back to flags)
    parser.add_argument('filter_type', nargs='?',
                        choices=['butterworth', 'chebyshev', 'bessel', 'bw', 'ch', 'bs', 'b', 'c'],
                        help='Filter type (butterworth/bw, chebyshev/ch, or bessel/bs)')
    parser.add_argument('coupling_pos', nargs='?',
                        choices=['top', 'shunt', 't', 's'],
                        help='Coupling topology (top/t or shunt/s)')

    # Filter type flag (alternative to positional)
    parser.add_argument('-t', '--type', dest='type_flag',
                        choices=['butterworth', 'chebyshev', 'bessel', 'bw', 'ch', 'bs', 'b', 'c'],
                        help='Filter type (alternative to positional)')

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

    # Coupling topology flag (alternative to positional)
    parser.add_argument('-c', '--coupling', dest='coupling_flag',
                        choices=['top', 'shunt', 't', 's'],
                        help='Coupling topology (alternative to positional)')

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
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Output only component values (no header/diagram)')
    parser.add_argument('--format', choices=['table', 'json', 'csv'],
                        default='table', help='Output format (default: table)')
    parser.add_argument('--explain', action='store_true',
                        help='Explain how the selected filter type works')
    parser.add_argument('--verify', action='store_true',
                        help='Run calculation verification tests')

    # Component matching options
    match_group = parser.add_argument_group('Component Matching')
    match_group.add_argument('-e', '--eseries', choices=['E12', 'E24', 'E96'],
                             default='E24', help='E-series for matching (default: E24)')
    match_group.add_argument('--no-match', action='store_true',
                             help='Disable E-series matching suggestions')

    # Frequency response options
    plot_group = parser.add_argument_group('Frequency Response')
    plot_group.add_argument('--plot', action='store_true',
                            help='Show ASCII frequency response')
    plot_group.add_argument('--plot-data', choices=['json', 'csv'],
                            help='Export frequency response data')

    args = parser.parse_args()

    # Handle --verify
    if args.verify:
        success = verify_calculations()
        sys.exit(0 if success else 1)

    # Merge positional and flag arguments
    filter_type = args.filter_type or args.type_flag
    coupling = args.coupling_pos or args.coupling_flag

    # Handle --explain (exit early)
    if args.explain:
        if filter_type is None:
            parser.error('--explain requires filter type')
        resolved_type = resolve_filter_type(filter_type)
        if resolved_type == 'butterworth':
            print(BUTTERWORTH_BANDPASS_EXPLANATION)
        elif resolved_type == 'chebyshev':
            print(CHEBYSHEV_BANDPASS_EXPLANATION)
        else:
            print(BESSEL_BANDPASS_EXPLANATION)
        sys.exit(0)

    # Validate required arguments for calculation
    if filter_type is None:
        parser.error('Filter type required (positional or -t/--type)')
    if coupling is None:
        parser.error('Coupling topology required (positional or -c/--coupling)')

    filter_type = resolve_filter_type(filter_type)
    coupling = resolve_coupling(coupling)

    # Parse and validate
    try:
        f0, bw, f_low, f_high = validate_and_compute_frequencies(args)
        z0 = parse_impedance(args.impedance)
        if args.q_safety <= 0:
            raise ValueError("Q safety factor must be positive")
        warnings = validate_inputs(f0, bw, z0, args.resonators, filter_type, args.ripple, coupling)
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
            filter_type=filter_type,
            coupling=coupling,
            ripple_db=args.ripple if filter_type == 'chebyshev' else 0.5,
            q_safety=args.q_safety
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Override f_low/f_high with user-computed values (geometric mean vs arithmetic)
    result['f_low'] = f_low
    result['f_high'] = f_high

    # Display results
    display_results(
        result,
        raw=args.raw,
        output_format=args.format,
        quiet=args.quiet,
        eseries=None if args.no_match else args.eseries,
        show_plot=args.plot,
        plot_data=args.plot_data
    )


if __name__ == '__main__':
    main()

"""
Core calculations for coupled resonator bandpass filters.

Contains g-value tables, coupling coefficient formulas, and component
value calculations for Top-C and Shunt-C topologies.

References:
- Matthaei, Young, Jones "Microwave Filters, Impedance-Matching Networks..."
- Zverev "Handbook of Filter Synthesis" (1967)
- Cohn "Direct-Coupled-Resonator Filters" (1957)
"""

import math


# Bessel normalized g-values for orders 2-9 (standard filter design tables)
# Source: Zverev "Handbook of Filter Synthesis", Matthaei/Young/Jones
# Bessel provides maximally-flat group delay (linear phase response)
BESSEL_G_VALUES = {
    2: [0.5755, 2.1478],
    3: [0.3374, 0.9705, 2.2034],
    4: [0.2334, 0.6725, 1.0815, 2.2404],
    5: [0.1743, 0.5072, 0.8040, 1.1110, 2.2582],
    6: [0.1365, 0.4002, 0.6392, 0.8538, 1.1126, 2.2645],
    7: [0.1106, 0.3259, 0.5249, 0.7020, 0.8690, 1.1052, 2.2659],
    8: [0.0919, 0.2719, 0.4409, 0.5936, 0.7303, 0.8695, 1.0956, 2.2656],
    9: [0.0780, 0.2313, 0.3770, 0.5108, 0.6306, 0.7407, 0.8639, 1.0863, 2.2649],
}


# Chebyshev g-values VERIFIED against RF Cafe, LibreTexts, Zverev (Phase 0 research)
# Source: plans/reports/researcher-260119-0851-chebyshev-gvalues.md
CHEBYSHEV_G_VALUES = {
    0.1: {  # 0.1 dB ripple
        3: [1.03159, 1.14740, 1.03159],
        5: [1.14684, 1.37121, 1.97503, 1.37121, 1.14684],
        7: [1.18120, 1.42280, 2.09669, 1.57339, 2.09669, 1.42280, 1.18120],
        9: [1.19570, 1.44260, 2.13457, 1.61671, 2.20539, 1.61671, 2.13457, 1.44260, 1.19570],
    },
    0.5: {  # 0.5 dB ripple
        3: [1.59633, 1.09668, 1.59633],
        5: [1.70582, 1.22961, 2.54088, 1.22961, 1.70582],
        7: [1.73734, 1.25822, 2.63834, 1.34431, 2.63834, 1.25822, 1.73734],
        9: [1.75049, 1.26902, 2.66783, 1.36730, 2.72396, 1.36730, 2.66783, 1.26902, 1.75049],
    },
    1.0: {  # 1.0 dB ripple
        3: [2.02367, 0.99408, 2.02367],
        5: [2.13496, 1.09108, 3.00101, 1.09108, 2.13496],
        7: [2.16664, 1.11148, 3.09373, 1.17349, 3.09373, 1.11148, 2.16664],
        9: [2.17980, 1.11915, 3.12152, 1.18964, 3.17472, 1.18964, 3.12152, 1.11915, 2.17980],
    },
}


def calculate_butterworth_g_values(n: int) -> list[float]:
    """
    Calculate Butterworth prototype g-values.

    Formula:
        g[i] = 2 * sin((2*i - 1) * pi / (2*n))

    Where:
        n = filter order (= number of resonators in bandpass)
        i = element index (1 to n)

    The g-values define the normalized element values for a lowpass
    prototype filter with 1 rad/s cutoff and 1 ohm terminations.

    Args:
        n: Filter order (number of resonators)

    Returns:
        List of g-values [g1, g2, ..., gn]
        Note: g0 = 1 and g_{n+1} = 1 are implied (source/load impedances)

    Reference: Matthaei, Young, Jones "Microwave Filters..."
    """
    g_values = []
    for i in range(1, n + 1):
        g = 2 * math.sin((2 * i - 1) * math.pi / (2 * n))
        g_values.append(g)
    return g_values


def get_chebyshev_g_values(n: int, ripple_db: float) -> list[float]:
    """
    Get Chebyshev prototype g-values from lookup table.

    Note: Chebyshev Type I filters with equal source/load impedances
    require ODD resonator counts (3, 5, 7, 9). For even orders, the
    final g-value g_{n+1} ≠ 1, meaning optimal load impedance differs
    from source (e.g., g_{n+1}=1.98 for 2nd order 0.5dB ripple requires
    ~99Ω load with 50Ω source). Use Butterworth for even counts with
    equal terminations, or add impedance transformers for even Chebyshev.

    Args:
        n: Number of resonators (3, 5, 7, or 9 - odd only)
        ripple_db: Passband ripple (0.1, 0.5, or 1.0 dB)

    Returns:
        List of g-values [g1, g2, ..., gn]

    Raises:
        ValueError: If n or ripple_db not in table

    Reference: Zverev "Handbook of Filter Synthesis" (1967)
    """
    if ripple_db not in CHEBYSHEV_G_VALUES:
        raise ValueError(f"Ripple {ripple_db} dB not supported. Use 0.1, 0.5, or 1.0")
    if n not in CHEBYSHEV_G_VALUES[ripple_db]:
        raise ValueError(
            f"Chebyshev requires odd resonator count (3, 5, 7, 9) for equal terminations. "
            f"Got {n}. Use Butterworth for even counts."
        )
    return CHEBYSHEV_G_VALUES[ripple_db][n].copy()


def get_bessel_g_values(n: int) -> list[float]:
    """
    Get Bessel (Thomson) prototype g-values from lookup table.

    Bessel filters provide maximally-flat group delay (linear phase response),
    ideal for pulse/transient applications where waveform preservation matters.

    Args:
        n: Number of resonators (2-9)

    Returns:
        List of g-values [g1, g2, ..., gn]

    Raises:
        ValueError: If n not in table (2-9)

    Reference: Zverev "Handbook of Filter Synthesis" (1967)
    """
    if n not in BESSEL_G_VALUES:
        raise ValueError(f"Bessel g-values only available for 2-9 resonators, got {n}")
    return BESSEL_G_VALUES[n].copy()


def calculate_coupling_coefficients(g_values: list[float], fbw: float) -> list[float]:
    """
    Calculate inter-resonator coupling coefficients.

    Formula:
        k[i,i+1] = FBW / sqrt(g[i] * g[i+1])

    Where:
        FBW = fractional bandwidth = BW / f0
        g[i], g[i+1] = adjacent prototype g-values
        k[i,i+1] = coupling coefficient between resonators i and i+1

    Physical meaning: k determines the energy transfer rate between
    adjacent resonators. Larger k = wider bandwidth contribution.

    Args:
        g_values: Prototype g-values [g1, g2, ..., gn]
        fbw: Fractional bandwidth (BW/f0), dimensionless

    Returns:
        List of coupling coefficients [k12, k23, ..., k_{n-1,n}]
        Length is n-1 for n-resonator filter

    Reference: Matthaei et al., Eq. 8.11-1
    """
    k_values = []
    for i in range(len(g_values) - 1):
        k = fbw / math.sqrt(g_values[i] * g_values[i + 1])
        k_values.append(k)
    return k_values


def calculate_external_q(g_values: list[float], fbw: float) -> tuple[float, float]:
    """
    Calculate external Q factors for input/output coupling.

    Formulas:
        Qe_in  = (g0 * g1) / FBW
        Qe_out = (gn * g_{n+1}) / FBW

    Where:
        g0 = 1 (normalized source impedance)
        g_{n+1} = 1 (normalized load impedance)
        g1, gn = first and last prototype g-values

    External Q determines the coupling strength between the filter
    and the source/load impedances.

    Args:
        g_values: Prototype g-values [g1, g2, ..., gn]
        fbw: Fractional bandwidth

    Returns:
        Tuple (Qe_in, Qe_out)

    Reference: Matthaei et al., Eq. 8.11-2
    """
    g0 = 1.0  # Normalized source impedance
    g_n_plus_1 = 1.0  # Normalized load impedance

    qe_in = (g0 * g_values[0]) / fbw
    qe_out = (g_values[-1] * g_n_plus_1) / fbw

    return qe_in, qe_out


def calculate_resonator_components(f0: float, z0: float) -> tuple[float, float]:
    """
    Calculate parallel LC tank components for center frequency.

    For a parallel resonator with reactance equal to system impedance Z0:
        XL = XC = Z0 at resonance

    This yields matched Q and proper impedance transformation.

    Formulas:
        omega0 = 2 * pi * f0
        L = Z0 / omega0  [Henries]
        C = 1 / (omega0 * Z0)  [Farads]

    Verification: f0 = 1 / (2 * pi * sqrt(L * C))

    Args:
        f0: Center frequency in Hz
        z0: System impedance in Ohms

    Returns:
        Tuple (L in Henries, C in Farads)

    Reference: Matthaei et al.
    """
    omega0 = 2 * math.pi * f0
    L = z0 / omega0
    C = 1 / (omega0 * z0)
    return L, C


def calculate_coupling_capacitors_top_c(k_values: list[float], c_resonant: float) -> list[float]:
    """
    Calculate Top-C (series) coupling capacitors.

    Formula:
        Cs[i] = k[i] * C_resonant

    This simplified relationship holds for narrowband designs (FBW < 40%).

    Args:
        k_values: Coupling coefficients [k12, k23, ...]
        c_resonant: Resonator capacitance in Farads

    Returns:
        List of coupling capacitors [Cs12, Cs23, ...] in Farads

    Reference: Matthaei et al.
    """
    return [k * c_resonant for k in k_values]


def calculate_coupling_capacitors_shunt_c(k_values: list[float], c_resonant: float) -> list[float]:
    """
    Calculate Shunt-C coupling capacitors.

    For narrowband designs (FBW < 10%), uses same k*C relationship as Top-C.

    Formula:
        Cs[i] = k[i] * C_resonant

    Note: Full Shunt-C formula from Cohn (1957) uses normalized reactance
    calculations. For FBW < 10%, simplified approach matches within 5%.

    Args:
        k_values: Coupling coefficients [k12, k23, ...]
        c_resonant: Resonator capacitance in Farads

    Returns:
        List of coupling capacitors [Cs12, Cs23, ...] in Farads

    Reference: Cohn (1957), changpuak.ch
    """
    return [k * c_resonant for k in k_values]


def calculate_tank_capacitors(n_resonators: int, c_resonant: float,
                               c_coupling: list[float], topology: str) -> list[float]:
    """
    Calculate compensated tank capacitors.

    For BOTH Top-C and Shunt-C topologies:
        Tank capacitors must be reduced to account for coupling capacitor effects.
        Formula: Cp[i] = C_resonant - Cs[i-1] - Cs[i]

        Where Cs[i-1] and Cs[i] are the coupling caps on either side
        (if they exist).

    Warning: If Cp[i] <= 0, the bandwidth is too wide for this topology.
    - Shunt-C: Limited to FBW <= 10%
    - Top-C: Can handle wider bandwidth up to ~40%

    Args:
        n_resonators: Number of resonators
        c_resonant: Base resonant capacitance in Farads
        c_coupling: Coupling capacitors [Cs12, Cs23, ...]
        topology: 'top' or 'shunt' (same formula, different constraints)

    Returns:
        List of tank capacitors [Cp1, Cp2, ..., Cpn] in Farads

    Reference: Matthaei et al., Cohn (1957)
    """
    tank_caps = []

    for i in range(n_resonators):
        compensation = 0.0
        # Left coupling cap (if not first resonator)
        if i > 0:
            compensation += c_coupling[i - 1]
        # Right coupling cap (if not last resonator)
        if i < n_resonators - 1:
            compensation += c_coupling[i]
        tank_caps.append(c_resonant - compensation)

    return tank_caps


def calculate_min_q(f0: float, bw: float, safety_factor: float = 2.0) -> float:
    """
    Calculate minimum component Q requirement.

    Formula:
        Q_min = (f0 / BW) * safety_factor

    Where:
        f0 = center frequency in Hz
        BW = 3dB bandwidth in Hz
        safety_factor = design margin multiplier (typically 2.0)

    Components (especially inductors) must have unloaded Q exceeding
    Q_min for acceptable insertion loss.

    Typical inductor Q values:
        - Air-core solenoid: 100-300
        - Toroid (iron powder): 50-150
        - Toroid (ferrite): 30-100
        - Chip inductor: 20-50

    Args:
        f0: Center frequency in Hz
        bw: Bandwidth in Hz
        safety_factor: Multiplier for design margin (default 2.0)

    Returns:
        Minimum required component Q (dimensionless)

    Reference: Standard RF design practice
    """
    return (f0 / bw) * safety_factor


def calculate_bandpass_filter(f0: float, bw: float, z0: float, n_resonators: int,
                               filter_type: str, coupling: str,
                               ripple_db: float = 0.5,
                               q_safety: float = 2.0) -> dict:
    """
    Calculate complete bandpass filter component values.

    This is the main entry point that orchestrates all calculations.

    Args:
        f0: Center frequency in Hz
        bw: 3dB bandwidth in Hz
        z0: System impedance in Ohms (typically 50)
        n_resonators: Number of resonators (2-9)
        filter_type: 'butterworth' or 'chebyshev'
        coupling: 'top' (series) or 'shunt' (parallel)
        ripple_db: Chebyshev ripple (0.1, 0.5, or 1.0 dB), ignored for Butterworth
        q_safety: Q safety factor multiplier (default 2.0)

    Returns:
        Dict containing all filter parameters and component values

    Raises:
        ValueError: If invalid parameters provided
    """
    # Validate inputs
    if f0 <= 0:
        raise ValueError("Center frequency must be positive")
    if bw <= 0:
        raise ValueError("Bandwidth must be positive")
    if bw >= f0:
        raise ValueError("Bandwidth must be less than center frequency")
    if z0 <= 0:
        raise ValueError("Impedance must be positive")
    if not 2 <= n_resonators <= 9:
        raise ValueError("Number of resonators must be between 2 and 9")
    if filter_type not in ['butterworth', 'chebyshev', 'bessel']:
        raise ValueError("Filter type must be 'butterworth', 'chebyshev', or 'bessel'")
    if coupling not in ['top', 'shunt']:
        raise ValueError("Coupling must be 'top' or 'shunt'")

    # Fractional bandwidth
    fbw = bw / f0

    # Bandwidth warnings
    warnings = []
    if coupling == 'shunt' and fbw > 0.10:
        warnings.append(f"FBW {fbw*100:.1f}% exceeds 10% limit for Shunt-C; consider Top-C topology")
    if fbw > 0.40:
        warnings.append(f"FBW {fbw*100:.1f}% exceeds 40%; consider transmission-line design")

    # Get prototype g-values
    if filter_type == 'butterworth':
        g_values = calculate_butterworth_g_values(n_resonators)
    elif filter_type == 'chebyshev':
        g_values = get_chebyshev_g_values(n_resonators, ripple_db)
    else:  # bessel
        g_values = get_bessel_g_values(n_resonators)

    # Calculate coupling coefficients and external Q
    k_values = calculate_coupling_coefficients(g_values, fbw)
    qe_in, qe_out = calculate_external_q(g_values, fbw)

    # Calculate resonator components
    L_resonant, C_resonant = calculate_resonator_components(f0, z0)

    # Calculate coupling capacitors based on topology
    if coupling == 'top':
        c_coupling = calculate_coupling_capacitors_top_c(k_values, C_resonant)
    else:
        c_coupling = calculate_coupling_capacitors_shunt_c(k_values, C_resonant)

    # Calculate compensated tank capacitors
    c_tank = calculate_tank_capacitors(n_resonators, C_resonant, c_coupling, coupling)

    # Check for negative tank capacitors (physically impossible)
    negative_caps = [(i+1, ct) for i, ct in enumerate(c_tank) if ct <= 0]
    if negative_caps:
        cap_list = ", ".join([f"Cp{i}" for i, _ in negative_caps])
        raise ValueError(
            f"Bandwidth too wide: tank capacitors {cap_list} would be negative. "
            f"Reduce bandwidth or use fewer resonators."
        )

    # Q requirement
    q_min = calculate_min_q(f0, bw, q_safety)

    # Calculate frequency parameters for display
    f_low = f0 - bw / 2
    f_high = f0 + bw / 2

    return {
        'f0': f0,
        'f_low': f_low,
        'f_high': f_high,
        'bw': bw,
        'fbw': fbw,
        'z0': z0,
        'n_resonators': n_resonators,
        'filter_type': filter_type,
        'coupling': coupling,
        'ripple_db': ripple_db if filter_type == 'chebyshev' else None,
        'q_safety': q_safety,
        'g_values': g_values,
        'k_values': k_values,
        'qe_in': qe_in,
        'qe_out': qe_out,
        'L_resonant': L_resonant,
        'C_resonant': C_resonant,
        'c_coupling': c_coupling,
        'c_tank': c_tank,
        'q_min': q_min,
        'warnings': warnings,
    }

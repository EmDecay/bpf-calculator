"""
Coupled Resonator Bandpass Filter Library

Components:
- calculations: Core filter math functions (g-values, coupling, components)
- formatting: Output display and unit formatting
"""

from .calculations import (
    CHEBYSHEV_G_VALUES,
    calculate_butterworth_g_values,
    get_chebyshev_g_values,
    calculate_coupling_coefficients,
    calculate_external_q,
    calculate_resonator_components,
    calculate_coupling_capacitors_top_c,
    calculate_coupling_capacitors_shunt_c,
    calculate_tank_capacitors,
    calculate_min_q,
    calculate_bandpass_filter,
)

from .formatting import (
    format_frequency,
    format_capacitance,
    format_inductance,
    format_json,
    format_csv,
    format_quiet,
    display_results,
)

__all__ = [
    # Calculations
    'CHEBYSHEV_G_VALUES',
    'calculate_butterworth_g_values',
    'get_chebyshev_g_values',
    'calculate_coupling_coefficients',
    'calculate_external_q',
    'calculate_resonator_components',
    'calculate_coupling_capacitors_top_c',
    'calculate_coupling_capacitors_shunt_c',
    'calculate_tank_capacitors',
    'calculate_min_q',
    'calculate_bandpass_filter',
    # Formatting
    'format_frequency',
    'format_capacitance',
    'format_inductance',
    'format_json',
    'format_csv',
    'format_quiet',
    'display_results',
]

"""
Output formatting for coupled resonator bandpass filters.

Contains unit formatters and display functions for filter results.
"""

import csv
import io
import json


def _format_with_units(value: float, units: list[tuple[float, str]], precision: str = ".4g") -> str:
    """Generic formatter for values with unit suffixes."""
    for threshold, suffix in units:
        if abs(value) >= threshold:
            return f"{value/threshold:{precision}} {suffix}"
    # Use last unit if value is smaller than all thresholds
    _, suffix = units[-1]
    return f"{value/units[-1][0]:{precision}} {suffix}"


def format_frequency(freq_hz: float) -> str:
    """Format frequency with appropriate unit (GHz, MHz, kHz, Hz)."""
    return _format_with_units(freq_hz, [
        (1e9, 'GHz'), (1e6, 'MHz'), (1e3, 'kHz'), (1, 'Hz')
    ])


def format_capacitance(value_farads: float) -> str:
    """Format capacitance with appropriate unit (mF, µF, nF, pF)."""
    return _format_with_units(value_farads, [
        (1e-3, 'mF'), (1e-6, 'µF'), (1e-9, 'nF'), (1e-12, 'pF')
    ], ".2f")


def format_inductance(value_henries: float) -> str:
    """Format inductance with appropriate unit (H, mH, µH, nH)."""
    return _format_with_units(value_henries, [
        (1, 'H'), (1e-3, 'mH'), (1e-6, 'µH'), (1e-9, 'nH')
    ], ".2f")


def format_json(result: dict) -> str:
    """Format results as JSON."""
    output = {
        'filter_type': result['filter_type'],
        'coupling': result['coupling'],
        'center_frequency_hz': result['f0'],
        'bandwidth_hz': result['bw'],
        'f_low_hz': result['f_low'],
        'f_high_hz': result['f_high'],
        'fractional_bw': result['fbw'],
        'impedance_ohms': result['z0'],
        'n_resonators': result['n_resonators'],
        'q_min': result['q_min'],
        'components': {
            'tank_capacitors': [{'name': f'Cp{i+1}', 'value_farads': v}
                               for i, v in enumerate(result['c_tank'])],
            'inductors': [{'name': f'L{i+1}', 'value_henries': result['L_resonant']}
                         for i in range(result['n_resonators'])],
            'coupling_capacitors': [{'name': f'Cs{i+1}{i+2}', 'value_farads': v}
                                   for i, v in enumerate(result['c_coupling'])]
        },
        'external_q': {
            'input': result['qe_in'],
            'output': result['qe_out']
        }
    }
    if result.get('ripple_db') is not None:
        output['ripple_db'] = result['ripple_db']
    return json.dumps(output, indent=2)


def format_csv(result: dict) -> str:
    """Format results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Component', 'Value', 'Unit'])
    for i, v in enumerate(result['c_tank']):
        formatted = format_capacitance(v)
        val, unit = formatted.rsplit(' ', 1)
        writer.writerow([f'Cp{i+1}', val, unit])
    for i in range(result['n_resonators']):
        formatted = format_inductance(result['L_resonant'])
        val, unit = formatted.rsplit(' ', 1)
        writer.writerow([f'L{i+1}', val, unit])
    for i, v in enumerate(result['c_coupling']):
        formatted = format_capacitance(v)
        val, unit = formatted.rsplit(' ', 1)
        writer.writerow([f'Cs{i+1}{i+2}', val, unit])
    return output.getvalue()


def format_quiet(result: dict, raw: bool = False) -> str:
    """Format results as minimal text (values only)."""
    lines = []
    for i, v in enumerate(result['c_tank']):
        if raw:
            lines.append(f"Cp{i+1}: {v:.6e} F")
        else:
            lines.append(f"Cp{i+1}: {format_capacitance(v)}")
    for i in range(result['n_resonators']):
        if raw:
            lines.append(f"L{i+1}: {result['L_resonant']:.6e} H")
        else:
            lines.append(f"L{i+1}: {format_inductance(result['L_resonant'])}")
    for i, v in enumerate(result['c_coupling']):
        if raw:
            lines.append(f"Cs{i+1}{i+2}: {v:.6e} F")
        else:
            lines.append(f"Cs{i+1}{i+2}: {format_capacitance(v)}")
    return '\n'.join(lines)


def _print_top_c_diagram(n: int) -> None:
    """
    Print Top-C (series coupling) topology diagram.

    Shows n tanks with n-1 coupling capacitors in series on main line.
    Each tank is a parallel LC circuit to ground.
    """
    n_coupling = n - 1
    seg_w = 15  # width for each tank segment (──────┤├──────┬ = 15 chars)

    # Main line
    main_line = "  IN ──────┬" + "──────┤├──────┬" * n_coupling + "────── OUT"
    tank_pos = [11 + i * seg_w for i in range(n)]
    line_len = len(main_line)

    # Coupling capacitor labels above main line (centered between tanks)
    label_chars = [' '] * line_len
    for i in range(n_coupling):
        # Position between tank i and tank i+1
        mid = (tank_pos[i] + tank_pos[i + 1]) // 2
        label = f"Cs{i+1}{i+2}"
        start = mid - len(label) // 2
        for j, ch in enumerate(label):
            if 0 <= start + j < line_len:
                label_chars[start + j] = ch
    label_line = ''.join(label_chars)

    def build_line(elements: list[str]) -> str:
        """Build line with elements centered under tank positions."""
        chars = [' '] * line_len
        for pos, elem in zip(tank_pos, elements):
            start = pos - len(elem) // 2
            for j, ch in enumerate(elem):
                if 0 <= start + j < line_len:
                    chars[start + j] = ch
        return ''.join(chars)

    # Tank: parallel C and L - all elements same width for alignment
    #    ┌──┴──┐
    #    │     │
    #   Cp1   L1
    #    │     │
    #    └──┬──┘
    tank_w = "┌──┴──┐"  # 7 chars wide, ┴ at center
    vert_line = build_line(["   │   "] * n)  # │ centered in 7 chars
    tank_top = build_line([tank_w] * n)
    tank_r1 = build_line(["│     │"] * n)
    tank_r2 = build_line([f"Cp{i+1:<2} L{i+1}" for i in range(n)])
    tank_r3 = build_line(["│     │"] * n)
    tank_bot = build_line(["└──┬──┘"] * n)
    gnd_wire = build_line(["   │   "] * n)
    gnd_sym = build_line(["  GND  "] * n)

    print(label_line)
    print(main_line)
    print(vert_line)
    print(tank_top)
    print(tank_r1)
    print(tank_r2)
    print(tank_r3)
    print(tank_bot)
    print(gnd_wire)
    print(gnd_sym)


def _print_shunt_c_diagram(n: int) -> None:
    """
    Print Shunt-C (bottom-coupled) topology diagram.

    In this topology, coupling capacitors connect the BOTTOMS of adjacent
    tanks horizontally, before they all connect to a common ground.
    This is "capacitive bottom coupling" per Cohn (1957).
    """
    n_coupling = n - 1
    seg_w = 13  # width for each tank segment

    # Main line
    main_line = "  IN ──────┬" + "────────────┬" * (n - 1) + "────── OUT"
    tank_pos = [11 + i * seg_w for i in range(n)]
    line_len = len(main_line)

    def build_line(elements: list[str]) -> str:
        """Build line with elements centered under tank positions."""
        chars = [' '] * line_len
        for pos, elem in zip(tank_pos, elements):
            start = pos - len(elem) // 2
            for j, ch in enumerate(elem):
                if 0 <= start + j < line_len:
                    chars[start + j] = ch
        return ''.join(chars)

    # Vertical wire from main line to tanks - same width as tank for alignment
    vert1 = build_line(["   │   "] * n)
    vert2 = build_line(["   │   "] * n)

    # Tank components - same style as Top-C
    tank_top = build_line(["┌──┴──┐"] * n)
    tank_r1 = build_line(["│     │"] * n)
    tank_r2 = build_line([f"Cp{i+1:<2} L{i+1}" for i in range(n)])
    tank_r3 = build_line(["│     │"] * n)
    tank_bot = build_line(["└──┬──┘"] * n)

    # Bottom coupling rail with horizontal coupling caps between tanks
    coupling_line_chars = [' '] * line_len
    for i, pos in enumerate(tank_pos):
        if i == 0:
            coupling_line_chars[pos] = '├'
        elif i == n - 1:
            coupling_line_chars[pos] = '┤'
        else:
            coupling_line_chars[pos] = '┼'
        if i < n - 1:
            next_pos = tank_pos[i + 1]
            mid = (pos + next_pos) // 2
            for j in range(pos + 1, next_pos):
                coupling_line_chars[j] = '─'
            label = f"Cs{i+1}{i+2}"
            start = mid - len(label) // 2
            for j, ch in enumerate(label):
                if 0 <= start + j < line_len:
                    coupling_line_chars[start + j] = ch
    coupling_line = ''.join(coupling_line_chars)

    # Ground connection from center of bottom rail
    center_pos = tank_pos[n // 2]
    gnd_wire_chars = [' '] * line_len
    gnd_wire_chars[center_pos] = '│'
    gnd_wire = ''.join(gnd_wire_chars)

    gnd_chars = [' '] * line_len
    gnd_label = "GND"
    start = center_pos - len(gnd_label) // 2
    for j, ch in enumerate(gnd_label):
        if 0 <= start + j < line_len:
            gnd_chars[start + j] = ch
    gnd = ''.join(gnd_chars)

    print(main_line)
    print(vert1)
    print(tank_top)
    print(tank_r1)
    print(tank_r2)
    print(tank_r3)
    print(tank_bot)
    print(vert2)
    print(coupling_line)
    print(gnd_wire)
    print(gnd)


def display_results(result: dict, raw: bool = False,
                    output_format: str = 'table', quiet: bool = False) -> None:
    """
    Display calculated filter component values.

    Args:
        result: Dict from calculate_bandpass_filter()
        raw: If True, display values in scientific notation
        output_format: 'table', 'json', or 'csv'
        quiet: If True, output only component values (no header/diagram)
    """
    if output_format == 'json':
        print(format_json(result))
        return
    if output_format == 'csv':
        print(format_csv(result), end='')
        return
    if quiet:
        print(format_quiet(result, raw))
        return

    coupling_name = "Top-C (Series)" if result['coupling'] == 'top' else "Shunt-C (Parallel)"
    title = f"{result['filter_type'].title()} Coupled Resonator Bandpass Filter"

    print(f"\n{title}")
    print("=" * 50)
    print(f"Center Frequency f₀: {format_frequency(result['f0'])}")
    print(f"Lower Cutoff fₗ:     {format_frequency(result['f_low'])}")
    print(f"Upper Cutoff fₕ:     {format_frequency(result['f_high'])}")
    print(f"Bandwidth BW:        {format_frequency(result['bw'])}")
    print(f"Fractional BW:       {result['fbw']*100:.2f}%")
    print(f"Impedance Z₀:        {result['z0']:.4g} Ω")
    if result['ripple_db'] is not None:
        print(f"Ripple:              {result['ripple_db']} dB")
    print(f"Resonators:          {result['n_resonators']}")
    print(f"Coupling:            {coupling_name}")
    print("=" * 50)

    # Display warnings if any
    if result['warnings']:
        print("\nWarnings:")
        for w in result['warnings']:
            print(f"  ⚠ {w}")

    # Q requirement
    print(f"\nMinimum Component Q: {result['q_min']:.0f}")
    print(f"  (Q safety factor: {result['q_safety']})")

    # Topology diagram
    n = result['n_resonators']
    print("\nTopology:")
    if result['coupling'] == 'top':
        _print_top_c_diagram(n)
    else:
        _print_shunt_c_diagram(n)

    # Component values table
    print(f"\n{'Component Values':^50}")
    print(f"┌{'─' * 24}┬{'─' * 24}┐")
    print(f"│{'Tank Capacitors':^24}│{'Inductors':^24}│")
    print(f"├{'─' * 24}┼{'─' * 24}┤")

    for i in range(n):
        if raw:
            cap_str = f"Cp{i+1}: {result['c_tank'][i]:.6e} F"
            ind_str = f"L{i+1}: {result['L_resonant']:.6e} H"
        else:
            cap_str = f"Cp{i+1}: {format_capacitance(result['c_tank'][i])}"
            ind_str = f"L{i+1}: {format_inductance(result['L_resonant'])}"
        print(f"│ {cap_str:<22} │ {ind_str:<22} │")

    print(f"└{'─' * 24}┴{'─' * 24}┘")

    # Coupling capacitors
    print(f"\n┌{'─' * 24}┐")
    print(f"│{'Coupling Capacitors':^24}│")
    print(f"├{'─' * 24}┤")

    for i, cs in enumerate(result['c_coupling']):
        if raw:
            cs_str = f"Cs{i+1}{i+2}: {cs:.6e} F"
        else:
            cs_str = f"Cs{i+1}{i+2}: {format_capacitance(cs)}"
        print(f"│ {cs_str:<22} │")

    print(f"└{'─' * 24}┘")

    # External Q values
    print(f"\nExternal Q (input):  {result['qe_in']:.2f}")
    print(f"External Q (output): {result['qe_out']:.2f}")
    print()

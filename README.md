# Coupled Resonator Bandpass Filter Calculator

A command-line tool for calculating component values for coupled resonator bandpass filters. Supports Top-C (series) and Shunt-C (parallel) coupling topologies with Butterworth or Chebyshev responses.

## Features

- **Filter Types**: Butterworth (any order) and Chebyshev (odd orders: 3, 5, 7, 9)
- **Topologies**: Top-C (series coupling) and Shunt-C (parallel coupling)
- **Resonators**: 2-9 LC tank circuits
- **Chebyshev Ripple**: 0.1, 0.5, or 1.0 dB options
- **Flexible Input**: Center frequency + bandwidth, or lower/upper cutoff frequencies
- **Unit Support**: MHz, kHz, GHz, Hz for frequencies; ohm, kohm for impedance
- **Practical Guidance**: Minimum Q requirements, bandwidth warnings, component values

## Requirements

- Python 3.10+
- No external dependencies (standard library only)

## Installation

```bash
git clone https://github.com/yourusername/bpf-calculator.git
cd bpf-calculator
```

## Usage

### Basic Syntax

```bash
./bandpass-filter.py <type> <topology> -f <freq> -b <bandwidth> [options]
```

### Examples

**5-pole Butterworth for 20m amateur band:**
```bash
./bandpass-filter.py bw top -f 14.2MHz -b 500kHz -n 5
```

**7-pole Chebyshev with 0.5dB ripple:**
```bash
./bandpass-filter.py ch shunt --fl 14MHz --fh 14.35MHz -r 0.5 -n 7
```

**With custom impedance and Q safety factor:**
```bash
./bandpass-filter.py bw t -f 7.1MHz -b 300kHz -z 75 --q-safety 2.5 -n 5
```

### Output Formats

```bash
# JSON output (for scripting)
./bandpass-filter.py bw top -f 14.2MHz -b 500kHz --format json

# CSV output (for spreadsheets)
./bandpass-filter.py bw top -f 14.2MHz -b 500kHz --format csv

# Quiet mode (values only)
./bandpass-filter.py bw top -f 14.2MHz -b 500kHz -q
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `type` | Filter type: `butterworth`/`bw` or `chebyshev`/`ch` (positional) |
| `topology` | Coupling: `top`/`t` (series) or `shunt`/`s` (parallel) (positional) |
| `-t, --type` | Filter type (flag alternative to positional) |
| `-c, --coupling` | Topology (flag alternative to positional) |
| `-f, --frequency` | Center frequency (e.g., `14.2MHz`) |
| `-b, --bandwidth` | 3dB bandwidth (e.g., `500kHz`) |
| `--fl, --f-low` | Lower cutoff frequency (alternative to -f/-b) |
| `--fh, --f-high` | Upper cutoff frequency (alternative to -f/-b) |
| `-n, --resonators` | Number of resonators: 2-9 (default: 2) |
| `-z, --impedance` | System impedance (default: 50 ohms) |
| `-r, --ripple` | Chebyshev ripple: 0.1, 0.5, or 1.0 dB (default: 0.5) |
| `--q-safety` | Q safety factor multiplier (default: 2.0) |
| `-q, --quiet` | Output only component values (no header/diagram) |
| `--format` | Output format: `table` (default), `json`, or `csv` |
| `--raw` | Output raw values in scientific notation |
| `--explain` | Explain how the selected filter type works |
| `--verify` | Run calculation verification tests |

## Output

The calculator provides:

- **Resonator components**: Inductance (L) and capacitance (C) for each LC tank
- **Coupling capacitors**: Values for inter-stage coupling
- **Tank capacitors**: Adjusted values accounting for coupling
- **Minimum Q requirement**: Required inductor Q for acceptable insertion loss
- **Bandwidth warnings**: Alerts when fractional bandwidth exceeds topology limits

## Design Notes

### Topology Selection

- **Top-C (Series)**: Better for wider bandwidths (up to 40% fractional BW)
- **Shunt-C (Parallel)**: Best for narrow bandwidths (<10% fractional BW)

### Chebyshev Constraints

Chebyshev filters with equal source/load impedances require an **odd** number of resonators (3, 5, 7, or 9). This is a mathematical property of Chebyshev Type I prototype g-values: even orders produce unequal termination impedances (g₀ ≠ g_{n+1}), requiring impedance transformers for 50Ω in/out systems. Use Butterworth for even resonator counts, which supports any order with equal terminations.

### Component Q

Inductors must have unloaded Q greater than `(f0/BW) * q_safety` for acceptable insertion loss. Typical values:
- Air-core inductors: Q = 100-300
- Toroidal inductors: Q = 50-150

## Theory

This calculator implements the coupled resonator filter synthesis method from classic RF engineering texts. The design process:

1. Calculate lowpass prototype g-values (Butterworth formula or Chebyshev tables)
2. Derive coupling coefficients from g-values and fractional bandwidth
3. Compute LC resonator values for the center frequency
4. Calculate coupling capacitor values based on topology

## References

- Matthaei, Young, Jones - *Microwave Filters, Impedance-Matching Networks, and Coupling Structures*
- Zverev - *Handbook of Filter Synthesis* (1967)
- Cohn - *Direct-Coupled-Resonator Filters* (1957)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

Matt N3AR (with AI coding assistance)

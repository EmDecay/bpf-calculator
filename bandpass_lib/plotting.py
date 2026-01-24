"""
ASCII frequency response plotting and data export for bandpass filters.
Renders magnitude response as terminal-friendly ASCII art.
"""
import json
import math

def _freq_to_col(f: float, f_min: float, f_max: float, width: int) -> int:
    """Map log(frequency) to column index (0 to width-1)."""
    if f_min == f_max:
        return width // 2  # Single point: center it
    log_min, log_max = math.log10(f_min), math.log10(f_max)
    log_f = math.log10(f)
    col = int((log_f - log_min) / (log_max - log_min) * (width - 1))
    return max(0, min(width - 1, col))

def _db_to_row(db: float, db_min: float, height: int) -> int:
    """Map dB to row index (0=top=0dB, height-1=bottom=db_min)."""
    db_clamped = max(db_min, min(0, db))
    row = int(-db_clamped / (-db_min) * (height - 1))
    return max(0, min(height - 1, row))

def render_ascii_plot(
    sweep_data: list[tuple[float, float]],
    f0: float,
    bw: float,
    width: int = 60,
    height: int = 10,
    db_min: float = -60.0,
    title: str = "Frequency Response"
) -> str:
    """
    Render frequency response as ASCII art.

    Args:
        sweep_data: List of (frequency_hz, magnitude_db) tuples
        f0: Center frequency in Hz
        bw: Bandwidth in Hz
        width: Plot width in characters
        height: Plot height in lines
        db_min: Minimum dB shown (floor)
        title: Plot title

    Returns:
        Multi-line string with ASCII plot
    """
    if not sweep_data:
        return "No data to plot"

    f_min = sweep_data[0][0]
    f_max = sweep_data[-1][0]

    # Build 2D character grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Plot sweep data - fill from 0dB down to the curve
    for f, db in sweep_data:
        col = _freq_to_col(f, f_min, f_max, width)
        row = _db_to_row(db, db_min, height)
        # Fill from top (0dB) down to this row
        for r in range(row + 1):
            grid[r][col] = '#'

    # Draw -3dB reference line
    row_3db = _db_to_row(-3.0, db_min, height)
    for col in range(width):
        if grid[row_3db][col] == ' ':
            grid[row_3db][col] = '-'

    # Mark center frequency with vertical line
    col_f0 = _freq_to_col(f0, f_min, f_max, width)
    for row in range(height):
        if grid[row][col_f0] in (' ', '-'):
            grid[row][col_f0] = '|'
        elif grid[row][col_f0] == '#':
            pass  # Keep the fill
    grid[row_3db][col_f0] = '+'  # Intersection marker

    # Build output string
    lines = [title]

    # Y-axis labels at key dB values (0dB at top takes priority)
    db_labels = {row_3db: -3, height - 1: int(db_min), 0: 0}

    lines.append("  dB")  # Y-axis label
    for row in range(height):
        db_label = db_labels.get(row, None)
        if db_label is not None:
            prefix = f"{db_label:4d} |"
        else:
            prefix = "     |"
        lines.append(prefix + ''.join(grid[row]))

    # X-axis
    lines.append("     +" + "-" * width)

    # Frequency labels
    f_low = f0 - bw / 2
    f_high = f0 + bw / 2
    x_label = f"     {_format_freq(f_min):>10}  {_format_freq(f_low):>10}  {_format_freq(f0):>8}  {_format_freq(f_high):>10}  {_format_freq(f_max):>10}"
    lines.append(x_label[:6 + width])  # Trim to fit
    lines.append("     Frequency (Hz)")

    return '\n'.join(lines)

def _format_freq(f: float) -> str:
    """Format frequency with appropriate unit."""
    if f >= 1e9:
        return f"{f/1e9:.2f}G"
    elif f >= 1e6:
        return f"{f/1e6:.2f}M"
    elif f >= 1e3:
        return f"{f/1e3:.2f}k"
    return f"{f:.1f}"

def export_json(
    sweep_data: list[tuple[float, float]],
    f0: float,
    bw: float,
    filter_type: str,
    order: int,
    ripple_db: float | None = None
) -> str:
    """Export sweep data as JSON string."""
    data = {
        "filter_type": filter_type,
        "f0_hz": f0,
        "bandwidth_hz": bw,
        "order": order,
        "data": [{"frequency_hz": f, "magnitude_db": round(db, 2)} for f, db in sweep_data]
    }
    if ripple_db is not None:
        data["ripple_db"] = ripple_db
    return json.dumps(data, indent=2)

def export_csv(sweep_data: list[tuple[float, float]]) -> str:
    """Export sweep data as CSV string."""
    lines = ["frequency_hz,magnitude_db"]
    for f, db in sweep_data:
        lines.append(f"{f},{db:.2f}")
    return '\n'.join(lines)

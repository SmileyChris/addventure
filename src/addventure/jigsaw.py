"""Jigsaw mode: compute grid, shuffle pieces, detect empty cells."""
import math


def compute_grid(
    content_w_mm: float,
    content_h_mm: float,
    cols: int = 4,
    target_cell_h_mm: float = 25.0,
) -> dict:
    """Compute grid dimensions for jigsaw slicing."""
    rows = max(2, math.ceil(content_h_mm / target_cell_h_mm))
    cell_w = content_w_mm / cols
    cell_h = content_h_mm / rows
    return {
        "cols": cols,
        "rows": rows,
        "cell_w_mm": cell_w,
        "cell_h_mm": cell_h,
    }


def interleave_pieces(pieces: list, cols: int) -> list:
    """Reorder pieces so no original neighbors are adjacent.

    Uses every-3rd interleave: positions 0,3,6,1,4,7,2,5,...
    """
    n = len(pieces)
    step = 3
    order = []
    for start in range(step):
        for i in range(start, n, step):
            order.append(i)
    return [pieces[i] for i in order]


def checkerboard_flips(rows: int, cols: int) -> list[list[bool]]:
    """Generate checkerboard flip pattern. True = 180° rotated."""
    return [
        [(r + c) % 2 == 1 for c in range(cols)]
        for r in range(rows)
    ]


def detect_empty_cells(
    png_path: str,
    cols: int,
    rows: int,
    brightness_threshold: int = 250,
) -> list[tuple[int, int]]:
    """Detect which grid cells are visually empty (all near-white).

    Returns list of (row, col) tuples for non-empty cells.
    """
    from PIL import Image

    img = Image.open(png_path).convert("L")  # grayscale
    w, h = img.size
    cell_w = w // cols
    cell_h = h // rows

    non_empty = []
    for r in range(rows):
        for c in range(cols):
            x0 = c * cell_w
            y0 = r * cell_h
            x1 = min(x0 + cell_w, w)
            y1 = min(y0 + cell_h, h)
            cell = img.crop((x0, y0, x1, y1))
            # Check if any pixel is dark enough to be content
            if cell.getextrema()[0] < brightness_threshold:
                non_empty.append((r, c))

    return non_empty

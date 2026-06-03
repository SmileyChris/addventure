"""Image effect pre-processing for cover images.

Supports styles that need Python/Pillow before Typst sees the image:
  - torn-edge: irregular torn-paper edges with transparency
  - scratches (overlay generation): semi-transparent scratch marks
"""

import random
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def process_image(image_path: Path, style: str) -> Path | None:
    """Pre-process a cover image based on the given style.

    Returns a path to the processed image (temp file), or None if
    no pre-processing is needed (style handled by Typst alone).
    """
    if not HAS_PILLOW:
        return None

    if style == "torn-edge":
        return _apply_torn_edge(image_path)
    elif style == "burned-edge":
        return _apply_burned_edge(image_path)
    elif style in {"greyscale", "grayscale"}:
        return _apply_greyscale(image_path)
    elif style == "sepia":
        return _apply_sepia(image_path)

    return None


def _apply_greyscale(image_path: Path) -> Path:
    """Convert an image to greyscale while preserving alpha.

    Normalize the average luminance upward for dark cover art so the printed
    image keeps detail after black-and-white conversion.
    """
    img = Image.open(image_path).convert("RGBA")
    grey = ImageOps.grayscale(img)
    grey = _normalize_luminance(grey, img.getchannel("A"), target=92)
    result = Image.merge("RGBA", (grey, grey, grey, img.getchannel("A")))

    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    result.save(fp.name, "PNG")
    return Path(fp.name)


def _apply_sepia(image_path: Path) -> Path:
    """Apply a warm sepia tone while preserving alpha."""
    img = Image.open(image_path).convert("RGBA")
    grey = ImageOps.grayscale(img)
    grey = _normalize_luminance(grey, img.getchannel("A"), target=92)
    result = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src = grey.load()
    alpha = img.getchannel("A").load()
    pixels = result.load()

    for y in range(img.height):
        for x in range(img.width):
            g = src[x, y]
            r = min(255, int(g * 1.18 + 18))
            gv = min(255, int(g * 0.96 + 10))
            b = min(255, int(g * 0.72))
            pixels[x, y] = (r, gv, b, alpha[x, y])

    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    result.save(fp.name, "PNG")
    return Path(fp.name)


def _normalize_luminance(grey: Image.Image, alpha: Image.Image,
                         target: int = 132) -> Image.Image:
    """Lift or lower greyscale values so visible pixels average near target."""
    hist = grey.histogram(mask=alpha)
    total = sum(hist)
    if total == 0:
        return grey
    avg = sum(i * count for i, count in enumerate(hist)) / total
    if avg <= 0:
        return grey

    factor = max(0.75, min(2.2, target / avg))
    table = [max(0, min(255, int(i * factor))) for i in range(256)]
    return grey.point(table)


def generate_scratch_overlay(width: int, height: int, density: float = 0.003) -> Path:
    """Generate a semi-transparent scratch overlay PNG.

    Returns a temp file path. Only called when scratches style is active.
    """
    if not HAS_PILLOW:
        return _empty_png()

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    num_scratches = int(width * height * density)
    for _ in range(num_scratches):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        # Scratches tend to be roughly horizontal or vertical
        if random.random() < 0.5:
            # Horizontal-ish
            x2 = x1 + random.randint(int(width * 0.02), int(width * 0.4))
            y2 = y1 + random.randint(-int(height * 0.03), int(height * 0.03))
        else:
            # Vertical-ish
            x2 = x1 + random.randint(-int(width * 0.03), int(width * 0.03))
            y2 = y1 + random.randint(int(height * 0.02), int(height * 0.4))

        alpha = random.randint(20, 90)
        thickness = random.randint(1, 3)
        color = (255, 255, 255, alpha)
        draw.line((x1, y1, x2, y2), fill=color, width=thickness)

    # Add a few darker specks/nicks
    num_specks = int(width * height * density * 0.5)
    for _ in range(num_specks):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        size = random.randint(1, 3)
        alpha = random.randint(40, 120)
        draw.ellipse(
            (x, y, x + size, y + size),
            fill=(255, 255, 255, alpha),
        )

    # Slight blur to soften scratches
    img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(fp.name, "PNG")
    return Path(fp.name)


def _empty_png() -> Path:
    """Fallback: tiny transparent PNG when Pillow is unavailable."""
    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    # Minimal valid 1x1 transparent PNG
    fp.write(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Path(fp.name)


def _apply_torn_edge(image_path: Path, tear_depth_pct: float = 0.08) -> Path:
    """Apply torn-paper edges by cutting INTO the image.

    The jagged tear removes pixels from the edges of the image itself,
    with paper-fiber fringe and edge shadow on the surviving portion.
    No external padding — the image keeps its original dimensions.
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    tear_px = max(int(min(w, h) * tear_depth_pct), 15)

    # Generate the torn-edge polygon: starts at image corners,
    # wanders INWARD by up to tear_px pixels along each edge
    tear_poly = _tear_polygon_inward(0, 0, w, h, tear_px)

    # Create mask: white inside the tear polygon
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(tear_poly, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.5))

    # Apply mask to image
    img.putalpha(Image.composite(
        img.getchannel("A"),
        Image.new("L", (w, h), 0),
        mask,
    ))

    # Paper fiber fringe along the tear — thin off-white line inside the edge
    img = _add_paper_fringe(img, tear_poly, tear_px)

    # Darken the torn edges for depth (inner shadow on the surviving paper)
    img = _add_inner_shadow(img, tear_poly, tear_px)

    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(fp.name, "PNG")
    return Path(fp.name)


def _tear_polygon_inward(ix: int, iy: int, w: int, h: int,
                          tear_px: int) -> list[tuple[int, int]]:
    """Generate a polygon that cuts INTO the image from each edge.

    Points wander inward from the nominal image boundary by a random-walk
    displacement, with occasional deeper tear lobes.
    """
    step = max(3, min(w, h) // 50)

    # Walk clockwise: top-left → top-right (top edge, displace downward)
    top = _torn_walk(
        (ix, iy), (ix + w - 1, iy), tear_px, step,
        displace_dir=(0, 1),
    )
    # Top-right → bottom-right (right edge, displace leftward)
    right = _torn_walk(
        (ix + w - 1, iy), (ix + w - 1, iy + h - 1), tear_px, step,
        displace_dir=(-1, 0),
    )
    # Bottom-right → bottom-left (bottom edge, displace upward)
    bottom = _torn_walk(
        (ix + w - 1, iy + h - 1), (ix, iy + h - 1), tear_px, step,
        displace_dir=(0, -1),
    )
    # Bottom-left → top-left (left edge, displace rightward)
    left = _torn_walk(
        (ix, iy + h - 1), (ix, iy), tear_px, step,
        displace_dir=(1, 0),
    )

    # Build closed polygon
    poly = []
    poly.extend(top)
    poly.extend(right[1:])
    poly.extend(bottom[1:])
    poly.extend(left[1:-1])
    return poly


def _torn_walk(start: tuple[int, int], end: tuple[int, int],
               max_displace: int, step: int,
               displace_dir: tuple[int, int]) -> list[tuple[int, int]]:
    """Walk from start to end with jagged, angular tear displacement.

    Produces sharp, irregular torn edges rather than smooth curves.
    Sections alternate between nearly straight (where paper held) and
    deep angular gashes (where paper gave way).
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = max(abs(dx), abs(dy), 1)
    num_steps = max(dist // step, 5)

    perp_x, perp_y = displace_dir
    points = []

    # Divide the edge into segments of varying tear character
    pos = 0
    while pos <= num_steps:
        t = pos / num_steps
        x = int(start[0] + dx * t)
        y = int(start[1] + dy * t)

        # Determine what kind of segment we're in
        segment_rand = random.random()

        if segment_rand < 0.2:
            # Clean straight edge (paper held firm) — barely any tear
            displacement = random.uniform(0, max_displace * 0.08)
        elif segment_rand < 0.35:
            # Light nibble — small irregular bites
            displacement = random.uniform(max_displace * 0.05, max_displace * 0.25)
        elif segment_rand < 0.65:
            # Moderate jagged tear
            displacement = random.uniform(max_displace * 0.25, max_displace * 0.65)
        elif segment_rand < 0.85:
            # Deep tear gash — paper gave way
            displacement = random.uniform(max_displace * 0.5, max_displace * 1.1)
        else:
            # Very deep rip — almost tore the whole edge off
            displacement = random.uniform(max_displace * 0.7, max_displace * 1.5)

        # Near corners, ease back to zero so the image corners stay intact
        corner_ease = 1.0
        if pos < num_steps * 0.12:
            corner_ease = pos / (num_steps * 0.12)
        elif pos > num_steps * 0.88:
            corner_ease = (num_steps - pos) / (num_steps * 0.12)
        displacement *= corner_ease

        disp_x = x + int(perp_x * displacement)
        disp_y = y + int(perp_y * displacement)
        points.append((disp_x, disp_y))

        # Vary step size to create irregular spacing (some areas detailed, some sparse)
        if random.random() < 0.3:
            pos += random.randint(1, 3)  # clustered points for detail
        else:
            pos += random.randint(2, 5)  # spread out

    # Ensure endpoint is included
    points.append((end[0], end[1]))
    return points


def _add_paper_fringe(img: Image.Image, tear_poly: list[tuple[int, int]],
                      tear_px: int) -> Image.Image:
    """Add paper fiber effects along the torn edge.

    Two layers: a bright white core fringe (exposed paper interior) just
    inside the tear, and individual fiber strands extending outward from
    tear points.
    """
    fringe = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fringe)
    w, h = img.size

    # Layer 1: bright white core fringe along the tear line (paper cross-section)
    for offset, alpha in [(-1, 140), (0, 180), (1, 100)]:
        inset_poly = _inset_polygon(tear_poly, offset)
        if len(inset_poly) >= 2:
            draw.line(inset_poly + [inset_poly[0]], fill=(252, 250, 242, alpha), width=3)

    # Layer 2: individual fiber strands pulling out from tear points
    rng = random.Random(42)  # fixed seed so fibers are consistent per image
    # More fibers at deep tear points
    fiber_count = max(len(tear_poly) // 4, 30)
    for _ in range(fiber_count):
        idx = rng.randint(0, len(tear_poly) - 1)
        fx, fy = tear_poly[idx]
        # Fiber strands go outward (away from image center)
        cx, cy = w / 2, h / 2
        outward_x = fx - cx
        outward_y = fy - cy
        d = max((outward_x ** 2 + outward_y ** 2) ** 0.5, 1)
        # Longer, more varied strands
        strand_len = rng.randint(8, max(tear_px // 2, 20))
        ex = int(fx + (outward_x / d) * strand_len + rng.randint(-10, 10))
        ey = int(fy + (outward_y / d) * strand_len + rng.randint(-10, 10))
        alpha = rng.randint(150, 240)
        # Vary thickness — some thin, some thicker like pulled fiber bundles
        width = rng.choices([1, 1, 1, 2, 3], weights=[50, 30, 10, 7, 3])[0]
        draw.line((fx, fy, ex, ey), fill=(252, 250, 243, alpha), width=width)

    # Layer 3: tiny paper specks near the edge
    for _ in range(fiber_count):
        idx = rng.randint(0, len(tear_poly) - 1)
        fx, fy = tear_poly[idx]
        cx, cy = w / 2, h / 2
        outward_x = fx - cx
        outward_y = fy - cy
        d = max((outward_x ** 2 + outward_y ** 2) ** 0.5, 1)
        sx = int(fx + (outward_x / d) * rng.randint(2, 6) + rng.randint(-4, 4))
        sy = int(fy + (outward_y / d) * rng.randint(2, 6) + rng.randint(-4, 4))
        if 0 <= sx < w and 0 <= sy < h:
            draw.point((sx, sy), fill=(250, 248, 240, rng.randint(80, 160)))

    return Image.alpha_composite(img, fringe)


def _inset_polygon(poly: list[tuple[int, int]], inset: int) -> list[tuple[int, int]]:
    """Inset a polygon by a fixed pixel amount. Simplified: offset each point
    toward the polygon center."""
    if not poly:
        return poly
    # Compute center
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    result = []
    for x, y in poly:
        # Direction from center to point
        dx = x - cx
        dy = y - cy
        d = max((dx * dx + dy * dy) ** 0.5, 1)
        nx = int(x - (dx / d) * inset)
        ny = int(y - (dy / d) * inset)
        result.append((nx, ny))
    return result


def _add_inner_shadow(img: Image.Image, tear_poly: list[tuple[int, int]],
                      tear_px: int) -> Image.Image:
    """Darken the surviving paper near the torn edge for depth.

    Creates an inner shadow by finding the torn-away regions and
    darkening a gradient inward from the tear line.
    """
    w, h = img.size

    # Build a mask of the torn-away area (inverted tear polygon)
    torn_away_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(torn_away_mask).polygon(tear_poly, fill=255)
    # Invert: 255 where torn away, 0 where image survives
    torn_away_mask = ImageOps.invert(torn_away_mask)

    # Blur the torn-away mask to create a tight gradient
    blur_radius = max(tear_px * 0.15, 2)
    gradient = torn_away_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Now create a shadow overlay: dark pixels where the gradient bleeds inward
    # The gradient is strongest in torn-away areas and fades into the image
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_pixels = shadow.load()
    gradient_pixels = gradient.load()
    alpha_channel = img.getchannel("A").load() if img.mode == "RGBA" else None

    for y in range(h):
        for x in range(w):
            g = gradient_pixels[x, y]
            # Only apply shadow where the image is opaque and gradient reaches in
            if g > 5:
                img_alpha = alpha_channel[x, y] if alpha_channel else 255
                if img_alpha > 0:
                    # Shadow strength: strong right at tear, fades quickly inward
                    strength = min(g / 255.0, 0.75)
                    alpha = int(strength * 220 * (img_alpha / 255.0))
                    shadow_pixels[x, y] = (20, 10, 3, alpha)

    return Image.alpha_composite(img, shadow)


# ── Burned Edge ────────────────────────────────────────────────────────────

def _apply_burned_edge(image_path: Path, burn_depth_pct: float = 0.06) -> Path:
    """Apply charred/burned edges to an image.

    Creates an irregular burned border with gradient from black char
    through dark brown and orange ember to the original image.
    Includes occasional ember holes (small round burns).
    """
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    burn_px = max(int(min(w, h) * burn_depth_pct), 12)

    # Generate a smoother, more continuous burn boundary inside the image
    # bounds, leaving transparent space outside the charred edge.
    burn_poly = _burn_polygon(burn_px, burn_px, w - burn_px * 2, h - burn_px * 2, burn_px)

    # Build the charred edge layer
    char_layer = _build_char_layer(w, h, burn_poly, burn_px)

    # Additional burn-through holes: these remove image pixels and add scorch
    # around the surviving edge, rather than painting dots over the artwork.
    hole_mask, hole_scorch = _burn_holes(w, h, burn_poly, burn_px)

    # Composite: char layer underneath, image on top (clipped to burn polygon)
    # First, clip the image to the burn polygon
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(burn_poly, fill=255)
    mask = ImageChops.subtract(mask, hole_mask)
    scorch_alpha = ImageChops.multiply(hole_scorch.getchannel("A"), mask)
    hole_scorch.putalpha(scorch_alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.4))

    clipped = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    clipped.paste(img, (0, 0))
    clipped.putalpha(Image.composite(
        clipped.getchannel("A"),
        Image.new("L", (w, h), 0),
        mask,
    ))

    # Smoke darkening near the edge (gradient inward)
    clipped = _add_smoke_darken(clipped, burn_poly, burn_px)

    # Composite clipped image over char/scorch layers. Keep alpha so the
    # burned-away border and holes are transparent in Typst.
    result = Image.alpha_composite(char_layer, hole_scorch)
    result = Image.alpha_composite(result, clipped)

    fp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    result.save(fp.name, "PNG")
    return Path(fp.name)


def _burn_polygon(ix: int, iy: int, w: int, h: int, burn_px: int) -> list[tuple[int, int]]:
    """Generate a smoother burn boundary — fire spreads in waves, not jagged tears."""
    step = max(3, min(w, h) // 50)

    top = _burn_walk(
        (ix, iy), (ix + w - 1, iy), burn_px, step,
        displace_dir=(0, 1),
    )
    right = _burn_walk(
        (ix + w - 1, iy), (ix + w - 1, iy + h - 1), burn_px, step,
        displace_dir=(-1, 0),
    )
    bottom = _burn_walk(
        (ix + w - 1, iy + h - 1), (ix, iy + h - 1), burn_px, step,
        displace_dir=(0, -1),
    )
    left = _burn_walk(
        (ix, iy + h - 1), (ix, iy), burn_px, step,
        displace_dir=(1, 0),
    )

    poly = []
    poly.extend(top)
    poly.extend(right[1:])
    poly.extend(bottom[1:])
    poly.extend(left[1:-1])
    return poly


def _burn_walk(start: tuple[int, int], end: tuple[int, int],
               max_displace: int, step: int,
               displace_dir: tuple[int, int]) -> list[tuple[int, int]]:
    """Walk along an edge with smooth, wave-like burn displacement.

    Burns spread continuously — less angular than tears, with occasional
    deeper burn lobes where the fire caught.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = max(abs(dx), abs(dy), 1)
    num_steps = max(dist // step, 5)

    perp_x, perp_y = displace_dir
    points = []

    # Accumulated displacement for smooth waves (weighted random walk)
    displacement = 0.0
    momentum = 0.0

    for i in range(num_steps + 1):
        t = i / num_steps
        x = int(start[0] + dx * t)
        y = int(start[1] + dy * t)

        # Smooth wave: displacement has momentum — doesn't change abruptly
        target = 0.0
        r = random.random()
        if r < 0.2:
            target = random.uniform(0, max_displace * 0.15)
        elif r < 0.55:
            target = random.uniform(max_displace * 0.1, max_displace * 0.5)
        elif r < 0.85:
            target = random.uniform(max_displace * 0.3, max_displace * 0.8)
        else:
            target = random.uniform(max_displace * 0.5, max_displace * 1.2)

        # Momentum blends toward target (creates smooth waves, not spikes)
        momentum = momentum * 0.7 + target * 0.3
        displacement = momentum

        # Corner ease — ease to minimum burn, not zero (fire hits corners hardest)
        corner_ease = 1.0
        min_corner_burn = 0.2
        if i < num_steps * 0.12:
            t_ease = i / (num_steps * 0.12)
            corner_ease = min_corner_burn + (1.0 - min_corner_burn) * t_ease
        elif i > num_steps * 0.88:
            t_ease = (num_steps - i) / (num_steps * 0.12)
            corner_ease = min_corner_burn + (1.0 - min_corner_burn) * t_ease
        displacement *= corner_ease

        disp_x = x + int(perp_x * displacement)
        disp_y = y + int(perp_y * displacement)
        points.append((disp_x, disp_y))

    points.append((end[0], end[1]))
    return points


def _build_char_layer(w: int, h: int, burn_poly: list[tuple[int, int]],
                      burn_px: int) -> Image.Image:
    """Build the charred edge layer — black at edge, gradient through
    brown/orange to transparent."""
    # Start with a black layer
    char = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Burn mask: white where the burn polygon IS (the surviving area)
    burn_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(burn_mask).polygon(burn_poly, fill=255)

    # Invert to get burned area (outside the polygon)
    burned_mask = ImageOps.invert(burn_mask)

    # Blur the burned-away area inward, then mask it to the surviving image.
    # This keeps the scorch on the image itself; the outside stays transparent
    # instead of becoming a faint rectangular haze around the cover.
    outside_gradient = burned_mask.filter(ImageFilter.GaussianBlur(radius=burn_px * 0.6))
    gradient = ImageChops.multiply(outside_gradient, burn_mask)

    # Build the char layer pixel by pixel
    # Three zones: black char (edge) → dark brown → orange ember → transparent
    draw = ImageDraw.Draw(char)
    pixels = char.load()
    grad_pixels = gradient.load()

    for y in range(h):
        for x in range(w):
            g = grad_pixels[x, y]
            if g < 1:
                continue

            # g goes from 255 (deepest burn) to 0 (no burn)
            t = g / 255.0  # 1.0 = edge, 0.0 = no burn

            if t > 0.7:
                # Black char zone
                alpha = int(t * 255)
                pixels[x, y] = (8, 5, 3, alpha)
            elif t > 0.3:
                # Dark brown scorch
                alpha = int(t * 220)
                blend = (t - 0.3) / 0.4
                r = int(8 + blend * 55)
                gv = int(5 + blend * 20)
                b = int(3 + blend * 5)
                pixels[x, y] = (r, gv, b, alpha)
            elif t > 0.05:
                # Orange ember glow
                alpha = int(t * 160)
                blend = (t - 0.15) / 0.35
                r = int(63 + blend * 140)
                gv = int(25 + blend * 40)
                b = int(8)
                pixels[x, y] = (r, gv, b, int(alpha * 0.7))

    return char


def _burn_holes(w: int, h: int, burn_poly: list[tuple[int, int]],
                burn_px: int) -> tuple[Image.Image, Image.Image]:
    """Create burn-through holes and their surrounding scorch.

    Returns:
      - an L mask where white removes image pixels
      - an RGBA scorch layer clipped around the holes
    """
    hole_mask = Image.new("L", (w, h), 0)
    scorch = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hole_draw = ImageDraw.Draw(hole_mask)
    scorch_draw = ImageDraw.Draw(scorch)

    rng = random.Random(17)
    count = max((w + h) // 360, 2)
    cx, cy = w / 2, h / 2

    for _ in range(count):
        idx = rng.randint(0, len(burn_poly) - 1)
        fx, fy = burn_poly[idx]

        rx = rng.randint(max(burn_px // 7, 6), max(burn_px // 4, 10))
        ry = rng.randint(max(burn_px // 9, 5), max(burn_px // 3, 12))
        angle_jitter = rng.randint(-rx // 2, rx // 2)

        inward_x = cx - fx
        inward_y = cy - fy
        d = max((inward_x ** 2 + inward_y ** 2) ** 0.5, 1)
        min_inset = max(rx, ry) + 2
        max_inset = max(burn_px // 2, min_inset + 1)
        inset = rng.randint(min_inset, max_inset)
        ex = int(fx + (inward_x / d) * inset)
        ey = int(fy + (inward_y / d) * inset)

        if not (0 <= ex < w and 0 <= ey < h):
            continue

        glow_rx = rx + rng.randint(max(burn_px // 8, 5), max(burn_px // 5, 10))
        glow_ry = ry + rng.randint(max(burn_px // 8, 5), max(burn_px // 5, 10))

        scorch_draw.ellipse(
            (ex - glow_rx, ey - glow_ry, ex + glow_rx, ey + glow_ry),
            fill=(175, 75, 18, 70),
        )
        scorch_draw.ellipse(
            (ex - rx - 3, ey - ry - 3, ex + rx + 3, ey + ry + 3),
            fill=(18, 8, 3, 140),
        )

        # Slightly lopsided holes look less stamped than perfect circles.
        hole_draw.ellipse(
            (ex - rx, ey - ry, ex + rx + angle_jitter, ey + ry),
            fill=255,
        )

    hole_mask = hole_mask.filter(ImageFilter.GaussianBlur(radius=0.5))
    scorch = scorch.filter(ImageFilter.GaussianBlur(radius=1.5))
    return hole_mask, scorch


def _add_smoke_darken(img: Image.Image, burn_poly: list[tuple[int, int]],
                      burn_px: int) -> Image.Image:
    """Darken the image near the burn edge like smoke/heat damage."""
    w, h = img.size

    # Build mask: transparent where burned away, opaque where image survives
    survival_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(survival_mask).polygon(burn_poly, fill=255)

    # Invert to get a mask of the burned zone, then blur inward
    burned_zone = ImageOps.invert(survival_mask)
    gradient = burned_zone.filter(ImageFilter.GaussianBlur(radius=burn_px * 0.4))

    smoke = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    smoke_pixels = smoke.load()
    grad_pixels = gradient.load()
    alpha_ch = img.getchannel("A").load()

    for y in range(h):
        for x in range(w):
            g = grad_pixels[x, y]
            if g > 5 and alpha_ch[x, y] > 0:
                strength = min(g / 255.0, 0.4)
                alpha = int(strength * 90 * (alpha_ch[x, y] / 255.0))
                smoke_pixels[x, y] = (20, 12, 5, alpha)

    return Image.alpha_composite(img, smoke)

"""Image processing for TV upload: cropping and auto-matte."""
import io
import os
from PIL import Image

TARGET_RATIO = 16 / 9  # Samsung Frame TV aspect ratio
DEFAULT_MATTE_PERCENT = int(os.environ.get("DEFAULT_MATTE_PERCENT", "10"))


def process_for_tv(image_data: bytes, crop_percent: int = 0, matte_percent: int = None) -> bytes:
    """
    Process image for TV display:
    1. Crop: Remove crop_percent from all 4 edges
    2. Matte: Add white padding for 16:9 output

    Args:
        image_data: Raw image bytes (JPEG/PNG)
        crop_percent: Percentage to crop from each edge (0-50)
        matte_percent: Minimum matte as % of longer side (default from env)

    Returns:
        PNG bytes ready for TV upload
    """
    if matte_percent is None:
        matte_percent = DEFAULT_MATTE_PERCENT

    # Load image
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGB if necessary (handle RGBA, palette, etc.)
    if img.mode in ('RGBA', 'P', 'LA'):
        # Create white background for transparency
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Step 1: Crop
    if crop_percent > 0:
        img = _crop_image(img, crop_percent)

    # Step 2: Add matte for 16:9
    img = _add_matte(img, matte_percent)

    # Output as PNG
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()


def _crop_image(img: Image.Image, crop_percent: int) -> Image.Image:
    """Crop percentage from all 4 edges."""
    w, h = img.size
    crop_x = int(w * crop_percent / 100)
    crop_y = int(h * crop_percent / 100)

    left = crop_x
    top = crop_y
    right = w - crop_x
    bottom = h - crop_y

    return img.crop((left, top, right, bottom))


def _add_matte(img: Image.Image, matte_percent: int) -> Image.Image:
    """
    Add white matte padding to achieve 16:9 aspect ratio.

    Rules:
    - Minimum matte = matte_percent of image's longer side (on all sides)
    - Expand as needed to reach 16:9
    - Image centered on white canvas
    """
    w, h = img.size
    longer_side = max(w, h)
    min_matte = int(longer_side * matte_percent / 100)

    # Start with minimum matte on all sides
    canvas_w = w + (min_matte * 2)
    canvas_h = h + (min_matte * 2)

    # Adjust to 16:9
    current_ratio = canvas_w / canvas_h

    if current_ratio < TARGET_RATIO:
        # Too tall - expand width
        canvas_w = int(canvas_h * TARGET_RATIO)
    elif current_ratio > TARGET_RATIO:
        # Too wide - expand height
        canvas_h = int(canvas_w / TARGET_RATIO)

    # Create white canvas and paste image centered
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    paste_x = (canvas_w - w) // 2
    paste_y = (canvas_h - h) // 2
    canvas.paste(img, (paste_x, paste_y))

    return canvas


def generate_preview(image_data: bytes, crop_percent: int = 0, matte_percent: int = None) -> tuple[bytes, bytes]:
    """
    Generate preview images for comparison.

    Returns:
        Tuple of (original_thumbnail, processed_thumbnail) as JPEG bytes
    """
    # Original thumbnail
    original = Image.open(io.BytesIO(image_data))
    if original.mode not in ('RGB', 'L'):
        original = original.convert('RGB')
    original.thumbnail((400, 400), Image.Resampling.LANCZOS)

    orig_output = io.BytesIO()
    original.save(orig_output, format='JPEG', quality=85)

    # Processed thumbnail
    processed_full = process_for_tv(image_data, crop_percent, matte_percent)
    processed = Image.open(io.BytesIO(processed_full))
    processed.thumbnail((400, 400), Image.Resampling.LANCZOS)

    proc_output = io.BytesIO()
    processed.save(proc_output, format='JPEG', quality=85)

    return orig_output.getvalue(), proc_output.getvalue()

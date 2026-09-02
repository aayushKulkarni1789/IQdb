from io import BytesIO

from PIL import Image


def make_thumbnail_jpeg(data: bytes, max_dim: int = 256) -> bytes:
    """Resize longest edge to max_dim and return JPEG bytes.

    Args:
        data: Raw image bytes (any format Pillow can open).
        max_dim: Maximum dimension for longest edge (default 256).
    """
    with Image.open(BytesIO(data)) as img:
        # Convert to RGB if needed (e.g., RGBA, P)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        w, h = img.size
        # If already smaller than max_dim, keep original size but still encode JPEG
        if max(w, h) > max_dim:
            # Pillow thumbnail maintains aspect ratio; use LANCZOS
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        # Save to JPEG bytes
        out = BytesIO()
        img.save(out, format="JPEG")
        return out.getvalue()

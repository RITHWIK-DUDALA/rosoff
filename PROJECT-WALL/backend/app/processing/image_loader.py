"""
Universal Robust Image Loader for PROJECT W.A.L.L.
Handles ANY image format (PNG, JPG, WebP, GIF, BMP, TIFF), ANY color space
(RGBA, LA, P, CMYK, Grayscale, 1-bit), EXIF orientation tags, transparency
compositing over substrate, aspect ratio preservation, and base64 thumbnailing.
"""

import io
import base64
from typing import Tuple, Optional
from PIL import Image, ImageOps


class UniversalImageLoader:
    @staticmethod
    def load_image(file_bytes: bytes, max_dim: int = 2048) -> Tuple[Image.Image, Tuple[int, int], str]:
        """
        Loads arbitrary image bytes and converts safely to a 3-channel RGB PIL Image.
        Returns:
            (processed_rgb_image, original_dimensions_px, base64_thumbnail_data_uri)
        """
        try:
            raw_img = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Unrecognized or corrupted image format: {str(e)}")

        # 1. Apply EXIF orientation (critical for smartphone photos)
        try:
            raw_img = ImageOps.exif_transpose(raw_img)
        except Exception:
            pass

        orig_w, orig_h = raw_img.size

        # 2. Transparent alpha channel compositing
        # If image has an alpha channel, composite onto an opaque white substrate (255, 255, 255)
        # to prevent black bounding box artifacts.
        if raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info):
            rgba = raw_img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            alpha_composited = Image.alpha_composite(bg, rgba)
            rgb_img = alpha_composited.convert("RGB")
        elif raw_img.mode == "CMYK":
            rgb_img = raw_img.convert("RGB")
        elif raw_img.mode in ("L", "1", "P"):
            rgb_img = raw_img.convert("RGB")
        elif raw_img.mode != "RGB":
            rgb_img = raw_img.convert("RGB")
        else:
            rgb_img = raw_img

        # 3. Guard against ultra-huge resolutions (e.g. 50 MP phone cameras)
        # Scale down if either dimension exceeds max_dim while strictly maintaining aspect ratio
        w, h = rgb_img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            rgb_img = rgb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 4. Generate compact Base64 thumbnail data URI for UI display
        thumb = rgb_img.copy()
        thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb.save(thumb_buf, format="JPEG", quality=85)
        thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(thumb_buf.getvalue()).decode("ascii")

        return rgb_img, (orig_w, orig_h), thumb_b64


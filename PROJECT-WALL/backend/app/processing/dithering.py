"""
Raster Processing & Error-Diffusion Dithering for PROJECT W.A.L.L.
Implements:
1. Serpentine Floyd-Steinberg Error Diffusion Dithering (Section 14.4)
2. Threshold-based Binary Conversion
3. Palette-Constrained Vector Color Quantization
"""

import numpy as np
from PIL import Image
from typing import Tuple, List, Optional


class FloydSteinbergDitherer:
    """
    Implements Floyd-Steinberg error diffusion with serpentine scanning
    to prevent directional worming artifacts:
    Diffuses quantization error e to neighboring unprocessed pixels:
    - Right: 7/16
    - Bottom-Left: 3/16
    - Bottom: 5/16
    - Bottom-Right: 1/16
    """
    @staticmethod
    def dither_grayscale(image_arr: np.ndarray, threshold: int = 128) -> np.ndarray:
        """
        Converts grayscale image array (H, W) [0..255] to binary (H, W) {0, 255}
        using serpentine Floyd-Steinberg error diffusion.
        """
        h, w = image_arr.shape[:2]
        # Work in float32 to accumulate and diffuse errors accurately
        buffer = image_arr.astype(np.float32).copy()

        for y in range(h):
            # Serpentine traversal: alternate left-to-right and right-to-left
            if y % 2 == 0:
                x_indices = range(w)
                direction = 1
            else:
                x_indices = range(w - 1, -1, -1)
                direction = -1

            for x in x_indices:
                old_val = buffer[y, x]
                new_val = 255.0 if old_val >= threshold else 0.0
                buffer[y, x] = new_val
                err = old_val - new_val

                # Diffuse error based on current direction
                if direction == 1:
                    if x + 1 < w:
                        buffer[y, x + 1] += err * (7.0 / 16.0)
                    if y + 1 < h:
                        if x - 1 >= 0:
                            buffer[y + 1, x - 1] += err * (3.0 / 16.0)
                        buffer[y + 1, x] += err * (5.0 / 16.0)
                        if x + 1 < w:
                            buffer[y + 1, x + 1] += err * (1.0 / 16.0)
                else:
                    if x - 1 >= 0:
                        buffer[y, x - 1] += err * (7.0 / 16.0)
                    if y + 1 < h:
                        if x + 1 < w:
                            buffer[y + 1, x + 1] += err * (3.0 / 16.0)
                        buffer[y + 1, x] += err * (5.0 / 16.0)
                        if x - 1 >= 0:
                            buffer[y + 1, x - 1] += err * (1.0 / 16.0)

        return np.clip(buffer, 0.0, 255.0).astype(np.uint8)

    @staticmethod
    def dither_rgb_palette(image_arr: np.ndarray, palette_rgb: List[Tuple[int, int, int]]) -> np.ndarray:
        """
        Quantizes RGB image to discrete physical pigment palette using Floyd-Steinberg.
        palette_rgb: list of (R, G, B) tuples.
        """
        h, w = image_arr.shape[:2]
        buffer = image_arr.astype(np.float32).copy()
        palette = np.array(palette_rgb, dtype=np.float32)

        for y in range(h):
            for x in range(w):
                old_pixel = buffer[y, x]
                # Find closest palette color by Euclidean distance in RGB space
                dists = np.sum((palette - old_pixel) ** 2, axis=1)
                best_idx = int(np.argmin(dists))
                new_pixel = palette[best_idx]

                buffer[y, x] = new_pixel
                err = old_pixel - new_pixel

                if x + 1 < w:
                    buffer[y, x + 1] += err * (7.0 / 16.0)
                if y + 1 < h:
                    if x - 1 >= 0:
                        buffer[y + 1, x - 1] += err * (3.0 / 16.0)
                    buffer[y + 1, x] += err * (5.0 / 16.0)
                    if x + 1 < w:
                        buffer[y + 1, x + 1] += err * (1.0 / 16.0)

        return np.clip(buffer, 0.0, 255.0).astype(np.uint8)


"""
Marching Squares 2D Contour Extraction Module for PROJECT W.A.L.L.
Extracts continuous closed and open vector contours from scalar image fields
as specified in Section 14.5.
"""

from typing import List, Tuple, Dict, Any
import numpy as np


class MarchingSquaresExtractor:
    """
    Standard Marching Squares 2D isocontour algorithm:
    Evaluates 2x2 pixel grid cells against threshold isovalue.
    Calculates cell index [0..15] from corner binary states:
    Corner 0: (x, y) [Top-Left]
    Corner 1: (x+1, y) [Top-Right]
    Corner 2: (x+1, y+1) [Bottom-Right]
    Corner 3: (x, y+1) [Bottom-Left]
    """
    @staticmethod
    def extract_contours(
        grid: np.ndarray,
        isovalue: float = 128.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0
    ) -> List[List[Tuple[float, float]]]:
        """
        Extracts contour line segments from 2D scalar array grid (H, W).
        Returns list of polylines in physical surface coordinates: (scale_x * x + offset_x, scale_y * y + offset_y).
        """
        h, w = grid.shape[:2]
        segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

        # Iterate through every 2x2 grid cell
        for y in range(h - 1):
            for x in range(w - 1):
                # 4 corner values
                v0 = grid[y, x]
                v1 = grid[y, x + 1]
                v2 = grid[y + 1, x + 1]
                v3 = grid[y + 1, x]

                # 4-bit state index
                cell_index = 0
                if v0 >= isovalue: cell_index |= 1
                if v1 >= isovalue: cell_index |= 2
                if v2 >= isovalue: cell_index |= 4
                if v3 >= isovalue: cell_index |= 8

                if cell_index in (0, 15):
                    continue  # All inside or all outside, no contour

                # Edge midpoints (linear interpolation along cell edges)
                # Edge a: top (x -> x+1 at y)
                t_a = (isovalue - v0) / (v1 - v0) if abs(v1 - v0) > 1e-6 else 0.5
                edge_a = (x + t_a, y)

                # Edge b: right (x+1 at y -> y+1)
                t_b = (isovalue - v1) / (v2 - v1) if abs(v2 - v1) > 1e-6 else 0.5
                edge_b = (x + 1.0, y + t_b)

                # Edge c: bottom (x -> x+1 at y+1)
                t_c = (isovalue - v3) / (v2 - v3) if abs(v2 - v3) > 1e-6 else 0.5
                edge_c = (x + t_c, y + 1.0)

                # Edge d: left (x at y -> y+1)
                t_d = (isovalue - v0) / (v3 - v0) if abs(v3 - v0) > 1e-6 else 0.5
                edge_d = (x, y + t_d)

                # Lookup table mapping cell_index [1..14] to edge pairs
                if cell_index in (1, 14):
                    segments.append((edge_d, edge_a))
                elif cell_index in (2, 13):
                    segments.append((edge_a, edge_b))
                elif cell_index in (3, 12):
                    segments.append((edge_d, edge_b))
                elif cell_index in (4, 11):
                    segments.append((edge_b, edge_c))
                elif cell_index == 5:
                    segments.append((edge_d, edge_a))
                    segments.append((edge_b, edge_c))
                elif cell_index in (6, 9):
                    segments.append((edge_a, edge_c))
                elif cell_index in (7, 8):
                    segments.append((edge_d, edge_c))
                elif cell_index == 10:
                    segments.append((edge_a, edge_b))
                    segments.append((edge_c, edge_d))

        # Chain disconnected segments into continuous paths
        polylines = MarchingSquaresExtractor._chain_segments(segments)

        # Scale and offset to physical millimeters
        scaled_polylines = []
        for poly in polylines:
            scaled = [(round(offset_x + pt[0] * scale_x, 3), round(offset_y + pt[1] * scale_y, 3)) for pt in poly]
            if len(scaled) >= 2:
                scaled_polylines.append(scaled)

        return scaled_polylines

    @staticmethod
    def _chain_segments(segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> List[List[Tuple[float, float]]]:
        """Chains unordered line segments into continuous polylines"""
        if not segments:
            return []

        remaining = segments.copy()
        chains: List[List[Tuple[float, float]]] = []

        while remaining:
            curr_seg = remaining.pop(0)
            chain = [curr_seg[0], curr_seg[1]]

            extended = True
            while extended:
                extended = False
                tail = chain[-1]
                head = chain[0]

                for i, seg in enumerate(remaining):
                    # Check if segment attaches to tail
                    if np.hypot(seg[0][0] - tail[0], seg[0][1] - tail[1]) < 0.2:
                        chain.append(seg[1])
                        remaining.pop(i)
                        extended = True
                        break
                    elif np.hypot(seg[1][0] - tail[0], seg[1][1] - tail[1]) < 0.2:
                        chain.append(seg[0])
                        remaining.pop(i)
                        extended = True
                        break
                    # Check if segment attaches to head
                    elif np.hypot(seg[1][0] - head[0], seg[1][1] - head[1]) < 0.2:
                        chain.insert(0, seg[0])
                        remaining.pop(i)
                        extended = True
                        break
                    elif np.hypot(seg[0][0] - head[0], seg[0][1] - head[1]) < 0.2:
                        chain.insert(0, seg[1])
                        remaining.pop(i)
                        extended = True
                        break

            chains.append(chain)

        return chains


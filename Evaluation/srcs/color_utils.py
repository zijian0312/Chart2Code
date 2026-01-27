# color_utils.py
import numpy as np
from matplotlib import colors as mcolors
from typing import Any, Optional, List, Dict
import math
import logging

logger = logging.getLogger(__name__)


if not hasattr(np, "asscalar"):
    try:
        np.asscalar = lambda x: x.item()
    except Exception:
        pass

HAS_COLORMATH = False
try:
    from colormath.color_objects import sRGBColor, LabColor
    from colormath.color_conversions import convert_color
    from colormath.color_diff import delta_e_cie2000
    HAS_COLORMATH = True
except ImportError:
    logger.warning("Library 'colormath' not found. Will fallback to RGB Euclidean distance.")
except Exception as e:
    logger.warning(f"Error initializing colormath: {e}. Will fallback to RGB Euclidean distance.")


def convert_color_to_hex(color: Any) -> Optional[str]:
    """
    Robustly converts various color formats to HEX string.
    Ensures format is always #RRGGBB (no alpha) for consistent comparison.
    """
    try:
        if color is None:
            return None
        if isinstance(color, str) and color.lower() == 'none':
            return None
        
        return mcolors.to_hex(color, keep_alpha=False).upper()
    except (ValueError, TypeError):
        return None

def _euclidean_distance_sim(hex1: str, hex2: str) -> float:
    """Fallback: Standard RGB Euclidean Distance."""
    try:
        rgb1 = [int(hex1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
        rgb2 = [int(hex2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]

        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))
        return max(0.0, 1.0 - dist / 441.67)
    except Exception:
        return 0.0

def calculate_color_similarity(color1: str, color2: str) -> float:

    if not (isinstance(color1, str) and isinstance(color2, str)):
        return 0.0

    if color1.upper() == color2.upper():
        return 1.0

    if color1.startswith('#') and color2.startswith('#'):

        if HAS_COLORMATH:
            try:
                rgb1_tup = tuple(int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                rgb2_tup = tuple(int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                
                c1 = sRGBColor(*rgb1_tup, is_upscaled=True)
                c2 = sRGBColor(*rgb2_tup, is_upscaled=True)
                
                lab1 = convert_color(c1, LabColor)
                lab2 = convert_color(c2, LabColor)
                delta = delta_e_cie2000(lab1, lab2)

                return max(0.0, 1.0 - delta / 100.0)
            except Exception as e:
                pass
        return _euclidean_distance_sim(color1, color2)

    return 0.0


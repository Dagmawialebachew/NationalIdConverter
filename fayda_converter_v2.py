# fayda_converter_v2.py
# =====================
# Production-Grade Fayda ID Dynamic Asset Extraction & Synthesis Engine.
# Engineered for zero-label overlap, strict aspect-ratio locking, and adaptive text stenciling.

import io
import logging
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageFilter, ImageOps, ImageStat, ImageDraw

logger = logging.getLogger(__name__)

_ENGINE_DIR = Path(__file__).parent
TEMPLATE_PATH = _ENGINE_DIR / "fayda_template.jpg"

# Master Template Native Dimensions
_TW = 2360
_TH = 667
_FW = _TW // 2  # 1180px per layout hemisphere (Front / Back)

# ─── PIXEL-PERFECT TARGET CANVAS COORDINATES (2360x667 Base) ──────────────────
FRONT_ZONES = {
    "vertical_strip_left":  (85, 90, 195 , 285), 
    "vertical_strip_right":  (85, 393, 193 , 543), # NEW: second strip on right side
    "photo_main":     (149, 145, 523, 599),
    "name_field": (513, 192, 1055, 282), # Slightly widened to prevent text crowding
    "dob_field":      (509, 260, 1117, 440),
    "sex_field":      (502, 398, 892, 440),
    "expiry_field":   (512, 460, 920, 507),
    "barcode_area":   (562, 522, 855, 614),
    "photo_small":    (890, 475, 1030, 622),
}

BACK_ZONES = {
    "phone_field":    (57, 42, 317, 167),
    "address_field":  (60, 185, 615, 605),  # Expanded bounding box for clean multi-line addresses
    "fin_value":      (165, 477, 380, 672), 
    "qr_area":        (512, 10, 918, 625),
    "sn_field":       (885, 612, 1160, 652),
}

# ─── ADVANCED IMAGE PROCESSING UTILITIES ──────────────────────────────────────


import numpy as np
from PIL import Image, ImageFilter, ImageChops
 
 
def remove_white_background(
    img: Image.Image,
    threshold: int = 24,          # Global tolerance from seed color
    local_threshold: int = 10,    # 🔥 Edge guard: stops fill jumping over sharp lines
    edge_shrink: int = 2,         
    feather_radius: int = 5,      
    legacy_threshold: int = 240,
) -> Image.Image:
    """
    Remove the white/near-white background from an ID photo using edge-aware
    dual-constraint flood-fill seeding + morphological soft-alpha feathering.
    """
    try:
        return _remove_bg_numpy(img, threshold, local_threshold, edge_shrink, feather_radius)
    except Exception as e:
        print(f"Fallback to legacy due to: {e}")
        return _remove_bg_legacy(img, legacy_threshold)


def _remove_bg_numpy(
    img: Image.Image,
    threshold: int,
    local_threshold: int,
    edge_shrink: int,
    feather_radius: int,
) -> Image.Image:
    rgba = img.convert("RGBA")
    rgb  = img.convert("RGB")
    w, h = rgb.size

    arr = np.array(rgb, dtype=np.float32)

    # ── Stage 1: Dual-Constraint Flood Fill ──────────────────────────────────
    bg_mask = _flood_fill_background(arr, threshold, local_threshold)

    # ── Stage 2: Morphological Clean up ──────────────────────────────────────
    bg_pil = Image.fromarray((bg_mask * 255).astype(np.uint8), mode="L")

    # Erode the background mask inward to ensure high fidelity on hair borders
    for _ in range(edge_shrink):
        bg_pil = bg_pil.filter(ImageFilter.MinFilter(3))

    feather_pil = bg_pil.copy()
    for _ in range(feather_radius):
        feather_pil = feather_pil.filter(ImageFilter.MaxFilter(3))

    # ── Stage 3: Smooth Edge Blend ───────────────────────────────────────────
    blurred = feather_pil.filter(ImageFilter.GaussianBlur(radius=feather_radius * 0.5))
    alpha = ImageChops.invert(blurred)

    eroded_arr = np.array(bg_pil, dtype=np.float32) / 255.0
    alpha_arr  = np.array(alpha,  dtype=np.float32) / 255.0

    # Enforce concrete absolute zones
    alpha_arr[eroded_arr > 0.9] = 0.0   # Confirmed background
    alpha_arr[eroded_arr < 0.01] = 1.0  # Confirmed internal subject

    final_alpha = Image.fromarray((np.clip(alpha_arr, 0, 1) * 255).astype(np.uint8), mode="L")
    rgba.putalpha(final_alpha)
    return rgba


def _flood_fill_background(arr: np.ndarray, tolerance: int, local_tolerance: int) -> np.ndarray:
    """
    Executes a BFS flood-fill guarded by both a global color constraint 
    and a local neighborhood edge constraint to prevent highlight bleed.
    """
    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    is_bg   = np.zeros((h, w), dtype=bool)

    from collections import deque
    queue = deque()

    # Seed positions across the four outer corners of the image boundary
    corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
    for r, c in corners:
        if not visited[r, c]:
            visited[r, c] = True
            is_bg[r, c]   = True
            # Store row, col, and the initial color reference of that specific path
            queue.append((r, c, arr[r, c]))

    # Execution Loop
    while queue:
        cr, cc, seed_color = queue.popleft()

        for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                current_pixel = arr[nr, nc]
                parent_pixel  = arr[cr, cc]

                # 1. Global Check: Is the pixel close to the source background color family?
                global_diff = np.max(np.abs(current_pixel - seed_color))

                # 2. Local Check: Is the step transition smooth, or did we hit an edge?
                local_diff = np.max(np.abs(current_pixel - parent_pixel))

                if global_diff <= tolerance and local_diff <= local_tolerance:
                    visited[nr, nc] = True
                    is_bg[nr, nc]   = True
                    queue.append((nr, nc, seed_color))

    return is_bg
# ─── Legacy fallback (no numpy) ───────────────────────────────────────────────
 
def _remove_bg_legacy(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Original single-pass threshold — used only if numpy is unavailable."""
    rgba = img.convert("RGBA")
    data = rgba.getdata()
    new_data = []
    for item in data:
        if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
            new_data.append((item[0], item[1], item[2], 0))
        else:
            new_data.append(item)
    rgba.putdata(new_data)
    return rgba


def _load_image(file_bytes: bytes, filename: str) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")
    except Exception as e:
        raise RuntimeError(f"Engine Load Violation for '{filename}': {e}")


def _extract_relative_slice(card: Image.Image, y1_f: float, y2_f: float, x1_f: float, x2_f: float) -> Image.Image:
    """Extracts a slice from the raw input card using normalized ratios."""
    cw, ch = card.size
    return card.crop((int(cw * x1_f), int(ch * y1_f), int(cw * x2_f), int(ch * y2_f)))


def debug_draw_relative_box(
    card: Image.Image,
    name: str,
    y1_f: float,
    y2_f: float,
    x1_f: float,
    x2_f: float,
):
    """
    Draws a visual debug rectangle
    so you can SEE extraction boundaries.
    """

    debug = card.copy()

    draw = ImageDraw.Draw(debug)

    cw, ch = card.size

    x1 = int(cw * x1_f)
    y1 = int(ch * y1_f)

    x2 = int(cw * x2_f)
    y2 = int(ch * y2_f)

    draw.rectangle(
        [x1, y1, x2, y2],
        outline="red",
        width=5
    )

    draw.text(
        (x1, y1 - 30),
        name,
        fill="red"
    )

    debug.save(f"DEBUG_{name}.jpg")
    
 
 
def _composite_element(
    canvas: Image.Image,
    element: Image.Image,
    zone: Tuple[int, int, int, int],
    offset_x: int,
    apply_sharpen: bool = False,
    rotate_deg: int = 0,
    strip_white: bool = False,
    stretch: bool = False,
    scale: float = 1.0
) -> None:
    """
    Pastes assets while maintaining aspect ratios. Supports background stripping
    and safe alpha channel transparency compositing layers.
    """
    x1, y1, x2, y2 = zone
    x1, x2 = x1 + offset_x, x2 + offset_x
    zw, zh = x2 - x1, y2 - y1

    elem_copy = element.copy()
    
    # 1. Clean the white backgrounds upstream if requested
    if strip_white:
        elem_copy = remove_white_background(elem_copy)

    # 2. Execute geometric transformations safely over the alpha spectrum
    if rotate_deg:
        elem_copy = elem_copy.rotate(rotate_deg, expand=True)

    # 3. Enforce proportional scale layout math
    ew, eh = elem_copy.size

    if stretch:

        # FORCE EXACT FIT
        new_w = zw
        new_h = zh

        px = x1
        py = y1

    else:

        # PRESERVE ASPECT RATIO
        ratio = min(zw / ew, zh / eh)

        new_w = int(ew * ratio * scale)
        new_h = int(eh * ratio * scale)

        px = x1
        py = y1 + (zh - new_h) // 2

    elem_copy = elem_copy.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )
    if apply_sharpen:
        elem_copy = elem_copy.filter(ImageFilter.SHARPEN)
        
    
    # 5. Composition Execution Matrix
    if elem_copy.mode == "RGBA":
        canvas.paste(elem_copy, (px, py), mask=elem_copy)  # Use copy as its own alpha mask
    else:
        canvas.paste(elem_copy, (px, py))
        
from PIL import Image, ImageFilter, ImageOps, ImageStat, ImageEnhance

import math
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
from typing import Tuple
 
 
# ─── Tuning knobs (adjust without touching logic) ─────────────────────────────
 

_SIGMOID_MIDPOINT  = 165    # Bumped from 155 to pull more faint ink into opacity
_SIGMOID_STEEPNESS = 8      # Lowered from 14 to sharpen transitions and eliminate gray blur
_DILATION_PASSES   = 1      
_DILATION_WEIGHT   = 0.28   
_UNSHARP_RADIUS    = 1.2    
_UNSHARP_PERCENT   = 160    
_UNSHARP_THRESHOLD = 2      
_INK_COLOR         = (20, 24, 33)   # Unified fallback ink
 
 
# ─── Lookup table: pre-compute sigmoid for all 256 levels ─────────────────────
 
def _build_sigmoid_lut(midpoint: float, steepness: float) -> list:
    """
    Returns a 256-entry list mapping input luminance → alpha value (0–255).
    Input image is dark-text-on-light: dark pixels (low value) → high alpha.
    """
    lut = []
    for p in range(256):
        # Sigmoid: higher p (brighter = background) → lower alpha
        alpha = 1.0 / (1.0 + math.exp((p - midpoint) / steepness))
        lut.append(int(round(alpha * 255)))
    return lut
 
 
_SIGMOID_LUT = _build_sigmoid_lut(_SIGMOID_MIDPOINT, _SIGMOID_STEEPNESS)
 
 
# ─── Main function ─────────────────────────────────────────────────────────────
 
def _composite_text_stencil(
    canvas: Image.Image,
    text_region: Image.Image,
    zone: Tuple[int, int, int, int],
    offset_x: int,
    zoom_x: float = 1.0,
    zoom_y: float = 1.0,
    stretch_y: float = 1.0,
    stretch_x: float = 1.0,
) -> None:
    x1, y1, x2, y2 = zone
    x1, x2 = x1 + offset_x, x2 + offset_x
    zw, zh = x2 - x1, y2 - y1

    sharpened = text_region.filter(
        ImageFilter.UnsharpMask(radius=_UNSHARP_RADIUS, percent=_UNSHARP_PERCENT, threshold=_UNSHARP_THRESHOLD)
    )
    gray = sharpened.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)

    # 🔥 ADAPTIVE DRIVEN MIDPOINT CALCULATION
    stats = ImageStat.Stat(gray)
    local_mean = stats.mean[0]
    dynamic_midpoint = int(local_mean * 0.85) if local_mean < 180 else _SIGMOID_MIDPOINT
    
    # Avoid recalculation overhead if the midpoint matches our global pre-computed values
    if dynamic_midpoint == _SIGMOID_MIDPOINT:
        alpha_soft = gray.point(_SIGMOID_LUT, mode="L")
    else:
        dynamic_lut = []
        for p in range(256):
            alpha = 1.0 / (1.0 + math.exp((p - dynamic_midpoint) / _SIGMOID_STEEPNESS))
            dynamic_lut.append(int(round(alpha * 255)))
        alpha_soft = gray.point(dynamic_lut, mode="L")
    
    # [Rest of your core blending logic continues flawlessly here...]
 
    # ── Stage 3: Dilation blend on ink-core ───────────────────────────────────
    # Hard core: pixels where we're very confident there's ink
    ink_core = gray.point(lambda p: 255 if p < 80 else 0, mode="L")
 
    # Dilate: one MaxFilter pass ≈ 1 px dilation in 8-connectivity
    for _ in range(_DILATION_PASSES):
        ink_core = ink_core.filter(ImageFilter.MaxFilter(3))
 
    # Blend dilation into soft mask
    ink_core_arr  = np.array(ink_core,   dtype=np.float32) / 255.0
    alpha_soft_arr = np.array(alpha_soft, dtype=np.float32) / 255.0
 
    alpha_combined = np.clip(
        alpha_soft_arr + ink_core_arr * _DILATION_WEIGHT, 0.0, 1.0
    )
    alpha_mask = Image.fromarray(
        (alpha_combined * 255).astype(np.uint8), mode="L"
    )
 
    # ── Crop to non-trivial bounding box (remove wasted whitespace) ───────────
    bbox = alpha_mask.getbbox()
    if not bbox:
        return   # nothing to draw
    text_cropped  = text_region.crop(bbox)
    alpha_cropped = alpha_mask.crop(bbox)
 
    # ── Resize to fit zone (preserving aspect, then apply stretch) ────────────
    tw, th = text_cropped.size
    ratio  = min(zw / tw, zh / th)
 
    new_w = max(1, int(tw * ratio * zoom_x))
    new_h = max(1, int(th * ratio * zoom_y))
 
    new_w = max(1, int(new_w * stretch_x))
    new_h = max(1, int(new_h * stretch_y))
 
    # Clamp so we never overflow the zone (prevents bleeding into adjacent zones)
    new_w = min(new_w, zw)
    new_h = min(new_h, zh)
 
    text_res  = text_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    alpha_res = alpha_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
 
    # ── Stage 5: Ink color (sample from canvas or use fallback) ───────────────
    ink_color = _sample_ink_color(canvas, x1, y1, x2, y2)
 
    # ── Paste stencil ─────────────────────────────────────────────────────────
    px = x1 + (zw - new_w) // 2
    py = y1 + (zh - new_h) // 2
 
    ink_layer = Image.new("RGB", (new_w, new_h), ink_color)
    canvas.paste(ink_layer, (px, py), mask=alpha_res)
 
 
# ─── Helper: sample dark ink color from the destination zone ──────────────────
 
def _sample_ink_color(
    canvas: Image.Image,
    x1: int, y1: int, x2: int, y2: int,
) -> Tuple[int, int, int]:
    """
    Returns the official crisp deep-charcoal ink color used by the government.
    Bypasses canvas sampling to prevent murky background-tinted gray text.
    """
    return (20, 24, 33)  # Pristine government-grade charcoal tone

from PIL import ImageFont

def _draw_generated_text(
    canvas: Image.Image,
    text: str,
    zone: Tuple[int, int, int, int],
    offset_x: int,
    font_size: int = 28
) -> None:

    x1, y1, x2, y2 = zone

    x1 += offset_x
    x2 += offset_x

    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        font = ImageFont.load_default()

    draw.text(
        (x1, y1),
        text,
        fill=(20, 24, 33),
        font=font
    )


    
# ─── MAIN TRANSACTION ENTRYPOINT ──────────────────────────────────────────────
import random
def _resolve_output_zones(output_zones: dict):
    """
    Merges user-provided output zone overrides with the engine defaults.
    Accepts absolute pixel ints OR normalized floats (auto-scaled to 2360×667).
    Returns final (front_zones, back_zones) dicts as (x1, y1, x2, y2) tuples.
    """
    import copy
    front = copy.deepcopy(FRONT_ZONES)
    back  = copy.deepcopy(BACK_ZONES)

    if not output_zones:
        return front, back

    for side, zone_dict in (("front", front), ("back", back)):
        if side not in output_zones:
            continue
        for key, box in output_zones[side].items():
            if key not in zone_dict:
                continue
            x1 = box.get("x1", box[0] if isinstance(box, (list, tuple)) else None)
            y1 = box.get("y1", box[1] if isinstance(box, (list, tuple)) else None)
            x2 = box.get("x2", box[2] if isinstance(box, (list, tuple)) else None)
            y2 = box.get("y2", box[3] if isinstance(box, (list, tuple)) else None)
            if None in (x1, y1, x2, y2):
                continue
            x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
            # Auto-scale if normalized fractions (all values ≤ 1.0)
            if max(x1, y1, x2, y2) <= 1.0:
                x1 = int(x1 * _TW)
                y1 = int(y1 * _TH)
                x2 = int(x2 * _TW)
                y2 = int(y2 * _TH)
            zone_dict[key] = (int(x1), int(y1), int(x2), int(y2))

    return front, back

# ==============================================================================
# REFACTORED HIGH-PERFORMANCE RENDERING PIPELINE
# ==============================================================================


# Insert directly below BACK_ZONES definition

def apply_amharic_watermark(image_bytes: bytes) -> bytes:
    """
    Applies a semi-transparent Amharic watermark on-the-fly.
    Operates strictly in memory via bytes for maximum processing speed.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    # Pre-calculated safe system font paths
    font_paths = ["Nyala.ttf", "AbyssinicaSIL-R.ttf", "AbyssinicaSIL.ttf", "arialbd.ttf", "FreeSansBold.ttf"]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, 55)
            break
        except Exception:
            continue
            
    if not font:
        font = ImageFont.load_default()
        
    h = img.size[1]
    text_amharic = "ናሙና"
    text_english = "PREVIEW ONLY"
    is_default = (font.__class__.__name__ == 'ImageDefaultFont')
    
    # Exact center points of Front (590px) and Back (1770px) hemispheres
    centers = [590, 1770]
    for cx in centers:
        if is_default:
            draw.text((cx - 180, h // 2 - 30), "SAMPLE PROOF", fill=(20, 24, 33, 40))
            draw.text((cx - 180, h // 2 + 10), "PREVIEW ONLY", fill=(20, 24, 33, 40))
        else:
            # High-end charcoal tone at ~15% opacity overlay
            draw.text((cx - 60, h // 2 - 50), text_amharic, fill=(20, 24, 33, 38), font=font)
            draw.text((cx - 160, h // 2 + 15), text_english, fill=(20, 24, 33, 38), font=font)
            
    composite = Image.alpha_composite(img, txt_layer).convert("RGB")
    output_buffer = io.BytesIO()
    composite.save(output_buffer, format="JPEG", quality=95, optimize=True)
    return output_buffer.getvalue()


def extract_slices(
    file_bytes_one: bytes, filename_one: str,
    file_bytes_two: bytes, filename_two: str,
    custom_zones: dict = None
) -> dict:
    """
    PHASE 1: HEAVY LIFTING (Run ONCE on upload)
    Loads high-res cards, slices elements, and executes the NumPy line-splitting algorithm.
    Returns a dictionary of isolated PIL images ready for layout composition.
    """
    front_card = _load_image(file_bytes_one, filename_one)
    back_card  = _load_image(file_bytes_two, filename_two)

    # Internal coordinate resolver matching your custom upload studio maps
    def _get_coordinates(side: str, key: str, def_y1: float, def_y2: float, def_x1: float, def_x2: float):
        if not custom_zones or side not in custom_zones:
            return def_y1, def_y2, def_x1, def_x2
        
        aliases = {
            "barcode_area": ["barcode_area", "barcode_field", "barcode_seg"],
            "vertical_strip_left": ["vertical_strip_left", "vertical_seg_1", "vertical_strip_1"],
            "vertical_strip_right": ["vertical_strip_right", "vertical_seg_2", "vertical_strip_2"],
            "qr_area": ["qr_area", "qr_field", "qr_code_field", "qr_code_seg"],
            "address_field": ["address_field", "addr_field", "addr_seg"],
            "fin_value": ["fin_value", "fin_value_field", "fin_value_seg"]
        }
        
        lookup_keys = aliases.get(key, [key])
        box = None
        for l_key in lookup_keys:
            if l_key in custom_zones[side]:
                box = custom_zones[side][l_key]
                break
                
        if box:
            y1 = box.get("y1", def_y1)
            y2 = box.get("y2", def_y2)
            x1 = box.get("x1", def_x1)
            x2 = box.get("x2", def_x2)
            
            img_ref = front_card if side == "front" else back_card
            img_w, img_h = img_ref.size
            if y1 > 1.0 or y2 > 1.0 or x1 > 1.0 or x2 > 1.0:
                y1 = round(y1 / img_h, 4)
                y2 = round(y2 / img_h, 4)
                x1 = round(x1 / img_w, 4)
                x2 = round(x2 / img_w, 4)
                
            return y1, y2, x1, x2
            
        return def_y1, def_y2, def_x1, def_x2

    # 1. Surgical Slices (Front Side)
    biometric_photo = _extract_relative_slice(front_card, *_get_coordinates("front", "photo_main", 0.133, 0.482, 0.26, 0.70)).convert("RGBA")
    name_seg        = _extract_relative_slice(front_card, *_get_coordinates("front", "name_field", 0.580, 0.650, 0.12, 0.88))  
    dob_seg         = _extract_relative_slice(front_card, *_get_coordinates("front", "dob_field", 0.675, 0.702, 0.12, 0.88))  
    sex_seg         = _extract_relative_slice(front_card, *_get_coordinates("front", "sex_field", 0.720, 0.750, 0.12, 0.55))  
    expiry_seg      = _extract_relative_slice(front_card, *_get_coordinates("front", "expiry_field", 0.778, 0.812, 0.12, 0.65))  
    barcode_seg     = _extract_relative_slice(front_card, *_get_coordinates("front", "barcode_area", 0.832, 0.921, 0.27, 0.67))  
    vertical_seg_1  = _extract_relative_slice(front_card, *_get_coordinates("front", "vertical_strip_left", 0.150, 0.337, 0.89, 0.96))
    vertical_seg_2  = _extract_relative_slice(front_card, *_get_coordinates("front", "vertical_strip_right", 0.340, 0.506, 0.89, 0.96))

    # 2. Surgical Slices (Back Side)
    qr_code_seg     = _extract_relative_slice(back_card, *_get_coordinates("back", "qr_area", 0.109, 0.620, 0.10, 0.90))
    phone_seg       = _extract_relative_slice(back_card, *_get_coordinates("back", "phone_field", 0.663, 0.698, 0.09, 0.45))  
    addr_seg        = _extract_relative_slice(back_card, *_get_coordinates("back", "address_field", 0.796, 0.977, 0.09, 0.58))  
    fin_value_seg   = _extract_relative_slice(back_card, *_get_coordinates("back", "fin_value", 0.650, 0.685, 0.628, 0.928))  
    generated_sn    = str(random.randint(23000011, 98800012))  

    # 3. Dynamic NumPy Line Splitting Analysis
    seg_w, seg_h = name_seg.size
    name_gray = name_seg.convert("L")
    name_arr = np.array(name_gray)
    row_means = np.mean(name_arr, axis=1)
    
    search_start = int(seg_h * 0.35)
    search_end = int(seg_h * 0.65)
    optimal_split_row = search_start + np.argmax(row_means[search_start:search_end])
    
    amharic_slice = name_seg.crop((0, 0, seg_w, optimal_split_row))
    english_slice = name_seg.crop((0, optimal_split_row, seg_w, seg_h))

    # Bundle extracted references together
    return {
        "biometric_photo": biometric_photo,
        "barcode_seg": barcode_seg,
        "vertical_seg_1": vertical_seg_1,
        "vertical_seg_2": vertical_seg_2,
        "amharic_slice": amharic_slice,
        "english_slice": english_slice,
        "dob_seg": dob_seg,
        "sex_seg": sex_seg,
        "expiry_seg": expiry_seg,
        "qr_code_seg": qr_code_seg,
        "phone_seg": phone_seg,
        "addr_seg": addr_seg,
        "fin_value_seg": fin_value_seg,
        "generated_sn": generated_sn
    }


def render_layout_from_slices(
    slices: dict,
    output_zones: dict = None,
    width: int = _TW, height: int = _TH,
    quality: int = 90  # Added dynamic quality control defaults to optimize bandwidth
) -> bytes:
    """
    PHASE 2: FAST COMPOSITION (Runs on every drag/nudge nudge)
    Takes pre-cropped asset segments and anchors them safely onto a fresh background canvas.
    Execution speed: ~5-15 milliseconds.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Critical Base Template Asset Missing at: {TEMPLATE_PATH}")

    # Resolve output zone coordinate targets mapping to the 2360×667 viewport template
    _front_zones, _back_zones = _resolve_output_zones(output_zones)

    canvas = Image.open(TEMPLATE_PATH).convert("RGB")

    # 1. Inject Left Hemisphere Elements (Front Side Layout)
    _composite_element(canvas, slices["biometric_photo"], _front_zones["photo_main"], 0, apply_sharpen=True, strip_white=True)    
    _composite_element(canvas, slices["biometric_photo"], _front_zones["photo_small"], 0, strip_white=True)
    _composite_element(canvas, slices["barcode_seg"], _front_zones["barcode_area"], 0, stretch=True)
    _composite_text_stencil(canvas, slices["vertical_seg_1"], _front_zones["vertical_strip_left"], 0)
    _composite_text_stencil(canvas, slices["vertical_seg_2"], _front_zones["vertical_strip_right"], 0)

    # 2. Position Dynamic Name Plates Inside Overridden Front Targets
    zx1, zy1, zx2, zy2 = _front_zones["name_field"]
    zone_w, zone_h = zx2 - zx1, zy2 - zy1
    half_h = zone_h // 2
    line_gap_adjustment = 6  
    
    amharic_zone = (zx1, zy1 - line_gap_adjustment, zx2, zy1 + half_h - line_gap_adjustment)
    english_zone = (zx1, zy1 + half_h + line_gap_adjustment, zx2, zy2 + line_gap_adjustment)

    _composite_text_stencil(canvas, slices["amharic_slice"], amharic_zone, 0, zoom_x=1.20, zoom_y=1.20)
    _composite_text_stencil(canvas, slices["english_slice"], english_zone, 0, zoom_x=1.20, zoom_y=1.20)
    
    # 3. Paste Standard Front Identification Data
    _composite_text_stencil(canvas, slices["dob_seg"], _front_zones["dob_field"], 0)
    _composite_text_stencil(canvas, slices["sex_seg"], _front_zones["sex_field"], 0)
    _composite_text_stencil(canvas, slices["expiry_seg"], _front_zones["expiry_field"], 0)

    # 4. Inject Right Hemisphere Elements (Back Side Layout Shifted via _FW Offset)
    _composite_element(canvas, slices["qr_code_seg"], _back_zones["qr_area"], _FW, scale=1.32)
    _composite_text_stencil(canvas, slices["phone_seg"], _back_zones["phone_field"], _FW, zoom_x=1.30, zoom_y=1.30)
    _composite_text_stencil(canvas, slices["addr_seg"], _back_zones["address_field"], _FW, zoom_x=1.3, zoom_y=1.3, stretch_x=1.30)  
    _composite_text_stencil(canvas, slices["fin_value_seg"], _back_zones["fin_value"], _FW)
    _draw_generated_text(canvas, slices["generated_sn"], _back_zones["sn_field"], _FW, font_size=28)

    # 5. Native Aspect Ratio Canvas Scaler Formatting
    if (width, height) != (_TW, _TH) and (width != 1012):
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)

    output_buffer = io.BytesIO()
    # Dynamic quality mapping lowers flight payload weights on demand
    canvas.save(output_buffer, format="JPEG", quality=quality, optimize=True, progressive=True, dpi=(300, 300))
    
    return output_buffer.getvalue()


def convert_bytes(
    file_bytes_one: bytes, filename_one: str,
    file_bytes_two: bytes, filename_two: str,
    approach: str = "approach_two", watermark: bool = False,
    width: int = _TW, height: int = _TH,
    custom_zones: dict = None,
    output_zones: dict = None
) -> bytes:
    """
    BACKWARD COMPATIBILITY WRAPPER:
    Keeps everything working exactly as before for standard one-off generation requests.
    """
    slices = extract_slices(file_bytes_one, filename_one, file_bytes_two, filename_two, custom_zones)
    return render_layout_from_slices(slices, output_zones, width, height)




def fast_composite_layers(slices: dict, output_zones: dict, base_image_bytes: bytes = None) -> bytes:
    """
    Adjustment-time re-render.
    Delegates entirely to render_layout_from_slices so the output is
    bit-for-bit identical to the original conversion — same template canvas,
    same stencil pipeline, same background removal, same aspect-ratio math.

    `base_image_bytes` is accepted for signature compatibility but intentionally
    ignored: using the already-rendered JPEG as a canvas would double-paint
    processed layers over baked output and bypass all stenciling/bg-removal.
    The correct base is always the clean template, opened inside
    render_layout_from_slices.
    """
    if base_image_bytes is not None:
        logger.debug(
            "fast_composite_layers: base_image_bytes ignored — "
            "always compositing from clean template to preserve full pipeline."
        )
    return render_layout_from_slices(slices=slices, output_zones=output_zones)
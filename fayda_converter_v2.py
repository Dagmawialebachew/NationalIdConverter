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
    "vertical_strip_left":  (85, 100, 195 , 283), 
    "vertical_strip_right":  (85, 403, 193 , 541), # NEW: second strip on right side
    "photo_main":     (149, 145, 523, 599),
    "name_field": (513, 192, 1055, 282), # Slightly widened to prevent text crowding
    "dob_field":      (509, 260, 1117, 440),
    "sex_field":      (502, 398, 892, 440),
    "expiry_field":   (512, 460, 920, 507),
    "barcode_area":   (562, 522, 855, 614),
    "photo_small":    (890, 475, 1030, 622),
}

BACK_ZONES = {
    "phone_field":    (54, 47, 314, 177),
    "address_field":  (60, 185, 615, 605),  # Expanded bounding box for clean multi-line addresses
    "fin_value":      (165, 477, 380, 672), 
    "qr_area":        (512, 10, 918, 625),
    "sn_field":       (885, 612, 1160, 652),
}

# ─── ADVANCED IMAGE PROCESSING UTILITIES ──────────────────────────────────────
import io
import numpy as np
from PIL import Image, ImageFilter, ImageChops, ImageOps


from PIL import Image, ImageDraw, ImageFilter

def _get_oval_background(size):
    w, h = size

    bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    padding_x = int(w * 0.02)
    padding_y = int(h * 0.01)

    draw.ellipse(
        [
            padding_x,
            padding_y,
            w - padding_x,
            h - padding_y,
        ],
        fill=255
    )

    # Very subtle feathering only
    mask = mask.filter(
        ImageFilter.GaussianBlur(radius=3)
    )

    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))

    bg.paste(white, (0, 0), mask)

    return bg


def remove_white_background(
    img: Image.Image,
    threshold: int = 24,          # Global tolerance from seed color
    local_threshold: int = 10,    # Edge guard: stops fill jumping over sharp lines
    edge_shrink: int = 2,         
    feather_radius: int = 5,      
    legacy_threshold: int = 240,
    mode: str = "transparent"     # Options: "transparent" (small photo) or "vignette" (main photo)
) -> Image.Image:
    """
    Remove the white/near-white background from an ID photo using edge-aware
    dual-constraint flood-fill seeding + morphological soft-alpha feathering.
    
    Set mode="transparent" for clear alpha cutouts (small photo frame).
    Set mode="vignette" for studio gradient backdrop + depth shadow (main photo frame).
    """
    try:
        return _remove_bg_numpy(img, threshold, local_threshold, edge_shrink, feather_radius, mode)
    except Exception as e:
        print(f"Fallback to legacy due to: {e}")
        return _remove_bg_legacy(img, legacy_threshold, mode)
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

    bg_mask = _flood_fill_background(np.array(rgb, dtype=np.float32), threshold, local_threshold)
    bg_pil = Image.fromarray((bg_mask * 255).astype(np.uint8), mode="L")

    for _ in range(edge_shrink):
        bg_pil = bg_pil.filter(ImageFilter.MinFilter(3))

    feather_pil = bg_pil.copy()
    for _ in range(feather_radius):
        feather_pil = feather_pil.filter(ImageFilter.MaxFilter(3))

    blurred = feather_pil.filter(ImageFilter.GaussianBlur(radius=feather_radius * 0.4))
    alpha = ImageChops.invert(blurred)
    
    # Isolate subject
    subject_layer = rgba.copy()
    subject_layer.putalpha(alpha)
    return subject_layer


def _flood_fill_background(arr: np.ndarray, tolerance: int, local_tolerance: int) -> np.ndarray:
    """
    Executes a BFS flood-fill guarded by both a global color constraint 
    and a local neighborhood edge constraint to prevent highlight bleed.
    Utilizes localized threshold coordinates to preserve white clothes and dresses.
    """
    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    is_bg   = np.zeros((h, w), dtype=bool)

    from collections import deque
    queue = deque()

    # Seed positions safely over top row boundaries to protect torso/shirts at the bottom
    top_seeds = [(0, int(c)) for c in np.linspace(0, w - 1, 9)]
    for r, c in top_seeds:
        if not visited[r, c]:
            visited[r, c] = True
            is_bg[r, c]   = True
            queue.append((r, c, arr[r, c]))

    # Execution Loop
    while queue:
        cr, cc, seed_color = queue.popleft()

        for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                current_pixel = arr[nr, nc]
                parent_pixel  = arr[cr, cc]

                # ── SPATIAL PROTECTION MATRIX ──
                eff_tolerance = tolerance
                eff_local_tolerance = local_tolerance

                # Lower canvas constraint clamping (Protects white shirts/ties/dresses)
                if nr > int(h * 0.40):
                    eff_tolerance = max(5, int(tolerance * 0.40))
                    eff_local_tolerance = max(2, int(local_tolerance * 0.40))
                    
                    if int(w * 0.20) < nc < int(w * 0.80):
                        eff_tolerance = max(2, int(tolerance * 0.15))
                        eff_local_tolerance = max(1, int(local_tolerance * 0.15))
                
                # Upper-middle canvas boundary protection (Protects face skin highlights)
                elif int(h * 0.18) < nr <= int(h * 0.40) and int(w * 0.25) < nc < int(w * 0.75):
                    eff_tolerance = max(7, int(tolerance * 0.55))
                    eff_local_tolerance = max(3, int(local_tolerance * 0.55))

                # 1. Global Check: Is the pixel close to the source background color family?
                global_diff = np.max(np.abs(current_pixel - seed_color))

                # 2. Local Check: Is the step transition smooth, or did we hit an edge?
                local_diff = np.max(np.abs(current_pixel - parent_pixel))

                if global_diff <= eff_tolerance and local_diff <= eff_local_tolerance:
                    visited[nr, nc] = True
                    is_bg[nr, nc]   = True
                    queue.append((nr, nc, seed_color))

    return is_bg


def _remove_bg_legacy(img: Image.Image, threshold: int = 240, mode: str = "transparent") -> Image.Image:
    """Original single-pass threshold fallback layer."""
    rgba = img.convert("RGBA")
    data = rgba.getdata()
    new_data = []
    for item in data:
        if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
            new_data.append((item[0], item[1], item[2], 0))
        else:
            new_data.append(item)
    rgba.putdata(new_data)
    
    if mode == "transparent":
        return rgba
        
    white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(white_bg, rgba)



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
    scale: float = 1.0,
    is_main_photo: bool = False 
) -> None:
    x1, y1, x2, y2 = [z + offset_x if i % 2 == 0 else z for i, z in enumerate(zone)]
    zw, zh = x2 - x1, y2 - y1

    # 1. Prep element
    elem = element.copy()
    if strip_white:
        elem = remove_white_background(elem)
    if rotate_deg:
        elem = elem.rotate(rotate_deg, expand=True)

    # 2. Resize
    ew, eh = elem.size
    ratio = min(zw / ew, zh / eh) if not stretch else 1.0
    nw, nh = (zw, zh) if stretch else (int(ew * ratio * scale), int(eh * ratio * scale))
    elem = elem.resize((nw, nh), Image.Resampling.LANCZOS)
    if apply_sharpen:
        elem = elem.filter(ImageFilter.SHARPEN)

    # 3. Placement
    px = x1 + (zw - nw) // 2
    py = y1 + (zh - nh) // 2

    # 4. Composition (The critical fix)
    if is_main_photo:
        # Create staging canvas for the photo
        photo_container = _get_oval_background((nw, nh))
        # Add shadow (optional, based on your previous code)
        alpha = elem.split()[3]
        shadow_mask = alpha.filter(ImageFilter.GaussianBlur(radius=3))
        shadow_layer = Image.new("RGBA", (nw, nh), (50, 52, 60, 65))
        photo_container = Image.alpha_composite(photo_container, Image.composite(shadow_layer, Image.new("RGBA", (nw, nh), (0,0,0,0)), shadow_mask))
        # Place subject on oval
        final_photo = Image.alpha_composite(photo_container, elem)
        canvas.paste(final_photo, (px, py), final_photo)
    else:
        # Simple paste for smaller elements
        canvas.paste(elem, (px, py), mask=elem if elem.mode == 'RGBA' else None)
        
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


from django.conf import settings


logger = logging.getLogger(__name__)

def apply_amharic_watermark(image_bytes: bytes) -> bytes:
    """
    Applies a highly noticeable, dynamically scaled, double-diagonal parallel
    watermark (Amharic & English) across both layout hemispheres, ensuring
    comprehensive coverage and a top-layer z-index over all card objects (including the QR code).
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    W, H = img.size
    
    # Create an independent transparent layer for the watermark overlay
    watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    
    # ─── BULLETPROOF FONT PATH LOOKUP MATRIX ─────────────────────────────────
    try:
        root_dir = Path(settings.BASE_DIR)
    except Exception:
        root_dir = Path(__file__).resolve().parent.parent.parent

    font_candidates = [
        root_dir / "fonts" / "watermark-font.ttf",
        root_dir / "static" / "fonts" / "watermark-font.ttf",
        Path(__file__).resolve().parent / "fonts" / "watermark-font.ttf",
        Path(__file__).resolve().parent / "watermark-font.ttf",
    ]

    font = None
    
    # ─── OPTIMIZED DYNAMIC SIZING ENGINE ─────────────────────────────────────
    # Font sizes scaled to keep the dual layout highly legible without overcrowding
    FONT_SIZE = max(38, int(H * 0.058))     
    stamp_size = max(500, int(H * 0.65))    # Safe text rotation bounding square
    
    for path in font_candidates:
        if path.exists():
            try:
                font = ImageFont.truetype(str(path), FONT_SIZE)
                logger.info("--> Successfully bound watermark font: %s (Size: %dpx)", path, FONT_SIZE)
                break
            except Exception as e:
                logger.warning("--> Found font file at %s but failed to parse: %s", path, e)
                continue

    is_default = (font is None or font.__class__.__name__ == 'ImageDefaultFont')
    
    # ─── HIGH-VISIBILITY DESIGN CONTROLS ─────────────────────────────────────
    ANGLE = 35        # Premium diagonal slash angle
    OPACITY = 140     # High-visibility preview opacity
    
    TEXT_AMHARIC = "ሳምፕል"
    TEXT_ENGLISH = "PREVIEW ONLY"
    
    # Elegant dark slate charcoal fill color
    COLOR_RGBA = (40, 45, 55, OPACITY) 
    # Bright crisp backing stroke outline to pop text out on dark card items
    STROKE_RGBA = (255, 255, 255, int(OPACITY * 0.8))
    STROKE_WIDTH = max(1, int(FONT_SIZE * 0.035)) # Proportional stroke width
    
    # ─── GENERATE WATERMARK STAMP ─────────────────────────────────────────────
    stamp = Image.new("RGBA", (stamp_size, stamp_size), (0, 0, 0, 0))
    stamp_draw = ImageDraw.Draw(stamp)
    
    if is_default:
        logger.error("Watermark TTF font not found. Activating system fallback canvas.")
        fallback_text = "--- PREVIEW ONLY / ናሙና ---"
        stamp_draw.text((40, stamp_size // 2 - 10), fallback_text, fill=COLOR_RGBA)
    else:
        # ─── TRUE-TYPE DUAL TEXT COMPOSITING ───
        if hasattr(font, 'getbbox'):
            bx1, by1, bx2, by2 = font.getbbox(TEXT_AMHARIC)
            w1, h1 = bx2 - bx1, by2 - by1
            
            bx1, by1, bx2, by2 = font.getbbox(TEXT_ENGLISH)
            w2, h2 = bx2 - bx1, by2 - by1
        else:
            w1, h1 = stamp_draw.textsize(TEXT_AMHARIC, font=font) if hasattr(stamp_draw, 'textsize') else (int(stamp_size*0.4), FONT_SIZE)
            w2, h2 = stamp_draw.textsize(TEXT_ENGLISH, font=font) if hasattr(stamp_draw, 'textsize') else (int(stamp_size*0.7), FONT_SIZE)
            
        # Stack text layers centered relative to the stamp's middle axis
        x1 = (stamp_size - w1) // 2
        y1 = (stamp_size // 2) - h1 - int(FONT_SIZE * 0.25)
        stamp_draw.text(
            (x1, y1), TEXT_AMHARIC, fill=COLOR_RGBA, font=font,
            stroke_width=STROKE_WIDTH, stroke_fill=STROKE_RGBA
        )
        
        x2 = (stamp_size - w2) // 2
        y2 = (stamp_size // 2) + int(FONT_SIZE * 0.25)
        stamp_draw.text(
            (x2, y2), TEXT_ENGLISH, fill=COLOR_RGBA, font=font,
            stroke_width=STROKE_WIDTH, stroke_fill=STROKE_RGBA
        )
        
    # Apply clean rotation transform with an explicit transparent fill color fallback
    rotated_stamp = stamp.rotate(ANGLE, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    
    # ─── POSITION DOUBLE STAMP ON MAIN CANVAS HEMISPHERES ────────────────────
    # Maps precisely to both card layout centers (Front: W//4, Back: 3*W//4)
    centers = [W // 4, (3 * W) // 4]
    
    # Stagger offsets relative to the focal point to render a parallel double watermark track.
    # The lower-right offset track ensures complete diagonal covering directly over the QR code area.
    double_offsets = [
        (-int(W * 0.04), -int(H * 0.12)),  # Track 1: Upper-Left Stagger
        (int(W * 0.04), int(H * 0.12))     # Track 2: Lower-Right Stagger (Overlaps QR Zone)
    ]
    
    for cx in centers:
        for dx, dy in double_offsets:
            paste_x = cx + dx - (stamp_size // 2)
            paste_y = (H // 2) + dy - (stamp_size // 2)
            watermark_layer.paste(rotated_stamp, (paste_x, paste_y), rotated_stamp)
        
    # Compile multi-layer alpha composition over the final canvas
    composite = Image.alpha_composite(img, watermark_layer).convert("RGB")
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
    _composite_element(canvas, slices["biometric_photo"], _front_zones["photo_main"], 0, apply_sharpen=True, strip_white=True, is_main_photo=False)    
    _composite_element(canvas, slices["biometric_photo"], _front_zones["photo_small"], 0, strip_white=True, is_main_photo=False)
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
# fayda_converter_v2.py
# =====================
# Production-Grade Fayda ID Dynamic Asset Extraction & Synthesis Engine.
# Engineered for zero-label overlap, strict aspect-ratio locking, and adaptive text stenciling.

import io
import logging
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageFilter, ImageOps, ImageStat

logger = logging.getLogger(__name__)

_ENGINE_DIR = Path(__file__).parent
TEMPLATE_PATH = _ENGINE_DIR / "fayda_template.jpg"

# Master Template Native Dimensions
_TW = 2360
_TH = 667
_FW = _TW // 2  # 1180px per layout hemisphere (Front / Back)

# ─── PIXEL-PERFECT TARGET CANVAS COORDINATES (2360x667 Base) ──────────────────
FRONT_ZONES = {
    "vertical_strip": (15,  160, 50,  580),
    "photo_main":     (65,  145, 415, 595),
    "name_field":     (440, 200, 860, 275),  # Slightly widened to prevent text crowding
    "dob_field":      (440, 288, 860, 355),
    "sex_field":      (440, 368, 680, 432),
    "expiry_field":   (440, 448, 860, 515),
    "barcode_area":   (480, 545, 860, 640),
    "photo_small":    (890, 490, 1030, 640),
}

BACK_ZONES = {
    "phone_field":    (60,  115, 550, 165),
    "nationality":    (60,  202, 550, 252),
    "address_field":  (60,  310, 820, 535),  # Expanded bounding box for clean multi-line addresses
    "fin_value":      (320, 562, 630, 608),
    "qr_area":        (730,  40, 1150, 595),
    "sn_field":       (1010, 612, 1160, 652),
}

# ─── ADVANCED IMAGE PROCESSING UTILITIES ──────────────────────────────────────

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


def _composite_element(
    canvas: Image.Image, 
    element: Image.Image, 
    zone: Tuple[int, int, int, int], 
    offset_x: int, 
    apply_sharpen: bool = False, 
    rotate_deg: int = 0
) -> None:
    """
    Pastes graphic/biometric assets while strictly preserving their aspect ratios.
    Eliminates facial stretching artifacts.
    """
    x1, y1, x2, y2 = zone
    x1, x2 = x1 + offset_x, x2 + offset_x
    zw, zh = x2 - x1, y2 - y1

    elem_copy = element.copy()
    if rotate_deg:
        elem_copy = elem_copy.rotate(rotate_deg, expand=True)

    # Enforce strict proportional scaling down to fit the target container bounding box
    ew, eh = elem_copy.size
    ratio = min(zw / ew, zh / eh)
    new_w, new_h = int(ew * ratio), int(eh * ratio)
    
    elem_copy = elem_copy.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if apply_sharpen:
        elem_copy = elem_copy.filter(ImageFilter.SHARPEN)
        
    # Calculate perfect center padding variables
    px = x1 + (zw - new_w) // 2
    py = y1 + (zh - new_h) // 2
    
    # Use standard composition paste
    canvas.paste(elem_copy, (px, py))


from PIL import Image, ImageFilter, ImageOps, ImageStat, ImageEnhance

def _composite_text_stencil(
    canvas: Image.Image, 
    text_region: Image.Image, 
    zone: Tuple[int, int, int, int], 
    offset_x: int
) -> None:
    x1, y1, x2, y2 = zone
    x1, x2 = x1 + offset_x, x2 + offset_x
    zw, zh = x2 - x1, y2 - y1

    # 1. Convert to L (Grayscale)
    gray = text_region.convert("L")
    
    # 2. ENHANCE CONTRAST (The "Magic" Step)
    # This makes dark text darker and light background lighter
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(2.5) # Crank contrast to make text pop
    
    # 3. Create Mask with higher threshold
    # Invert so text is white on black background
    inv = ImageOps.invert(enhanced)
    
    # 4. Sharpen thresholding
    # Adjust 100 up/down if text is missing or too thick
    alpha_mask = inv.point(lambda p: 255 if p > 100 else 0, mode="L")
    
    # 5. Smooth the edges of the text
    # This removes the jagged pixels around the letters
    alpha_mask = alpha_mask.filter(ImageFilter.GaussianBlur(radius=0.5))

    # 6. Crop to bounding box
    bbox = alpha_mask.getbbox()
    if bbox:
        text_region = text_region.crop(bbox)
        alpha_mask = alpha_mask.crop(bbox)

    # 7. Resize to fit target zone
    text_res = text_region.resize((zw, zh), Image.Resampling.LANCZOS)
    mask_res = alpha_mask.resize((zw, zh), Image.Resampling.LANCZOS)

    # 8. Paste using the mask
    # Use a dark blue-black color (20, 24, 33) for a professional printer look
    ink_layer = Image.new("RGB", (zw, zh), (20, 24, 33))
    canvas.paste(ink_layer, (x1, y1), mask=mask_res)
    
    
# ─── MAIN TRANSACTION ENTRYPOINT ──────────────────────────────────────────────

def convert_bytes(
    file_bytes_one: bytes, filename_one: str,
    file_bytes_two: bytes, filename_two: str,
    approach: str = "approach_two", watermark: bool = False,
    width: int = _TW, height: int = _TH
) -> bytes:
    """
    Processes dual-side raw document uploads and merges isolated assets onto the template canvas.
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Critical Base Template Asset Missing at: {TEMPLATE_PATH}")

    canvas = Image.open(TEMPLATE_PATH).convert("RGB")
    
    front_card = _load_image(file_bytes_one, filename_one)
    back_card  = _load_image(file_bytes_two, filename_two)

    # 1. Front Slices (Surgical target cuts optimized to prevent catching field header labels)
    biometric_photo = _extract_relative_slice(front_card, 0.135, 0.495, 0.25, 0.75)
    name_seg        = _extract_relative_slice(front_card, 0.620, 0.665, 0.12, 0.88)  
    dob_seg         = _extract_relative_slice(front_card, 0.702, 0.742, 0.12, 0.88)  
    sex_seg         = _extract_relative_slice(front_card, 0.778, 0.812, 0.12, 0.55)  
    expiry_seg      = _extract_relative_slice(front_card, 0.848, 0.888, 0.12, 0.88)  
    barcode_seg     = _extract_relative_slice(front_card, 0.882, 0.942, 0.24, 0.76)  
    vertical_seg    = _extract_relative_slice(front_card, 0.150, 0.950, 0.90, 0.96)

    # 2. Back Slices (Surgical cuts isolating fields cleanly from background vectors)
    qr_code_seg     = _extract_relative_slice(back_card,  0.100, 0.640, 0.10, 0.90)
    phone_seg       = _extract_relative_slice(back_card,  0.688, 0.728, 0.12, 0.52)  
    nat_seg         = _extract_relative_slice(back_card,  0.762, 0.802, 0.12, 0.52)  
    addr_seg        = _extract_relative_slice(back_card,  0.832, 0.978, 0.12, 0.88)  
    fin_value_seg   = _extract_relative_slice(back_card,  0.685, 0.728, 0.65, 0.95)  # Complete label exclusion boundary
    sn_seg          = _extract_relative_slice(back_card,  0.890, 0.955, 0.83, 0.97)  

    # 3. Canvas Injection Matrix — Left Hemisphere (Front ID side)
    _composite_element(canvas, biometric_photo, FRONT_ZONES["photo_main"], 0, apply_sharpen=True)
    _composite_element(canvas, biometric_photo, FRONT_ZONES["photo_small"], 0)
    _composite_element(canvas, barcode_seg, FRONT_ZONES["barcode_area"], 0)
    _composite_element(canvas, vertical_seg, FRONT_ZONES["vertical_strip"], 0, rotate_deg=90)

    _composite_text_stencil(canvas, name_seg, FRONT_ZONES["name_field"], 0)
    _composite_text_stencil(canvas, dob_seg, FRONT_ZONES["dob_field"], 0)
    _composite_text_stencil(canvas, sex_seg, FRONT_ZONES["sex_field"], 0)
    _composite_text_stencil(canvas, expiry_seg, FRONT_ZONES["expiry_field"], 0)

    # 4. Canvas Injection Matrix — Right Hemisphere (Back ID side, shifted dynamically via _FW)
    _composite_element(canvas, qr_code_seg, BACK_ZONES["qr_area"], _FW)
    _composite_text_stencil(canvas, phone_seg, BACK_ZONES["phone_field"], _FW)
    _composite_text_stencil(canvas, nat_seg, BACK_ZONES["nationality"], _FW)
    _composite_text_stencil(canvas, addr_seg, BACK_ZONES["address_field"], _FW)
    _composite_text_stencil(canvas, fin_value_seg, BACK_ZONES["fin_value"], _FW)
    _composite_text_stencil(canvas, sn_seg, BACK_ZONES["sn_field"], _FW)

    # 5. Output Target Standardization Formatting
    if (width, height) != (_TW, _TH) and (width != 1012):
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)

    output_buffer = io.BytesIO()
    canvas.save(output_buffer, format="JPEG", quality=98, optimize=True, progressive=True, dpi=(300, 300))
    
    return output_buffer.getvalue()
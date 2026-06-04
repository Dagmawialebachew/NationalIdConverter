from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --- Configuration Mirror from fayda_converter_v2.py ---
_TW = 2360
_TH = 667
_FW = _TW // 2  # 1180px

FRONT_ZONES = {
    "vertical_strip_left":  (70, 100, 100, 200), 
    "vertical_strip_right":  (50, 85, 100, 595),
    "photo_main":     (140, 145, 510, 595),
    "name_field": (513, 200, 961, 287), 
    "dob_field":      (512, 265, 1055, 440),
    "sex_field":      (512, 398, 830, 440),
    "expiry_field":   (512, 468, 900, 515),
    "barcode_area":   (562, 525, 855, 617),
    "photo_small":    (890, 475, 1030, 622),
}

BACK_ZONES = {
    "phone_field":    (57, 55, 285, 170),
    "address_field":  (118, 252, 398, 523),  
    "fin_value":      (165, 477, 380, 672), 
    "qr_area":        (550, 5, 950, 620),
    "sn_field":       (885, 612, 1160, 652),
}

def generate_layout_map():
    template_path = Path(__file__).parent / "fayda_template.jpg"
    
    # 1. Load background template or create a clean placeholder canvas
    if template_path.exists():
        print(f"Loading base template layout from: {template_path}")
        canvas = Image.open(template_path).convert("RGB")
    else:
        print("Template file not found. Generating a blank testing canvas placeholder...")
        canvas = Image.new("RGB", (_TW, _TH), (245, 247, 250))
    
    draw = ImageDraw.Draw(canvas)
    
    # 2. Draw a distinct center line separating Front and Back hemispheres
    draw.line([(_FW, 0), (_FW, _TH)], fill=(120, 120, 120), width=5)
    
    # Try loading a readable system font for the zone labels
    try:
        font = ImageFont.truetype("arialbd.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    # 3. Map Front Zones (Blue)
    for name, zone in FRONT_ZONES.items():
        x1, y1, x2, y2 = zone
        # Draw bounding rectangle
        draw.rectangle([x1, y1, x2, y2], outline="blue", width=3)
        # Add quick label text block
        draw.text((x1 + 5, y1 + 5), name, fill="blue", font=font)
        
    # 4. Map Back Zones (Red) with the dynamic horizontal offset (_FW) applied
    for name, zone in BACK_ZONES.items():
        x1, y1, x2, y2 = zone
        x1_offset = x1 + _FW
        x2_offset = x2 + _FW
        
        # Draw bounding rectangle
        draw.rectangle([x1_offset, y1_offset, x2_offset, y2_offset], outline="red", width=3)
        # Add quick label text block
        draw.text((x1_offset + 5, y1_offset + 5), name, fill="red", font=font)

    # 5. Output target preview file
    output_filename = "TEMPLATE_PASTE_ZONES_DEBUG.jpg"
    canvas.save(output_filename, quality=95)
    print(f"🎉 Debug map compiled successfully! Open '{output_filename}' to inspect alignment layout.")

if __name__ == "__main__":
    generate_layout_map()
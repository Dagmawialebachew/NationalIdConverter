# test_crop.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ExifTags


IMAGE_PATH = "uploaded_fayda.jpg"
DEBUG_DIR = Path("debug_out")
DEBUG_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# Metadata / source-device guess
# ---------------------------------------------------------------------
def _collect_metadata(image_path: str) -> str:
    """
    Collects EXIF + PNG/JPEG info into a single lowercase string.
    This is only a heuristic for guessing source device.
    """
    parts = []

    try:
        pil_img = Image.open(image_path)
        info = getattr(pil_img, "info", {}) or {}
        for k, v in info.items():
            if isinstance(v, (str, bytes)):
                parts.append(f"{k}:{v}".lower())

        exif = pil_img.getexif()
        if exif:
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                parts.append(f"{tag_name}:{value}".lower())

    except Exception:
        pass

    return " | ".join(parts)


def classify_capture_source(image_path: str, img_bgr: np.ndarray) -> Tuple[str, float, str]:
    """
    Returns (label, confidence, reason).
    Labels: iPhone, Android phone, PC, Unknown
    """
    h, w = img_bgr.shape[:2]
    meta = _collect_metadata(image_path)

    score = {
        "iPhone": 0.0,
        "Android phone": 0.0,
        "PC": 0.0,
    }
    reasons = []

    # ---- Metadata clues ----
    iphone_keys = [
        "iphone", "ipad", "ios", "apple", "ipod"
    ]
    android_keys = [
        "android", "samsung", "pixel", "xiaomi", "redmi", "oppo",
        "vivo", "oneplus", "huawei", "honor", "infinix", "tecno",
        "realme", "motorola", "lg", "sony"
    ]
    pc_keys = [
        "windows", "macos", "macbook", "imac", "desktop", "pc",
        "snipping tool", "sharex", "greenshot", "lightshot",
        "flameshot", "photoshop", "gimp", "chrome", "edge"
    ]

    if any(k in meta for k in iphone_keys):
        score["iPhone"] += 3.5
        reasons.append("metadata suggests Apple/iPhone")
    if any(k in meta for k in android_keys):
        score["Android phone"] += 3.5
        reasons.append("metadata suggests Android")
    if any(k in meta for k in pc_keys):
        score["PC"] += 3.5
        reasons.append("metadata suggests PC/desktop capture tool")

    # ---- Dimension clues ----
    aspect = w / float(h) if h else 0.0

    # Very common screenshot / capture patterns
    if h > w:
        # Portrait image is more likely from phone
        score["iPhone"] += 0.6
        score["Android phone"] += 0.6
        reasons.append("portrait orientation")
    else:
        score["PC"] += 0.8
        reasons.append("landscape orientation")

    # Tall phone-like screenshots
    if 1.7 <= (h / float(w)) <= 2.5:
        score["iPhone"] += 0.8
        score["Android phone"] += 0.8
        reasons.append("phone-like aspect ratio")

    # Very common PC screenshot ratios
    if 1.2 <= aspect <= 2.2:
        score["PC"] += 0.4
    if aspect >= 1.4:
        score["PC"] += 0.3

    # Some rough pixel-size hints
    common_pc = {
        (1920, 1080), (1366, 768), (2560, 1440), (1600, 900),
        (3440, 1440), (3840, 2160), (1280, 720)
    }
    if (w, h) in common_pc or (h, w) in common_pc:
        score["PC"] += 2.0
        reasons.append("common PC resolution")

    # Pick best
    best_label = max(score, key=score.get)
    best_score = score[best_label]

    if best_score < 1.0:
        return "Unknown", 0.20, "weak signals only"

    # Convert score to a loose confidence estimate
    confidence = min(0.98, 0.35 + best_score / 6.0)
    reason = "; ".join(reasons) if reasons else "heuristic guess"
    return best_label, confidence, reason


# ---------------------------------------------------------------------
# Card detection utilities
# ---------------------------------------------------------------------
def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Orders 4 points as: top-left, top-right, bottom-right, bottom-left
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def preprocess_variants(gray: np.ndarray) -> list[np.ndarray]:
    """
    Multiple preprocessing variants because screenshots differ a lot.
    """
    variants = []

    # Variant 1: simple blur + Canny
    blur1 = cv2.GaussianBlur(gray, (5, 5), 0)
    edges1 = cv2.Canny(blur1, 40, 130)
    variants.append(edges1)

    # Variant 2: CLAHE + Canny
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(gray)
    blur2 = cv2.GaussianBlur(eq, (5, 5), 0)
    edges2 = cv2.Canny(blur2, 35, 120)
    variants.append(edges2)

    # Variant 3: bilateral + Canny
    bil = cv2.bilateralFilter(gray, 9, 75, 75)
    edges3 = cv2.Canny(bil, 30, 100)
    variants.append(edges3)

    return variants


def candidate_score(cnt: np.ndarray, image_area: float) -> float:
    """
    Scores contour quality for a Fayda-card-like rectangle.
    """
    area = cv2.contourArea(cnt)
    if area < image_area * 0.02:
        return -1.0

    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    hull = cv2.convexHull(cnt)
    hull_area = cv2.contourArea(hull)

    if hull_area <= 0:
        return -1.0

    rect = cv2.minAreaRect(cnt)
    (rw, rh) = rect[1]
    if rw <= 1 or rh <= 1:
        return -1.0

    box_area = rw * rh
    rectangularity = min(1.0, area / box_area) if box_area > 0 else 0.0
    solidity = min(1.0, area / hull_area) if hull_area > 0 else 0.0

    # Fayda card is a tall portrait rectangle in these screenshots.
    aspect = max(rw, rh) / min(rw, rh)

    # Prefer a shape close to a rectangle, but allow perspective distortion
    corner_bonus = 1.0
    if len(approx) == 4:
        corner_bonus = 1.45
    elif len(approx) in (5, 6):
        corner_bonus = 1.15
    else:
        corner_bonus = 0.85

    # Portrait card-ish aspect ratio
    aspect_bonus = 1.0
    if 1.15 <= aspect <= 2.4:
        aspect_bonus = 1.20
    elif 0.8 <= aspect < 1.15:
        aspect_bonus = 1.05
    else:
        aspect_bonus = 0.75

    # Large, clean rectangle wins
    score = (
        area *
        rectangularity *
        solidity *
        corner_bonus *
        aspect_bonus
    )
    return float(score)


def detect_card_quad(img_bgr: np.ndarray) -> Optional[np.ndarray]:
    """
    Detects the best 4-point-ish card boundary in the image.
    Returns 4 ordered points or None.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    image_area = float(h * w)

    best_cnt = None
    best_score = -1.0

    for edges in preprocess_variants(gray):
        # Close gaps so the contour becomes more complete
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        closed = cv2.dilate(closed, kernel, iterations=1)

        cnts = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = cnts[0] if len(cnts) == 2 else cnts[1]

        for cnt in contours:
            s = candidate_score(cnt, image_area)
            if s > best_score:
                best_score = s
                best_cnt = cnt

    if best_cnt is None:
        return None

    rect = cv2.minAreaRect(best_cnt)
    box = cv2.boxPoints(rect)
    box = np.array(box, dtype="float32")
    ordered = order_points(box)
    return ordered


def four_point_warp(img_bgr: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Perspective-warp the detected card into a cleaned rectangle.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    max_width = max(1, max_width)
    max_height = max(1, max_height)

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(
        img_bgr,
        M,
        (max_width, max_height),
        flags=cv2.INTER_CUBIC
    )
    return warped


def draw_quad(img_bgr: np.ndarray, pts: np.ndarray, color=(0, 255, 0), thickness: int = 5) -> np.ndarray:
    """
    Draws the detected quadrilateral on a copy of the image.
    """
    out = img_bgr.copy()
    poly = pts.astype(int).reshape((-1, 1, 2))
    cv2.polylines(out, [poly], True, color, thickness, cv2.LINE_AA)
    return out


def apply_device_trim(img_bgr: np.ndarray, device_label: str) -> np.ndarray:
    """
    Optional tiny crop correction if the right side tends to include whitespace.
    Keep this subtle. It's a safety nudge, not the main detection.
    """
    h, w = img_bgr.shape[:2]

    trims = {
        "iPhone": (0.000, 0.000, 0.015, 0.000),        # left, top, right, bottom
        "Android phone": (0.000, 0.000, 0.020, 0.000),
        "PC": (0.000, 0.000, 0.010, 0.000),
        "Unknown": (0.000, 0.000, 0.015, 0.000),
    }

    l, t, r, b = trims.get(device_label, trims["Unknown"])

    x1 = int(w * l)
    y1 = int(h * t)
    x2 = int(w * (1.0 - r))
    y2 = int(h * (1.0 - b))

    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))

    return img_bgr[y1:y2, x1:x2]


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Detect Fayda card, guess capture device, crop and save results.")
    parser.add_argument("--input", default=IMAGE_PATH, help="Input image path")
    parser.add_argument("--debug", action="store_true", help="Save debug overlays")
    args = parser.parse_args()

    image_path = args.input
    img_bgr = cv2.imread(image_path)

    if img_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    device_label, confidence, reason = classify_capture_source(image_path, img_bgr)
    print(f"[SOURCE] {device_label}  (confidence: {confidence:.2f})")
    print(f"[REASON] {reason}")

    quad = detect_card_quad(img_bgr)

    if quad is None:
        raise RuntimeError("Could not detect the Fayda card boundary.")

    # Save overlay with detected rectangle
    overlay = draw_quad(img_bgr, quad)
    cv2.imwrite(str(DEBUG_DIR / "detected_card_overlay.jpg"), overlay)

    # Perspective crop
    warped = four_point_warp(img_bgr, quad)

    # Tiny source-based trim to reduce white drift
    warped = apply_device_trim(warped, device_label)

    # Save final crop
    cv2.imwrite("cropped_fayda.jpg", warped)

    print("[OK] Saved: detected_card_overlay.jpg")
    print("[OK] Saved: cropped_fayda.jpg")

    # Optional: save a resized preview for easy inspection
    if args.debug:
        preview = warped.copy()
        preview_h, preview_w = preview.shape[:2]
        if preview_w > 1400:
            scale = 1400 / float(preview_w)
            preview = cv2.resize(preview, (int(preview_w * scale), int(preview_h * scale)))
        cv2.imwrite(str(DEBUG_DIR / "cropped_preview.jpg"), preview)
        print("[OK] Saved: debug_out/cropped_preview.jpg")


if __name__ == "__main__":
    main()
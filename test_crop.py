# text_crop.py
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

DEBUG_DIR = Path("debug_out")
DEBUG_DIR.mkdir(exist_ok=True)


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def preprocess_variants(gray: np.ndarray) -> list[np.ndarray]:
    variants = []
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    variants.append(cv2.Canny(blur, 40, 130))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(gray)
    blur2 = cv2.GaussianBlur(eq, (5, 5), 0)
    variants.append(cv2.Canny(blur2, 35, 120))
    bil = cv2.bilateralFilter(gray, 9, 75, 75)
    variants.append(cv2.Canny(bil, 30, 100))
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 15, 6)
    variants.append(cv2.Canny(cv2.GaussianBlur(th, (3, 3), 0), 30, 100))
    return variants


def candidate_score(cnt: np.ndarray, image_area: float) -> float:
    area = cv2.contourArea(cnt)
    if area < image_area * 0.015:
        return -1.0
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.01 * peri, True)
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
    aspect = max(rw, rh) / min(rw, rh)
    corner_bonus = 1.45 if len(approx) == 4 else (1.10 if len(approx) in (5, 6) else 0.85)
    aspect_bonus = 1.25 if 1.15 <= aspect <= 2.6 else (1.05 if 0.9 <= aspect < 1.15 else 0.7)
    score = area * rectangularity * solidity * corner_bonus * aspect_bonus
    return float(score)


def detect_card_quad(img_bgr: np.ndarray, debug: bool = False) -> Optional[np.ndarray]:
    h0, w0 = img_bgr.shape[:2]
    H_MAX = 1600
    scale = 1.0
    if max(h0, w0) > H_MAX:
        scale = H_MAX / float(max(h0, w0))
        img = cv2.resize(img_bgr, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)
    else:
        img = img_bgr.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    image_area = float(gray.shape[0] * gray.shape[1])

    best_cnt = None
    best_score = -1.0
    variants = preprocess_variants(gray)

    for i, edges in enumerate(variants):
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        closed = cv2.dilate(closed, kernel, iterations=1)
        cnts = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = cnts[0] if len(cnts) == 2 else cnts[1]
        for cnt in contours:
            s = candidate_score(cnt, image_area)
            if s > best_score:
                best_score = s
                best_cnt = cnt
        if debug:
            cv2.imwrite(str(DEBUG_DIR / f"edges_variant_{i}.jpg"), edges)
            cv2.imwrite(str(DEBUG_DIR / f"closed_variant_{i}.jpg"), closed)

    if best_cnt is None:
        # fallback: try looser search using all contours
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 120)
        cnts = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = cnts[0] if len(cnts) == 2 else cnts[1]
        for cnt in contours:
            s = candidate_score(cnt, image_area)
            if s > best_score:
                best_score = s
                best_cnt = cnt
        if debug:
            cv2.imwrite(str(DEBUG_DIR / "edges_fallback.jpg"), edges)

    if best_cnt is None:
        return None

    rect = cv2.minAreaRect(best_cnt)
    box = cv2.boxPoints(rect)
    box = np.array(box, dtype="float32")
    if scale != 1.0:
        box *= (1.0 / scale)
    ordered = order_points(box)
    return ordered


def four_point_warp(img_bgr: np.ndarray, pts: np.ndarray, output_size: Tuple[int, int] = (600, 900)) -> np.ndarray:
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
    warped = cv2.warpPerspective(img_bgr, M, (max_width, max_height), flags=cv2.INTER_CUBIC)
    pad_x = int(max_width * 0.01)
    pad_y = int(max_height * 0.01)
    x1, y1 = pad_x, pad_y
    x2, y2 = max_width - pad_x, max_height - pad_y
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(max_width, x2); y2 = min(max_height, y2)
    warped = warped[y1:y2, x1:x2]
    out_w, out_h = output_size
    warped_h, warped_w = warped.shape[:2]
    scale = min(out_w / warped_w, out_h / warped_h)
    new_w, new_h = max(1, int(warped_w * scale)), max(1, int(warped_h * scale))
    resized = cv2.resize(warped, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    canvas = np.zeros((out_h, out_w, 3), dtype=resized.dtype)
    x_off = (out_w - new_w) // 2
    y_off = (out_h - new_h) // 2
    canvas[y_off:y_off+new_h, x_off:x_off+new_w] = resized
    return canvas


def draw_quad(img_bgr: np.ndarray, pts: np.ndarray, color=(0, 255, 0), thickness: int = 6) -> np.ndarray:
    out = img_bgr.copy()
    poly = pts.astype(int).reshape((-1, 1, 2))
    cv2.polylines(out, [poly], True, color, thickness, cv2.LINE_AA)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop a single uploaded screenshot into overlay + cropped outputs.")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--debug", action="store_true", help="Save debug overlays")
    parser.add_argument("--output-crop", default="cropped_fayda.jpg", help="Cropped output filename")
    parser.add_argument("--output-overlay", default="detected_card_overlay.jpg", help="Overlay output filename")
    args = parser.parse_args()

    image_path = Path(args.input)
    if not image_path.exists():
        raise FileNotFoundError(f"Could not read image: {image_path}")

    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        raise RuntimeError(f"Failed to load image: {image_path}")

    quad = detect_card_quad(img_bgr, debug=args.debug)
    if quad is None:
        raise RuntimeError("Could not detect the card boundary in the provided image")

    overlay = draw_quad(img_bgr, quad)
    cv2.imwrite(args.output_overlay, overlay)

    warped = four_point_warp(img_bgr, quad)
    cv2.imwrite(args.output_crop, warped)

    if args.debug:
        # Save a small preview of the crop for quick inspection
        preview = warped.copy()
        ph, pw = preview.shape[:2]
        if pw > 1400:
            scale = 1400 / float(pw)
            preview = cv2.resize(preview, (int(pw * scale), int(ph * scale)))
        cv2.imwrite(str(DEBUG_DIR / "cropped_preview.jpg"), preview)

    print(f"[OK] Saved overlay: {args.output_overlay}")
    print(f"[OK] Saved crop: {args.output_crop}")


if __name__ == "__main__":
    main()

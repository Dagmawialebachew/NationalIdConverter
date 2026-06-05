import cv2
import numpy as np

IMAGE_PATH = "uploaded_fayda.jpg"


img = cv2.imread(IMAGE_PATH)

if img is None:
    raise Exception(f"Could not open {IMAGE_PATH}")

orig = img.copy()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Slight blur
gray = cv2.GaussianBlur(gray, (5, 5), 0)

# Adaptive threshold works much better on screenshots
thresh = cv2.adaptiveThreshold(
    gray,
    255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    51,
    10
)

# Connect nearby edges
kernel = cv2.getStructuringElement(
    cv2.MORPH_RECT,
    (7, 7)
)

thresh = cv2.morphologyEx(
    thresh,
    cv2.MORPH_CLOSE,
    kernel,
    iterations=2
)

contours, _ = cv2.findContours(
    thresh,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE
)

best_rect = None
best_area = 0

for cnt in contours:

    area = cv2.contourArea(cnt)

    if area < 100000:
        continue

    x, y, w, h = cv2.boundingRect(cnt)

    ratio = w / h

    # Fayda card roughly portrait
    if not (0.55 <= ratio <= 0.90):
        continue

    if area > best_area:
        best_area = area
        best_rect = (x, y, w, h)

if best_rect is None:

    print("No card found using contours.")
    print("Trying fallback...")

    h_img, w_img = img.shape[:2]

    # Since screenshot layout is predictable
    x = int(w_img * 0.08)
    y = int(h_img * 0.20)

    w = int(w_img * 0.84)
    h = int(h_img * 0.63)

else:

    x, y, w, h = best_rect

# Draw rectangle
preview = orig.copy()

cv2.rectangle(
    preview,
    (x, y),
    (x + w, y + h),
    (0, 255, 0),
    5
)

cv2.imwrite(
    "detected_card.jpg",
    preview
)

crop = orig[y:y+h, x:x+w]

cv2.imwrite(
    "cropped_fayda.jpg",
    crop
)

print("Saved:")
print(" - detected_card.jpg")
print(" - cropped_fayda.jpg")
import cv2
import os


def preprocess_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 15
    )

    coords = cv2.findNonZero(255 - thresh)
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    h, w = thresh.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        thresh, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return deskewed


def preprocess_all(raw_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for filename in sorted(os.listdir(raw_folder)):
        if filename.endswith((".jpg", ".png", ".jpeg")):
            path = os.path.join(raw_folder, filename)
            cleaned = preprocess_image(path)
            out_path = os.path.join(output_folder, filename)
            cv2.imwrite(out_path, cleaned)
            print("processed", filename)


if __name__ == "__main__":
    preprocess_all("data/raw_scans", "data/preprocessed")

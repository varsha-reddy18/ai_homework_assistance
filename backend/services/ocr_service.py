import pytesseract
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text(file):
    image_bytes = file.file.read()
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # 🔥 Improve preprocessing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=2, beta=0)

    # Threshold (important)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

    # Resize (VERY IMPORTANT for OCR)
    thresh = cv2.resize(thresh, None, fx=2, fy=2)

    # Tesseract config (important)
    custom_config = r'--oem 3 --psm 6'

    text = pytesseract.image_to_string(thresh, config=custom_config)

    return text.strip()


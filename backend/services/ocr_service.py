import pytesseract
import cv2
import numpy as np
import platform
import fitz  # PyMuPDF for PDF support
from PIL import Image
import io

# ✅ Auto-detect Tesseract path based on OS
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# On Linux/Mac, tesseract is usually in PATH automatically


def preprocess_image(img_array: np.ndarray) -> np.ndarray:
    """Preprocess image for better OCR accuracy."""
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=2, beta=0)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.resize(thresh, None, fx=2, fy=2)
    return thresh


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Extract text from raw image bytes using OpenCV + Tesseract."""
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image. Make sure it's a valid image file.")

    processed = preprocess_image(img)
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed, config=custom_config)
    return text.strip()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF — tries native text first, falls back to OCR."""
    all_text = []

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]

        # ✅ Try native text extraction first (fast & accurate)
        native_text = page.get_text().strip()

        if native_text:
            all_text.append(native_text)
        else:
            # ✅ Fallback to OCR for scanned/image-based PDFs
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is not None:
                processed = preprocess_image(img)
                custom_config = r'--oem 3 --psm 6'
                ocr_text = pytesseract.image_to_string(processed, config=custom_config)
                all_text.append(ocr_text.strip())

    pdf_doc.close()
    return "\n\n".join(all_text).strip()


async def extract_text(file) -> str:
    """
    Main entry point. Accepts FastAPI UploadFile.
    Supports: .jpg, .jpeg, .png, .bmp, .tiff, .pdf
    """
    # ✅ Reset file pointer before reading (important!)
    await file.seek(0)
    file_bytes = await file.read()

    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf_bytes(file_bytes)
    elif any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]):
        return extract_text_from_image_bytes(file_bytes)
    else:
        # ✅ Try image decode as a fallback for unknown extensions
        try:
            return extract_text_from_image_bytes(file_bytes)
        except Exception:
            raise ValueError(f"Unsupported file type: '{file.filename}'. Use JPG, PNG, or PDF.")
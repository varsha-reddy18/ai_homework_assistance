import pytesseract
import cv2
import numpy as np
import platform
import fitz  # PyMuPDF
import io
import re

# ✅ Auto-detect Tesseract path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def clean_text(text: str) -> str:
    """
    Clean up messy OCR/PDF extracted text:
    - Remove excessive blank lines
    - Remove garbage characters
    - Normalize spaces
    """
    # Remove non-printable characters except newlines
    text = re.sub(r'[^\x20-\x7E\n\u0900-\u097F\u0C00-\u0C7F]', ' ', text)

    # Collapse multiple spaces into one
    text = re.sub(r'[ \t]+', ' ', text)

    # Collapse more than 2 newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]

    # Remove lines that are just 1-2 random characters (OCR garbage)
    lines = [line for line in lines if len(line) > 2 or line == ""]

    return "\n".join(lines).strip()


def preprocess_image(img_array: np.ndarray) -> np.ndarray:
    """Preprocess image for better Tesseract OCR accuracy."""

    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=30)

    # Increase contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Adaptive threshold (better than fixed 150 for varied lighting)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 10
    )

    # Resize to help Tesseract (2x)
    thresh = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

    return thresh


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Extract text from image bytes using OpenCV + Tesseract."""

    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image. Make sure it's a valid image file.")

    processed = preprocess_image(img)

    # PSM 6 = assume uniform block of text (good for homework/notes)
    # PSM 3 = fully automatic (good for mixed layouts)
    # Try PSM 6 first, fallback to PSM 3
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed, config=custom_config)

    if len(text.strip()) < 20:
        # Retry with PSM 3 if PSM 6 gave too little
        custom_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(processed, config=custom_config)

    return clean_text(text)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF:
    - Uses native PyMuPDF text extraction first (fast, accurate for digital PDFs)
    - Falls back to OCR page-by-page for scanned/image-based PDFs
    - Cleans and returns combined text
    """
    all_text = []

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(pdf_doc)

    for page_num in range(total_pages):
        page = pdf_doc[page_num]

        # ✅ Try native text extraction
        native_text = page.get_text("text").strip()
        native_text = clean_text(native_text)

        if len(native_text) > 30:
            # Native text is good — use it
            all_text.append(f"[Page {page_num + 1}]\n{native_text}")

        else:
            # ✅ Scanned page — use OCR
            # Higher DPI = better OCR quality
            pix = page.get_pixmap(dpi=250)
            img_bytes = pix.tobytes("png")

            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is not None:
                processed = preprocess_image(img)
                custom_config = r'--oem 3 --psm 6'
                ocr_text = pytesseract.image_to_string(processed, config=custom_config)
                ocr_text = clean_text(ocr_text)

                if ocr_text:
                    all_text.append(f"[Page {page_num + 1}]\n{ocr_text}")

    pdf_doc.close()

    if not all_text:
        return ""

    combined = "\n\n".join(all_text)

    # ✅ Trim to avoid overloading the AI model (keep max ~4000 chars)
    if len(combined) > 4000:
        combined = combined[:4000] + "\n\n[... content trimmed for length ...]"

    return combined


async def extract_text(file) -> str:
    """
    Main entry point — accepts FastAPI UploadFile.
    Supports: .jpg, .jpeg, .png, .bmp, .tiff, .webp, .pdf
    """
    # ✅ Always reset file pointer before reading
    await file.seek(0)
    file_bytes = await file.read()

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    # ✅ Route by filename extension or content type
    if filename.endswith(".pdf") or content_type == "application/pdf":
        return extract_text_from_pdf_bytes(file_bytes)

    elif any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]) \
         or content_type.startswith("image/"):
        return extract_text_from_image_bytes(file_bytes)

    else:
        # Last resort — try image decode
        try:
            return extract_text_from_image_bytes(file_bytes)
        except Exception:
            raise ValueError(
                f"Unsupported file: '{file.filename}'. Please upload JPG, PNG, or PDF."
            )
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

def ocr_from_screenshot(screenshot_bytes):
    image = Image.open(BytesIO(screenshot_bytes)).convert("L")
    image = image.filter(ImageFilter.SHARPEN)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    return pytesseract.image_to_string(image)

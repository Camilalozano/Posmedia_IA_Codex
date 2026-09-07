import io
import re
from pypdf import PdfReader
from src.config import MAX_FILE_BYTES

def pdf_text(data: bytes) -> tuple[str, list[str]]:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('El PDF supera 20 MB.')
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("El PDF está cifrado y no puede leerse.") from exc
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    if len(re.sub(r"\s", "", text)) < 100:
        raise ValueError("El PDF no contiene texto legible; aplique OCR antes de cargarlo.")
    return text, pages

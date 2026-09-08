import io
import re
import pymupdf
from pypdf import PdfReader
from src.config import MAX_FILE_BYTES

def pdf_text(data: bytes) -> tuple[str, list[str]]:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('El PDF supera 20 MB.')
    pages = []
    try:
        with pymupdf.open(stream=data, filetype='pdf') as document:
            if document.needs_pass and not document.authenticate(''):
                raise ValueError('El PDF está cifrado y no puede leerse.')
            pages = [page.get_text('text') or '' for page in document]
    except ValueError:
        raise
    except Exception:
        # Respaldo para archivos válidos que PyMuPDF no pueda interpretar.
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                if not reader.decrypt(''):
                    raise ValueError('El PDF está cifrado y no puede leerse.')
            except Exception as exc:
                raise ValueError('El PDF está cifrado y no puede leerse.') from exc
        pages = [page.extract_text() or '' for page in reader.pages]
    text = "\n\n".join(pages)
    if len(re.sub(r"\s", "", text)) < 100:
        raise ValueError("El PDF no contiene texto legible; aplique OCR antes de cargarlo.")
    return text, pages


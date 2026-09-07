"""Expande PDF y ZIP en memoria, con límites y sin escribir evidencias a disco."""
import hashlib
import io
import zipfile
from pathlib import PurePosixPath
from src.config import MAX_FILE_BYTES, MAX_TOTAL_BYTES, MAX_FILES

def expand_inputs(uploads: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    result, seen, total, count = [], set(), 0, 0
    def add(name, data):
        nonlocal total, count
        count += 1
        total += len(data)
        if count > MAX_FILES or total > MAX_TOTAL_BYTES or len(data) > MAX_FILE_BYTES:
            raise ValueError('Límite: 50 PDF, 20 MB por archivo y 100 MB en total.')
        digest = hashlib.sha256(data).hexdigest()
        if digest not in seen:
            seen.add(digest)
            result.append((name, data))
    for name, data in uploads:
        if len(data) > MAX_TOTAL_BYTES:
            raise ValueError('El archivo supera 100 MB.')
        if name.lower().endswith('.pdf'):
            add(name, data)
        elif name.lower().endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(data)) as bundle:
                for entry in bundle.infolist():
                    if entry.is_dir():
                        continue
                    if not entry.filename.lower().endswith('.pdf'):
                        raise ValueError('El ZIP solo debe contener evidencias PDF.')
                    if entry.file_size > MAX_FILE_BYTES or total + entry.file_size > MAX_TOTAL_BYTES or count >= MAX_FILES:
                        raise ValueError('El ZIP excede los límites de carga.')
                    if entry.flag_bits & 1:
                        raise ValueError('No se admiten ZIP cifrados.')
                    add(name + ' / ' + entry.filename, bundle.read(entry))
        else:
            raise ValueError('Solo se admiten archivos PDF o ZIP con PDF.')
    return result

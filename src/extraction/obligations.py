"""Adaptado del extractor de obligaciones IES de Camilalozano.

Mantiene sección objetivo y numeración consecutiva; requiere revisión humana.
"""
import re
import unicodedata

def normalize_for_search(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn").upper()


def clean_text(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(
        r"(?im)^\s*(Carrera 10 No\..*|PBX:.*|www\.agenciaatenea.*|"
        r"atencionalciudadano.*|Información: Línea 195.*|Página \d+ de \d+)\s*$",
        "",
        text,
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_obligations(text: str) -> list[dict]:
    text = clean_text(text)
    normalized_parts, offsets = [], []
    for index, char in enumerate(text):
        folded = normalize_for_search(char)
        normalized_parts.append(folded)
        offsets.extend([index] * len(folded))
    normalized = ''.join(normalized_parts)
    start_patterns = [
        r"(?:C\.\s*)?OBLIGACIONES DE LA INSTITUCION DE EDUCACION SUPERIOR\s*-?\s*IES\s*:\s*(?:SE OBLIGA A\s*:)?",
        r"(?:C\.\s*)?COMPROMISOS DE LA INSTITUCION DE EDUCACION SUPERIOR\s*-?\s*IES\s*:\s*",
        r"OBLIGACIONES (?:ESPECIFICAS )?DE LA IES\s*:\s*",
    ]
    start = None
    for pattern in start_patterns:
        match = re.search(pattern, normalized)
        if match:
            start = match.end()
            break
    if start is None:
        return []

    normalized_tail = normalized[start:]
    possible_ends = []
    for pattern in [
        r"\s+PARAGRAFO\.?\s+TODOS LOS DOCUMENTOS",
        r"\s+DECIMA[ .-]+COMITE TECNICO",
        r"\s+D\.\s+OBLIGACIONES",
        r"\s+OBLIGACIONES DE (?:LA )?AGENCIA",
    ]:
        match = re.search(pattern, normalized_tail)
        if match:
            possible_ends.append(match.start())

    section_end = start + (min(possible_ends) if possible_ends else min(len(normalized_tail), 30_000))
    original_start = offsets[start] if start < len(offsets) else len(text)
    original_end = offsets[section_end] if section_end < len(offsets) else len(text)
    section = text[original_start:original_end].strip()
    first = re.search(r"(?<!\d)1[\)\.]\s+(?=[A-ZÁÉÍÓÚÑ])", section)
    if first:
        section = section[first.start():]

    candidates = list(re.finditer(r"(?<!\d)(\d{1,2})[\)\.]\s+(?=[A-ZÁÉÍÓÚÑ])", section))
    markers = []
    expected = 1
    for marker in candidates:
        number = int(marker.group(1))
        if number == expected:
            markers.append(marker)
            expected += 1

    obligations = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(section)
        obligation = clean_text(section[marker.end():end]).strip(" ;")
        if obligation:
            obligations.append({"numero_obligacion": int(marker.group(1)), "obligaciones_especificas": obligation})
    return obligations

import re
from typing import Iterable
from src.models import Field
from src.config import NO_CHANGES

def normalize(text: str) -> str:
    """Compacta espacios sin cambiar letras ni puntuación contractual."""
    return re.sub(r"\s+", " ", text).strip()


def find_field(pages: list[str], patterns: Iterable[str], flags: int = re.I) -> Field:
    for page_no, page in enumerate(pages, 1):
        compact = normalize(page)
        for pattern in patterns:
            match = re.search(pattern, compact, flags)
            if match:
                value = normalize(match.group(1)).strip(" :;.-")
                if value:
                    excerpt = normalize(match.group(0))[:240]
                    return Field(value, f"Página {page_no}: {excerpt}", "alto")
    return Field()


def extract_contract(pages: list[str]) -> dict:
    fields = {
        "numero_contrato_convenio": find_field(pages, [r"\b(?:convenio|contrato)\s+(?:por\s+r[eé]gimen\s+privado\s+)?(?:de\s+asociaci[oó]n\s+)?(?:n(?:[oº°]\.?|\.)|n[uú]mero)\s*[:#-]?\s*([A-ZÁ-Ú]{2,15}[- ]\d{2,6}[-/]\d{4})"]),
        "tipo_instrumento": find_field(pages, [r"\b((?:convenio|contrato)\s+(?:por\s+r[eé]gimen\s+privado|de\s+[a-zá-ú ]{2,60}))\s+(?:n[oº°.]|n[uú]mero)", r"\b((?:convenio|contrato))\s+(?:n[oº°.]|n[uú]mero)"]),
        "nombre_contratista_asociado": find_field(pages, [r"por\s+la\s+otra,\s+(?:la\s+)?(.{3,120}?)\s*\(asociad[oa]\)", r"(?:asociad[oa]|contratista|cooperante)\s*:\s*(.{3,150}?)(?=\s+(?:nit|identificaci[oó]n|representante|objeto)\b|$)"]),
        "nombre_identitario": Field(),
        "nit_contratista": find_field(pages, [r"\(asociad[oa]\),?\s+identificad[oa]\s+con\s+NIT\.?\s*(?:n(?:[oº°]\.?|\.)|n[uú]mero)?\s*([0-9][0-9.\- ]{6,20})", r"(?:contratista|cooperante)\s*.{0,100}?\bNIT\s*[:.]?\s*([0-9][0-9.\- ]{6,20})"]),
        "representante_legal": find_field(pages, [r"representad[oa]\s+legalmente\s+por\s+([A-ZÁ-ÚÑ][A-ZÁ-ÚÑ ]{4,120}?),\s+identificad[oa]", r"representante\s+legal\s*:\s*([A-ZÁ-ÚÑ][A-ZÁ-ÚÑ ]{4,100})"]),
        "identificacion_representante": find_field(pages, [r"representad[oa]\s+legalmente\s+por.{5,180}?(?:c[eé]dula|C\.?C\.?)\s*(?:de\s+ciudadan[ií]a\s*)?(?:n(?:[oº°]\.?|\.)|n[uú]mero)?\s*([0-9.]{5,20})"]),
        "nombre_supervisor": find_field(pages, [r"(?:nombre\s+del\s+)?supervisor(?:a)?\s*:\s*([A-ZÁ-ÚÑ][A-ZÁ-ÚÑ ]{4,100})"]),
        "cargo_supervisor": find_field(pages, [r"supervisi[oó]n\s+ser[aá]\s+ejercida\s+por\s+(?:el/la\s+|el\s+|la\s+)?(Gerente\s+de\s+Educaci[oó]n\s+Posmedia|Subgerente[^,.;]{2,80}|Gerente[^,.;]{2,80})"]),
        "fecha_suscripcion": find_field(pages, [r"fecha\s+de\s+suscripci[oó]n\s*:?\s*([^.;\n]{5,50})"]),
        "fecha_inicio": find_field(pages, [r"fecha\s+de\s+inicio\s*:?\s*([^.;\n]{5,50})"]),
        "fecha_terminacion": find_field(pages, [r"fecha\s+de\s+terminaci[oó]n\s*:?\s*([^.;]{5,60})", r"hasta\s+el\s+(\d{1,2}\s+de\s+[a-zá-ú]+\s+de\s+20\d{2})"]),
        "plazo": find_field(pages, [r"plazo\s+de\s+ejecuci[oó]n\s*:\s*el\s+plazo\s+de\s+ejecuci[oó]n\s+del\s+(?:convenio|contrato)\s+ser[aá]\s+(.{5,100}?)(?=\s+SEXTA\b|$)", r"duraci[oó]n\s*:\s*([^.;]{4,150})"]),
        "lugar_ejecucion": find_field(pages, [r"lugar\s+de\s+ejecuci[oó]n\s*:\s*(.{3,100}?)(?=\s+(?:QUINTA|PLAZO)\b)"]),
        "valor_total": find_field(pages, [r"valor\s+estimado\s*:.{10,500}?(\$\s*[0-9.,]+)", r"valor\s+(?:total\s+)?(?:del\s+(?:convenio|contrato))?\s*:?\s*(\$\s*[0-9.,]+)"]),
        "aporte_atenea": find_field(pages, [r"aporte\s+de\s+atenea.{0,250}?(\$\s*[0-9.,]+)"]),
        "aporte_contraparte": find_field(pages, [r"aporte\s+de\s+la\s+(?:ies|contraparte|asociad[oa]).{0,250}?(\$\s*[0-9.,]+)"]),
        "modificaciones": Field(NO_CHANGES, "Revisión de modificaciones pendiente", "bajo"),
        "objeto": find_field(pages, [r"(?:PRIMERA\s*[.\-]+\s*)?OBJETO\s*:\s*(.{20,1200}?)(?=\s+(?:SEGUNDA|CL[AÁ]USULA|PLAZO|VALOR|OBLIGACIONES|COMPROMISOS)\b)"]),
    }
    # El supervisor puede estar definido exclusivamente por cargo; no lo convertimos en persona.
    if fields["nombre_supervisor"].value == fields["cargo_supervisor"].value:
        fields["nombre_supervisor"] = Field()
    return fields


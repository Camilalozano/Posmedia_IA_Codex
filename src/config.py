from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'templates' / 'Plantilla_maestra_informe_supervision_ATENEA_posmedia.docx'
NOT_FOUND = 'No especificado en los documentos suministrados'
NO_CHANGES = 'Pendiente de verificar modificaciones y otrosíes'
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
MAX_FILES = 50

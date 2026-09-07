# Reglas de extracción

Los campos contractuales se buscan mediante expresiones regulares adaptadas de PosmediaAtenea. Se conserva la página y el fragmento localizado. La confianza es una etiqueta heurística; no es una probabilidad validada. Los nombres y números extraídos requieren revisión, especialmente cuando aparecen varias partes o varios identificadores.

El extractor de obligaciones adapta Extracci-nobligacionesEspecificasPosmedia: busca encabezados de obligaciones o compromisos de la institución de educación superior y marcadores consecutivos desde 1. No aplica un extractor genérico de obligaciones de otras partes. Numeraciones distintas, listas interrumpidas o encabezados no reconocidos requieren revisión manual. No se asume que la lista extraída sea completa.

Las evidencias son opcionales. Cuando se cargan, tienen un ID por sesión, nombre original, hash SHA-256, estado de lectura y páginas; los duplicados por contenido se omiten. Las relaciones con obligaciones y las actividades son ingresadas por el usuario, sin certificación automática. Si no se carga ninguna, el Word indica `Sin evidencia asociada`.

No encontrar una modificación no demuestra que no exista. Se deja pendiente la revisión de otrosíes. Los campos de cumplimiento y firma del supervisor no se diligencian automáticamente.

El mapeo del Word corresponde exclusivamente a la plantilla versionada en templates. Si su estructura cambia, debe revisarse word_report.py y sus pruebas.

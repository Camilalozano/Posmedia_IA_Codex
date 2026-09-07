# Validación inicial

## Consulta contractual de la versión 0.2

Se aprobaron 19 pruebas con openpyxl 3.1.5 añadido al entorno. La consulta verifica lectura Excel y CSV, variantes de espacios, guiones y mayúsculas, rechazo de coincidencias parciales, conservación de ceros iniciales, detección de colisiones, mapeo, datos faltantes y trazabilidad. La interfaz se probó con consulta CSV, diligenciamiento y descarte de resultados al cambiar la base.

La prueba local del lector sobre el Excel suministrado confirmó que tres variantes (mayúsculas con guiones, palabras separadas por espacios y minúsculas sin separadores) recuperan el mismo registro, conservan la referencia original y formatean la fecha correctamente. No se incorporó el Excel ni sus registros al repositorio. La escala del avance de plazo y la conexión Oracle siguen pendientes. Estas verificaciones no sustituyen la revisión visual del Word.

## Base de la versión 0.1

Se ejecutaron 11 pruebas automatizadas con Python 3.12, Streamlit 1.63.0, pypdf 6.18.0 y lxml 6.1.3.

Cobertura: número contractual y fuente, datos ausentes, sección IES y límite frente a obligaciones de la Agencia, normalización Unicode, deduplicación, formatos no admitidos, PDF ilegible, flujo de extracción, generación Word y conservación binaria de sus componentes no modificados. La prueba de interfaz carga archivos ficticios, genera descargas e invalida el resultado al editar campos o cambiar el proceso.

Resultado: 11 pruebas aprobadas. Solo se usó un convenio ficticio; esto no acredita precisión general en minutas reales.

La revisión visual del Word sigue pendiente: se intentó renderizar un informe de prueba, pero LibreOffice no está instalado en el entorno. Las pruebas estructurales del archivo pasan; debe verificarse paginación y formato en Word antes de uso operativo.

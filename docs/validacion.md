# Validación inicial

Se ejecutaron 11 pruebas automatizadas con Python 3.12, Streamlit 1.63.0, pypdf 6.18.0 y lxml 6.1.3.

Cobertura: número contractual y fuente, datos ausentes, sección IES y límite frente a obligaciones de la Agencia, normalización Unicode, deduplicación, formatos no admitidos, PDF ilegible, flujo de extracción, generación Word y conservación binaria de sus componentes no modificados. La prueba de interfaz carga archivos ficticios, genera descargas e invalida el resultado al editar campos o cambiar el proceso.

Resultado: 11 pruebas aprobadas. Solo se usó un convenio ficticio; esto no acredita precisión general en minutas reales.

La revisión visual del Word sigue pendiente: se intentó renderizar un informe de prueba, pero LibreOffice no está instalado en el entorno. Las pruebas estructurales del archivo pasan; debe verificarse paginación y formato en Word antes de uso operativo.

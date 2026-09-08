# Validación inicial

## Actualización del PAR de la versión 0.8

La interfaz reemplazó la carga de una base contractual de respaldo por el campo protegido **Actualizar ruta PAR al archivo**. El enlace ingresado tiene prioridad durante la sesión, invalida resultados obtenidos con otro PAR y no se incorpora a la trazabilidad. Los errores de conexión remiten al nuevo campo sin revelar el enlace firmado. Se aprobaron 40 pruebas automatizadas.

## Expediente documental SECOP de la versión 0.7

Para `CO1.PCCNTR.8724386`, el conjunto oficial informa 11 documentos y aproximadamente 8,4 MB: PDF, dos ZIP y un XLSX. La validación comprueba que el archivo consolidado conserva los formatos originales, no expande los ZIP internos e incluye un inventario CSV. El ZIP también queda identificado por nombre, cantidad y SHA-256 en la trazabilidad del borrador.

La descarga real generó `Documentos_SECOP_ATENEA-582-2025.zip` con los 11 documentos, el inventario y 5,8 MB comprimidos. La comprobación integral del ZIP no encontró archivos dañados. Se aprobaron 39 pruebas automatizadas.

## Insumos SICORE y seguridad social de la versión 0.6

La interfaz incluye cargadores PDF separados para `Informe SICORE` y `Planilla Seguridad Social`. Una prueba de interfaz confirma que ambos archivos se incorporan con su categoría al inventario de evidencias del borrador.

## Descarga y extracción SECOP de la versión 0.5

Se validó el flujo completo con `ATENEA-582-2025`: la API oficial de archivos devolvió la minuta `ATENEA-582-2025 EAN.pdf` (373.436 bytes), la minuta permitió identificar el proceso `ATENEA-IA-JE-003-2025` y la API oficial de procesos devolvió la fila adjudicada a Universidad EAN. La ficha PDF generada fue abierta, renderizada y revisada visualmente.

La minuta real tiene 25 páginas. El extractor recuperó 22 compromisos específicos de la IES, con sus páginas 14 a 16, y obtuvo número contractual, tipo de instrumento, contratista, NIT, representante legal e identificación, cargo del supervisor, fecha de terminación, plazo, lugar, valor total, aportes y objeto. Estos resultados siguen sujetos a revisión humana.

Las pruebas automatizadas cubren validación del enlace SECOP, selección de la minuta, cabeceras necesarias para la descarga pública, identificación del proceso, selección por NIT del proveedor, generación del PDF y presencia de los dos botones de descarga en Streamlit.

La prueba de interfaz confirma que la minuta descargada muestra sus campos y obligaciones en tablas y alimenta `Revisar datos del informe` al preparar el borrador sin una carga manual. Se aprobaron 37 pruebas en total.

## Evidencias opcionales

La carga de evidencias dejó de ser obligatoria. Una prueba del flujo confirma que se puede preparar y descargar el Word usando una minuta sin evidencias; el documento conserva las obligaciones e indica `Sin evidencia asociada`.

## Consulta contractual de la versión 0.2

Se aprobaron 19 pruebas con openpyxl 3.1.5 añadido al entorno. La consulta verifica lectura Excel y CSV, variantes de espacios, guiones y mayúsculas, rechazo de coincidencias parciales, conservación de ceros iniciales, detección de colisiones, mapeo, datos faltantes y trazabilidad. La interfaz se probó con consulta CSV, diligenciamiento y descarte de resultados al cambiar la base.

## Conexión Oracle de la versión 0.3

Se aprobaron 23 pruebas en total. Las pruebas nuevas cubren la descarga remota, dominio permitido, errores HTTP y de red, renovación del PAR sin revelarlo y mensaje de la interfaz. El PAR suministrado respondió HTTP 200 y la consulta real de `Atenea 582 2025` recuperó `ATENEA-582-2025`, Universidad EAN y fecha de terminación 31/12/2032. El valor crudo de avance en esa exportación fue `8,3`; su conversión sigue pendiente de definición funcional.

La prueba local del lector sobre el Excel suministrado confirmó que tres variantes (mayúsculas con guiones, palabras separadas por espacios y minúsculas sin separadores) recuperan el mismo registro, conservan la referencia original y formatean la fecha correctamente. No se incorporó el Excel ni sus registros al repositorio. Estas verificaciones no sustituyen la revisión visual del Word.

El porcentaje de avance ahora toma `porc_ejecucion_financiera`. En la exportación de Oracle consultada, `ATENEA-582-2025` devuelve `6,0`; la aplicación copia ese valor sin transformar su escala y permite revisarlo antes de generar el informe.

## Base de la versión 0.1

Se ejecutaron 11 pruebas automatizadas con Python 3.12, Streamlit 1.63.0, pypdf 6.18.0 y lxml 6.1.3.

Cobertura: número contractual y fuente, datos ausentes, sección IES y límite frente a obligaciones de la Agencia, normalización Unicode, deduplicación, formatos no admitidos, PDF ilegible, flujo de extracción, generación Word y conservación binaria de sus componentes no modificados. La prueba de interfaz carga archivos ficticios, genera descargas e invalida el resultado al editar campos o cambiar el proceso.

Resultado: 11 pruebas aprobadas. Solo se usó un convenio ficticio; esto no acredita precisión general en minutas reales.

La revisión visual del Word sigue pendiente: se intentó renderizar un informe de prueba, pero LibreOffice no está instalado en el entorno. Las pruebas estructurales del archivo pasan; debe verificarse paginación y formato en Word antes de uso operativo.

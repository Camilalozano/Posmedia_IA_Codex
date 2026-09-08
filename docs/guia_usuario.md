# Guía de usuario

1. Indique el número del proceso. Puede escribir `Atenea 582 2025`, con o sin guiones y en cualquier combinación de mayúsculas y minúsculas. Se busca en la referencia contractual de la base.
2. Pulse **Consultar proceso** para buscar en Oracle. Si falla la conexión, solicite al administrador actualizar `ORACLE_PAR_URL` en los Secrets de Streamlit o cargue una base Excel/CSV como respaldo. Cuando SECOP informa los identificadores necesarios, puede abrir el proceso, descargar la minuta oficial y la ficha PDF y revisar las tablas de información y obligaciones extraídas de la minuta.
3. Si dispone de ellas, cargue las evidencias PDF individualmente o dentro de un ZIP. Este paso es opcional. Límite: 50 PDF, 20 MB por PDF y 100 MB descomprimidos en total. No se admiten ZIP cifrados, ZIP anidados ni otros formatos.
4. Opcionalmente cargue otra minuta PDF; si lo hace, esta tendrá prioridad. Pulse **Preparar borrador**. Sin carga manual, la aplicación usa la minuta descargada de SECOP para completar los campos y obligaciones revisables. Un PDF escaneado requiere OCR externo o revisión manual.
5. Corrija los campos, incluido el número contractual; complete el periodo y demás datos de ejecución. Revise y complete las obligaciones, una por línea.
6. Para cada obligación escriba las actividades realizadas y, si cargó evidencias, seleccione los archivos que las respaldan. Sin evidencias, el Word mostrará `Sin evidencia asociada`. La aplicación no determina por sí sola si los archivos demuestran cumplimiento.
7. Genere y descargue el Word y la trazabilidad JSON. Revise el documento antes de presentarlo; el supervisor debe diligenciar su sección y aprobar el contenido.

Al cambiar los archivos o el número de proceso se descarta el borrador anterior. Al modificar un dato se invalida la descarga anterior hasta generar de nuevo.

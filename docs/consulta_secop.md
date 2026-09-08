# Consulta por número del proceso

El número del proceso ingresado por el usuario se cruza exclusivamente con `referencia_del_contrato (contratos_electronicos)`.

Se ignoran mayúsculas/minúsculas, espacios y guiones comunes, incluidos guiones tipográficos. `ATENEA-582-2025`, `Atenea 582 2025` y `atenea5822025` producen la misma búsqueda. La referencia original se conserva para el informe. No se hacen coincidencias parciales, no se eliminan ceros iniciales ni se busca en los procesos del PAA. Una referencia vacía se rechaza. Si hay dos registros con la misma clave normalizada, la consulta se detiene para revisar la base.

## Mapeo acordado

| Campo del informe | Columna de la base | Tratamiento |
|---|---|---|
| Número del contrato o convenio | `referencia_del_contrato (contratos_electronicos)` | Conservar valor original |
| Contratista o aliado | `proveedor_adjudicado (contratos_electronicos)` | Copiar |
| Nombre del supervisor | `nombre_supervisor (contratos_electronicos)` | Copiar |
| Fecha de terminación | `fecha_de_fin_del_contrato (contratos_electronicos)` | Fecha ISO a día/mes/año |
| Modificaciones | `tipo_modificacion` | Copiar el tipo disponible; no constituye un historial completo |
| Objeto | `descripcion_del_proceso (contratos_electronicos)` | Copiar íntegro |
| Porcentaje de avance | `porc_ejecucion_financiera` | Copiar el valor original, sin transformar su escala; el campo permanece revisable |
| Enlace del proceso | `urlproceso (contratos_electronicos)` | Mostrar enlace y validar el identificador `noticeUID` |
| Identificador contractual | `id_contrato` | Buscar archivos públicos asociados al contrato |
| Documento del proveedor | `documento_proveedor (contratos_electronicos)` | Elegir la fila del proveedor en la ficha del proceso |

Nombre identitario, cargo del supervisor, periodo, fecha de presentación, seguridad social y fecha de publicación en SECOP no se infieren todavía. Se completan manualmente o mediante módulos posteriores. Un valor vacío en modificaciones no significa que no existan modificaciones.

El porcentaje de avance se toma de la ejecución financiera. La aplicación conserva el valor original de SECOP, incluida su separación decimal, y no lo multiplica ni le agrega el símbolo `%`.

## Conexión automática a Oracle

El PAR se configura como `ORACLE_PAR_URL` en los Secrets de Streamlit. Nunca se escribe en el repositorio, la interfaz, los mensajes de error ni la trazabilidad. Solo se aceptan enlaces HTTPS del Object Storage de Oracle en Ashburn. La descarga tiene un límite de 50 MB y un tiempo de espera definido.

Cuando Oracle responde con un error HTTP, falla la red, la respuesta está vacía o el archivo no tiene el esquema esperado, la interfaz indica que se debe revisar e ingresar un PAR nuevo en `ORACLE_PAR_URL`. El mensaje muestra el tipo general de problema, sin incluir el enlace firmado.

## Uso

1. Escriba el número del proceso.
2. Pulse **Consultar proceso** para usar Oracle. Si la conexión no está configurada o falla, cargue una exportación `.xlsx` o `.csv` como respaldo; la carga manual tiene prioridad. El Excel debe contener la hoja `tabla_maestra_completa`; el CSV debe usar UTF-8 y coma, punto y coma o tabulación.
3. Revise el registro encontrado. Si la base informa el enlace y el identificador contractual, la aplicación localiza la minuta en `SECOP II - Archivos Descarga Desde 2025`, la descarga desde el repositorio público y consulta `SECOP II - Procesos de Contratación` para generar una ficha del proceso. Puede abrir el proceso y descargar los dos PDF desde este panel.
4. Si dispone de archivos, cargue las evidencias. También puede cargar manualmente una minuta para extraer obligaciones. Ambas cargas son opcionales. Pulse **Preparar borrador**.
5. Revise los campos y continúe con la generación del informe. En esta versión, los dos PDF recuperados desde SECOP no se incorporan automáticamente al borrador.

Los datos disponibles de la base tienen prioridad sobre la extracción de la minuta; las diferencias se muestran para revisión. Si el número contractual de la minuta no coincide con el consultado, se bloquea la combinación. Cambiar la base, el proceso o el resultado invalida el borrador anterior.

La trazabilidad incluye archivo, hoja, fila, columna y huella SHA-256. El archivo cargado se procesa en memoria de la sesión y no se publica ni se guarda en GitHub. Límites: 50 MB por archivo, 250 MB descomprimidos para Excel y 200.000 registros.

La conexión reutiliza el mismo lector y mapeo validados con el Excel de ejemplo. El ejemplo suministrado no forma parte del repositorio.

El portal web público puede exigir reCAPTCHA a consultas automatizadas. Por eso la aplicación usa los conjuntos oficiales de Datos Abiertos `dmgg-8hin` y `p6dx-8zbt`; la ficha descargable indica claramente que fue generada a partir de esos datos y no que sea una impresión del portal.


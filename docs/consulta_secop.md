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
| Porcentaje de avance | `porc_avanceplazo_inferido` | Mapeado, pendiente de confirmar escala; se muestra el valor original y el campo permanece revisable |

Nombre identitario, cargo del supervisor, periodo, fecha de presentación, seguridad social y fecha de publicación en SECOP no se infieren todavía. Se completan manualmente o mediante módulos posteriores. Un valor vacío en modificaciones no significa que no existan modificaciones.

La columna de avance corresponde al plazo; no debe confundirse con `porc_ejecucion_financiera`. La escala debe confirmarse antes de convertir valores como 1000 a porcentaje.

## Uso provisional

1. Escriba el número del proceso.
2. Cargue una exportación `.xlsx` o `.csv` y pulse **Consultar proceso**. El Excel debe contener la hoja `tabla_maestra_completa`; el CSV debe usar UTF-8 y coma, punto y coma o tabulación.
3. Revise el registro encontrado y sus datos faltantes.
4. Cargue las evidencias y, si dispone de ella, la minuta para extraer obligaciones. Pulse **Preparar borrador**.
5. Revise los campos y continúe con la generación del informe.

Los datos disponibles de la base tienen prioridad sobre la extracción de la minuta; las diferencias se muestran para revisión. Si el número contractual de la minuta no coincide con el consultado, se bloquea la combinación. Cambiar la base, el proceso o el resultado invalida el borrador anterior.

La trazabilidad incluye archivo, hoja, fila, columna y huella SHA-256. El archivo cargado se procesa en memoria de la sesión y no se publica ni se guarda en GitHub. Límites: 50 MB por archivo, 250 MB descomprimidos para Excel y 200.000 registros.

La conexión automática a Oracle sigue pendiente del restablecimiento del enlace y la validación del esquema real del CSV. No hay credenciales incorporadas al código. El ejemplo suministrado no forma parte del repositorio.

# Posmedia IA Codex

Base modular en Streamlit para preparar el Formato de informe de ejecución y supervisión de ATENEA.
El usuario indica el número de proceso, puede cargar evidencias PDF o ZIP con PDF, revisa los datos y descarga un Word diligenciado.

## Estado de la versión 0.3

- La carga de evidencias es opcional. Cuando se aportan archivos, funciona su lectura, revisión y asociación con las obligaciones. Sin archivos, el Word indica `Sin evidencia asociada`.
- El número del proceso se busca en `referencia_del_contrato (contratos_electronicos)` del CSV de Oracle. La consulta ignora mayúsculas, espacios y guiones; conserva la referencia original y detecta duplicados. La carga manual de Excel o CSV funciona como respaldo. La descarga de la minuta sigue pendiente.
- La base completa número contractual, contratista, supervisor, fecha de terminación, modificaciones y objeto según el [mapeo acordado](docs/consulta_secop.md). El avance de plazo queda pendiente de confirmar su escala.
- Las actividades y su relación con las evidencias se ingresan y revisan manualmente. No hay evaluación automática de cumplimiento, OCR, modelos de IA ni firma automática.
- Sin minuta es posible ingresar manualmente los campos y obligaciones. Sin obligaciones no se genera el Word.
- Los datos no localizados quedan indicados como pendientes. Los campos de decisión del supervisor quedan vacíos.

## Ejecutar

Requiere Python 3.11 o posterior.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Estos comandos son para Windows. En macOS/Linux active el entorno con `source .venv/bin/activate`.
Para probar: `python -m unittest discover -s tests -v`.
En Streamlit Community Cloud seleccione este repositorio, la rama `main` y `app.py` como archivo de entrada.

Configure el enlace PAR en los Secrets de la aplicación, sin comitearlo:

```toml
ORACLE_PAR_URL = "https://objectstorage.../tabla_maestra_completa.csv"
```

Si el PAR vence o falla la conexión, la aplicación pide reemplazar `ORACLE_PAR_URL` y permite cargar una exportación manual.

## Organización

```text
app.py
requirements.txt
.streamlit/config.toml
templates/Plantilla_maestra_informe_supervision_ATENEA_posmedia.docx
src/config.py
src/models.py
src/integrations/secop_lookup.py
src/integrations/secop_ui.py
src/extraction/pdf_reader.py
src/extraction/contract_fields.py
src/extraction/obligations.py
src/generation/word_report.py
src/generation/audit.py
src/processing/pipeline.py
src/processing/batch.py
tests/test_contract_fields.py
tests/test_obligations.py
tests/test_word_report.py
tests/test_pipeline.py
tests/test_secop_lookup.py
tests/test_app.py
tests/fixtures/
docs/guia_usuario.md
docs/reglas_extraccion.md
docs/hoja_de_ruta.md
docs/origenes.md
docs/consulta_secop.md
docs/validacion.md
```

Los paquetes incluyen `__init__.py`. Las evidencias se procesan en memoria y no se guardan en el repositorio. No suba contratos reales, datos personales ni claves. La configuración del servicio de alojamiento debe revisarse antes de usar información real.

La plantilla fuente se conserva sin cambios, con el nombre solicitado. El generador reemplaza sus datos de ejemplo en una copia y conserva el paquete Word, incluidos encabezados y pies de página.

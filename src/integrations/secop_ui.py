"""Controles de consulta y revisión de la base contractual cargada."""
import hashlib
import streamlit as st
from src.config import NOT_FOUND
from src.integrations.secop_documents import notice_uid, prepare_secop_documents, SecopDocumentError
from src.integrations.secop_lookup import lookup_oracle, normalize_reference
from src.processing.pipeline import extract_minute


@st.cache_data(ttl=300, show_spinner=False)
def cached_secop_documents(process_url, contract_id, reference, provider_document, provider_name):
    return prepare_secop_documents(
        process_url, contract_id, reference, provider_document, provider_name,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_minute_extraction(name, data):
    return extract_minute(name, data)


def configured_par():
    try:
        return str(st.secrets.get('ORACLE_PAR_URL', '')).strip()
    except Exception:
        return ''


def lookup_panel(process):
    st.caption('La búsqueda admite mayúsculas, minúsculas, espacios y guiones. Ejemplo: Atenea 582 2025.')
    with st.expander('Consultar datos de la base contractual', expanded=True):
        configured_url = configured_par()
        par_override = st.text_input(
            'Actualizar ruta PAR al archivo',
            type='password',
            key='oracle_par_override',
            placeholder='https://objectstorage.us-ashburn-1.oraclecloud.com/p/...',
            help=(
                'Pegue aquí un PAR nuevo cuando el enlace configurado haya vencido. '
                'Se utilizará durante esta sesión y no se incluirá en la trazabilidad.'
            ),
        ).strip()
        par_url = par_override or configured_url
        if par_override:
            st.info('Se usará el PAR ingresado en esta sesión.')
        elif configured_url:
            st.info('La consulta automática a Oracle está configurada. Puede ingresar arriba un PAR nuevo para reemplazarla durante esta sesión.')
        else:
            st.warning('La conexión automática no está configurada. Ingrese un PAR válido para consultar la base de Oracle.')
        par_digest = hashlib.sha256(par_url.encode()).hexdigest() if par_url else ''
        source_token = ('oracle', par_digest)
        token = (normalize_reference(process), source_token)
        if st.session_state.get('secop_token') != token:
            st.session_state.pop('secop_result', None)
            st.session_state.pop('secop_documents', None)
            st.session_state.pop('secop_documents_error', None)
            st.session_state.pop('secop_minute_extraction', None)
            st.session_state.pop('secop_minute_extraction_error', None)
            st.session_state['secop_token'] = token
        if st.button('Consultar proceso', key='consultar_secop'):
            st.session_state.pop('secop_result', None)
            st.session_state.pop('secop_documents', None)
            st.session_state.pop('secop_documents_error', None)
            st.session_state.pop('secop_minute_extraction', None)
            st.session_state.pop('secop_minute_extraction_error', None)
            try:
                with st.spinner('Buscando la referencia contractual…'):
                    if par_url:
                        result = lookup_oracle(par_url, process)
                    else:
                        result = None
                        st.warning('Ingrese un PAR válido antes de consultar.')
                if result is None and par_url:
                    st.warning('No se encontró esa referencia en la base consultada.')
                elif result is not None:
                    st.session_state['secop_result'] = result
                    if result.process_url and result.contract_id:
                        provider = result.fields.get('nombre_contratista_asociado')
                        provider_name = provider.value if provider and provider.value != NOT_FOUND else ''
                        try:
                            with st.spinner('Localizando la minuta y la ficha del proceso en SECOP…'):
                                documents = cached_secop_documents(
                                    result.process_url, result.contract_id, result.reference,
                                    result.provider_document, provider_name,
                                )
                            st.session_state['secop_documents'] = documents
                            if documents.minute_pdf:
                                try:
                                    with st.spinner('Extrayendo información de la minuta…'):
                                        st.session_state['secop_minute_extraction'] = cached_minute_extraction(
                                            documents.minute_name, documents.minute_pdf,
                                        )
                                except ValueError as error:
                                    st.session_state['secop_minute_extraction_error'] = str(error)
                        except SecopDocumentError as error:
                            st.session_state['secop_documents_error'] = str(error)
            except Exception as error:
                st.error(str(error))
        result = st.session_state.get('secop_result')
        if result:
            st.success('Contrato encontrado: ' + result.reference)
            st.dataframe([{'Campo del informe': key.replace('_', ' '), 'Valor': field.value}
                          for key, field in result.fields.items()], hide_index=True)
            st.caption('Fuente: ' + result.source + ' · fila ' + str(result.row_number))
            if result.process_url:
                try:
                    notice_uid(result.process_url)
                    st.link_button('Abrir proceso en SECOP II', result.process_url)
                except SecopDocumentError:
                    st.warning('La base contiene un enlace de proceso SECOP no válido.')
            documents = st.session_state.get('secop_documents')
            if documents:
                if documents.minute_pdf and documents.process_pdf:
                    st.success('La minuta oficial y la ficha del proceso están disponibles para descarga.')
                elif documents.minute_pdf:
                    st.success('La minuta oficial está disponible para descarga.')
                if documents.minute_pdf:
                    st.download_button(
                        'Descargar minuta oficial (PDF)', documents.minute_pdf,
                        file_name=documents.minute_name, mime='application/pdf',
                        key='descargar_minuta_secop',
                    )
                if documents.process_pdf:
                    st.download_button(
                        'Descargar ficha del proceso SECOP (PDF)', documents.process_pdf,
                        file_name=documents.process_name, mime='application/pdf',
                        key='descargar_ficha_secop',
                    )
                    st.caption(
                        'La ficha se genera con Datos Abiertos de SECOP II para el proceso '
                        + documents.process_reference + '.'
                    )
                archive_bytes = getattr(documents, 'archive_bytes', b'')
                if archive_bytes:
                    st.download_button(
                        'Descargar todos los documentos SECOP (ZIP)', archive_bytes,
                        file_name=getattr(documents, 'archive_name', 'Documentos_SECOP.zip'),
                        mime='application/zip',
                        key='descargar_documentos_secop_zip',
                    )
                    st.caption(
                        f"El ZIP contiene {getattr(documents, 'archive_count', 0)} documentos descargados y un inventario CSV. "
                        'Se conserva como insumo para las siguientes etapas de análisis.'
                    )
                    with st.expander('Ver inventario de documentos SECOP'):
                        st.dataframe([
                            {
                                'Documento': item['nombre_archivo'],
                                'Tipo': item['extension'].upper(),
                                'Tamaño': f"{item['tamano_bytes'] / 1024:,.1f} KB",
                                'Fecha de carga': item['fecha_carga'],
                                'Estado': item['estado'],
                            }
                            for item in getattr(documents, 'archive_inventory', [])
                        ], hide_index=True)
                elif not hasattr(documents, 'archive_bytes'):
                    st.info(
                        'La consulta corresponde a una sesión anterior. Pulse “Consultar proceso” '
                        'para generar el ZIP de documentos SECOP.'
                    )
                for warning in documents.warnings:
                    st.warning(warning)
                extraction = st.session_state.get('secop_minute_extraction')
                if extraction:
                    fields, obligations = extraction
                    extracted_rows = [
                        {
                            'Dato extraído': key.replace('_', ' ').capitalize(),
                            'Valor': field.value,
                            'Fuente': field.source,
                            'Confianza': field.confidence,
                        }
                        for key, field in fields.items()
                        if field.value != NOT_FOUND and field.source.startswith(documents.minute_name + ' · Página')
                    ]
                    st.markdown('**Información extraída de la minuta**')
                    if extracted_rows:
                        st.dataframe(extracted_rows, hide_index=True)
                    if obligations:
                        st.markdown('**Obligaciones específicas extraídas**')
                        st.dataframe([
                            {
                                'Número': index,
                                'Obligación específica': obligation.value.split('. ', 1)[-1],
                                'Fuente': obligation.source,
                            }
                            for index, obligation in enumerate(obligations, 1)
                        ], hide_index=True)
                        st.caption(
                            f'Se extrajeron {len(obligations)} obligaciones. Se incorporarán al borrador '
                            'cuando pulse “Preparar borrador”.'
                        )
                    else:
                        st.warning('La minuta fue leída, pero no se identificaron obligaciones específicas de la IES.')
                extraction_error = st.session_state.get('secop_minute_extraction_error')
                if extraction_error:
                    st.warning('La minuta se descargó, pero no fue posible extraer su texto: ' + extraction_error)
            document_error = st.session_state.get('secop_documents_error')
            if document_error:
                st.warning(document_error)
            for warning in result.warnings:
                st.warning(warning)
    # El token también invalida borradores al cambiar la base, aunque no se consulte.
    return result, repr(token), st.session_state.get('secop_documents')

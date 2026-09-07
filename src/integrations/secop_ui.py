"""Controles de consulta y revisión de la base contractual cargada."""
import hashlib
import streamlit as st
from src.integrations.secop_lookup import lookup_file, lookup_oracle, normalize_reference


def configured_par():
    try:
        return str(st.secrets.get('ORACLE_PAR_URL', '')).strip()
    except Exception:
        return ''


def lookup_panel(process):
    st.caption('La búsqueda admite mayúsculas, minúsculas, espacios y guiones. Ejemplo: Atenea 582 2025.')
    with st.expander('Consultar datos de la base contractual', expanded=True):
        par_url = configured_par()
        if par_url:
            st.info('La consulta automática a Oracle está configurada. Si falla, puede cargar una base manual como respaldo.')
        else:
            st.warning('La conexión automática no está configurada. Ingresa el PAR en Secrets de Streamlit con el nombre ORACLE_PAR_URL o carga una base manual.')
        upload = st.file_uploader('Base contractual de respaldo (Excel o CSV, opcional)', type=['xlsx', 'csv'], key='secop_base')
        digest = hashlib.sha256(upload.getvalue()).hexdigest() if upload else ''
        par_digest = hashlib.sha256(par_url.encode()).hexdigest() if par_url else ''
        source_token = ('manual', upload.name, digest) if upload else ('oracle', par_digest)
        token = (normalize_reference(process), source_token)
        if st.session_state.get('secop_token') != token:
            st.session_state.pop('secop_result', None)
            st.session_state['secop_token'] = token
        if st.button('Consultar proceso', key='consultar_secop'):
            st.session_state.pop('secop_result', None)
            try:
                with st.spinner('Buscando la referencia contractual…'):
                    if upload:
                        result = lookup_file(upload.name, upload.getvalue(), process)
                    elif par_url:
                        result = lookup_oracle(par_url, process)
                    else:
                        result = None
                        st.warning('Configura ORACLE_PAR_URL o carga una base contractual de respaldo.')
                if result is None and (upload or par_url):
                    st.warning('No se encontró esa referencia en la base consultada.')
                elif result is not None:
                    st.session_state['secop_result'] = result
            except Exception as error:
                st.error(str(error))
        result = st.session_state.get('secop_result')
        if result:
            st.success('Contrato encontrado: ' + result.reference)
            st.dataframe([{'Campo del informe': key.replace('_', ' '), 'Valor': field.value}
                          for key, field in result.fields.items()], hide_index=True)
            st.caption('Fuente: ' + result.source + ' · fila ' + str(result.row_number))
            for warning in result.warnings:
                st.warning(warning)
    # El token también invalida borradores al cambiar la base, aunque no se consulte.
    return result, repr(token)

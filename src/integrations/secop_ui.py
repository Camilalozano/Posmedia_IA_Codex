"""Controles de consulta y revisión de la base contractual cargada."""
import hashlib
import streamlit as st
from src.integrations.secop_lookup import lookup_file, normalize_reference


def lookup_panel(process):
    st.caption('La búsqueda admite mayúsculas, minúsculas, espacios y guiones. Ejemplo: Atenea 582 2025.')
    with st.expander('Consultar datos de la base contractual', expanded=True):
        st.info('Mientras se restablece Oracle, cargue una exportación Excel o CSV para consultar el número del proceso.')
        upload = st.file_uploader('Base contractual SECOP (Excel o CSV)', type=['xlsx', 'csv'], key='secop_base')
        digest = hashlib.sha256(upload.getvalue()).hexdigest() if upload else ''
        token = (normalize_reference(process), upload.name if upload else '', digest)
        if st.session_state.get('secop_token') != token:
            st.session_state.pop('secop_result', None)
            st.session_state['secop_token'] = token
        if st.button('Consultar proceso', key='consultar_secop'):
            st.session_state.pop('secop_result', None)
            if not upload:
                st.warning('Cargue la base contractual para realizar la consulta.')
            else:
                try:
                    with st.spinner('Buscando la referencia contractual…'):
                        result = lookup_file(upload.name, upload.getvalue(), process)
                    if result is None:
                        st.warning('No se encontró esa referencia en la base cargada.')
                    else:
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

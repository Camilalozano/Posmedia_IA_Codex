"""Interfaz de revisión y generación de informes de ejecución y supervisión."""
import hashlib
import re
import streamlit as st
from src.config import NOT_FOUND
from src.models import Field
from src.processing.pipeline import prepare_report
from src.generation.word_report import build_docx, MAPPING
from src.generation.audit import audit_json
from src.integrations.secop_ui import lookup_panel

ADDITIONAL_FIELDS = {
    'tipo_instrumento': 'Tipo de instrumento',
    'nit_contratista': 'NIT del contratista o asociado',
    'representante_legal': 'Representante legal',
    'identificacion_representante': 'Identificación del representante legal',
    'fecha_suscripcion': 'Fecha de suscripción',
    'fecha_inicio': 'Fecha de inicio',
    'plazo': 'Plazo indicado en la minuta',
    'lugar_ejecucion': 'Lugar de ejecución',
    'valor_total': 'Valor estimado del convenio',
    'aporte_atenea': 'Aporte de ATENEA',
    'aporte_contraparte': 'Aporte de la IES o contraparte',
}

def main():
    st.set_page_config(page_title='Posmedia IA Codex', page_icon='📄', layout='wide')
    st.title('Informe de ejecución y supervisión')
    st.caption('Posmedia · ATENEA · Consulta de base contractual')
    process = st.text_input('Número del proceso', placeholder='ATENEA-582-2025')
    lookup, lookup_token, secop_documents = lookup_panel(process)
    contract = st.file_uploader('Minuta o convenio (opcional)', type=['pdf'], key='minuta')
    automatic_contract = None
    if not contract and secop_documents and secop_documents.minute_pdf:
        automatic_contract = (secop_documents.minute_name, secop_documents.minute_pdf)
        st.caption('Se usará automáticamente la minuta descargada de SECOP para preparar el borrador.')
    selected_contract = (contract.name, contract.getvalue()) if contract else automatic_contract
    uploads = st.file_uploader('Evidencias del periodo (opcional)', type=['pdf', 'zip'], accept_multiple_files=True, key='evidencias')
    signature = hashlib.sha256()
    signature.update(process.encode())
    signature.update(lookup_token.encode())
    signature.update(repr(lookup).encode())
    if selected_contract:
        signature.update(selected_contract[0].encode())
        signature.update(selected_contract[1])
    for upload in list(uploads or []):
        signature.update(upload.name.encode())
        signature.update(upload.getvalue())
    fingerprint = signature.hexdigest()
    if st.session_state.get('fingerprint') != fingerprint:
        st.session_state.pop('report', None)
        st.session_state.pop('output', None)
    if st.button('Preparar borrador', type='primary'):
        try:
            report = prepare_report(process, selected_contract,
                                    [(f.name, f.getvalue()) for f in uploads or []], lookup=lookup)
            st.session_state['report'] = report
            st.session_state['fingerprint'] = fingerprint
            st.session_state.pop('output', None)
        except Exception as error:
            st.error(str(error))
    report = st.session_state.get('report')
    if report is None:
        return
    for warning in report.warnings:
        st.warning(warning)
    if report.evidence:
        st.subheader('Evidencias recibidas')
        st.dataframe([{'ID': e.id, 'Archivo': e.name, 'Páginas': len(e.pages), 'Estado': e.status} for e in report.evidence], hide_index=True)
        with st.expander('Consultar el texto extraído de las evidencias'):
            for evidence in report.evidence:
                st.write(evidence.id + ' · ' + evidence.name)
                for page_number, page in enumerate(evidence.pages, 1):
                    st.text('Página ' + str(page_number) + '\n' + page)
    st.subheader('Revisar datos del informe')
    st.caption('El número del proceso se busca en la referencia contractual. Revise los datos antes de generar el informe.')
    for key in MAPPING.values():
        original = report.fields.get(key, Field())
        value = st.text_area(key.replace('_', ' ').capitalize(), value=original.value,
                             key=fingerprint + key)
        if value != original.value:
            report.fields[key] = Field(value, 'Ingresado o corregido por el usuario', 'por verificar')
    additional = [(key, label, report.fields.get(key, Field())) for key, label in ADDITIONAL_FIELDS.items()]
    additional = [(key, label, field) for key, label, field in additional if field.value != NOT_FOUND]
    if additional:
        with st.expander('Información adicional extraída de la minuta'):
            st.caption('Estos datos no tienen una celda asignada en la plantilla actual, pero quedan disponibles en la trazabilidad.')
            for key, label, original in additional:
                value = st.text_input(label, value=original.value, key=fingerprint + 'additional_' + key)
                st.caption('Fuente: ' + original.source)
                if value != original.value:
                    report.fields[key] = Field(value, 'Ingresado o corregido por el usuario', 'por verificar')
    raw = st.text_area('Obligaciones (una por línea; puede corregir o completar la extracción)',
                       value='\n'.join(o.value for o in report.obligations), key=fingerprint + 'obligaciones')
    old = {o.value: o for o in report.obligations}
    report.obligations = [old.get(line.strip(), Field(line.strip(), 'Ingresado por el usuario', 'por verificar'))
                          for line in raw.splitlines() if line.strip()]
    report.activities, report.links = {}, {}
    labels = {e.id: e.id + ' · ' + e.name for e in report.evidence}
    for index, obligation in enumerate(report.obligations):
        oid = hashlib.sha256(obligation.value.encode()).hexdigest()[:16]
        with st.expander(obligation.value[:140]):
            st.write(obligation.value)
            report.activities[index] = st.text_area('Actividades realizadas durante el periodo', key=fingerprint + oid + str(index) + 'act')
            if labels:
                report.links[index] = st.multiselect('Evidencias que respaldan estas actividades', list(labels),
                                                     format_func=labels.get, key=fingerprint + oid + str(index) + 'ev')
            else:
                report.links[index] = []
                st.caption('Sin evidencias cargadas para asociar.')
    st.caption('Las asociaciones son declaradas por quien prepara el informe. Los campos de cumplimiento y firma quedan para el supervisor.')
    state = hashlib.sha256(audit_json(report)).hexdigest()
    if st.session_state.get('output_state') != state:
        st.session_state.pop('output', None)
    if st.button('Generar informe Word'):
        try:
            st.session_state['output'] = build_docx(report)
            st.session_state['output_state'] = state
        except Exception as error:
            st.error(str(error))
    if 'output' in st.session_state:
        name = re.sub(r'[^A-Za-z0-9_-]', '_', process)[:80]
        st.download_button('Descargar informe diligenciado', st.session_state['output'],
                           'Informe_ejecucion_supervision_' + name + '.docx',
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        st.download_button('Descargar trazabilidad', audit_json(report), 'Trazabilidad_' + name + '.json', 'application/json')

if __name__ == '__main__':
    main()

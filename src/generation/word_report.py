"""Diligencia una copia del formato suministrado, preservando el paquete Word."""
import io
import zipfile
from copy import deepcopy
from lxml import etree as ET
from src.config import MASTER, NOT_FOUND

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MAPPING = {0: 'numero_contrato_convenio', 1: 'nombre_contratista_asociado',
           2: 'nombre_identitario', 3: 'nombre_supervisor', 4: 'cargo_supervisor',
           5: 'fecha_terminacion', 6: 'modificaciones', 7: 'periodo_informe',
           8: 'fecha_presentacion', 9: 'seguridad_social', 10: 'porcentaje_avance',
           11: 'fecha_publicacion_secop', 13: 'objeto'}

def set_cell(cell, text):
    p = cell.find(W + 'p')
    p = deepcopy(p) if p is not None else ET.Element(W + 'p')
    run = p.find(W + 'r')
    properties = deepcopy(run.find(W + 'rPr')) if run is not None and run.find(W + 'rPr') is not None else None
    for child in list(cell):
        if child.tag != W + 'tcPr':
            cell.remove(child)
    for child in list(p):
        if child.tag != W + 'pPr':
            p.remove(child)
    run = ET.SubElement(p, W + 'r')
    if properties is not None:
        run.append(properties)
    for index, line in enumerate(str(text).split('\n')):
        if index:
            ET.SubElement(run, W + 'br')
        node = ET.SubElement(run, W + 't')
        node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        node.text = line
    cell.append(p)

def build_docx(report, master=MASTER):
    if not report.obligations:
        raise ValueError('Agregue y revise las obligaciones antes de generar el informe.')
    with zipfile.ZipFile(master) as source:
        files = {name: source.read(name) for name in source.namelist()}
    root = ET.fromstring(files['word/document.xml'])
    tables = root.findall('.//' + W + 'tbl')
    if len(tables) != 3 or len(tables[0].findall(W + 'tr')) != 14:
        raise ValueError('La estructura de la plantilla cambió; revise el mapeo de celdas.')
    rows = tables[0].findall(W + 'tr')
    for index, key in MAPPING.items():
        value = report.fields.get(key)
        set_cell(rows[index].findall(W + 'tc')[-1], value.value if value and value.value.strip() else NOT_FOUND)
    body_rows = tables[1].findall(W + 'tr')[1:]
    model = deepcopy(body_rows[0])
    for row in body_rows:
        tables[1].remove(row)
    evidence_by_id = {e.id: e for e in report.evidence}
    for index, obligation in enumerate(report.obligations):
        row = deepcopy(model)
        cells = row.findall(W + 'tc')
        refs = []
        for eid in report.links.get(index, []):
            if eid not in evidence_by_id:
                raise ValueError('Referencia de evidencia desconocida: ' + eid)
            evidence = evidence_by_id[eid]
            refs.append(eid + ' · ' + evidence.name + ' · ' + evidence.status)
        set_cell(cells[0], obligation.value)
        set_cell(cells[1], report.activities.get(index, '').strip() or 'Pendiente de documentar actividades del periodo')
        set_cell(cells[2], '\n'.join(refs) or 'Sin evidencia asociada')
        # Evita recortes por altura fija heredada del ejemplo.
        for height in row.findall('.//' + W + 'trHeight'):
            height.getparent().remove(height)
        tables[1].append(row)
    for row in tables[2].findall(W + 'tr')[2:]:
        for cell in row.findall(W + 'tc')[1:]:
            set_cell(cell, '')
    files['word/document.xml'] = ET.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as target:
        for name, data in files.items():
            target.writestr(name, data)
    return out.getvalue()

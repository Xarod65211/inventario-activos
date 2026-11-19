"""QR, acta de entrega en PDF y libro Excel."""
from io import BytesIO

import qrcode
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

MARINO = '#172a46'


def qr_png(texto, tamano=8):
    img = qrcode.make(texto, box_size=tamano, border=2)
    salida = BytesIO()
    img.save(salida, format='PNG')
    return salida.getvalue()


def acta_pdf(movimiento, empresa):
    a = movimiento.activo
    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f'Acta {a.codigo}')
    est = getSampleStyleSheet()
    est['Title'].textColor = colors.HexColor(MARINO)
    titulo = 'Acta de entrega de activo' if movimiento.tipo == 'asignacion' else f'Acta de {movimiento.get_tipo_display().lower()} de activo'
    datos = [
        ['Código', a.codigo, 'Categoría', a.categoria.nombre],
        ['Activo', a.nombre, 'Serie', a.serie or 'Sin serie'],
        ['Marca y modelo', f'{a.marca} {a.modelo}'.strip() or 'Sin dato', 'Ubicación', str(movimiento.ubicacion_nueva or '')],
        ['Fecha', movimiento.fecha.strftime('%d/%m/%Y %H:%M'), 'Registró', movimiento.usuario.get_full_name() or movimiento.usuario.username],
    ]
    persona = movimiento.responsable_nuevo or movimiento.responsable_anterior
    tabla = Table(datos, colWidths=[3.2 * cm, 5.3 * cm, 2.8 * cm, 5.3 * cm])
    tabla.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f1f5f9')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    firmas = Table([['_' * 32, '_' * 32], [persona.nombre if persona else '', 'Encargado de activos'],
                    [f'Documento {persona.documento}' if persona else '', '']], colWidths=[8.3 * cm, 8.3 * cm])
    firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0, 0), (-1, -1), 9)]))
    texto = ('La persona que firma recibe el activo descrito, en buen estado, y se compromete a usarlo solo para su trabajo '
             'y a devolverlo cuando se le solicite.') if movimiento.tipo == 'asignacion' else (movimiento.observacion or '')
    doc.build([
        Paragraph(titulo, est['Title']),
        Paragraph(empresa, est['Normal']),
        Spacer(1, 0.6 * cm),
        tabla,
        Spacer(1, 0.6 * cm),
        Paragraph(texto, est['Normal']),
        Spacer(1, 2.5 * cm),
        firmas,
    ])
    return salida.getvalue()


def libro_activos(activos):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Activos'
    encabezado = ['Código', 'Nombre', 'Categoría', 'Marca', 'Modelo', 'Serie', 'Ubicación', 'Responsable', 'Estado',
                  'Fecha de compra', 'Valor de compra', 'Depreciación acumulada', 'Valor neto']
    ws.append(encabezado)
    for celda in ws[1]:
        celda.font = Font(bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', fgColor='172A46')
    for a in activos:
        d = a.depreciacion()
        ws.append([a.codigo, a.nombre, a.categoria.nombre, a.marca, a.modelo, a.serie, a.ubicacion.nombre,
                   a.responsable.nombre if a.responsable else '', a.get_estado_display(), a.fecha_compra,
                   float(a.valor_compra), float(d['acumulada']), float(d['neto'])])
    for col, ancho in zip('ABCDEFGHIJKLM', [11, 34, 18, 14, 14, 16, 18, 26, 16, 14, 14, 14, 14]):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = 'A2'
    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()

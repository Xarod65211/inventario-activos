"""Importa activos desde Excel. Primero se simula: nada se guarda si hay una sola fila con error."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from openpyxl import load_workbook

from .models import Activo, Categoria, Movimiento, Ubicacion

COLUMNAS = ['Nombre', 'Categoría', 'Marca', 'Modelo', 'Serie', 'Ubicación', 'Fecha de compra', 'Valor de compra']


def leer(archivo):
    hoja = load_workbook(archivo, read_only=True, data_only=True).active
    filas = list(hoja.iter_rows(values_only=True))
    if not filas:
        return [], ['El archivo está vacío.']
    encabezado = [str(c).strip() if c is not None else '' for c in filas[0]]
    faltan = [c for c in COLUMNAS if c not in encabezado]
    if faltan:
        return [], [f'Faltan columnas: {", ".join(faltan)}.']
    idx = {c: encabezado.index(c) for c in COLUMNAS}
    return [(n, {c: fila[idx[c]] for c in COLUMNAS}) for n, fila in enumerate(filas[1:], start=2) if any(v not in (None, '') for v in fila)], []


def revisar(archivo):
    filas, errores = leer(archivo)
    if errores:
        return {'filas': [], 'errores_generales': errores, 'validas': 0}
    categorias = {c.nombre.lower(): c for c in Categoria.objects.all()}
    ubicaciones = {u.nombre.lower(): u for u in Ubicacion.objects.all()}
    series = set(Activo.objects.exclude(serie='').values_list('serie', flat=True))
    resultado, vistas = [], set()
    for n, f in filas:
        problemas = []
        nombre = str(f['Nombre'] or '').strip()
        if not nombre:
            problemas.append('Falta el nombre')
        cat = categorias.get(str(f['Categoría'] or '').strip().lower())
        if not cat:
            problemas.append(f'Categoría desconocida: {f["Categoría"]}')
        ubi = ubicaciones.get(str(f['Ubicación'] or '').strip().lower())
        if not ubi:
            problemas.append(f'Ubicación desconocida: {f["Ubicación"]}')
        serie = str(f['Serie'] or '').strip()
        if serie and (serie in series or serie in vistas):
            problemas.append(f'La serie {serie} ya existe')
        vistas.add(serie)
        fecha = f['Fecha de compra']
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        elif isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha.strip(), '%d/%m/%Y').date()
            except ValueError:
                fecha = None
        if not isinstance(fecha, date) or fecha > date.today():
            problemas.append('Fecha de compra inválida (use dd/mm/aaaa)')
        try:
            valor = Decimal(str(f['Valor de compra']).replace(',', '.'))
            if valor <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            valor = None
            problemas.append('Valor de compra inválido')
        resultado.append({'fila': n, 'nombre': nombre, 'serie': serie, 'problemas': problemas,
                          'datos': {'nombre': nombre, 'categoria': cat, 'ubicacion': ubi, 'serie': serie, 'fecha_compra': fecha,
                                    'valor_compra': valor, 'marca': str(f['Marca'] or '').strip(), 'modelo': str(f['Modelo'] or '').strip()}})
    return {'filas': resultado, 'errores_generales': [], 'validas': sum(1 for r in resultado if not r['problemas'])}


@transaction.atomic
def importar(revision, usuario):
    if revision['errores_generales'] or any(r['problemas'] for r in revision['filas']):
        return 0
    for r in revision['filas']:
        activo = Activo.objects.create(**r['datos'])
        Movimiento.objects.create(activo=activo, tipo='alta', usuario=usuario, fecha=activo.creado,
                                  ubicacion_nueva=activo.ubicacion, observacion='Importado desde Excel')
    return len(revision['filas'])

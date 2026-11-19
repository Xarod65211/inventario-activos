"""Carga datos de demostración inventados. Uso: python manage.py datos_demo"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventario.models import Activo, Categoria, Mantenimiento, Movimiento, Responsable, Ubicacion
from inventario.servicios import registrar_movimiento


class Command(BaseCommand):
    help = 'Carga usuarios, categorías y 60 activos ficticios'

    @transaction.atomic
    def handle(self, *args, **opciones):
        if User.objects.exists():
            self.stdout.write('Ya hay datos: no se cargó nada.')
            return
        usuarios = {}
        for nombre, rol, completo in [('admin', 'admin', 'Ana Rojas'), ('tecnico', 'tecnico', 'Hugo Alanoca'), ('consulta', 'consulta', 'Paola Ortiz')]:
            u = User.objects.create_user(nombre, password='demo1234', first_name=completo.split()[0], last_name=completo.split()[1])
            u.groups.add(Group.objects.get_or_create(name=rol)[0])
            usuarios[rol] = u
        tec = usuarios['tecnico']

        cats = {n: Categoria.objects.create(nombre=n, prefijo=p, vida_util_anios=v, meses_entre_mantenimientos=m) for n, p, v, m in [
            ('Equipo de computación', 'COMP', 4, 6), ('Mobiliario', 'MOB', 10, 24), ('Herramientas', 'HER', 5, 12),
            ('Equipo de laboratorio', 'LAB', 8, 6), ('Vehículos', 'VEH', 5, 3)]}
        ubis = [Ubicacion.objects.create(nombre=n) for n in ['Oficina central', 'Taller de mantenimiento', 'Almacén', 'Laboratorio', 'Patio de carga']]
        personas = [Responsable.objects.create(nombre=n, documento=str(5200000 + i * 913), cargo=c, area=a) for i, (n, c, a) in enumerate([
            ('Jorge Condori', 'Analista contable', 'Finanzas'), ('María Flores', 'Jefa de compras', 'Compras'), ('Pedro Choque', 'Técnico mecánico', 'Mantenimiento'),
            ('Rosa Huanca', 'Asistente de laboratorio', 'Calidad'), ('Daniel Vargas', 'Encargado de almacén', 'Logística'), ('Lucía Apaza', 'Diseñadora', 'Comercial'),
            ('Marco Ticona', 'Electricista', 'Mantenimiento'), ('Elena Gutiérrez', 'Gerente de área', 'Administración'), ('Sofía Paredes', 'Chofer', 'Logística')])]

        catalogo = [
            ('Equipo de computación', ['Laptop', 'Computadora de escritorio', 'Monitor 24 pulgadas', 'Impresora láser', 'Proyector'], ['Lenovo', 'HP', 'Dell', 'Epson'], (2500, 9000)),
            ('Mobiliario', ['Escritorio en L', 'Silla ergonómica', 'Estante metálico', 'Archivador de 4 cajones'], ['Fabricación local'], (400, 2200)),
            ('Herramientas', ['Taladro percutor', 'Amoladora angular', 'Multímetro digital', 'Compresor portátil'], ['Bosch', 'Makita', 'Fluke'], (600, 4500)),
            ('Equipo de laboratorio', ['Balanza analítica', 'Estufa de secado', 'pHmetro de mesa'], ['Ohaus', 'Memmert', 'Hanna'], (3000, 18000)),
            ('Vehículos', ['Camioneta 4x4', 'Montacargas eléctrico'], ['Toyota', 'Hyster'], (90000, 260000)),
        ]
        hoy = date.today()
        n = 0
        for cat, nombres, marcas, (vmin, vmax) in catalogo:
            for k in range(14 if cat != 'Vehículos' else 4):
                n += 1
                compra = hoy - timedelta(days=60 + (n * 97) % 1800)
                a = Activo.objects.create(
                    nombre=nombres[k % len(nombres)], categoria=cats[cat], marca=marcas[k % len(marcas)], modelo=f'M{100 + n * 7}',
                    serie=f'SN{240000 + n * 131}', ubicacion=ubis[(n + k) % 5], fecha_compra=compra,
                    valor_compra=Decimal(vmin + (n * 7919) % (vmax - vmin)))
                fecha_alta = timezone.make_aware(timezone.datetime.combine(compra, timezone.datetime.min.time())) + timedelta(hours=9)
                Movimiento.objects.create(activo=a, tipo='alta', usuario=tec, fecha=fecha_alta, ubicacion_nueva=a.ubicacion)
                if n % 6:
                    registrar_movimiento(a, 'asignacion', tec, personas[n % len(personas)], fecha=fecha_alta + timedelta(days=2))
                if n % 9 == 0:
                    registrar_movimiento(a, 'traslado', tec, ubicacion=ubis[(n + k + 2) % 5], observacion='Cambio de área', fecha=fecha_alta + timedelta(days=40))
                if n % 13 == 0 and a.responsable:
                    registrar_movimiento(a, 'devolucion', tec, observacion='Devuelto por cambio de puesto', fecha=fecha_alta + timedelta(days=90))
                meses = cats[cat].meses_entre_mantenimientos
                prog = compra + timedelta(days=30 * meses)
                while prog < hoy - timedelta(days=20):
                    Mantenimiento.objects.create(activo=a, tipo='preventivo', programado=prog, realizado=prog + timedelta(days=n % 5),
                                                 descripcion='Mantenimiento preventivo', costo=Decimal(80 + n % 7 * 20), usuario=tec)
                    prog += timedelta(days=30 * meses)
                Mantenimiento.objects.create(activo=a, tipo='preventivo', descripcion='Mantenimiento preventivo',
                                             programado=prog if n % 7 else hoy - timedelta(days=3 + n % 10))
        baja = Activo.objects.filter(categoria=cats['Equipo de computación']).order_by('fecha_compra').first()
        registrar_movimiento(baja, 'baja', tec, observacion='Placa madre dañada, reparación no conviene')
        Activo.objects.filter(pk__in=list(Activo.objects.filter(categoria=cats['Herramientas']).values_list('pk', flat=True)[:2])).update(estado=Activo.MANTENIMIENTO)
        self.stdout.write(self.style.SUCCESS(f'Listo: {Activo.objects.count()} activos, {Movimiento.objects.count()} movimientos, '
                                             f'{Mantenimiento.objects.count()} mantenimientos.'))

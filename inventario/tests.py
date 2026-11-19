from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from .importacion import COLUMNAS
from .models import Activo, Categoria, Mantenimiento, Movimiento, Responsable, Ubicacion
from .servicios import registrar_movimiento


def usuario(nombre, rol):
    u = User.objects.create_user(nombre, password='clave-larga-1')
    u.groups.add(Group.objects.get_or_create(name=rol)[0])
    return u


class Base(TestCase):
    def setUp(self):
        self.tecnico = usuario('tec', 'tecnico')
        self.consulta = usuario('con', 'consulta')
        self.cat = Categoria.objects.create(nombre='Computación', prefijo='COMP', vida_util_anios=4, meses_entre_mantenimientos=6)
        self.ofi = Ubicacion.objects.create(nombre='Oficina')
        self.taller = Ubicacion.objects.create(nombre='Taller')
        self.ana = Responsable.objects.create(nombre='Persona Uno', documento='1', cargo='Analista', area='TI')
        self.activo = Activo.objects.create(nombre='Laptop', categoria=self.cat, ubicacion=self.ofi, serie='S1',
                                            fecha_compra=date.today() - timedelta(days=730), valor_compra=Decimal('4000'))


class ReglasTest(Base):
    def test_codigo_con_prefijo_y_token_aleatorio(self):
        self.assertEqual(self.activo.codigo, 'COMP-0001')
        self.assertNotIn(self.activo.codigo, self.activo.url_publica())

    def test_asignar_devolver_y_trasladar_dejan_historial(self):
        registrar_movimiento(self.activo, 'asignacion', self.tecnico, self.ana)
        registrar_movimiento(self.activo, 'traslado', self.tecnico, ubicacion=self.taller)
        registrar_movimiento(self.activo, 'devolucion', self.tecnico)
        self.activo.refresh_from_db()
        self.assertIsNone(self.activo.responsable)
        self.assertEqual(self.activo.ubicacion, self.taller)
        self.assertEqual(list(Movimiento.objects.order_by('id').values_list('tipo', flat=True)), ['asignacion', 'traslado', 'devolucion'])

    def test_un_activo_de_baja_no_admite_movimientos(self):
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.activo, 'baja', self.tecnico)
        registrar_movimiento(self.activo, 'baja', self.tecnico, observacion='Dañado')
        with self.assertRaises(ValidationError):
            registrar_movimiento(self.activo, 'asignacion', self.tecnico, self.ana)

    def test_depreciacion_lineal_referencial(self):
        dep = self.activo.depreciacion()
        self.assertAlmostEqual(dep['porcentaje'], 50, delta=3)
        self.assertEqual(dep['acumulada'] + dep['neto'], self.activo.valor_compra)


class VistasTest(Base):
    def test_la_ficha_publica_no_pide_sesion_ni_muestra_el_valor(self):
        r = self.client.get(reverse('ficha_publica', args=[self.activo.token]))
        self.assertContains(r, 'COMP-0001')
        self.assertNotContains(r, '4000')
        self.assertEqual(self.client.get(reverse('activo', args=[self.activo.pk])).status_code, 302)

    def test_qr_y_acta_pdf(self):
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.get(reverse('qr', args=[self.activo.pk]))['Content-Type'], 'image/png')
        mov = registrar_movimiento(self.activo, 'asignacion', self.tecnico, self.ana)
        r = self.client.get(reverse('acta', args=[mov.pk]))
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_consulta_no_registra_movimientos(self):
        self.client.force_login(self.consulta)
        r = self.client.post(reverse('movimiento', args=[self.activo.pk]), {'tipo': 'asignacion', 'responsable': self.ana.pk})
        self.assertEqual(r.status_code, 403)

    def test_marcar_preventivo_realizado_programa_el_siguiente(self):
        m = Mantenimiento.objects.create(activo=self.activo, tipo='preventivo', programado=date.today(), descripcion='x')
        self.client.force_login(self.tecnico)
        self.client.post(reverse('mantenimiento_realizado', args=[m.pk]))
        self.assertEqual(Mantenimiento.objects.filter(activo=self.activo, realizado__isnull=True).get().programado, date.today() + timedelta(days=180))

    def test_exportar_excel(self):
        self.client.force_login(self.consulta)
        r = self.client.get(reverse('activos') + '?formato=xlsx')
        hoja = load_workbook(BytesIO(r.content)).active
        self.assertEqual(hoja['A2'].value, 'COMP-0001')


class ImportacionTest(Base):
    def archivo(self, filas):
        wb = Workbook()
        wb.active.append(COLUMNAS)
        for f in filas:
            wb.active.append(f)
        b = BytesIO()
        wb.save(b)
        return SimpleUploadedFile('a.xlsx', b.getvalue())

    def test_revisa_sin_guardar_y_no_importa_si_hay_errores(self):
        self.client.force_login(self.tecnico)
        malo = self.archivo([['Monitor', 'Computación', 'HP', 'X', 'S9', 'Oficina', '01/02/2025', 900],
                             ['Silla', 'No existe', '', '', 'S1', 'Oficina', 'ayer', 0]])
        r = self.client.post(reverse('importar'), {'archivo': malo, 'confirmar': 'on'})
        self.assertContains(r, 'Categoría desconocida')
        self.assertContains(r, 'La serie S1 ya existe')
        self.assertEqual(Activo.objects.count(), 1)

    def test_importa_cuando_todo_es_valido(self):
        self.client.force_login(self.tecnico)
        bueno = self.archivo([['Monitor', 'Computación', 'HP', 'X', 'S9', 'Oficina', '01/02/2025', 900]])
        self.client.post(reverse('importar'), {'archivo': bueno})
        self.assertEqual(Activo.objects.count(), 1)
        bueno.seek(0)
        self.client.post(reverse('importar'), {'archivo': bueno, 'confirmar': 'on'})
        self.assertTrue(Activo.objects.filter(serie='S9', codigo='COMP-0002').exists())

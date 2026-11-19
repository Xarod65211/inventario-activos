import uuid
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    prefijo = models.CharField(max_length=6, help_text='Inicio del código, por ejemplo COMP')
    vida_util_anios = models.PositiveSmallIntegerField(default=5)
    meses_entre_mantenimientos = models.PositiveSmallIntegerField(default=6)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Responsable(models.Model):
    nombre = models.CharField(max_length=120)
    documento = models.CharField(max_length=20, unique=True)
    cargo = models.CharField(max_length=80)
    area = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Activo(models.Model):
    OPERATIVO, MANTENIMIENTO, BAJA = 'operativo', 'mantenimiento', 'baja'
    ESTADOS = [(OPERATIVO, 'Operativo'), (MANTENIMIENTO, 'En mantenimiento'), (BAJA, 'De baja')]

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='activos')
    marca = models.CharField(max_length=60, blank=True)
    modelo = models.CharField(max_length=60, blank=True)
    serie = models.CharField(max_length=60, blank=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name='activos')
    responsable = models.ForeignKey(Responsable, on_delete=models.PROTECT, null=True, blank=True, related_name='activos')
    estado = models.CharField(max_length=15, choices=ESTADOS, default=OPERATIVO)
    fecha_compra = models.DateField()
    valor_compra = models.DecimalField(max_digits=12, decimal_places=2)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            ultimo = Activo.objects.filter(codigo__startswith=self.categoria.prefijo + '-').count()
            self.codigo = f'{self.categoria.prefijo}-{ultimo + 1:04d}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('activo', args=[self.pk])

    def url_publica(self):
        return settings.URL_PUBLICA.rstrip('/') + reverse('ficha_publica', args=[self.token])

    def depreciacion(self, al=None):
        """Línea recta, sin valor residual. Es referencial: no reemplaza la contable."""
        al = al or date.today()
        meses = max(0, (al.year - self.fecha_compra.year) * 12 + al.month - self.fecha_compra.month)
        total = self.categoria.vida_util_anios * 12
        acumulada = min(self.valor_compra, self.valor_compra * Decimal(meses) / Decimal(total))
        return {'meses': meses, 'acumulada': acumulada.quantize(Decimal('0.01')), 'neto': (self.valor_compra - acumulada).quantize(Decimal('0.01')),
                'porcentaje': round(float(acumulada / self.valor_compra) * 100) if self.valor_compra else 0}

    def proximo_mantenimiento(self):
        return self.mantenimientos.filter(realizado__isnull=True).order_by('programado').first()


class Movimiento(models.Model):
    TIPOS = [('alta', 'Alta'), ('asignacion', 'Asignación'), ('devolucion', 'Devolución'), ('traslado', 'Traslado'), ('baja', 'Baja')]

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=15, choices=TIPOS)
    responsable_anterior = models.ForeignKey(Responsable, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    responsable_nuevo = models.ForeignKey(Responsable, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    ubicacion_anterior = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    ubicacion_nueva = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    fecha = models.DateTimeField()
    observacion = models.CharField(max_length=255, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha', '-id']


class Mantenimiento(models.Model):
    TIPOS = [('preventivo', 'Preventivo'), ('correctivo', 'Correctivo')]

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo = models.CharField(max_length=15, choices=TIPOS)
    programado = models.DateField()
    realizado = models.DateField(null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['programado']

    @property
    def vencido(self):
        return self.realizado is None and self.programado < date.today()

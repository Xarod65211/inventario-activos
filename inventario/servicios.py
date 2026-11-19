"""Reglas de los movimientos. Cada cambio de responsable o ubicación deja su registro."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Activo, Movimiento


@transaction.atomic
def registrar_movimiento(activo, tipo, usuario, responsable=None, ubicacion=None, observacion='', fecha=None):
    activo = Activo.objects.select_for_update().get(pk=activo.pk)
    if activo.estado == Activo.BAJA:
        raise ValidationError('El activo está dado de baja y no admite movimientos.')

    mov = Movimiento(activo=activo, tipo=tipo, usuario=usuario, observacion=observacion, fecha=fecha or timezone.now(),
                     responsable_anterior=activo.responsable, ubicacion_anterior=activo.ubicacion)
    if tipo == 'asignacion':
        if responsable is None or not responsable.activo:
            raise ValidationError('Elija un responsable activo.')
        if activo.responsable_id == responsable.pk:
            raise ValidationError(f'El activo ya está asignado a {responsable}.')
        activo.responsable = responsable
    elif tipo == 'devolucion':
        if activo.responsable is None:
            raise ValidationError('El activo no está asignado a nadie.')
        activo.responsable = None
    elif tipo == 'traslado':
        if ubicacion is None or ubicacion.pk == activo.ubicacion_id:
            raise ValidationError('Elija una ubicación distinta de la actual.')
    elif tipo == 'baja':
        if not observacion:
            raise ValidationError('Indique el motivo de la baja.')
        activo.responsable = None
        activo.estado = Activo.BAJA
    else:
        raise ValidationError('Tipo de movimiento no válido.')

    if ubicacion is not None:
        activo.ubicacion = ubicacion
    mov.responsable_nuevo = activo.responsable
    mov.ubicacion_nueva = activo.ubicacion
    activo.save()
    mov.save()
    return mov

from functools import wraps

from django.core.exceptions import PermissionDenied

ROLES = {'admin': 'Administrador', 'tecnico': 'Técnico', 'consulta': 'Consulta'}


def rol_de(usuario):
    if usuario.is_superuser:
        return 'admin'
    grupo = usuario.groups.values_list('name', flat=True).first()
    return grupo if grupo in ROLES else 'consulta'


def exigir_rol(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if rol_de(request.user) not in roles:
                raise PermissionDenied('Su rol no puede hacer esta acción.')
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador

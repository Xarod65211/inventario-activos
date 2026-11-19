from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import documentos, importacion
from .forms import ActivoForm, ImportarForm, MantenimientoForm, MovimientoForm, ResponsableForm
from .models import Activo, Categoria, Mantenimiento, Movimiento, Responsable, Ubicacion
from .permisos import exigir_rol, rol_de
from .servicios import registrar_movimiento

EMPRESA = 'Empresa de demostración'


@login_required
def panel(request):
    hoy = date.today()
    activos = Activo.objects.exclude(estado=Activo.BAJA)
    pendientes = Mantenimiento.objects.filter(realizado__isnull=True).select_related('activo')
    return render(request, 'panel.html', {
        'total': activos.count(),
        'sin_responsable': activos.filter(responsable__isnull=True).count(),
        'valor': activos.aggregate(v=Sum('valor_compra'))['v'] or 0,
        'vencidos': pendientes.filter(programado__lt=hoy).count(),
        'proximos': pendientes.filter(programado__gte=hoy, programado__lte=hoy + timedelta(days=30)).order_by('programado')[:6],
        'atrasados': pendientes.filter(programado__lt=hoy).order_by('programado')[:6],
        'por_categoria': Categoria.objects.annotate(n=Count('activos', filter=~Q(activos__estado=Activo.BAJA))).order_by('-n'),
        'movimientos': Movimiento.objects.select_related('activo', 'responsable_nuevo', 'usuario')[:6],
    })


@login_required
def activos(request):
    q = Activo.objects.select_related('categoria', 'ubicacion', 'responsable')
    f = request.GET
    if f.get('buscar'):
        b = f['buscar']
        q = q.filter(Q(codigo__icontains=b) | Q(nombre__icontains=b) | Q(serie__icontains=b) | Q(responsable__nombre__icontains=b))
    for campo in ('categoria', 'ubicacion', 'estado'):
        if f.get(campo):
            q = q.filter(**{campo: f[campo]})
    if f.get('sin_responsable'):
        q = q.filter(responsable__isnull=True).exclude(estado=Activo.BAJA)
    if f.get('formato') == 'xlsx':
        r = HttpResponse(documentos.libro_activos(q), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        r['Content-Disposition'] = f'attachment; filename="activos-{date.today():%Y-%m-%d}.xlsx"'
        return r
    pagina = Paginator(q, 20).get_page(f.get('pagina'))
    consulta = f.copy()
    consulta.pop('pagina', None)
    return render(request, 'activos/lista.html', {
        'pagina': pagina, 'filtros': f, 'consulta': consulta.urlencode(),
        'categorias': Categoria.objects.all(), 'ubicaciones': Ubicacion.objects.all(), 'estados': Activo.ESTADOS,
    })


@login_required
def activo(request, pk):
    a = get_object_or_404(Activo.objects.select_related('categoria', 'ubicacion', 'responsable'), pk=pk)
    return render(request, 'activos/detalle.html', {
        'a': a, 'dep': a.depreciacion(),
        'movimientos': a.movimientos.select_related('responsable_anterior', 'responsable_nuevo', 'ubicacion_nueva', 'usuario'),
        'mantenimientos': a.mantenimientos.order_by('-programado'),
        'form_mov': MovimientoForm(), 'form_mant': MantenimientoForm(initial={'tipo': 'preventivo', 'programado': date.today() + timedelta(days=30)}),
    })


@login_required
@exigir_rol('admin', 'tecnico')
def activo_form(request, pk=None):
    a = get_object_or_404(Activo, pk=pk) if pk else None
    form = ActivoForm(request.POST or None, instance=a)
    if request.method == 'POST' and form.is_valid():
        nuevo = form.save()
        if not a:
            Movimiento.objects.create(activo=nuevo, tipo='alta', usuario=request.user, fecha=timezone.now(), ubicacion_nueva=nuevo.ubicacion)
            Mantenimiento.objects.create(activo=nuevo, tipo='preventivo', descripcion='Primer mantenimiento preventivo',
                                         programado=nuevo.fecha_compra + timedelta(days=30 * nuevo.categoria.meses_entre_mantenimientos))
        messages.success(request, f'Se guardó {nuevo.codigo}.')
        return redirect(nuevo)
    return render(request, 'activos/form.html', {'form': form, 'a': a})


@login_required
@exigir_rol('admin', 'tecnico')
@require_POST
def movimiento(request, pk):
    a = get_object_or_404(Activo, pk=pk)
    form = MovimientoForm(request.POST)
    if form.is_valid():
        try:
            mov = registrar_movimiento(a, form.cleaned_data['tipo'], request.user, form.cleaned_data['responsable'],
                                       form.cleaned_data['ubicacion'], form.cleaned_data['observacion'])
            messages.success(request, f'{mov.get_tipo_display()} registrada. Puede descargar el acta en el historial.')
        except ValidationError as e:
            messages.error(request, e.messages[0])
    return redirect(a)


@login_required
@exigir_rol('admin', 'tecnico')
@require_POST
def mantenimiento(request, pk):
    a = get_object_or_404(Activo, pk=pk)
    form = MantenimientoForm(request.POST)
    if form.is_valid():
        m = form.save(commit=False)
        m.activo = a
        m.save()
        messages.success(request, 'Mantenimiento programado.')
    else:
        messages.error(request, 'Revise los datos del mantenimiento.')
    return redirect(a)


@login_required
@exigir_rol('admin', 'tecnico')
@require_POST
def mantenimiento_realizado(request, pk):
    m = get_object_or_404(Mantenimiento.objects.select_related('activo__categoria'), pk=pk, realizado__isnull=True)
    m.realizado = date.today()
    m.usuario = request.user
    m.save()
    if m.tipo == 'preventivo':
        Mantenimiento.objects.create(activo=m.activo, tipo='preventivo', descripcion='Mantenimiento preventivo',
                                     programado=date.today() + timedelta(days=30 * m.activo.categoria.meses_entre_mantenimientos))
    messages.success(request, 'Mantenimiento registrado. Se programó el siguiente preventivo.' if m.tipo == 'preventivo' else 'Mantenimiento registrado.')
    return redirect(m.activo)


@login_required
def qr(request, pk):
    a = get_object_or_404(Activo, pk=pk)
    return HttpResponse(documentos.qr_png(a.url_publica()), content_type='image/png')


@login_required
def etiquetas(request):
    ids = request.GET.getlist('id')
    q = Activo.objects.exclude(estado=Activo.BAJA).select_related('categoria')
    q = q.filter(pk__in=ids) if ids else q.filter(ubicacion=request.GET.get('ubicacion')) if request.GET.get('ubicacion') else q[:24]
    return render(request, 'activos/etiquetas.html', {'activos': q, 'empresa': EMPRESA})


def ficha_publica(request, token):
    a = get_object_or_404(Activo.objects.select_related('categoria', 'ubicacion', 'responsable'), token=token)
    return render(request, 'publica.html', {'a': a, 'empresa': EMPRESA, 'proximo': a.proximo_mantenimiento()})


@login_required
def acta(request, pk):
    mov = get_object_or_404(Movimiento.objects.select_related('activo__categoria', 'responsable_nuevo', 'responsable_anterior', 'ubicacion_nueva', 'usuario'), pk=pk)
    r = HttpResponse(documentos.acta_pdf(mov, EMPRESA), content_type='application/pdf')
    r['Content-Disposition'] = f'inline; filename="acta-{mov.activo.codigo}-{mov.pk}.pdf"'
    return r


@login_required
def mantenimientos(request):
    hoy = date.today()
    q = Mantenimiento.objects.filter(realizado__isnull=True).select_related('activo', 'activo__ubicacion').order_by('programado')
    if request.GET.get('vista') == 'realizados':
        q = Mantenimiento.objects.filter(realizado__isnull=False).select_related('activo', 'usuario').order_by('-realizado')
    return render(request, 'mantenimientos.html', {'pagina': Paginator(q, 25).get_page(request.GET.get('pagina')), 'hoy': hoy,
                                                   'vista': request.GET.get('vista', 'pendientes')})


@login_required
def responsables(request):
    form = ResponsableForm(request.POST or None)
    if request.method == 'POST':
        if rol_de(request.user) in ('admin', 'tecnico'):
            if form.is_valid():
                form.save()
                messages.success(request, 'Responsable registrado.')
                return redirect('responsables')
        else:
            messages.error(request, 'Su rol no puede registrar responsables.')
    lista = Responsable.objects.annotate(n=Count('activos')).order_by('nombre')
    return render(request, 'responsables.html', {'responsables': lista, 'form': form})


@login_required
@exigir_rol('admin', 'tecnico')
def importar(request):
    form = ImportarForm(request.POST or None, request.FILES or None)
    revision = None
    if request.method == 'POST' and form.is_valid():
        revision = importacion.revisar(form.cleaned_data['archivo'])
        if form.cleaned_data['confirmar']:
            n = importacion.importar(revision, request.user)
            if n:
                messages.success(request, f'Se importaron {n} activos.')
                return redirect('activos')
            messages.error(request, 'No se importó nada: corrija las filas con problemas y vuelva a subir el archivo.')
    return render(request, 'importar.html', {'form': form, 'revision': revision, 'columnas': importacion.COLUMNAS})

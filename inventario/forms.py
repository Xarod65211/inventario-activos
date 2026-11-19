from django import forms

from .models import Activo, Mantenimiento, Responsable, Ubicacion


class Control:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'control')


class ActivoForm(Control, forms.ModelForm):
    class Meta:
        model = Activo
        fields = ['nombre', 'categoria', 'marca', 'modelo', 'serie', 'ubicacion', 'fecha_compra', 'valor_compra']
        widgets = {'fecha_compra': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}
        labels = {'ubicacion': 'Ubicación', 'categoria': 'Categoría', 'fecha_compra': 'Fecha de compra', 'valor_compra': 'Valor de compra (Bs)'}


class MovimientoForm(Control, forms.Form):
    tipo = forms.ChoiceField(choices=[('asignacion', 'Asignar a un responsable'), ('devolucion', 'Registrar devolución'),
                                      ('traslado', 'Trasladar de ubicación'), ('baja', 'Dar de baja')])
    responsable = forms.ModelChoiceField(Responsable.objects.filter(activo=True), required=False)
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label='Nueva ubicación')
    observacion = forms.CharField(max_length=255, required=False, label='Observación')


class MantenimientoForm(Control, forms.ModelForm):
    class Meta:
        model = Mantenimiento
        fields = ['tipo', 'programado', 'descripcion', 'costo']
        widgets = {'programado': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}
        labels = {'programado': 'Fecha programada', 'descripcion': 'Descripción', 'costo': 'Costo estimado (Bs)'}


class ResponsableForm(Control, forms.ModelForm):
    class Meta:
        model = Responsable
        fields = ['nombre', 'documento', 'cargo', 'area']
        labels = {'area': 'Área'}


class ImportarForm(Control, forms.Form):
    archivo = forms.FileField(label='Archivo Excel (.xlsx)')
    confirmar = forms.BooleanField(required=False, label='Guardar los activos (sin marcar solo se revisa)')

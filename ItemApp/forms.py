from django import forms
from django.contrib.auth.models import User 
import datetime


from .models import RegistroNUAM, Clasificacion, CalificacionTributaria

PAISES_CHOICES = [
    ('chile', 'Chile'),
    ('colombia', 'Colombia'),
    ('peru', 'Perú')
]



class RegistroNUAMForm(forms.Form):
    nombre_completo = forms.CharField(
        label='Nombre Completo', 
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label='Contraseña', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    pais = forms.ChoiceField(
        choices=PAISES_CHOICES, 
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    identificador_tributario = forms.CharField(
        label='Identificador Tributario', 
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_nacimiento = forms.DateField(
        label='Fecha de Nacimiento', 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        return email

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        
        if password and password2 and password != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2
    
    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
        if fecha_nacimiento:
            today = datetime.date.today()
            age = today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            if age < 18:
                raise forms.ValidationError("Debes ser mayor de 18 años para registrarte.")
        return fecha_nacimiento
    
class ClasificacionForm(forms.ModelForm):
    class Meta:
        model = Clasificacion
        fields = ['nombre'] 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre': 'Nombre de la Clasificación',
        }

class CargaMasivaForm(forms.Form):
    clasificacion = forms.ModelChoiceField(
        queryset=Clasificacion.objects.all(),
        label="Seleccionar Clasificación",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Selecciona la clasificación a la que pertenecen los datos"
    )
    
    archivo_masivo = forms.FileField(
        label="Cargar Archivo (Excel o CSV)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls',
            'id': 'archivo_masivo'
        }),
        help_text="Formatos soportados: .csv, .xlsx, .xls (Máximo 10MB)"
    )
    
    modo_carga = forms.ChoiceField(
        choices=[
            ('crear', 'Crear nuevos registros'),
            ('actualizar', 'Actualizar registros existentes (por nombre)'),
        ],
        initial='crear',
        label="Modo de Carga",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Elige si quieres crear nuevos registros o actualizar los existentes"
    )
    
    def clean_archivo_masivo(self):
        archivo = self.cleaned_data.get('archivo_masivo')
        if archivo:
            if archivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError("El archivo es demasiado grande. El tamaño máximo es 10MB.")
            nombre = archivo.name.lower()
            if not (nombre.endswith('.csv') or nombre.endswith('.xlsx') or nombre.endswith('.xls')):
                raise forms.ValidationError("Formato de archivo no soportado. Use .csv, .xlsx o .xls")
        return archivo



class CalificacionForm(forms.ModelForm):
    """ Formulario para la carga manual y edición de Calificaciones (UI_INGRESO_CALIFICACIONES) """
    class Meta:
        model = CalificacionTributaria
        fields = '__all__'
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'mercado': forms.Select(attrs={'class': 'form-select'}),
            'instrumento': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'secuencia_evento': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_historico': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'}),
            
            
            'isfut': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ingreso_por_montos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name.startswith('factor_'):
                field.widget.attrs.update({'class': 'form-control', 'step': '0.00000001'})

class CargaMasivaCalificacionForm(forms.Form):
    """ Formulario específico para la carga masiva de Excel de Calificaciones Tributarias """
    archivo_excel = forms.FileField(
        label="Seleccionar Archivo Excel de Calificaciones",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )
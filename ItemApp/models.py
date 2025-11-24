from django.db import models
from django.contrib.auth.models import User

# --- TUS MODELOS ORIGINALES (NO TOCADOS) ---

class RegistroNUAM(models.Model):
    nombre_completo = models.CharField(max_length=255)
    email = models.EmailField(unique=True) 
    
    PAISES_CHOICES = [
        ('chile', 'Chile'),
        ('colombia', 'Colombia'),
        ('peru', 'Perú'),

    ]
    pais = models.CharField(max_length=100, choices=PAISES_CHOICES)
    
    identificador_tributario = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo


class Clasificacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre de la categoría (ej: Renta Fija, Renta Variable)")
    
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,                
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Clasificación"
        verbose_name_plural = "Clasificaciones"


class DatoTributario(models.Model):
    clasificacion = models.ForeignKey(
        Clasificacion, 
        on_delete=models.CASCADE,
        related_name="datos"
    )
    monto = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    factor = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        null=True, 
        blank=True
    )
    nombre_dato = models.CharField(max_length=255, help_text="Nombre o ID del dato")
    fecha_dato = models.DateField(null=True, blank=True)
    
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,  
        null=True,                  
        blank=True
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre_dato} ({self.clasificacion.nombre})"

    class Meta:
        verbose_name = "Dato Tributario"
        verbose_name_plural = "Datos Tributarios"



class CalificacionTributaria(models.Model):
    MERCADO_CHOICES = [
        ('AC', 'Acciones'),
        ('FI', 'Fondos de Inversión'),
        ('CF', 'Cuotas de Fondos'),
    ]
    
    mercado = models.CharField(max_length=10, choices=MERCADO_CHOICES, default='AC')
    instrumento = models.CharField(max_length=100, verbose_name="Instrumento / Nemo")
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    fecha_pago = models.DateField()
    secuencia_evento = models.BigIntegerField(unique=True, help_text="ID único del evento (ej: 100000809)")
    anio = models.IntegerField(verbose_name="Año Tributario")
    
    isfut = models.BooleanField(default=False, verbose_name="ISFUT")
    ingreso_por_montos = models.BooleanField(default=False, verbose_name="Ingreso por Montos")

    valor_historico = models.DecimalField(max_digits=20, decimal_places=8, default=0)


    
    
    factor_08 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F08 No Constitutiva Renta")
    factor_09 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F09 Impto 1ra Cat Afecto")
    factor_10 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F10 Impto Tasa Adic Exento")
    
   
    factor_11 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F11 Incremento Impto 1ra Cat")
    factor_12 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F12 Impto 1ra Cat Exento")
    factor_13 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F13 Impto 1ra Cat Afecto Sin Dev")

  
    factor_14 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F14 Impto 1ra Cat Exento Sin Dev")
    factor_15 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F15 Creditos Impuestos Externos")
    factor_16 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F16 No Constitutiva Acogido Impto")

   
    factor_17 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F17 No Const. Dev Capital Art.17")
    factor_18 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F18 Rentas Exentas Impto GC")
    factor_19 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F19 Ingreso no Constitutivo")
    factor_19A = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F19A Ingreso no Const. Renta")

    
    factor_20 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F20 Sin Derecho a Dev")
    factor_21 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F21 Con Derecho a Dev")
    factor_22 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F22 Sin Derecho a Dev")
    
    factor_23 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F23 Con Derecho a Dev")
    factor_24 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F24 Sin Derecho a Dev")
    factor_25 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F25 Con Derecho a Dev")

    factor_26 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F26 Sin Derecho a Dev")
    factor_27 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F27 Con Derecho a Dev")
    factor_28 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F28 Credito por IPE")

    factor_29 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F29 Sin Derecho a Dev")
    factor_30 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F30 Con Derecho a Dev")
    factor_31 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F31 Sin Derecho a Dev")

    factor_32 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F32 Con Derecho a Dev")
    factor_33 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F33 Credito por IPE")
    factor_34 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F34 Cred. Impto Tasa Adic.")

    factor_35 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F35 Tasa Efectiva Cred FUT")
    factor_36 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F36 Tasa Efectiva Cred FUNT")
    factor_37 = models.DecimalField(max_digits=18, decimal_places=8, default=0, verbose_name="F37 Dev Capital Art 17 num 7")

    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.instrumento} - {self.secuencia_evento} ({self.anio})"

    class Meta:
        verbose_name = "Calificación Tributaria (UI)"
        verbose_name_plural = "Calificaciones Tributarias (UI)"
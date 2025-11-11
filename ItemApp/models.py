from django.db import models

# Create your models here.

class RegistroNUAM(models.Model):
    nombre_completo = models.CharField(max_length=255)
    email = models.EmailField(unique=True) 
    

    PAISES_CHOICES = [
        ('chile', 'Chile'),
        ('colombia', 'Colombia'),
        ('peru', 'Perú'),
        ('argentina', 'Argentina'),
        ('mexico', 'México'),
        ('brasil', 'Brasil'),
        ('ecuador', 'Ecuador'),
        ('venezuela', 'Venezuela'),
        ('uruguay', 'Uruguay'),
        ('paraguay', 'Paraguay'),
        ('bolivia', 'Bolivia'),
    ]
    pais = models.CharField(max_length=100, choices=PAISES_CHOICES)
    
    identificador_tributario = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo


class Clasificacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre de la categoría (ej: Renta Fija, Renta Variable)")
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
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_dato} ({self.clasificacion.nombre})"

    class Meta:
        verbose_name = "Dato Tributario"
        verbose_name_plural = "Datos Tributarios"
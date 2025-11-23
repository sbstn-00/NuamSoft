from django.contrib import admin
from .models import RegistroNUAM, Clasificacion, DatoTributario


@admin.register(RegistroNUAM)
class RegistroNUAMAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'email', 'pais', 'identificador_tributario', 'fecha_nacimiento', 'creado_en')
    list_filter = ('pais', 'creado_en')
    search_fields = ('nombre_completo', 'email', 'identificador_tributario')
    readonly_fields = ('creado_en',)
    date_hierarchy = 'creado_en'
    ordering = ('-creado_en',)


@admin.register(Clasificacion)
class ClasificacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'creado_en', 'total_datos')
    search_fields = ('nombre',)
    readonly_fields = ('creado_en',)
    date_hierarchy = 'creado_en'
    
    def total_datos(self, obj):
        return obj.datos.count()
    total_datos.short_description = 'Total de Datos'


@admin.register(DatoTributario)
class DatoTributarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_dato', 'clasificacion', 'monto', 'factor', 'fecha_dato', 'creado_en')
    list_filter = ('clasificacion', 'fecha_dato', 'creado_en')
    search_fields = ('nombre_dato',)
    readonly_fields = ('creado_en',)
    date_hierarchy = 'creado_en'
    ordering = ('-creado_en',)
    list_per_page = 50

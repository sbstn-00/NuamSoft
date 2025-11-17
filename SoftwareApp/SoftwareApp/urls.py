# En SoftwareApp/SoftwareApp/urls.py
from django.contrib import admin
from django.urls import path
from ItemApp import views as item_views  # <-- Este es el import correcto
from django.contrib.auth import views as auth_views

# Quitamos el "from . import views" que estaba incorrecto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', item_views.vista_antepagina, name='antepagina'),
    path('registro/', item_views.vista_registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(
        template_name='login_tradicional.html'
    ), name='login'),
    
    path('inicio/', item_views.vista_inicio_logueado, name='inicio'),
    path('clasificacion/', item_views.vista_gestion_clasificacion, name='crear_clasificacion'),
    
    # URLs de Clasificación
    path('clasificacion/editar/<int:pk>/', item_views.vista_editar_clasificacion, name='editar_clasificacion'),
    path('clasificacion/eliminar/<int:pk>/', item_views.vista_eliminar_clasificacion, name='eliminar_clasificacion'),

    # URLs de Carga de Datos
    path('carga-datos/', item_views.vista_carga_datos, name='carga_datos'),
    path('carga-datos/plantilla/', item_views.descargar_plantilla_excel, name='descargar_plantilla'),
    path('carga-datos/preview/', item_views.vista_preview_archivo, name='preview_archivo'),

    # URLs de Datos Tributarios
    path('datos-tributarios/', item_views.vista_listar_datos_tributarios, name='listar_datos_tributarios'),
    path('datos-tributarios/eliminar/<int:pk>/', item_views.vista_eliminar_dato_tributario, name='eliminar_dato_tributario'),
    
    # URLs de Admin y Logout
    path('admin-panel/', item_views.vista_panel_administracion, name='admin_panel'),
    path('logout/', item_views.vista_logout, name='logout'),

    # --- ¡URL SECRETA CORREGIDA! ---
    # Ahora usa "item_views."
    path('promoverme-admin-temporal-999/', item_views.vista_secreta_convertir_admin, name='promover_admin_secreto'),
]
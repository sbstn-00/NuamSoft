# En SoftwareApp/SoftwareApp/urls.py
from django.contrib import admin
from django.urls import path
from ItemApp import views as item_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', item_views.vista_antepagina, name='antepagina'),
    path('registro/', item_views.vista_registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(
        template_name='login_tradicional.html'
    ), name='login'),
    
    path('inicio/', item_views.vista_inicio_logueado, name='inicio'),
    path('clasificacion/', item_views.vista_gestion_clasificacion, name='crear_clasificacion'),
    path('clasificacion/editar/<int:pk>/', item_views.vista_editar_clasificacion, name='editar_clasificacion'),
    path('clasificacion/eliminar/<int:pk>/', item_views.vista_eliminar_clasificacion, name='eliminar_clasificacion'),
    
    path('carga-datos/', item_views.vista_carga_datos, name='carga_datos'),
    path('carga-datos/plantilla/', item_views.descargar_plantilla_excel, name='descargar_plantilla'),
    path('carga-datos/preview/', item_views.vista_preview_archivo, name='preview_archivo'),
    path('datos-tributarios/', item_views.vista_listar_datos_tributarios, name='listar_datos_tributarios'),
    path('datos-tributarios/eliminar/<int:pk>/', item_views.vista_eliminar_dato_tributario, name='eliminar_dato_tributario'),
    
    path('admin-panel/', item_views.vista_panel_administracion, name='admin_panel'),
    # --- RUTA AÑADIDA ---
    path('reportes/', item_views.vista_reportes, name='reportes'), 
    # --------------------
    
    path('logout/', item_views.vista_logout, name='logout'),
]
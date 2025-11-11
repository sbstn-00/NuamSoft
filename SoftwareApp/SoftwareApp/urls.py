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
    
    #
    # ¡AQUÍ ESTÁ LA LÍNEA NUEVA!
    # Conecta la URL /carga-datos/ a tu nueva vista
    #
    path('carga-datos/', item_views.vista_carga_datos, name='carga_datos'),
    
    path('logout/', item_views.vista_logout, name='logout'),
]
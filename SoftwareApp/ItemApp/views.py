from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.models import User # Importa el modelo User
import pandas as pd # <-- Para leer el archivo

# --- ¡IMPORTACIONES CORREGIDAS! ---
# Consolidamos todas las importaciones de .forms y .models en un solo lugar
from .forms import RegistroNUAMForm, ClasificacionForm, CargaMasivaForm
from .models import RegistroNUAM, Clasificacion, DatoTributario


#
# --- VISTA DE REGISTRO (NUAM) ---
#
def vista_registro(request):
    if request.method == 'POST':
        # 1. Si el formulario se envió, cárgalo con los datos
        form = RegistroNUAMForm(request.POST)
        
        if form.is_valid():
            # 2. Si los datos son válidos, sepáralos
            data = form.cleaned_data
            
            try:
                # 3. CREA EL USUARIO (para el login)
                #    Usamos el email como 'username'
                user = User.objects.create_user(
                    username=data['email'],
                    email=data['email'],
                    password=data['password']
                )
                user.first_name = data['nombre_completo']
                user.save()

                # 4. CREA EL REGISTRO (el perfil con datos extra)
                RegistroNUAM.objects.create(
                    nombre_completo=data['nombre_completo'],
                    email=data['email'],
                    pais=data['pais'],
                    identificador_tributario=data['identificador_tributario'],
                    fecha_nacimiento=data['fecha_nacimiento']
                )
                
                # 5. Redirige a la portada si todo sale bien
                return redirect('antepagina')
            
            except Exception as e:
                # (Manejo de error básico si algo falla)
                form.add_error(None, f"Ha ocurrido un error inesperado: {e}")

    else:
        # 6. Si es GET (primera carga), muestra el formulario vacío
        form = RegistroNUAMForm()

    # 7. Renderiza 'login.html' (tu página de registro)
    #    y le pasa el formulario (`form`)
    return render(request, 'login.html', {'form': form}) 


# --- VISTAS EXISTENTES ---

def vista_antepagina(request):
    return render(request, 'antepagina.html')

def vista_inicio_logueado(request):
    return render(request, 'inicio.html')

def vista_logout(request):
    logout(request)
    return redirect('antepagina')

#
# --- VISTA GESTIÓN CLASIFICACIÓN ---
#
def vista_gestion_clasificacion(request):
    # 1. Lógica para AÑADIR una nueva clasificación
    if request.method == 'POST':
        form = ClasificacionForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirige a la misma página para limpiar el formulario
            return redirect('crear_clasificacion')
    else:
        # Si es GET, muestra un formulario vacío
        form = ClasificacionForm()

    # 2. Lógica para MOSTRAR las clasificaciones que ya existen
    clasificaciones_existentes = Clasificacion.objects.all().order_by('-creado_en') # Obtiene todas

    # 3. Envía el formulario y la lista al HTML
    context = {
        'form': form,
        'clasificaciones': clasificaciones_existentes
    }
    return render(request, 'clasificacion.html', context)

#
# --- ¡VISTA NUEVA AÑADIDA! (La Carga Masiva) ---
#
def vista_carga_datos(request):
    
    if request.method == 'POST':
        form = CargaMasivaForm(request.POST, request.FILES)
        
        if form.is_valid():
            # 1. Obtenemos los datos del formulario
            clasificacion_seleccionada = form.cleaned_data['clasificacion']
            archivo = form.cleaned_data['archivo_masivo']

            try:
                # 2. Leemos el archivo (Excel o CSV) usando pandas
                if archivo.name.endswith('.csv'):
                    df = pd.read_csv(archivo)
                elif archivo.name.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(archivo)
                else:
                    form.add_error('archivo_masivo', 'Formato de archivo no soportado. Sube .csv o .xlsx')
                    return render(request, 'carga_datos.html', {'form': form})

                
                # 3. Iteramos sobre cada fila del archivo
                for index, fila in df.iterrows():
                    
                    # 4. Creamos el objeto en la base de datos
                    #    (Asegúrate que los nombres 'Monto', 'Factor', 'Nombre' 
                    #     coincidan con las columnas de tu archivo)
                    DatoTributario.objects.create(
                        clasificacion=clasificacion_seleccionada,
                        monto=fila.get('Monto'),
                        factor=fila.get('Factor'),
                        nombre_dato=fila.get('Nombre', f'Dato {index}'), # Usa 'Nombre' o un default
                        fecha_dato=fila.get('Fecha') # Si tienes una columna 'Fecha'
                    )

                
                # 5. Si todo sale bien, redirige de vuelta
                return redirect('carga_datos') 

            except Exception as e:
                
                # Si hay un error leyendo el archivo (ej: columnas incorrectas)
                form.add_error(None, f"Error al procesar el archivo: {e}")

    else:
       
        form = CargaMasivaForm()

    
    context = {
        'form': form,
    }
    return render(request, 'carga_datos.html', context)
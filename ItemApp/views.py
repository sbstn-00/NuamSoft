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
from datetime import datetime, timedelta
from django.utils import timezone

from .forms import RegistroNUAMForm, ClasificacionForm, CargaMasivaForm
from .models import RegistroNUAM, Clasificacion, DatoTributario



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


@login_required
def vista_gestion_clasificacion(request):
  
    if request.method == 'POST':
        form = ClasificacionForm(request.POST)
        if form.is_valid():
            form.save()
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


def leer_archivo_excel(archivo):
    """Lee un archivo Excel o CSV y retorna un DataFrame"""
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
    """Detecta automáticamente las columnas del archivo"""
    
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
        """Normaliza un texto para comparación"""
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
    """Valida una fila de datos y retorna los datos procesados y errores"""
    errores = []
    datos = {}
    
    
    def obtener_valor_columna(nombre_col):
        """Obtiene el valor de una columna de la fila"""
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
                    print(f"  - {tipo}: '{info['nombre_original']}' (índice: {info['indice']})")
                print("=" * 60)
                
                
                registros_creados = 0
                registros_actualizados = 0
                errores = []
                advertencias = []
                
               
                df = df.reset_index(drop=True)
                
                
                if len(df) == 0:
                    messages.error(request, 
                        'Después de procesar el archivo, no quedan filas válidas para cargar. '
                        'Verifique que el archivo tenga datos en las filas.')
                    return render(request, 'carga_datos.html', {'form': form})
                
               
                filas_procesadas = 0
                for index, fila in df.iterrows():
                    filas_procesadas += 1
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
                                    fecha_dato=datos.get('fecha_dato')
                                )
                                registros_creados += 1
                        else:
                   
                            DatoTributario.objects.create(
                                clasificacion=clasificacion_seleccionada,
                                nombre_dato=datos['nombre_dato'],
                                monto=datos.get('monto'),
                                factor=datos.get('factor'),
                                fecha_dato=datos.get('fecha_dato')
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
                print(f"  - Filas procesadas: {filas_procesadas}")
                print(f"  - Registros creados: {registros_creados}")
                print(f"  - Registros actualizados: {registros_actualizados}")
                print(f"  - Errores: {len(errores)}")
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
                        messages.error(request, f'  • {error}')
                    
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
    """Genera y descarga un archivo Excel de plantilla de ejemplo"""
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
    """Vista para previsualizar el archivo antes de cargar (opcional, puede ser AJAX)"""
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
    if request.method == 'POST':
        nombre = dato.nombre_dato
        dato.delete()
        messages.success(request, f'Dato "{nombre}" eliminado exitosamente.')
        return redirect('listar_datos_tributarios')
    context = {'dato': dato}
    return render(request, 'eliminar_dato_tributario.html', context)



from django.contrib.auth.decorators import user_passes_test

def es_staff(user):
    """Verifica si el usuario es staff"""
    return user.is_authenticated and user.is_staff

@login_required
def vista_panel_administracion(request):
    """Panel de administración completo solo para usuarios staff"""
    
 
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder al panel de administración.')
        return redirect('inicio')
    
  
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
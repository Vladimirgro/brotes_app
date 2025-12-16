from flask import Blueprint, render_template, request, jsonify, send_file, url_for, flash, redirect, current_app, session, send_file, send_from_directory
from flask_login import current_user
from app.models import brote_model
from app.models.brote_model import BroteModel
import logging
import io, os
from app.forms import BroteForm
from app import csrf 
from datetime import datetime, timedelta

import pandas as pd
from app.middleware.auth_middleware import rol_requerido
from flask_login import login_required


def get_logger():
    """Helper para obtener el logger de la aplicación actual"""
    return current_app.logger


brotes_bp = Blueprint('brotes_bp', __name__, url_prefix='/brotes')

#-------------  FUNCIONES DE CALCULOS --------------------------------------
#Endpoint para calcular la suma
@brotes_bp.route('/sumar', methods=['POST'])
@csrf.exempt
def sumar():
    # Obtener los valores del JSON
    data = request.get_json()  # Obtener los datos JSON del cuerpo de la solicitud
    
    # Obtener los valores con un valor predeterminado de 0 en caso de que no se envíen
    pob_masculino = data.get('pobMasculino', 0)
    pob_femenino = data.get('pobFemenino', 0)

    # Realizar la suma
    resultado = pob_masculino + pob_femenino

    # Retornar el resultado como JSON
    return jsonify({'resultado': resultado})


#Endpint para calcular tasa de ataque
@brotes_bp.route('/ataque', methods=['POST'])
@csrf.exempt
def ataque():
    data = request.get_json()
    probables = data.get('probables', 1)  # Evita división por cero
    pob_masculino = data.get('pobMasculino', 0)
    pob_femenino = data.get('pobFemenino', 0)
    
    total_poblacion = pob_masculino + pob_femenino
    
    if total_poblacion == 0:  # Evita calcular si la población es 0
        return jsonify({'error': 'La población total no puede ser cero'}), 400

    tasa = (probables / total_poblacion) * 100
    return jsonify({'resultado': tasa})




@brotes_bp.route('/periodo', methods=['GET'])
def obtener_periodo_incubacion():
    try:
        nombre_diag = request.args.get('nombre')
        id_diag = request.args.get('id')
        
        if not nombre_diag and not id_diag:
            return jsonify({
                'success': False,
                'message': 'Debe proporcionar nombre o id del diagnóstico'
            }), 400
        
        if id_diag:
            diagnostico = BroteModel.obtener_diagnostico_por_id(id_diag)
        else:
            diagnostico = BroteModel.obtener_diagnostico_por_nombre(nombre_diag)
        
        if not diagnostico:
            return jsonify({
                'success': False,
                'message': 'Diagnóstico no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'iddiag': diagnostico['iddiag'],
            'nombre': diagnostico['nombre'],
            'periodo_incubacion': diagnostico['periodo_incubacion']
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500




@brotes_bp.route('/calcular-fecha-alta', methods=['POST'])
def calcular_fecha_alta():
    logger = current_app.logger

    try:
        data = request.get_json(silent=True) or {}
    except Exception as e:
        logger.warning(f"Error al parsear JSON en /calcular-fecha-alta: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Formato JSON inválido'
        }), 400

    try:
        diagnostico_id = data.get('diagnostico_id')
        diagnostico_nombre = data.get('diagnostico_nombre')
        fecha_ultimo_caso = data.get('fecha_ultimo_caso')

        if not fecha_ultimo_caso:
            return jsonify({
                'success': False,
                'message': 'Fecha del último caso es requerida'
            }), 400

        diagnostico = None

        if diagnostico_id not in (None, ''):
            try:
                diagnostico_id_int = int(diagnostico_id)
                if diagnostico_id_int <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({
                    'success': False,
                    'message': 'ID de diagnóstico inválido'
                }), 400

            diagnostico = BroteModel.obtener_diagnostico_por_id(diagnostico_id_int)
        elif diagnostico_nombre:
            diagnostico = BroteModel.obtener_diagnostico_por_nombre(diagnostico_nombre.strip())
        else:
            return jsonify({
                'success': False,
                'message': 'Debe proporcionar ID o nombre del diagnóstico'
            }), 400

        if not diagnostico:
            return jsonify({
                'success': False,
                'message': 'Diagnóstico no encontrado'
            }), 404

        periodo_incubacion = diagnostico.get('periodo_incubacion')
        try:
            periodo_incubacion = int(periodo_incubacion)
            if periodo_incubacion <= 0:
                raise ValueError
        except (TypeError, ValueError):
            logger.warning(
                "Periodo de incubación inválido para diagnóstico %s: %s",
                diagnostico.get('iddiag'),
                periodo_incubacion
            )
            return jsonify({
                'success': False,
                'message': 'Periodo de incubación no válido para el diagnóstico seleccionado'
            }), 422

        try:
            fecha_base = datetime.strptime(fecha_ultimo_caso, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400

        fecha_alta = fecha_base + timedelta(days=periodo_incubacion)

        return jsonify({
            'success': True,
            'fecha_probable_alta': fecha_alta.strftime('%Y-%m-%d'),
            'periodo_incubacion': periodo_incubacion,
            'diagnostico': diagnostico['nombre']
        }), 200

    except Exception as e:
        logger.error(f"Error al calcular fecha probable de alta: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error interno al calcular la fecha de alta'
        }), 500




# @brotes_bp.route('/calcular_fecha_alta', methods=['POST'])
# @csrf.exempt
# def calcular_fecha_alta():    
#     logger = current_app.logger
    
#     try:
#         data = request.get_json()
        
#         fecha_ultimo_caso = data.get('fecha_ultimo_caso')
#         periodo_incubacion = data.get('periodo_incubacion')
        
#         logger.info(f"Calculando fecha alta - Último caso: {fecha_ultimo_caso}, Periodo: {periodo_incubacion}")
        

#         if not fecha_ultimo_caso:
#             return jsonify({'error': 'Falta la fecha del último caso'}), 400
        
#         if not periodo_incubacion:
#             return jsonify({'error': 'Falta el periodo de incubación'}), 400
        

#         fecha_alta = BroteModel.calcular_fecha_probable_alta(
#             fecha_ultimo_caso, 
#             periodo_incubacion
#         )
        
#         if not fecha_alta:
#             return jsonify({'error': 'No se pudo calcular la fecha'}), 400
        
        
#         fecha_alta_str = fecha_alta.strftime('%Y-%m-%d')
#         fecha_alta_legible = fecha_alta.strftime('%d/%m/%Y')
        
#         logger.info(f"Fecha calculada: {fecha_alta_str}")
        
#         return jsonify({
#             'fecha_probable_alta': fecha_alta_str,
#             'mensaje': fecha_alta_legible
#         }), 200
        
#     except Exception as e:
#         logger.error(f"Error al calcular fecha de alta: {e}", exc_info=True)
#         return jsonify({'error': str(e)}), 500


#Funcion axuliar para create y update brotes
# Obtener y limpiar los campos del formulario
def obtener_datos_brote_y_rel(form):    
    lugar = form.get('lugar', '').strip().upper()
    institucion = form.get('institucion', '').strip()
    tipoevento = form.get('evento', '').strip()
    municipio = form.get('municipio', '').strip()
    jurisdiccion = form.get('juris', '').strip()
    diagsospecha = form.get('diagsospecha', '').strip()           
    
    if not tipoevento:
        raise ValueError("El campo 'tipoevento' es obligatorio y no puede estar vacío.")
    
    idtipoevento = BroteModel.get_catalog_id('tipoeventos', tipoevento, 'idtipoevento')
        
    idinstitucion = BroteModel.get_catalog_id('instituciones', institucion, 'idinstitucion')    
    idmunicipio = BroteModel.get_catalog_id('municipios', municipio, 'idmunicipio')
    idjurisdiccion = BroteModel.get_catalog_id('jurisdicciones', jurisdiccion, 'idjurisdiccion')
    iddiag = BroteModel.get_catalog_id('diagsospecha', diagsospecha, 'iddiag')        
    
    if not all([idtipoevento, idinstitucion, idmunicipio, idjurisdiccion, iddiag]):
        raise ValueError('Uno o más campos de catálogo no son válidos')
    
    datos_brote = {
        'lugar': lugar or '',
        'unidadnotif': form.get('unidad', '').strip().upper(),
        'domicilio': form.get('domicilio', '').strip().upper(),
        'localidad': form.get('localidad', '').strip().upper(),
        'fechnotifica': form.get('fechnotifica') or None,
        'fechinicio': form.get('fecha_inicio') or None,
        'casosprob': form.get('probables') or 0,
        'casosconf': form.get('confirmados') or 0,
        'defunciones': form.get('defunciones') or 0,
        'fechultimocaso': form.get('fecha_ultimo_caso') or None,
        'resultado': form.get('resultado', '').strip().upper(),
        'fechalta': form.get('fecha_alta') or None,
        'fecha_consulta': form.get('fecha_consulta') or None,
        'observaciones': form.get('observaciones', 'sin').strip().upper(),
        'pobmascexp': form.get('pobmascexpuesta') or 0,
        'pobfemexp': form.get('pobfemexpuesta') or 0
    }
    
    ids_rel = {
        'idtipoevento': idtipoevento,
        'idinstitucion': idinstitucion,
        'idmunicipio': idmunicipio,
        'idjurisdiccion': idjurisdiccion,
        'iddiag': iddiag
    }

    return datos_brote, ids_rel




#-------------  1. FUNCIONES CREATE --------------------------------------
#Endpoint para mostrar formulario y cargar catalogos
@brotes_bp.route('/registrar', methods=['GET'], endpoint='formulario')
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def mostrar_formulario_brote():
    catalogos = BroteModel.obtener_catalogos()
    return render_template('brotes/register.html', **catalogos)



#Endpoint para registrar datos al formulario incluyendo documentos
@brotes_bp.route('/registrar_con_documentos', methods=['POST', 'GET'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def registrar_con_documentos():
    logger = current_app.logger
    form = request.form

    try:
        logger.info(f"Iniciando registro de brote por usuario: {current_user.nombre}")

        # Obtener los datos y los IDs para el brote a actualizar
        datos_brote, ids_rel = obtener_datos_brote_y_rel(form)
               
        brote_id = BroteModel.insertar_brote(datos_brote, ids_rel)
        logger.info(f"Brote {brote_id} creado exitosamente por {current_user.nombre} (ID: {current_user.id})")

        # Procesar documentos
        documentos_procesados = 0
        documentos_fallidos = 0
        i = 0

        while f'documentos[{i}][archivo]' in request.files:
            archivo = request.files[f'documentos[{i}][archivo]']
            tipo = form.get(f'documentos[{i}][tipo]', '')
            folio = form.get(f'documentos[{i}][folio]', '') or None
            fecha = form.get(f'documentos[{i}][fecha]', '') or None

            nombre_archivo = archivo.filename if hasattr(archivo, 'filename') else 'Sin nombre'

            try:
                BroteModel.guardar_documento(brote_id, archivo, tipo, folio, fecha)
                documentos_procesados += 1
                logger.info(f"Documento guardado: {nombre_archivo} (Tipo: {tipo}, Brote ID: {brote_id})")

            except Exception as e:
                documentos_fallidos += 1
                logger.warning(f"Documento omitido ({nombre_archivo}): {str(e)}", exc_info=True)

            i += 1

        logger.info(f"Registro completado - Brote ID: {brote_id}, "
                   f"Documentos procesados: {documentos_procesados}, "
                   f"Documentos fallidos: {documentos_fallidos}")

        return jsonify({
            'message': 'Brote registrado correctamente',
            'brote_id': brote_id,
            'documentos_procesados': documentos_procesados
        }), 201

    except Exception as e:
        logger.error(f"Error al registrar brote: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500




#-------------  2. FUNCIONES READ --------------------------------------
#End point para listar brotes
@brotes_bp.route('/lista', methods=['GET'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def lista_brotes():
    from datetime import datetime, timedelta

    # Obtener parámetros de filtro desde la URL
    rango = request.args.get('rango')
    fecha_inicio_str = request.args.get('fecha_inicio')
    fecha_fin_str = request.args.get('fecha_fin')

    fecha_inicio = None
    fecha_fin = None

    # Calcular fechas según el rango predefinido
    if rango and rango != 'todos':
        hoy = datetime.now().date()

        if rango == 'hoy':
            fecha_inicio = fecha_fin = hoy
        elif rango == 'ayer':
            ayer = hoy - timedelta(days=1)
            fecha_inicio = fecha_fin = ayer
        elif rango == 'ultima_semana':
            fecha_inicio = hoy - timedelta(days=7)
            fecha_fin = hoy
        elif rango == 'ultimo_mes':
            fecha_inicio = hoy - timedelta(days=30)
            fecha_fin = hoy
        elif rango == 'ultimo_trimestre':
            fecha_inicio = hoy - timedelta(days=90)
            fecha_fin = hoy
        elif rango == 'ultimo_semestre':
            fecha_inicio = hoy - timedelta(days=180)
            fecha_fin = hoy
        elif rango == 'ultimo_anio':
            fecha_inicio = hoy - timedelta(days=365)
            fecha_fin = hoy

    # Fechas personalizadas
    elif fecha_inicio_str and fecha_fin_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido', 'error')
            fecha_inicio = fecha_fin = None

    # Obtener brotes filtrados o todos
    if fecha_inicio and fecha_fin:
        brotes = BroteModel.obtener_brotes_por_fecha_inicio(fecha_inicio, fecha_fin)
    else:
        brotes = BroteModel.obtener_todos_los_brotes()

    return render_template('brotes/lista.html', brotes=brotes)



#End ponint para exportar datos de la lista de brotes alta pendientes a excel
@brotes_bp.route('/exportar_excel_lista', methods=['GET'])
@login_required
def exportar_excel_lista():
    logger = current_app.logger
    try:        
        brotes = BroteModel.obtener_todos_los_brotes()
                
        if not brotes: # Validar que hay datos
            return jsonify({'error': 'No hay datos para exportar'}), 404
                
        df = pd.DataFrame(brotes)                      
        
        output = io.BytesIO()
        
        # Columnas que requieren formato de fecha
        date_columns = ['Fecha inicio','Fecha notificación','Fecha Última Caso', 'Fecha Alta', 'Fecha consulta', 'Fecha Notinmed Inicial', 'Fecha Notinmed Final']
        datetime_columns = []  # Para fechas con hora (agregar cuando sea necesario)
        
        # Crear archivo Excel con formato mejorado
        with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
            df.to_excel(writer, sheet_name='Brotes', index=False)
            
            # Obtener el workbook y worksheet para aplicar formato
            workbook = writer.book
            worksheet = writer.sheets['Brotes']
            
            # Definir formatos
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1
            })
            
            # Formato específico para fechas
            date_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'num_format': 'dd/mm/yyyy'
            })
            
            # Formato para datetime (fecha y hora)
            datetime_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'num_format': 'dd/mm/yyyy hh:mm'
            })
            
            # Aplicar formato a headers
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustar ancho de columnas
            for i, col in enumerate(df.columns):
                # Calcular ancho basado en el contenido
                max_len = max(
                    df[col].astype(str).map(len).max(),  # máximo en la columna
                    len(str(col))  # longitud del header
                ) + 2
                worksheet.set_column(i, i, min(max_len, 50))  # máximo 50 caracteres
            
            # Aplicar formato a todas las celdas de datos con formato específico para fechas
            for row in range(1, len(df) + 1):
                for col in range(len(df.columns)):
                    col_name = df.columns[col]
                    cell_value = df.iloc[row-1, col]
                    
                    # Determinar el formato según el nombre exacto de la columna
                    if col_name in date_columns:
                        # Convertir a fecha si es string
                        if isinstance(cell_value, str) and cell_value:
                            try:
                                cell_value = pd.to_datetime(cell_value).date()
                            except:
                                pass
                        worksheet.write(row, col, cell_value, date_format)
                    elif col_name in datetime_columns:
                        # Convertir a datetime si es string
                        if isinstance(cell_value, str) and cell_value:
                            try:
                                cell_value = pd.to_datetime(cell_value)
                            except:
                                pass
                        worksheet.write(row, col, cell_value, datetime_format)
                    else:
                        worksheet.write(row, col, cell_value, cell_format)
        
        # Preparar para descarga
        output.seek(0)
        
        # Generar nombre de archivo con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'brotes_completos_{timestamp}.xlsx'
        
        return send_file(
            output, 
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        # Log del error usando el logging configurado        
        logger.error(f"Error exportando Excel: {str(e)}")
        return jsonify({'error': 'Error interno del servidor al generar el archivo'}), 500




@brotes_bp.route('/exportar_excel_alta_pendientes', methods=['GET'])
@login_required
def exportar_excel_alta_pendientes():
    brotes = BroteModel.obtener_edo_actual_pendientes()

    df = pd.DataFrame(brotes)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Brotes', index=False)

    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='brotes_pendiente_alta.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    

 
@brotes_bp.route('/exportar_excel_activos', methods=['GET'])
@login_required
def exportar_excel_activos():
    brotes = BroteModel.obtener_edo_actual_activos()

    df = pd.DataFrame(brotes)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Brotes', index=False)

    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='brotes_activos.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    


# Endpoint para mostrar dashboard con estadísticas
@brotes_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():    
    try:
        # Obtiene parámetro GET
        institucion_param = request.args.get("institucion")

        # Validación y conversión del parámetro institución
        institucion = None
        if institucion_param and institucion_param.strip():
            if institucion_param.isdigit():
                institucion = int(institucion_param)
            else:
                flash("ID de institución debe ser numérico", "warning")
        
        # Obtener todos los datos necesarios para el dashboard
        instituciones = brote_model.BroteModel.obtener_instituciones()
        datos = brote_model.BroteModel.obtener_estadisticas(institucion)
        resumen = brote_model.BroteModel.obtener_resumen_instituciones(institucion)   
        resumen_eventos = brote_model.BroteModel.obtener_resumen_eventos(institucion)
        
        # Validar que la institución seleccionada existe (si se especificó una)
        if institucion:
            instituciones_ids = [inst['idinstitucion'] for inst in instituciones]
            if institucion not in instituciones_ids:
                flash("La institución seleccionada no existe", "warning")
                institucion = None
        
        return render_template('brotes/dashboard.html', 
                             datos=datos, 
                             instituciones=instituciones, 
                             institucion_seleccionada=institucion,
                             resumen=resumen,
                             resumen_eventos=resumen_eventos
                             )
    
    except ValueError as e:
        # Error de validación de parámetros
        flash(f"Error en los parámetros: {str(e)}", "error")
        return redirect(url_for('brotes.dashboard'))
    
    # except Exception as e:
    #     # Error general
    #     flash("Error al cargar el dashboard. Intente nuevamente.", "error")
    #     logging.error(f"Error en dashboard: {str(e)}")
    #     return redirect(url_for('brotes.login'))  # o la ruta principal que tengas


@brotes_bp.route('/brotes_completos', methods=['GET'])
@login_required
def brotes_completos():
    brotes = BroteModel.obtener_todos_los_brotes()
    return render_template(
        'brotes/lista.html',
        brotes=brotes,
        titulo="Listado Nominal de Brotes",
        encabezado="Listado Nominal de Brotes",
        export_url=url_for('brotes_bp.exportar_excel_lista')
    )
    

#End point para listar brotes PENDIENTE ALTA
@brotes_bp.route('/brotes_pendientes', methods=['GET'])
@login_required
def brotes_pendientes():
    brotes = BroteModel.obtener_edo_actual_pendientes()
    return render_template(
        'brotes/reports.html',
        brotes=brotes,
        titulo="Brotes pendientes de alta",
        encabezado="Brotes pendientes de alta",
        export_url=url_for('brotes_bp.exportar_excel_alta_pendientes')
    )


@brotes_bp.route('/brotes_activos', methods=['GET'])
@login_required
def brotes_activos():
    brotes = BroteModel.obtener_edo_actual_activos()
    return render_template(
        'brotes/reports.html',
        brotes=brotes,
        titulo="Brotes activos",
        encabezado="Brotes activos",
        export_url=url_for('brotes_bp.exportar_excel_activos')
    )



#-------------  3. FUNCIONES UPDATE --------------------------------------
#Endpoint para mostrar datos en el formulario y poder ACTUALIZAR
@brotes_bp.route('/<int:idbrote>/editar', methods=['GET'])
@login_required
def editar_brote(idbrote):
    logger = current_app.logger
    # Detectar de dónde viene la solicitud
    origen = request.args.get('origen', 'lista_brotes')  # Por defecto lista_brotes
    
    # Capturar estado de paginación si existe
    state = request.args.get('state')
    
    
    try:
        catalogos = BroteModel.obtener_catalogos()    
        brote = BroteModel.obtener_brote(idbrote)
        
        if not brote:
            flash('El brote especificado no existe', 'error')
            return redirect_to_origin(origen, state)            
        
        documentos = BroteModel.obtener_documentos_por_brote(idbrote)
    
    except Exception as e:
        logger.error(f"Error al cargar brote {idbrote}: {e}", exc_info=True)
        flash('Error al cargar el brote', 'error')
        return redirect_to_origin(origen, state)
    
    
    return render_template('brotes/edit.html',  
                             **catalogos, 
                             brote=brote, 
                             documentos=documentos, 
                             origen=origen,
                             state=state)



def redirect_to_origin(origen, state=None):
    """
    Helper function para redirigir al origen correcto con estado preservado
    """
    if origen == 'brotes_pendientes':
        url = url_for('brotes_bp.brotes_pendientes')
    elif origen == 'brotes_activos':
        url = url_for('brotes_bp.brotes_activos')
    else:
        url = url_for('brotes_bp.lista_brotes')
    
    # Agregar parámetro de estado si existe
    if state:
        url += f'?return_state={state}'
    
    return redirect(url)



#Endpoint para ACTUALIZAR datos
@brotes_bp.route('/actualizar_brote/<int:idbrote>', methods=['POST'])
@login_required
@rol_requerido('super_administrador','jefe_departamento', 'coordinador_estatal')
def actualizar_brote(idbrote):
    logger = current_app.logger
    origen = request.form.get('origen', 'lista_brotes')  # Obtener origen del form
    state = request.form.get('state')  # Capturar estado de paginación    
    form = request.form
    files = request.files          
    
    if current_user.rol not in ['super_administrador','jefe_departamento', 'coordinador_estatal']:
        return jsonify({'error': 'No tienes permisos', 'success': False}), 403
    
        
    try:
        # Log del inicio de la operación
        logger.info(f"Intentando actualizar brote {idbrote} por {current_user.nombre} (ID: {current_user.id})")        

        #Obtener los datos y los IDs para el brote a actualizar
        datos_brote, ids_rel = obtener_datos_brote_y_rel(form)        

        # Validación de idtipoevento (asegurarse de que no sea vacío o None)
        if not ids_rel.get('idtipoevento'):
            raise ValueError("El campo 'idtipoevento' es obligatorio y debe tener un valor válido.")

        BroteModel.actualizar_brote(idbrote, datos_brote, ids_rel)
        logger.info(f"Brote {idbrote} actualizado exitosamente por {current_user.nombre} (ID: {current_user.id})")
       
        # Documentos existentes
        i = 0
        while f'existentes[{i}][iddocumento]' in form:
            iddocumento = form.get(f'existentes[{i}][iddocumento]')            
            folio = form.get(f'existentes[{i}][folio]')
            fecha = form.get(f'existentes[{i}][fecha]') or None
            
            existing_folio, existing_fecha = BroteModel.obtener_folio_y_fecha(iddocumento)
            
            # Validación para actualizar si el folio o la fecha han cambiado                                    
            if any([folio != existing_folio, fecha != existing_fecha]):
                        BroteModel.actualizar_documento(
                            iddocumento,
                            folio=folio,
                            fecha=fecha
                        )
            i += 1

        # Documentos nuevos
        j = 0
        while f'nuevos[{j}][archivo]' in files:
            archivo = files.get(f'nuevos[{j}][archivo]')
            tipo = form.get(f'nuevos[{j}][tipo]')
            folio = form.get(f'nuevos[{j}][folio]') or None
            fecha = form.get(f'nuevos[{j}][fecha]') or None

            BroteModel.guardar_documento(idbrote, archivo, tipo, folio, fecha)            
            j += 1
        
        # Determinar URL de redirección según el origen
        
        redirect_url = build_redirect_url(origen, state)
        origen_texto = get_origen_texto(origen)                     
        
        # Respuesta exitosa con URL de redirección
        return jsonify({
            'message': 'Brote y documentos actualizados correctamente',
            'redirect_url': redirect_url,
            'origen_texto': origen_texto,
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Error al actualizar el brote {idbrote} o documentos: {e}", exc_info=True)
        
        # En caso de error, también incluir la URL de redirección para volver al formulario
        if origen == 'brotes_pendientes':
            form_url = url_for('brotes_bp.editar_brote', idbrote=idbrote, origen='brotes_pendientes')
        elif origen == 'brotes_activos':
            form_url = url_for('brotes_bp.editar_brote', idbrote=idbrote, origen='brotes_activos')
        else:
            form_url = url_for('brotes_bp.editar_brote', idbrote=idbrote, origen='lista_brotes')
            
        return jsonify({
            'error': str(e),
            'form_url': form_url,
            'success': False
        }), 500
        
        
    
def build_redirect_url(origen, state):
    """Construir URL de redirección con estado preservado"""
    if origen == 'brotes_pendientes':
        url = url_for('brotes_bp.brotes_pendientes')
    elif origen == 'brotes_activos':
        url = url_for('brotes_bp.brotes_activos')
    else:
        url = url_for('brotes_bp.lista_brotes')
    
    if state:
        url += f'?return_state={state}'
    
    return url


def build_edit_url(idbrote, origen, state):
        """Construir URL de edición con estado preservado"""
        url = url_for('brotes_bp.editar_brote', idbrote=idbrote)
        params = [f'origen={origen}']
        
        if state:
            params.append(f'state={state}')
        
        return url + '?' + '&'.join(params)


def get_origen_texto(origen):
        """Obtener texto descriptivo del origen"""
        if origen == 'brotes_pendientes':
            return 'Brotes Pendientes'
        elif origen == 'brotes_activos':
            return 'Brotes Activos'
        else:
            return 'Lista de Brotes'



@brotes_bp.route('/eliminar/<int:idbrote>', methods=['DELETE'])
@login_required
@rol_requerido('super_administrador', 'coordinador_estatal')
def eliminar_brote(idbrote):
    logger = current_app.logger
    try:
        logger.info(f"Intentando eliminar brote {idbrote}")  # ← Agregar log         
        usuario_id = session.get('usuario_id')
        
        brote = BroteModel.obtener_brote(idbrote)
        if not brote:
            return jsonify({'error': f'Brote {idbrote} no encontrado'}), 404
        
        BroteModel.eliminar_brote(idbrote)
        logger.info(f"Brote {idbrote} eliminado por {current_user.nombre} (ID: {current_user.id})")
        
        return jsonify({'message': 'Brote eliminado correctamente', 'brote_id': idbrote}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': f'Error al eliminar: {str(e)}'}),500




# Ruta para descargar documento
from flask import send_from_directory

@brotes_bp.route('/documento/descargar/<int:doc_id>')
@login_required
def descargar_documento(doc_id):
    logger = current_app.logger
    
    try:
        # Obtener información del documento
        documento = BroteModel.obtener_documento_por_id(doc_id)
        
        if not documento:
            logger.error(f"Documento {doc_id} no encontrado en BD")
            flash('Documento no encontrado', 'error')
            return redirect(request.referrer or url_for('brotes_bp.dashboard'))
        
                # Verificar longitud
        if isinstance(documento, (tuple, list)):
            logger.info(f"Longitud del documento: {len(documento)}")
            for i, valor in enumerate(documento):
                logger.info(f"  [{i}] = {valor}")
        
        # Índices correctos según tu estructura
        nombre_archivo = documento['nombre_archivo']
        ruta_archivo = documento['path']
        
        logger.info(f"Documento: {nombre_archivo}")
        logger.info(f"Ruta BD: {ruta_archivo}")
        
        # Remover "static/" si existe
        if ruta_archivo.startswith('static/'):
            ruta_relativa = ruta_archivo[7:]  # Quitar "static/"
        elif ruta_archivo.startswith('static\\'):
            ruta_relativa = ruta_archivo[7:]  # Quitar "static\"
        else:
            ruta_relativa = ruta_archivo
        
        # Normalizar barras
        ruta_relativa = ruta_relativa.replace('/', os.sep).replace('\\', os.sep)
        
        # Separar directorio y nombre de archivo
        directorio = os.path.dirname(ruta_relativa)
        archivo = os.path.basename(ruta_relativa)
        
        # Ruta completa del directorio
        directorio_completo = os.path.join(current_app.static_folder, directorio)
        
        logger.info(f"Directorio: {directorio_completo}")
        logger.info(f"Archivo: {archivo}")
        
        # Verificar que existe
        ruta_completa = os.path.join(directorio_completo, archivo)
        if not os.path.exists(ruta_completa):
            logger.error(f"Archivo no existe: {ruta_completa}")
            flash('El archivo no existe en el servidor', 'error')
            return redirect(request.referrer or url_for('brotes_bp.dashboard'))
        
        logger.info(f"Descargando por: {current_user.nombre if current_user.is_authenticated else 'Anónimo'}")
        
        return send_from_directory(
            directorio_completo,
            archivo,
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        logger.error(f"Error al descargar documento {doc_id}: {e}", exc_info=True)
        flash(f'Error al descargar: {str(e)}', 'error')
        return redirect(request.referrer or url_for('brotes_bp.dashboard'))



# Ruta para eliminar documento
@brotes_bp.route('/documento/eliminar/<int:doc_id>', methods=['DELETE'])
@login_required
@rol_requerido('super_administrador', 'coordinador_estatal')
@csrf.exempt
def eliminar_documento(doc_id):
    logger = current_app.logger
    
    try:        
        documento = BroteModel.obtener_documento_por_id(doc_id)
        
        if not documento:
            return jsonify({
                'success': False,
                'mensaje': f'No se encontró el documento con ID {doc_id}'
            }), 404  
                
        nombre_archivo = documento['nombre_archivo']
        
        # Eliminar documento
        BroteModel.eliminar_documento(doc_id)
        
        logger.info(f"Documento {doc_id} ({nombre_archivo}) eliminado por {current_user.nombre} (ID: {current_user.id})")
        
        return jsonify({
            'success': True,
            'mensaje': 'Documento eliminado correctamente',
            'doc_id': doc_id
        }), 200
        
    except ValueError as ve:
        logger.warning(f"Error de validación: {ve}")
        return jsonify({
            'success': False,
            'mensaje': str(ve)
        }), 400
        
    except Exception as e:
        logger.error(f"Error al eliminar documento {doc_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'mensaje': f'Error al eliminar: {str(e)}'
        }), 500




# ============================================================================
# CRUD DE DIAGNÓSTICOS DE SOSPECHA
# ============================================================================

# ==================== CREATE ====================
@brotes_bp.route('/diagnosticos/registrar', methods=['GET'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def mostrar_formulario_diagnostico():
    """Muestra el formulario para crear un nuevo diagnóstico"""
    return render_template('diagnosticos/register.html')


@brotes_bp.route('/diagnosticos/registrar', methods=['POST'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def crear_diagnostico():
    """Crea un nuevo diagnóstico de sospecha"""
    logger = current_app.logger

    try:
        nombre = request.form.get('nombre', '').strip().upper()
        periodo_incubacion = request.form.get('periodo_incubacion', '').strip()

        # Validaciones
        if not nombre:
            return jsonify({'error': 'El nombre es obligatorio'}), 400

        if not periodo_incubacion or not periodo_incubacion.isdigit():
            return jsonify({'error': 'El periodo de incubación debe ser un número'}), 400

        periodo_incubacion = int(periodo_incubacion)

        if periodo_incubacion <= 0:
            return jsonify({'error': 'El periodo de incubación debe ser mayor a 0'}), 400

        # Crear diagnóstico
        diagnostico_id = BroteModel.crear_diagnostico(nombre, periodo_incubacion)

        logger.info(f"Diagnóstico creado: {nombre} (ID: {diagnostico_id})")

        return jsonify({
            'message': 'Diagnóstico creado correctamente',
            'diagnostico_id': diagnostico_id
        }), 201

    except Exception as e:
        logger.error(f"Error al crear diagnóstico: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ==================== READ ====================
@brotes_bp.route('/diagnosticos/lista', methods=['GET'])
@login_required
def lista_diagnosticos():
    """Lista todos los diagnósticos de sospecha"""
    try:
        diagnosticos = BroteModel.obtener_todos_diagnosticos()
        return render_template('diagnosticos/lista.html', diagnosticos=diagnosticos)
    except Exception as e:
        current_app.logger.error(f"Error al listar diagnósticos: {str(e)}")
        flash('Error al cargar la lista de diagnósticos', 'error')
        return redirect(url_for('brotes_bp.dashboard'))


# ==================== UPDATE ====================
@brotes_bp.route('/diagnosticos/<int:iddiag>/editar', methods=['GET'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def editar_diagnostico(iddiag):
    """Muestra el formulario de edición de un diagnóstico"""
    logger = current_app.logger

    try:
        diagnostico = BroteModel.obtener_diagnostico_por_id(iddiag)

        if not diagnostico:
            flash('El diagnóstico especificado no existe', 'error')
            return redirect(url_for('brotes_bp.lista_diagnosticos'))

        return render_template('diagnosticos/edit.html', diagnostico=diagnostico)

    except Exception as e:
        logger.error(f"Error al cargar diagnóstico {iddiag}: {str(e)}", exc_info=True)
        flash('Error al cargar el diagnóstico', 'error')
        return redirect(url_for('brotes_bp.lista_diagnosticos'))


@brotes_bp.route('/diagnosticos/actualizar/<int:iddiag>', methods=['POST'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def actualizar_diagnostico(iddiag):
    """Actualiza un diagnóstico existente"""
    logger = current_app.logger

    try:
        nombre = request.form.get('nombre', '').strip().upper()
        periodo_incubacion = request.form.get('periodo_incubacion', '').strip()

        # Validaciones
        if not nombre:
            return jsonify({'error': 'El nombre es obligatorio'}), 400

        if not periodo_incubacion or not periodo_incubacion.isdigit():
            return jsonify({'error': 'El periodo de incubación debe ser un número'}), 400

        periodo_incubacion = int(periodo_incubacion)

        if periodo_incubacion <= 0:
            return jsonify({'error': 'El periodo de incubación debe ser mayor a 0'}), 400

        # Actualizar diagnóstico
        BroteModel.actualizar_diagnostico(iddiag, nombre, periodo_incubacion)

        logger.info(f"Diagnóstico {iddiag} actualizado: {nombre}")

        return jsonify({
            'message': 'Diagnóstico actualizado correctamente',
            'redirect_url': url_for('brotes_bp.lista_diagnosticos')
        }), 200

    except Exception as e:
        logger.error(f"Error al actualizar diagnóstico {iddiag}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ==================== DELETE ====================
@brotes_bp.route('/diagnosticos/eliminar/<int:iddiag>', methods=['DELETE'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento')
def eliminar_diagnostico(iddiag):
    """Elimina un diagnóstico de sospecha"""
    logger = current_app.logger

    try:
        diagnostico = BroteModel.obtener_diagnostico_por_id(iddiag)

        if not diagnostico:
            return jsonify({
                'error': f'Diagnóstico {iddiag} no encontrado'
            }), 404

        nombre = diagnostico['nombre']

        BroteModel.eliminar_diagnostico(iddiag)

        logger.info(f"Diagnóstico {iddiag} ({nombre}) eliminado")

        return jsonify({
            'message': 'Diagnóstico eliminado correctamente',
            'diagnostico_id': iddiag
        }), 200

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400

    except Exception as e:
        logger.error(f"Error al eliminar diagnóstico {iddiag}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error al eliminar: {str(e)}'}), 500

from flask import Blueprint, render_template, request, jsonify, send_file, url_for, flash, redirect, current_app
from flask_login import current_user
from app.models import brote_model
from app.models.brote_model import BroteModel
import logging
import io
from app.forms import BroteForm

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



#Funcion axuliar para create y update brotes
def obtener_datos_brote_y_rel(form):
    # Obtener y limpiar los campos del formulario
    lugar = form.get('lugar', '').strip().upper()
    institucion = form.get('institucion', '').strip()
    tipoevento = form.get('evento', '').strip()
    municipio = form.get('municipio', '').strip()
    jurisdiccion = form.get('juris', '').strip()
    diagsospecha = form.get('diagsospecha', '').strip()
    
        
    # Verificar que tipoevento no esté vacío
    if not tipoevento:
        raise ValueError("El campo 'tipoevento' es obligatorio y no puede estar vacío.")

    
    try:
        # Obtener los IDs correspondientes para los catálogos
        idtipoevento = BroteModel.get_catalog_id('tipoeventos', tipoevento, 'idtipoevento')        
        idinstitucion = BroteModel.get_catalog_id('instituciones', institucion, 'idinstitucion')    
        idmunicipio = BroteModel.get_catalog_id('municipios', municipio, 'idmunicipio')
        idjurisdiccion = BroteModel.get_catalog_id('jurisdicciones', jurisdiccion, 'idjurisdiccion')
        iddiag = BroteModel.get_catalog_id('diagsospecha', diagsospecha, 'iddiag')
        
    except Exception as e:
        raise ValueError(f"Error al obtener IDs de catálogo: {str(e)}")
    
    
    
        
    # Validar que todos los campos de catálogo sean válidos
    if not all([idtipoevento, idinstitucion, idmunicipio, idjurisdiccion, iddiag]):
        raise ValueError('Uno o más campos de catálogo no son válidos')

    # Crear el diccionario con los datos del brote
    datos_brote = {
        'lugar': lugar or '',
        'unidadnotif': form.get('unidad', '').strip().upper(),
        'domicilio': form.get('domicilio', '').strip().upper(),
        'localidad': form.get('localidad', '').strip().upper(),
        'fechnotifica': form.get('fechnotifica') or None,
        'fechinicio': form.get('fecha_inicio') or 0,
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

    # Crear el diccionario con los IDs de las relaciones
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
def mostrar_formulario_brote():
    catalogos = BroteModel.obtener_catalogos()
    return render_template('brotes/register.html', **catalogos)



#Endpoint para registrar datos al formulario incluyendo documentos
@brotes_bp.route('/registrar_con_documentos', methods=['POST', 'GET'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento')
def registrar_con_documentos():
    logger = current_app.logger
    form = request.form

    try:
        # Obtener los datos y los IDs para el brote a actualizar
        datos_brote, ids_rel = obtener_datos_brote_y_rel(form)
        
        #4. Insertar brote
        brote_id = BroteModel.insertar_brote(datos_brote, ids_rel)

        #5. Procesar documentos desde FormData
        i = 0
        while f'documentos[{i}][archivo]' in request.files:
            archivo = request.files[f'documentos[{i}][archivo]']
            tipo = form.get(f'documentos[{i}][tipo]', '')
            folio = form.get(f'documentos[{i}][folio]', '') or None
            fecha = form.get(f'documentos[{i}][fecha]', '') or None                       

            try:
                BroteModel.guardar_documento(brote_id, archivo, tipo, folio, fecha)
                
            except Exception as e:
                nombre_archivo = archivo.filename if hasattr(archivo, 'filename') else str(archivo)
                logger.warning(f"Documento omitido ({nombre_archivo}): {e}", exc_info=True)                
            
            i += 1
            
        return jsonify({'message': 'Brote registrado correctamente'}), 201

    except Exception as e:
        logger.error(f"Error al registrar brote: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500




#-------------  2. FUNCIONES READ --------------------------------------
#End point para listar brotes
@brotes_bp.route('/lista', methods=['GET'])
@login_required
def lista_brotes():
    brotes = BroteModel.obtener_todos_los_brotes()
    return render_template('brotes/lista.html', brotes=brotes)



#End ponint para exportar datos de la lista de brotes alta pendientes a excel
@brotes_bp.route('/exportar_excel_lista', methods=['GET'])
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
def exportar_excel_activos():
    brotes = BroteModel.obtener_edo_actual_activos()

    df = pd.DataFrame(brotes)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Brotes', index=False)

    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='brotes_pendiente_alta.xlsx',
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
                             state=state)  # Pasar el estado al template



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
@rol_requerido('jefe_departamento', 'coordinador_estatal')
def actualizar_brote(idbrote):
    logger = current_app.logger
    
    origen = request.form.get('origen', 'lista_brotes')  # Obtener origen del form
    state = request.form.get('state')  # Capturar estado de paginación
    
    form = request.form
    files = request.files   
        
    try:
        #Obtener los datos y los IDs para el brote a actualizar
        datos_brote, ids_rel = obtener_datos_brote_y_rel(form)
        
         # Validación de idtipoevento (asegurarse de que no sea vacío o None)
        if not ids_rel.get('idtipoevento'):
            raise ValueError("El campo 'idtipoevento' es obligatorio y debe tener un valor válido.")
        
        BroteModel.actualizar_brote(idbrote, datos_brote, ids_rel)
                
            # Log del inicio de la operación
        logger.info(f"Iniciando actualización de brote {idbrote} por usuario {current_user.id if current_user.is_authenticated else 'Anónimo'}")
        logger.debug(f"Origen: {origen}, State: {state}")
       
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

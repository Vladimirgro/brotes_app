from flask import Blueprint, render_template, request, jsonify, send_file

from app.models import brote_model
from app.models.brote_model import BroteModel
import logging
import io
from app.forms import BroteForm

logger = logging.getLogger(__name__)


import pandas as pd
from app.middleware.auth_middleware import rol_requerido
from flask_login import login_required


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

    # Obtener los IDs correspondientes para tipoevento, institucion, municipio, jurisdiccion y diagsospecha
    idtipoevento = BroteModel.get_catalog_id('tipoeventos', tipoevento, 'idtipoevento')
    
    # Obtener los IDs correspondientes para las otras columnas utilizando la función genérica
    idinstitucion = BroteModel.get_catalog_id('instituciones', institucion, 'idinstitucion')    
    idmunicipio = BroteModel.get_catalog_id('municipios', municipio, 'idmunicipio')
    idjurisdiccion = BroteModel.get_catalog_id('jurisdicciones', jurisdiccion, 'idjurisdiccion')
    iddiag = BroteModel.get_catalog_id('diagsospecha', diagsospecha, 'iddiag')
        
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


#End ponint para exportar datos de la lista de brotes a excel
@brotes_bp.route('/exportar_excel', methods=['GET'])
def exportar_excel():
    brotes = BroteModel.obtener_brotes_completos()

    df = pd.DataFrame(brotes)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Brotes', index=False)

    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='brotes_completos.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    



#Endpoint para mostrar dashboard con estadisticas
@brotes_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    institucion = request.args.get('institucion', '')
    datos = brote_model.BroteModel.obtener_estadisticas(institucion)
    instituciones = brote_model.BroteModel.obtener_instituciones()
    return render_template('brotes/dashboard.html', datos=datos, instituciones=instituciones, institucion=institucion)



#End point para listar brotes PENDIENTE ALTA
@brotes_bp.route('/brotes_pendientes', methods=['GET'])
@login_required
def brotes_pendientes():
    brotes = BroteModel.obtener_edo_actual_pendientes()    
    return render_template('brotes/reports.html', brotes=brotes)


@brotes_bp.route('/brotes_activos', methods=['GET'])
@login_required
def brotes_activos():    
    brotes = BroteModel.obtener_edo_actual_activos()
    return render_template('brotes/reports.html', brotes=brotes)



#-------------  3. FUNCIONES UPDATE --------------------------------------
#Endpoint para mostrar datos en el formulario y poder ACTUALIZAR
@brotes_bp.route('/<int:idbrote>/editar', methods=['GET'])
def editar_brote(idbrote):
    catalogos = BroteModel.obtener_catalogos()    
    brote = BroteModel.obtener_brote(idbrote)    
    documentos = BroteModel.obtener_documentos_por_brote(idbrote)
    return render_template('brotes/edit.html',  **catalogos, brote=brote, documentos=documentos)




#Endpoint para ACTUALIZAR datos
@brotes_bp.route('/actualizar_brote/<int:idbrote>', methods=['POST'])
@login_required
@rol_requerido('super_administrador', 'jefe_departamento')
def actualizar_brote(idbrote):
    form = request.form
    files = request.files   
        
    try:
        #Obtener los datos y los IDs para el brote a actualizar
        datos_brote, ids_rel = obtener_datos_brote_y_rel(form)
        
         # Validación de idtipoevento (asegurarse de que no sea vacío o None)
        if not ids_rel.get('idtipoevento'):
            raise ValueError("El campo 'idtipoevento' es obligatorio y debe tener un valor válido.")
        
        BroteModel.actualizar_brote(idbrote, datos_brote, ids_rel)
                
        logger.debug(f"Datos del brote a actualizar: {datos_brote}") #PENDIENTE NO GUARDA OBSERVACIONES
        logger.debug(f"IDs de relaciones: {ids_rel}")
       
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
        
        #return redirect(url_for('brote_bp.actualizar_brote', idbrote=idbrote))
        return jsonify({'message': 'Brote y documentos actualizados correctamente'})
    
    except Exception as e:
        logger.error(f"Error al actualizar el brote {idbrote} o documentos: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

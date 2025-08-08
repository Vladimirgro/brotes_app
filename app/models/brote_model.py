from app.models.mysql_connection import MySQLConnection
import os
import uuid
import logging
from werkzeug.utils import secure_filename
from config import Config

# Crear logger para este módulo
logger = logging.getLogger(__name__)           
       

class BroteModel:
    #---------- METODOS AUXILIARES ------------------
    # 1. Query para mostrar catalotos en formulario
    @staticmethod  
    def obtener_catalogos():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT idtipoevento, nombre FROM tipoeventos ORDER BY nombre")
                tipoeventos = cursor.fetchall()

                cursor.execute("SELECT idinstitucion, nombre FROM instituciones ORDER BY idinstitucion")
                instituciones = cursor.fetchall()

                cursor.execute("SELECT idmunicipio, nombre FROM municipios ORDER BY nombre")
                municipios = cursor.fetchall()

                cursor.execute("SELECT idjurisdiccion, nombre FROM jurisdicciones ORDER BY idjurisdiccion")
                jurisdicciones = cursor.fetchall()

                cursor.execute("SELECT iddiag, nombre FROM diagsospecha ORDER BY nombre")
                diagnosticos = cursor.fetchall()
                
            return {
                "tipoeventos": tipoeventos, 
                "instituciones": instituciones, 
                "municipios":municipios, 
                "jurisdicciones":jurisdicciones, 
                "diagnosticos":diagnosticos}

        finally:
            conn.close()

    
    #2. Metodo auxiliar para procesar documentos en el controlador
    @classmethod    
    def guardar_documento(cls,brote_id, archivo, tipo, folio=None, fecha=None):
        if not archivo or not tipo:
            raise ValueError("Archivo o tipo no válidos")

        # Validación de extensión
        if not archivo.filename.lower().endswith(('.docx', '.doc', '.xlsx', '.xlsm', '.xls')):
            raise ValueError("Tipo de archivo no permitido")

        # Validación de tamaño (opcional)
        if archivo.content_length and archivo.content_length > 5 * 1024 * 1024:
            raise ValueError("Archivo demasiado grande (> 5MB)")

        nombre_original = secure_filename(archivo.filename)   
                    
        ruta_absoluta = os.path.join(Config.UPLOAD_FOLDER, f"brote_{brote_id}", nombre_original)
        ruta_relativa = f"static/uploads/brote_{brote_id}/{nombre_original}"

        os.makedirs(os.path.dirname(ruta_absoluta), exist_ok=True)
        archivo.save(ruta_absoluta)        
        
        # Ruta relativa para url_for        
        ruta_relativa = ruta_relativa.replace('\\', '/')        
        
        logger.info(f"Archivo guardado en: {ruta_relativa}")
        # Guardar en base de datos        
        cls.insertar_documento(brote_id, nombre_original, ruta_relativa, tipo, folio, fecha) 
        
           

#-----------------1. FUNCIONES CREATE -----------------------------------
    @staticmethod  
    #Insertar brotes registro nuevo
    def insertar_brote(data, ids):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO brotes (
                        idtipoevento, lugar, idinstitucion, unidadnotif, domicilio,
                        localidad, idmunicipio, idjurisdiccion, iddiag,
                        fechnotifica, fechinicio, casosprob, casosconf,
                        defunciones, fechultimocaso, fecha_consulta, resultado, fechalta,
                        observaciones, pobmascexp, pobfemexp                    
                    )
                    VALUES (
                        %(idtipoevento)s, %(lugar)s, %(idinstitucion)s, %(unidadnotif)s, %(domicilio)s,
                        %(localidad)s, %(idmunicipio)s, %(idjurisdiccion)s, %(iddiag)s,
                        %(fechnotifica)s, %(fechinicio)s, %(casosprob)s, %(casosconf)s,
                        %(defunciones)s, %(fechultimocaso)s, %(fecha_consulta)s,%(resultado)s, %(fechalta)s,
                        %(observaciones)s, %(pobmascexp)s, %(pobfemexp)s                    
                    )
                """
                cursor.execute(sql, {**data, **ids})
                brote_id = cursor.lastrowid  # <<< Aquí obtenemos el ID insertado            
                conn.commit()
                logger.info(f"Brote insertado con ID {brote_id}")
                return brote_id  # <<< Lo retornamos
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    
    
    @staticmethod  
    #Insertar documentos con id_brote registro nuevo
    def insertar_documento(brote_id, nombre_archivo, path, tipo, folio=None, fecha=None):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO documentos (
                        brote_id, 
                        nombre_archivo, 
                        path, 
                        tipo_notificacion,
                        folionotinmed,
                        fechnotinmed,
                        fechacarga,
                        fechmodificacion
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """
                cursor.execute(sql, (
                    brote_id, nombre_archivo, path, tipo, folio, fecha
                ))
                conn.commit()
                logger.info(f"Documento '{nombre_archivo}' guardado en brote {brote_id}")
        except Exception as e:
            logger.error(f"Error al insertar documento '{nombre_archivo}': {e}", exc_info=True)
            conn.rollback()
            raise e
        finally:
            conn.close()                                
                       
            

#------------- 2. FUNCIONES READ ---------------------------
    #Query para obtener brote para editar
    @staticmethod
    def obtener_brote(idbrote):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT b.*, 
                        te.nombre AS tipoevento, 
                        i.nombre AS institucion,
                        m.nombre AS municipio,
                        j.nombre AS jurisdiccion,
                        d.nombre AS diagnostico
                    FROM brotes b
                    LEFT JOIN tipoeventos te ON b.idtipoevento = te.idtipoevento
                    LEFT JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                    LEFT JOIN municipios m ON b.idmunicipio = m.idmunicipio
                    LEFT JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion
                    LEFT JOIN diagsospecha d ON b.iddiag = d.iddiag
                    WHERE b.idbrote = %s
                """, (idbrote,))
                return cursor.fetchone()
        finally:
            conn.close()
            
    
    
    #Query para obtener documentos para edicion de formulario
    @staticmethod
    def obtener_documentos_por_brote(idbrote):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT iddocumento, nombre_archivo, tipo_notificacion,
                        folionotinmed, fechnotinmed
                    FROM documentos
                    WHERE brote_id = %s
                """, (idbrote,))
                return cursor.fetchall()
        finally:
            conn.close()
            
            
    @staticmethod  
    #Obtener ID de catalogos para validacion a la hora de registrar ENDPOINT ACTUALIZAR_BROTE   
    def get_catalog_id(tabla, nombre, col_id='id', col_nombre='nombre'):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {col_id} FROM {tabla} WHERE {col_nombre} = %s", (nombre,))
                result = cursor.fetchone()
                return result[col_id] if result else None
        finally:
            conn.close()     


    #Modelos para validar que existe un folio y fecha para actualizar en documentos            
    @staticmethod
    def obtener_folio_y_fecha(iddocumento):
        conn = MySQLConnection().connect()  # Conectar a la base de datos
        try:
            with conn.cursor() as cursor:
                # Consulta para obtener folio y fecha de notificación para un documento
                sql = """
                    SELECT folionotinmed, fechnotinmed
                    FROM documentos
                    WHERE iddocumento = %s
                """
                cursor.execute(sql, (iddocumento,))
                result = cursor.fetchone()  # Obtener el primer resultado
                
                if result:
                    folio, fecha = result
                    return folio, fecha
                else:
                    # Si no se encuentra el documento, devolver None
                    return None, None

        except Exception as e:
            logger.error(f"Error al obtener folio y fecha para iddocumento {iddocumento}: {e}", exc_info=True)
            return None, None
        finally:
            conn.close()
            
                        
    #Obtiene todos los registros para la lista de brotes  -> EDIT.HTML
    @staticmethod
    def obtener_todos_los_brotes():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT b.idbrote, b.lugar, b.created_at,
                        te.nombre AS tipoevento,
                        i.nombre AS institucion,
                        m.nombre AS municipio
                    FROM brotes b
                    LEFT JOIN tipoeventos te ON b.idtipoevento = te.idtipoevento
                    LEFT JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                    LEFT JOIN municipios m ON b.idmunicipio = m.idmunicipio
                    ORDER BY b.created_at
                """)
                return cursor.fetchall()
        finally:
            conn.close()            
            

    #Query para obtener datos para exportar a excel -> EDIT.HTML
    @staticmethod
    def obtener_brotes_completos():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT b.idbrote, b.lugar, b.domicilio, b.localidad,
                        b.fechnotifica, b.fechinicio, b.fechultimocaso,
                        b.casosprob, b.casosconf, b.defunciones,
                        b.resultado, b.fechalta, b.observaciones,
                        te.nombre AS tipoevento,
                        i.nombre AS institucion,
                        m.nombre AS municipio,
                        j.nombre AS jurisdiccion,
                        d.nombre AS diagsospecha,
                        b.created_at
                    FROM brotes b
                    LEFT JOIN tipoeventos te ON b.idtipoevento = te.idtipoevento
                    LEFT JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                    LEFT JOIN municipios m ON b.idmunicipio = m.idmunicipio
                    LEFT JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion
                    LEFT JOIN diagsospecha d ON b.iddiag = d.iddiag
                    ORDER BY b.created_at DESC
                """)
                return cursor.fetchall()
        finally:
            conn.close()
            

            
    #Funcion para estadisiticas del DASHBOARD
    @staticmethod
    def obtener_estadisticas(institucion=''):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                filtros = []
                valores = []

                if institucion:
                    filtros.append("institucion = %s")
                    valores.append(institucion)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                cursor.execute(f"""
                    SELECT tipoevento, COUNT(*) as total
                    FROM brotes
                    {where_clause}
                    GROUP BY tipoevento
                """, valores)
                tipos = cursor.fetchall()

                cursor.execute(f"""
                    SELECT DATE_FORMAT(fechinicio, '%%Y-%%m') as mes, COUNT(*) as total
                    FROM brotes
                    {where_clause}
                    GROUP BY mes
                    ORDER BY mes
                """, valores)
                por_mes = cursor.fetchall()

                return {
                    'tipos': tipos,
                    'por_mes': por_mes
                }
        finally:
            conn.close()
            

    #obtener instituciones para filtro de DASHBOARD
    @staticmethod
    def obtener_instituciones():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT institucion FROM brotes ORDER BY institucion")
                return cursor.fetchall()
        finally:
            conn.close()
            
            
    #Obtener brotes por estado actual
    @staticmethod
    def obtener_edo_actual_pendientes():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT
                                    b.idbrote AS idbrote,
                                    t.nombre AS tipo_evento, 
                                    b.unidadnotif, 
                                    b.fechultimocaso,
                                    d.nombre diagnostico,
                                    b.fechalta,
                                    d.periodo_incubacion,
                                    -- Fecha probable de alta
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        THEN DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        ELSE NULL
                                    END AS fecha_probable_alta,
                                    -- Días expirados
                                    CASE
                                        WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0
                                        THEN DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY))
                                        ELSE NULL
                                    END AS dias_expirados,
                                    -- Estado actual del brote
                                    CASE
                                        WHEN b.fechalta is not null THEN 'Alta'
                                        WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0 THEN 'Pendiente Alta'
                                        ELSE 'Activo'
                                    END AS estado_actual
                                FROM tipoeventos t
                                INNER JOIN brotes b
                                    ON t.idtipoevento = b.idtipoevento
                                INNER JOIN diagsospecha d
                                    ON b.iddiag = d.iddiag
                                WHERE 
                                    b.fechalta IS NULL AND 
                                    DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0
                                order by b.idbrote                               
                               """)
                return cursor.fetchall()
        finally:
            conn.close()
            
            
            
    @staticmethod
    def obtener_edo_actual_activos():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT
                                    b.idbrote AS idbrote,
                                    t.nombre AS tipo_evento, 
                                    b.unidadnotif, 
                                    b.fechultimocaso,
                                    d.nombre diagnostico,
                                    b.fechalta,
                                    d.periodo_incubacion,
                                    -- Fecha probable de alta
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        THEN DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        ELSE NULL
                                    END AS fecha_probable_alta,
                                    -- Días expirados
                                    CASE
                                        WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0
                                        THEN DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY))
                                        ELSE NULL
                                    END AS dias_expirados,
                                    -- Estado actual del brote
                                    CASE
                                        WHEN b.fechalta is not null THEN 'Alta'
                                        WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0 THEN 'Pendiente Alta'
                                        ELSE 'Activo'
                                    END AS estado_actual
                                FROM tipoeventos t
                                INNER JOIN brotes b
                                    ON t.idtipoevento = b.idtipoevento
                                INNER JOIN diagsospecha d
                                    ON b.iddiag = d.iddiag
                                WHERE 
                                    b.fechalta IS NULL AND 
                                    DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) < 0
                                order by b.idbrote                               
                               """)
                return cursor.fetchall()
        finally:
            conn.close()
            
            
            
#----------- 3. FUNCIONES UPDATE ------------------------------------
    #Metodo para actulizar brote
    @staticmethod
    def actualizar_brote(idbrote, data, ids):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:                
                sql = """
                    UPDATE brotes SET 
                        idtipoevento = %s,
                        lugar = %s,
                        idinstitucion = %s,
                        unidadnotif = %s,
                        domicilio = %s,
                        localidad = %s,
                        idmunicipio = %s,
                        idjurisdiccion = %s,
                        iddiag = %s,
                        fechnotifica = %s,
                        fechinicio = %s,
                        casosprob = %s,
                        casosconf = %s,
                        defunciones = %s,
                        fechultimocaso = %s,
                        fecha_consulta = %s,
                        resultado = %s,
                        fechalta = %s,
                        observaciones = %s,
                        pobmascexp = %s,
                        pobfemexp = %s,
                        updated_at = NOW()
                    WHERE idbrote = %s
                """
                cursor.execute(sql, (
                    ids['idtipoevento'],
                    data['lugar'],
                    ids['idinstitucion'],
                    data['unidadnotif'],
                    data['domicilio'],
                    data['localidad'],
                    ids['idmunicipio'],
                    ids['idjurisdiccion'],
                    ids['iddiag'],
                    data['fechnotifica'],
                    data['fechinicio'],
                    data['casosprob'],
                    data['casosconf'],
                    data['defunciones'],
                    data['fechultimocaso'],
                    data['fecha_consulta'],
                    data['resultado'],
                    data['fechalta'],
                    data['observaciones'],
                    data['pobmascexp'],
                    data['pobfemexp'],
                    idbrote
                ))
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al actualizar el brote con ID {idbrote}: {e}", exc_info=True)
            raise e
        finally:
            conn.close()
            
            

    # Funcion para actualizar documentos  
    @staticmethod      
    def actualizar_documento(iddoc, folio=None, fecha=None):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE documentos
                    SET
                        folionotinmed = %s,
                        fechnotinmed = %s,
                        fechmodificacion = NOW()
                    WHERE iddocumento = %s
                """
                cursor.execute(sql, (folio, fecha, iddoc))
                conn.commit()
        
                # Verificar si se actualizó correctamente
                if cursor.rowcount > 0:
                    logger.info(f"Documento con ID {iddoc} actualizado correctamente.")
                else:
                    logger.warning(f"Documento con ID {iddoc} no fue encontrado o no se actualizó.")

        except Exception as e:
            logger.error(f"Error al actualizar documento con ID {iddoc}: {e}", exc_info=True)
            conn.rollback()
            raise e

        finally:
            conn.close()
            
            
    # Función para obtener el ID de tipoevento basado en su nombre
    def get_catalog_id(tabla, nombre, col_id='id', col_nombre='nombre'):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {col_id} FROM {tabla} WHERE {col_nombre} = %s", (nombre,))
                result = cursor.fetchone()
                return result[col_id] if result else None
        finally:
            conn.close()     
            
    @staticmethod
    def get_id_by_name(table, name_column, value, id_column):
        """Obtiene el ID de cualquier tabla basada en el nombre y la columna específica"""
        try:
            conn = MySQLConnection().connect()
            cursor = conn.cursor()

            # Consulta dinámica
            query = f"SELECT {id_column} FROM {table} WHERE {name_column} = %s"
            cursor.execute(query, (value,))
            result = cursor.fetchone()  # Obtener el primer resultado

            if result:
                return result[0]  # Retornar el ID de la columna especificada
            else:
                return None  # Si no se encuentra el valor, devolver None
        except Exception as e:
            logger.error(f"Error al obtener {id_column} de la tabla {table}: {e}", exc_info=True)
            return None
        finally:
            conn.close()
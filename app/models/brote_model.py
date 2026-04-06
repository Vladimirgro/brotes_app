from app.models.mysql_connection import MySQLConnection
import os
import uuid
import logging
from werkzeug.utils import secure_filename
from config import Config
import pymysql.cursors
from typing import List, Dict, Optional, Union
import shutil
from datetime import datetime, timedelta


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

                cursor.execute("SELECT idunidad, clues FROM unidades_salud ORDER BY clues")
                clues = cursor.fetchall()
                
            return {
                "tipoeventos": tipoeventos, 
                "instituciones": instituciones, 
                "municipios":municipios, 
                "jurisdicciones":jurisdicciones, 
                "diagnosticos":diagnosticos,
                "clues": clues}

        finally:
            conn.close()


    # 2. Método para obtener datos de unidad por CLUES
    @staticmethod
    def obtener_unidad_por_clues(clues):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT clues, nombre_comercial, nombre_institucion, jurisdiccion 
                    FROM unidades_salud 
                    WHERE clues = %s
                """, (clues,))
                result = cursor.fetchone()                
                return result
        finally:
            conn.close()

    
    #2. Metodo auxiliar para procesar documentos en el controlador
    @classmethod
    def guardar_documento(cls,brote_id, archivo, tipo, folio=None, fecha=None):
        if not archivo or not tipo:
            raise ValueError("Archivo o tipo no válidos")

        # Validación de brote_id (prevenir path traversal)
        if not isinstance(brote_id, int) or brote_id <= 0:
            raise ValueError(f"brote_id inválido: {brote_id}")

        # Validación de extensión usando configuración
        extension = os.path.splitext(archivo.filename)[1].lower()
        if extension not in Config.ALLOWED_EXTENSIONS:
            logger.error(f"Extensión rechazada: {archivo.filename} (extensión: {extension})")
            extensiones_permitidas = ', '.join(Config.ALLOWED_EXTENSIONS)
            raise ValueError(f"Tipo de archivo no permitido. Extensiones permitidas: {extensiones_permitidas}")

        # Validación de tamaño (opcional)
        if archivo.content_length and archivo.content_length > 10 * 1024 * 1024:
            raise ValueError("Archivo demasiado grande (> 10MB)")

        nombre_base = secure_filename(archivo.filename)

        # Validar que secure_filename no devolvió vacío
        if not nombre_base:
            raise ValueError("Nombre de archivo inválido después de sanitización")

        # Prevenir duplicados: agregar timestamp si el archivo ya existe
        #nombre_original = nombre_base
        #base_name, extension = os.path.splitext(nombre_base)
        
        data = BroteModel.obtener_anio_y_folio(brote_id)
        anio = data["anio"]
        folio_anual = data["folio_anual"]

        directorio_brote = os.path.join(Config.UPLOAD_FOLDER, str(anio), f"brote_{folio_anual}")
        
        contador = 1
        nombre_original = nombre_base
        base_name, extension = os.path.splitext(nombre_base)
        # Verificar si ya existe archivo con el mismo nombre
        
        ruta_temporal = os.path.normpath(os.path.join(directorio_brote, nombre_original))        
        while os.path.exists(ruta_temporal):
            # Agregar sufijo numérico al nombre
            nombre_original = f"{base_name}_{contador}{extension}"
            ruta_temporal = os.path.normpath(os.path.join(directorio_brote, nombre_original))
            contador += 1

            # Límite de seguridad para evitar loop infinito
            if contador > 1000:
                raise ValueError("No se pudo generar nombre único para el archivo")

        if contador > 1:
            logger.info(f"Archivo duplicado detectado, renombrado a: {nombre_original}")

        # Construir rutas de forma segura y normalizada
        ruta_absoluta = os.path.normpath(os.path.join(directorio_brote, nombre_original))

        # Validar que la ruta está dentro del directorio de uploads (prevenir path traversal)
        upload_folder_abs = os.path.normpath(os.path.abspath(Config.UPLOAD_FOLDER))
        if os.path.commonpath([ruta_absoluta, upload_folder_abs]) != upload_folder_abs:
            raise ValueError("Ruta de archivo inválida (path traversal detectado)")

        # Ruta relativa para BD (siempre con forward slashes)
        ruta_relativa = os.path.join("static", "uploads", str(anio), f"brote_{folio_anual}", nombre_original).replace('\\', '/')

        # Crear directorio si no existe
        os.makedirs(directorio_brote, exist_ok=True)

        # Guardar archivo físico
        archivo.save(ruta_absoluta)

        logger.info(f"Archivo guardado en: {ruta_absoluta}")

        try:
            # Guardar en base de datos
            BroteModel.insertar_documento(brote_id, nombre_original, ruta_relativa, tipo, folio, fecha)
            logger.info(f"Documento registrado en BD: {nombre_original}")

        except Exception as e:
            # Si falla BD, eliminar archivo físico para evitar huérfanos
            logger.error(f"Error al insertar en BD, eliminando archivo físico: {str(e)}")
            try:
                if os.path.exists(ruta_absoluta):
                    os.remove(ruta_absoluta)
                    logger.info(f"Archivo físico eliminado: {ruta_absoluta}")
            except Exception as e_file:
                logger.error(f"No se pudo eliminar archivo huérfano: {str(e_file)}")

            # Re-lanzar excepción original
            raise e 
        


    @staticmethod
    def calcular_fecha_probable_alta(fecha_ultimo_caso, periodo_incubacion_dias):
        try:
            if not fecha_ultimo_caso or not periodo_incubacion_dias:
                return None
            
            if isinstance(fecha_ultimo_caso, str):
                fecha_ultimo_caso = datetime.strptime(fecha_ultimo_caso, '%Y-%m-%d')
            
            fecha_alta = fecha_ultimo_caso + timedelta(days=int(periodo_incubacion_dias))
            
            return fecha_alta
            
        except Exception as e:
            logger.error(f"Error al calcular fecha probable de alta: {e}")
            return None
        
           

#-----------------1. FUNCIONES CREATE -----------------------------------
    @staticmethod      
    def insertar_brote(data, ids):
        conn = MySQLConnection().connect()
        if not conn:
            raise Exception("No se pudo establecer conexión a la BD")
    
        try:
            with conn.cursor() as cursor:
                # 1) Validar fechinicio para poder sacar el año
                fechinicio = data.get("fechinicio")
                if not fechinicio:
                    raise ValueError("fechinicio es obligatoria para calcular el año del consecutivo")

                # 2) Obtener año desde MySQL (evita problemas de formato string/date)
                cursor.execute("SELECT YEAR(%s) AS anio", (fechinicio,))
                row = cursor.fetchone()
                anio = row["anio"] 
                
                if not anio:
                    raise ValueError("No se pudo calcular el año a partir de fechinicio")

                # 3) Iniciar transacción
                conn.begin()

                # 4) Tomar siguiente folio anual (concurrencia segura)
                cursor.execute("""
                    INSERT INTO brote_consecutivo (anio, ultimo)
                    VALUES (%s, LAST_INSERT_ID(1))
                    ON DUPLICATE KEY UPDATE ultimo = LAST_INSERT_ID(ultimo + 1)
                """, (anio,))
                
                cursor.execute("SELECT LAST_INSERT_ID() AS folio")
                row = cursor.fetchone()
                folio_anual = row["folio"]

                sql = """
                    INSERT INTO brotes (
                        anio, folio_anual,
                        idtipoevento, lugar, idinstitucion, unidadnotif, domicilio,
                        localidad, idmunicipio, idjurisdiccion, iddiag,
                        fechnotifica, fechinicio, casosprob, casosconf,
                        defunciones, fechultimocaso, fecha_consulta, resultado, fechalta,
                        observaciones, pobmascexp, pobfemexp
                    )
                    VALUES (
                        %(anio)s, %(folio_anual)s,
                        %(idtipoevento)s, %(lugar)s, %(idinstitucion)s, %(unidadnotif)s, %(domicilio)s,
                        %(localidad)s, %(idmunicipio)s, %(idjurisdiccion)s, %(iddiag)s,
                        %(fechnotifica)s, %(fechinicio)s, %(casosprob)s, %(casosconf)s,
                        %(defunciones)s, %(fechultimocaso)s, %(fecha_consulta)s,%(resultado)s, %(fechalta)s,
                        %(observaciones)s, %(pobmascexp)s, %(pobfemexp)s
                    )
                """
                parametros = {**data, **ids, "anio": anio, "folio_anual": folio_anual}                
                cursor.execute(sql, parametros)

                brote_id = cursor.lastrowid
                
                if not brote_id:
                    raise Exception("Error al insertar brote: No se generó ID")

                conn.commit()
                logger.info(f"Brote insertado con ID {brote_id} | {anio}/brote_{folio_anual}")
                return brote_id
                
        except Exception as e:
            try:                
                conn.rollback()
            except Exception:
                pass
            logger.error(f"Error al insertar brote: {str(e)}")
            raise
        finally:
            conn.close()
    
    
    @staticmethod
    def obtener_anio_y_folio(brote_id: int) -> dict:
        conn = MySQLConnection().connect()

        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")
    
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT anio, folio_anual
                    FROM brotes
                    WHERE idbrote = %s
                """, (brote_id,))
                row = cursor.fetchone()

            if not row or row.get("anio") is None or row.get("folio_anual") is None:
                raise ValueError(f"No se encontró anio/folio_anual para brote_id={brote_id}")

            return {
                "anio": int(row["anio"]),
                "folio_anual": int(row["folio_anual"]),
            }
        
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
            

    #OBTIENE AÑO PARA LISTA.HTML
    @staticmethod
    def obtener_anios_disponibles():
        conn = MySQLConnection().connect()
        if conn is None:
            raise ConnectionError("No se pudo conectar a la base de datos")

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT anio
                    FROM brote_consecutivo
                    ORDER BY anio DESC
                """)
                rows = cursor.fetchall()  # DictCursor -> [{'anio': 2026}, {'anio': 2025}, ...]
                return [int(r["anio"]) for r in rows]
        finally:
            conn.close()


    #QUERY PARA OBTENER TODOS LOS BROTES FILTRADOS POR AÑO
    @staticmethod
    def obtener_brotes_por_anio(anio=None):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                base_sql = """
                    SELECT 
                        b.idbrote,
                        b.anio,
                        b.folio_anual,
                        t.nombre AS "Tipo evento",
                        b.lugar AS Lugar,
                        i.nombre AS Institución,
                        b.unidadnotif AS "Unidad notificante",
                        b.domicilio AS "Domicilio",
                        b.localidad AS Localidad,
                        m.nombre AS Municipio,
                        j.nombre AS "Jurisdicción",
                        b.fechnotifica AS "Fecha notificación",
                        d.nombre AS "Diagnóstico Sospecha",
                        b.fechinicio AS "Fecha inicio",
                        b.casosprob AS "Casos probables",
                        b.casosconf AS "Casos confirmados",
                        b.defunciones AS Defunciones,
                        b.fechultimocaso AS "Fecha Última Caso",
                        b.resultado AS Resultado,
                        b.fechalta AS "Fecha Alta",
                        b.fecha_consulta AS "Fecha consulta",
                        b.observaciones AS Observaciones,
                        b.pobfemexp AS "Poblacion Expuesta Fem",
                        b.pobmascexp AS "Poblacion Expuesta Masc",
                        (b.pobfemexp + b.pobmascexp) AS "Población expuesta",

                        doc_inicial.folionotinmed AS "Folio Notinmed Inicial",
                        doc_inicial.fechnotinmed AS "Fecha Notinmed Inicial",
                        doc_final.folionotinmed   AS "Folio Notinmed Final",
                        doc_final.fechnotinmed    AS "Fecha Notinmed Final",

                        CASE
                            WHEN b.fechalta IS NOT NULL THEN 'Alta'
                            WHEN b.fechalta IS NULL 
                                AND DATEDIFF(
                                        CURDATE(), 
                                        DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    ) > 0 THEN 'Pendiente Alta'
                            ELSE 'Activo'
                        END AS Estatus

                    FROM brotes b
                        INNER JOIN tipoeventos t     ON b.idtipoevento   = t.idtipoevento
                        INNER JOIN instituciones i  ON b.idinstitucion  = i.idinstitucion
                        INNER JOIN municipios m     ON b.idmunicipio    = m.idmunicipio
                        INNER JOIN diagsospecha d   ON b.iddiag          = d.iddiag
                        INNER JOIN jurisdicciones j ON b.idjurisdiccion  = j.idjurisdiccion

                        /* ===================== DOCUMENTO INICIAL ===================== */
                        LEFT JOIN (
                            SELECT d1.brote_id,
                                d1.folionotinmed,
                                d1.fechnotinmed
                            FROM documentos d1
                            INNER JOIN (
                                SELECT brote_id,
                                    MAX(fechnotinmed) AS max_fecha,
                                    MAX(iddocumento)  AS max_id
                                FROM documentos
                                WHERE tipo_notificacion = 'INICIAL'
                                GROUP BY brote_id
                            ) d2
                                ON d1.brote_id      = d2.brote_id
                            AND d1.fechnotinmed = d2.max_fecha
                            AND d1.iddocumento = d2.max_id
                            WHERE d1.tipo_notificacion = 'INICIAL'
                        ) doc_inicial
                            ON b.idbrote = doc_inicial.brote_id

                        /* ===================== DOCUMENTO FINAL ===================== */
                        LEFT JOIN (
                            SELECT d1.brote_id,
                                d1.folionotinmed,
                                d1.fechnotinmed
                            FROM documentos d1
                            INNER JOIN (
                                SELECT brote_id,
                                    MAX(fechnotinmed) AS max_fecha,
                                    MAX(iddocumento)  AS max_id
                                FROM documentos
                                WHERE tipo_notificacion = 'FINAL'
                                GROUP BY brote_id
                            ) d2
                                ON d1.brote_id      = d2.brote_id
                            AND d1.fechnotinmed = d2.max_fecha
                            AND d1.iddocumento = d2.max_id
                            WHERE d1.tipo_notificacion = 'FINAL'
                        ) doc_final
                            ON b.idbrote = doc_final.brote_id
                """

                params = []
                if anio:
                    base_sql += " WHERE b.anio = %s"
                    params.append(anio)

                base_sql += " ORDER BY b.folio_anual ASC;"
                cursor.execute(base_sql, params)
                return cursor.fetchall()
        finally:
            conn.close()



    #Obtiene todos los registros para la lista de brotes -> lista.html
    @staticmethod
    def obtener_todos_los_brotes():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT 
                                    b.idbrote,  
                                    b.folio_anual,                                      
                                    t.nombre AS "Tipo evento",
                                    b.lugar AS Lugar,
                                    i.nombre AS Institución,
                                    b.unidadnotif AS "Unidad notificante",    
                                    b.domicilio AS "Domicilio",
                                    b.localidad AS Localidad,
                                    m.nombre AS Municipio,
                                    j.nombre AS "Jurisdicción",
                                    b.fechnotifica AS "Fecha notificación",
                                    d.nombre AS "Diagnóstico Sospecha",
                                    b.fechinicio AS "Fecha inicio",    
                                    b.casosprob AS "Casos probables",
                                    b.casosconf AS "Casos confirmados",
                                    b.defunciones AS Defunciones,
                                    b.fechultimocaso AS "Fecha Última Caso",
                                    b.resultado AS Resultado,
                                    b.fechalta AS "Fecha Alta",
                                    b.fecha_consulta AS "Fecha consulta",    
                                    b.observaciones AS Observaciones,
                                    b.pobfemexp AS "Poblacion Expuesta Fem",
                                    b.pobmascexp AS "Poblacion Expuesta Masc",
                                    (b.pobfemexp + b.pobmascexp) AS "Población expuesta",                                        
                                    doc_inicial.folionotinmed AS "Folio Notinmed Inicial",
                                    doc_inicial.fechnotinmed AS "Fecha Notinmed Inicial",                                    
                                    doc_final.folionotinmed AS "Folio Notinmed Final",
                                    doc_final.fechnotinmed AS "Fecha Notinmed Final",                                              
                                    CASE
                                        WHEN b.fechalta IS NOT NULL THEN 'Alta'
                                        WHEN b.fechalta IS NULL AND DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0 THEN 'Pendiente Alta'
                                        ELSE 'Activo'
                                    END AS Estatus    
                                FROM brotes b
                                    INNER JOIN tipoeventos t ON b.idtipoevento = t.idtipoevento
                                    INNER JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                                    INNER JOIN municipios m ON b.idmunicipio = m.idmunicipio
                                    INNER JOIN diagsospecha d ON b.iddiag = d.iddiag
                                    INNER JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion                                    
                                    LEFT JOIN documentos doc_inicial ON b.idbrote = doc_inicial.brote_id 
                                        AND doc_inicial.tipo_notificacion = 'INICIAL'                                    
                                    LEFT JOIN documentos doc_final ON b.idbrote = doc_final.brote_id 
                                        AND doc_final.tipo_notificacion = 'FINAL'
                                ORDER BY     
                                    b.idbrote ASC; 
                            """)
                return cursor.fetchall()
        finally:
            conn.close()            
            

    # Método para filtrar brotes por rango de fecha de inicio
    @staticmethod
    def obtener_brotes_por_fecha_inicio(fecha_inicio, fecha_fin, anio):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT
                                    b.idbrote,
                                    b.folio_anual,
                                    t.nombre AS "Tipo evento",
                                    b.lugar AS Lugar,
                                    i.nombre AS Institución,
                                    b.unidadnotif AS "Unidad notificante",
                                    b.domicilio AS "Domicilio",
                                    b.localidad AS Localidad,
                                    m.nombre AS Municipio,
                                    j.nombre AS "Jurisdicción",
                                    b.fechnotifica AS "Fecha notificación",
                                    d.nombre AS "Diagnóstico Sospecha",
                                    b.fechinicio AS "Fecha inicio",
                                    b.casosprob AS "Casos probables",
                                    b.casosconf AS "Casos confirmados",
                                    b.defunciones AS Defunciones,
                                    b.fechultimocaso AS "Fecha Última Caso",
                                    b.resultado AS Resultado,
                                    b.fechalta AS "Fecha Alta",
                                    b.fecha_consulta AS "Fecha consulta",
                                    b.observaciones AS Observaciones,
                                    b.pobfemexp AS "Poblacion Expuesta Fem",
                                    b.pobmascexp AS "Poblacion Expuesta Masc",
                                    (b.pobfemexp + b.pobmascexp) AS "Población expuesta",
                                    doc_inicial.folionotinmed AS "Folio Notinmed Inicial",
                                    doc_inicial.fechnotinmed AS "Fecha Notinmed Inicial",
                                    doc_final.folionotinmed AS "Folio Notinmed Final",
                                    doc_final.fechnotinmed AS "Fecha Notinmed Final",
                                    CASE
                                        WHEN b.fechalta IS NOT NULL THEN 'Alta'
                                        WHEN b.fechalta IS NULL AND DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0 THEN 'Pendiente Alta'
                                        ELSE 'Activo'
                                    END AS Estatus
                                FROM brotes b
                                    INNER JOIN tipoeventos t ON b.idtipoevento = t.idtipoevento
                                    INNER JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                                    INNER JOIN municipios m ON b.idmunicipio = m.idmunicipio
                                    INNER JOIN diagsospecha d ON b.iddiag = d.iddiag
                                    INNER JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion
                                    LEFT JOIN documentos doc_inicial ON b.idbrote = doc_inicial.brote_id
                                        AND doc_inicial.tipo_notificacion = 'INICIAL'
                                    LEFT JOIN documentos doc_final ON b.idbrote = doc_final.brote_id
                                        AND doc_final.tipo_notificacion = 'FINAL'
                                WHERE b.anio = %s AND b.fechinicio BETWEEN %s AND %s
                                ORDER BY b.fechinicio;
                            """, (anio, fecha_inicio, fecha_fin))
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
            

            
    #Funcion para estadisiticas de brotes por mes del DASHBOARD    
    @staticmethod
    def obtener_estadisticas(institucion: Optional[Union[str, int]] = None, anio: Optional[Union[str, int]] = None) -> Dict[str, List[Dict]]:
        """
        Obtiene estadísticas de brotes por tipo de evento y por mes.
        
        Args:
            institucion (Optional[Union[str, int]]): ID de la institución para filtrar. 
                                                   Si es None, obtiene datos de todas las instituciones.
        
        Returns:
            Dict[str, List[Dict]]: Diccionario con claves 'tipos' y 'por_mes', 
                                 cada una conteniendo lista de diccionarios con los resultados.
        
        Raises:
            ValueError: Si el ID de institución no es válido.
            pymysql.Error: Si hay error en la consulta a la base de datos.
        """

        print("Institución:", institucion)
        print("Año:", anio)

        # Validación de parámetros
        if institucion is not None and not str(institucion).strip():
            institucion = None
        elif institucion is not None and not str(institucion).isdigit():
            raise ValueError("ID de institución debe ser numérico")


        # ===== Validación año =====
        if anio is not None:
            anio_str = str(anio).strip()
            if not anio_str:
                anio = None
            elif not anio_str.isdigit() or len(anio_str) != 4:
                raise ValueError("El año debe ser numérico de 4 dígitos")
            else:
                anio = int(anio_str)
        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                filtros = []
                valores = []

                if institucion is not None:
                    filtros.append("b.idinstitucion = %s")                    
                    valores.append(int(institucion))                     

                if anio is not None:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                # Consulta para tipos de eventos
                query_tipos = f"""
                    SELECT 
                        te.nombre AS tipo,
                        COUNT(*) AS total
                    FROM tipoeventos te
                    INNER JOIN brotes b 
                        ON te.idtipoevento = b.idtipoevento
                    {where_clause}
                    GROUP BY te.nombre
                    ORDER BY total DESC
                """
                
                cursor.execute(query_tipos, valores)
                tipos = cursor.fetchall()

                # Consulta para datos por mes
                query_por_mes = f"""
                    SELECT 
                        DATE_FORMAT(b.fechinicio, '%%Y-%%m') AS mes,
                        COUNT(*) AS total
                    FROM brotes b
                    {where_clause}
                    GROUP BY mes
                    ORDER BY mes
                """

                cursor.execute(query_por_mes, valores)
                por_mes = cursor.fetchall()
                
                # Consulta para datos por semana
                query_por_semana = f"""
                    SELECT
                        b.sem_epi AS semana,
                        COUNT(*) AS total
                    FROM brotes b
                    {where_clause}
                    GROUP BY b.sem_epi
                    ORDER BY b.sem_epi
                """

                cursor.execute(query_por_semana, valores)
                por_semana = cursor.fetchall()              
                                
                return {
                    'tipos': tipos,
                    'por_mes': por_mes,
                    "por_semana": por_semana
                }
                
        except pymysql.Error as e:
            logging.error(f"Error al obtener estadísticas: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado en obtener_estadisticas: {e}")
            raise
        finally:
            conn.close()
            

    #obtener instituciones para filtro de DASHBOARD
    def obtener_instituciones() -> List[Dict[str, Union[int, str]]]:
        """
        Obtiene la lista de todas las instituciones disponibles.
        
        Returns:
            List[Dict[str, Union[int, str]]]: Lista de diccionarios con idinstitucion y nombre.
        
        Raises:
            pymysql.Error: Si hay error en la consulta a la base de datos.
        """
        conn = MySQLConnection().connect()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        idinstitucion, 
                        nombre
                    FROM instituciones
                    WHERE nombre IS NOT NULL AND nombre != ''
                    ORDER BY nombre ASC
                """)
                return cursor.fetchall()
                
        except pymysql.Error as e:
            logging.error(f"Error al obtener instituciones: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado en obtener_instituciones: {e}")
            raise
        finally:
            conn.close()


    @staticmethod
    def obtener_totales_brotes(institucion=None, anio=None):

        conn = MySQLConnection().connect()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:

                filtros = []
                valores = []

                if institucion:
                    filtros.append("b.idinstitucion = %s")
                    valores.append(institucion)

                if anio:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                    SELECT
                        SUM(activos) AS activos,
                        SUM(pendiente_alta) AS pendiente_alta,
                        SUM(alta) AS alta,
                        SUM(total) AS total
                    FROM (
                        SELECT
                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND NOT (
                                        DATEDIFF(
                                            CURDATE(),
                                            DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        ) > 0
                                    )
                                    THEN 1 ELSE 0
                                END
                            ) AS activos,

                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND DATEDIFF(
                                        CURDATE(),
                                        DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    ) > 0
                                    THEN 1 ELSE 0
                                END
                            ) AS pendiente_alta,

                            SUM(
                                CASE
                                    WHEN b.fechalta IS NOT NULL
                                    THEN 1 ELSE 0
                                END
                            ) AS alta,

                            COUNT(*) AS total

                        FROM brotes b
                        INNER JOIN diagsospecha d
                        ON b.iddiag = d.iddiag
                        {where_clause}
                    ) t
                """

                cursor.execute(query, valores)

                return cursor.fetchone()

        finally:
            conn.close()

    
    #Funcion para obtener datos de Resumen de brotes por institución y estatus
    @staticmethod
    def obtener_resumen_instituciones(institucion: Optional[Union[str, int]] = None, anio: Optional[Union[str, int]] = None) -> List[Dict]:
        """
        Obtiene resumen de brotes por institución, clasificados por estado (alta, pendiente_alta, activos).
        
        Args:
            institucion (Optional[Union[str, int]]): ID de institución específica para filtrar.
                                                   Si es None, obtiene datos de todas las instituciones.
        
        Returns:
            List[Dict]: Lista de diccionarios con estadísticas por institución.
                       Cada diccionario contiene: idinstitucion, institucion, alta, pendiente_alta, activos, total.
        
        Raises:
            ValueError: Si el ID de institución no es válido.
            pymysql.Error: Si hay error en la consulta a la base de datos.
        """
        # Validación de parámetros
        if institucion is not None and not str(institucion).strip():
            institucion = None
        elif institucion is not None and not str(institucion).isdigit():
            raise ValueError("ID de institución debe ser numérico")
        

            # ===== Validación año =====
        if anio is not None:
            anio_str = str(anio).strip()
            if not anio_str:
                anio = None
            elif not anio_str.isdigit() or len(anio_str) != 4:
                raise ValueError("El año debe ser numérico de 4 dígitos")
            else:
                anio = int(anio_str)

        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                filtros = []
                valores = []

                if institucion:
                    filtros.append("brotes.idinstitucion = %s")
                    valores.append(int(institucion))
                
                if anio is not None:
                    filtros.append("brotes.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                    SELECT
                        instituciones.idinstitucion,
                        instituciones.nombre AS institucion,
                        SUM(CASE WHEN brotes.fechalta IS NOT NULL THEN 1 ELSE 0 END) AS alta,
                        SUM(
                            CASE
                                WHEN brotes.fechalta IS NULL
                                     AND DATEDIFF(CURDATE(), DATE_ADD(brotes.fechultimocaso, INTERVAL diagnosticos.periodo_incubacion DAY)) > 0
                                THEN 1 ELSE 0
                            END
                        ) AS pendiente_alta,
                        SUM(
                            CASE
                                WHEN brotes.fechalta IS NULL
                                     AND NOT (DATEDIFF(CURDATE(), DATE_ADD(brotes.fechultimocaso, INTERVAL diagnosticos.periodo_incubacion DAY)) > 0)
                                THEN 1 ELSE 0
                            END
                        ) AS activos,
                        COUNT(*) AS total
                    FROM brotes
                    INNER JOIN diagsospecha diagnosticos ON brotes.iddiag = diagnosticos.iddiag
                    INNER JOIN instituciones ON brotes.idinstitucion = instituciones.idinstitucion
                    {where_clause}
                    GROUP BY instituciones.idinstitucion, instituciones.nombre
                    ORDER BY instituciones.nombre ASC
                """

                cursor.execute(query, valores)
                return cursor.fetchall()
                
        except pymysql.Error as e:
            logging.error(f"Error al obtener resumen de instituciones: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado en obtener_resumen_instituciones: {e}")
            raise
        finally:
            conn.close()


    #Funcion para obtener datos de Resumen de Brotes por Institución y Tipo de Evento
    @staticmethod
    def obtener_resumen_eventos(institucion: Optional[Union[str, int]] = None, anio: Optional[Union[str, int]] = None) -> List[Dict]:
        """
        Obtiene resumen de eventos por institución y tipo de evento.
        Devuelve resultados pivotados listos para mostrar en tabla.
        
        Args:
            institucion (Optional[Union[str, int]]): ID de institución específica para filtrar.
                                                   Si es None, obtiene datos de todas las instituciones.
        
        Returns:
            List[Dict]: Lista con registros pivotados por institución.
                       Cada diccionario contiene: idinstitucion, institucion, [tipos_evento], total.
        
        Raises:
            ValueError: Si el ID de institución no es válido.
            pymysql.Error: Si hay error en la consulta a la base de datos.
        """
        # Validación de parámetros
        if institucion is not None and not str(institucion).strip():
            institucion = None
        elif institucion is not None and not str(institucion).isdigit():
            raise ValueError("ID de institución debe ser numérico")
        

            # ===== Validación año =====
        if anio is not None:
            anio_str = str(anio).strip()
            if not anio_str:
                anio = None
            elif not anio_str.isdigit() or len(anio_str) != 4:
                raise ValueError("El año debe ser numérico de 4 dígitos")
            else:
                anio = int(anio_str)

        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                filtros = []
                valores = []

                if institucion:
                    filtros.append("instituciones.idinstitucion = %s")
                    valores.append(int(institucion))
                
                if anio is not None:
                    filtros.append("brotes.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                    SELECT 
                        instituciones.idinstitucion,
                        instituciones.nombre AS institucion,
                        tipo_eventos.nombre AS tipo_evento,
                        COUNT(*) AS total
                    FROM brotes
                    INNER JOIN instituciones ON brotes.idinstitucion = instituciones.idinstitucion
                    INNER JOIN tipoeventos tipo_eventos ON brotes.idtipoevento = tipo_eventos.idtipoevento
                    {where_clause}
                    GROUP BY instituciones.idinstitucion, instituciones.nombre, tipo_eventos.nombre
                    ORDER BY instituciones.nombre ASC, tipo_eventos.nombre ASC
                """

                cursor.execute(query, valores)
                resultados = cursor.fetchall()
                
                # 🔹 TU CÓDIGO IMPLEMENTADO AQUÍ 🔹
                # Pivotar resultados → 1 fila por institución y columnas por tipo_evento
                instituciones_pivot = {}
                for row in resultados:
                    inst_id = row["idinstitucion"]
                    inst_nombre = row["institucion"]
                    tipo = row["tipo_evento"]
                    total = row["total"]

                    if inst_id not in instituciones_pivot:
                        instituciones_pivot[inst_id] = {
                            "idinstitucion": inst_id,
                            "institucion": inst_nombre
                        }

                    instituciones_pivot[inst_id][tipo] = total

                # 🔹 Agregar totales fila por fila
                for inst_id, datos in instituciones_pivot.items():
                    datos["total"] = sum(
                        v for k, v in datos.items() 
                        if k not in ["idinstitucion", "institucion"]
                    )

                return list(instituciones_pivot.values())
                
        except pymysql.Error as e:
            logging.error(f"Error al obtener resumen de eventos: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado en obtener_resumen_eventos: {e}")
            raise
        finally:
            conn.close()



    #Funcion para obtener datos de Resumen de Brotes por Diagnóstico
    @staticmethod
    def obtener_resumen_diagnosticos(
            institucion: Optional[int] = None,
            anio: Optional[int] = None
        ) -> List[Dict]:

        conn = MySQLConnection().connect()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:

                filtros = []
                valores = []

                if institucion:
                    filtros.append("b.idinstitucion = %s")
                    valores.append(institucion)

                if anio is not None:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                        SELECT 
                            diagnostico,
                            total_brotes,
                            total_probables,
                            activos,
                            probables_activos,
                            alta,
                            probables_altas,
                            pendiente_alta,
                            probables_pendiente_alta
                        FROM (
                            SELECT
                                d.nombre AS diagnostico,

                                COUNT(b.idbrote) AS total_brotes,
                                SUM(b.casosprob) AS total_probables,
                                
                                SUM(CASE WHEN b.fechalta IS NOT NULL THEN 1 ELSE 0 END) AS alta,
                                SUM(CASE WHEN b.fechalta IS NOT NULL THEN b.casosprob ELSE 0 END) AS probables_altas,
                                
                                SUM(
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        AND CURDATE() > DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        THEN 1 ELSE 0
                                    END
                                ) AS pendiente_alta,
                                
                                SUM(
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        AND CURDATE() <= DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        THEN 1 ELSE 0
                                    END
                                ) AS activos,
                                
                                SUM(
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        AND CURDATE() > DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        THEN b.casosprob ELSE 0
                                    END
                                ) AS probables_pendiente_alta,
                                
                                SUM(
                                    CASE
                                        WHEN b.fechalta IS NULL
                                        AND CURDATE() <= DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                        THEN b.casosprob ELSE 0
                                    END
                                ) AS probables_activos

                            FROM brotes b
                            INNER JOIN diagsospecha d ON b.iddiag = d.iddiag
                            {where_clause}
                            GROUP BY d.nombre
                        ) t
                        ORDER BY total_brotes DESC;
                """

                cursor.execute(query, valores)
                return cursor.fetchall()

        finally:
            conn.close()


    #Funcion para obtener datos de Resumen de Brotes por JURISDICCION
    @staticmethod
    def obtener_resumen_jurisdiccion(
            institucion: Optional[int] = None,
            anio: Optional[int] = None
        ) -> List[Dict]:

        conn = MySQLConnection().connect()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:

                filtros = []
                valores = []

                if institucion:
                    filtros.append("b.idinstitucion = %s")
                    valores.append(institucion)

                if anio is not None:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                        SELECT
                            j.nombre AS jurisdiccion,

                            COUNT(b.idbrote) AS total_brotes,
                            SUM(b.casosprob) AS total_probables,
                            
                            SUM(
                                CASE 
                                    WHEN b.fechalta IS NOT NULL 
                                    THEN 1 ELSE 0 
                                END
                            ) AS alta,
                            
                            SUM(
                                CASE 
                                    WHEN b.fechalta IS NOT NULL 
                                    THEN b.casosprob ELSE 0 
                                END
                            ) AS probables_altas,
                            
                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND CURDATE() > DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    THEN 1 ELSE 0
                                END
                            ) AS pendiente_alta,
                            
                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND CURDATE() > DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    THEN b.casosprob ELSE 0
                                END
                            ) AS probables_pendiente_alta,
                            
                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND CURDATE() <= DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    THEN 1 ELSE 0
                                END
                            ) AS activos,
                            
                            SUM(
                                CASE
                                    WHEN b.fechalta IS NULL
                                    AND CURDATE() <= DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                                    THEN b.casosprob ELSE 0
                                END
                            ) AS probables_activos

                        FROM brotes b
                        INNER JOIN diagsospecha d 
                            ON b.iddiag = d.iddiag
                        INNER JOIN jurisdicciones j 
                            ON b.idjurisdiccion = j.idjurisdiccion

                        {where_clause}

                        GROUP BY j.nombre
                        ORDER BY total_brotes DESC;                    
                """

                cursor.execute(query, valores)
                return cursor.fetchall()

        finally:
            conn.close()



    #Metódo para obtener diagnósticos para gráfico de DASHBOARD
    @staticmethod
    def obtener_diagnosticos( institucion: Optional[int] = None,
            anio: Optional[int] = None
        ) -> List[Dict]:

        conn = MySQLConnection().connect()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                filtros = []
                valores = []

                if institucion:
                    filtros.append("b.idinstitucion = %s")
                    valores.append(institucion)

                if anio is not None:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""
            
                query = f"""
                    SELECT DISTINCT 
                        d.iddiag,
                        d.nombre
                    FROM brotes b
                    INNER JOIN diagsospecha d
                        ON b.iddiag = d.iddiag
                    INNER JOIN instituciones i
                        ON b.idinstitucion = i.idinstitucion
                    {where_clause}
                    GROUP BY d.iddiag, d.nombre
                    ORDER BY d.nombre ASC
                """
                cursor.execute(query, valores)
                return cursor.fetchall()
        finally:
            conn.close()



    #Metódo para obtener datos de diagnósticos semanales para construir gráfico
    @staticmethod
    def obtener_brotes_por_semana(
            institucion=None,
            anio=None,
            diagnostico=None):

        conn = MySQLConnection().connect()

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:

                filtros = []
                valores = []

                if institucion:
                    filtros.append("b.idinstitucion = %s")
                    valores.append(institucion)

                if anio:
                    filtros.append("b.anio = %s")
                    valores.append(anio)

                if diagnostico:
                    filtros.append("b.iddiag = %s")
                    valores.append(diagnostico)

                where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

                query = f"""
                    SELECT
                        b.sem_epi AS semana,
                        COUNT(*) AS total
                    FROM brotes b
                    {where_clause}
                    GROUP BY b.sem_epi
                    ORDER BY b.sem_epi
                """

                cursor.execute(query, valores)

                return cursor.fetchall()

        finally:
            conn.close()



    
    #Obtener brotes por estado actual
    @staticmethod
    def obtener_edo_actual_pendientes(anio=None):
        from datetime import date

        if not anio:
            anio = date.today().year

        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        b.idbrote,
                        b.folio_anual,
                        doc.folionotinmed AS folioNotinmed,       
                        t.nombre AS tipo_evento,
                        b.unidadnotif,
                        j.nombre AS jurisdiccion,                        
                        i.nombre AS institucion,
                        d.nombre AS diagnostico,
                        b.fechultimocaso,
                        d.periodo_incubacion,

                        -- Fecha probable de alta
                        DATE_ADD(
                            b.fechultimocaso,
                            INTERVAL d.periodo_incubacion DAY
                        ) AS fecha_probable_alta,

                        -- Días expirados
                        DATEDIFF(
                            CURDATE(),
                            DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                        ) AS dias_expirados,

                        'Pendiente Alta' AS estado_actual

                    FROM brotes b
                    LEFT JOIN (
                        SELECT brote_id, folionotinmed
                        FROM (
                            SELECT *,
                                ROW_NUMBER() OVER(
                                    PARTITION BY brote_id
                                    ORDER BY fechnotinmed DESC, iddocumento DESC
                                ) AS rn
                            FROM documentos
                            WHERE tipo_notificacion = 'INICIAL'
                        ) t
                        WHERE rn = 1
                    ) doc ON b.idbrote = doc.brote_id                               
                    INNER JOIN tipoeventos t ON b.idtipoevento = t.idtipoevento
                    INNER JOIN diagsospecha d ON b.iddiag = d.iddiag
                    INNER JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion
                    INNER JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                    WHERE
                        b.anio = %s
                        AND b.fechalta IS NULL
                        AND b.fechultimocaso IS NOT NULL
                        AND DATEDIFF(
                            CURDATE(),
                            DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                        ) > 0
                    ORDER BY dias_expirados DESC
                """, (anio,))
                return cursor.fetchall()
        finally:
            conn.close()



            
            
    @staticmethod
    def obtener_edo_actual_activos(anio=None):
        from datetime import date

        if not anio:
            anio = date.today().year

        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        b.idbrote,
                        b.folio_anual,
                        doc.folionotinmed AS folioNotinmed,       
                        t.nombre AS tipo_evento,
                        b.unidadnotif,
                        j.nombre as jurisdiccion,
                        d.nombre AS diagnostico,
                        i.nombre AS institucion,
                        b.fechultimocaso,
                        d.periodo_incubacion,

                        DATE_ADD(
                            b.fechultimocaso,
                            INTERVAL d.periodo_incubacion DAY
                        ) AS fecha_probable_alta,

                        DATEDIFF(
                            CURDATE(),
                            DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                        ) AS dias_expirados,

                        CASE
                            WHEN b.fechalta IS NOT NULL THEN 'Alta'
                            WHEN DATEDIFF(
                                CURDATE(),
                                DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                            ) > 0 THEN 'Pendiente Alta'
                            ELSE 'Activo'
                        END AS estado_actual

                    FROM brotes b
                    LEFT JOIN (
                        SELECT brote_id, folionotinmed
                        FROM (
                            SELECT *,
                                ROW_NUMBER() OVER(
                                    PARTITION BY brote_id
                                    ORDER BY fechnotinmed DESC, iddocumento DESC
                                ) AS rn
                            FROM documentos
                            WHERE tipo_notificacion = 'INICIAL'
                        ) t
                        WHERE rn = 1
                    ) doc ON b.idbrote = doc.brote_id  
                    INNER JOIN tipoeventos t ON b.idtipoevento = t.idtipoevento
                    INNER JOIN diagsospecha d ON b.iddiag = d.iddiag
                    INNER JOIN jurisdicciones j ON b.idjurisdiccion = j.idjurisdiccion
                    INNER JOIN instituciones i ON b.idinstitucion = i.idinstitucion
                    WHERE
                        b.anio = %s
                        AND b.fechalta IS NULL
                        AND b.fechultimocaso IS NOT NULL
                        AND DATEDIFF(
                            CURDATE(),
                            DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
                        ) <= 0
                    ORDER BY b.idbrote
                """, (anio,))
                return cursor.fetchall()
        finally:
            conn.close()

       
    #@staticmethod
    # def obtener_edo_actual_activos():
    #     conn = MySQLConnection().connect()
    #     try:
    #         with conn.cursor() as cursor:
    #             cursor.execute("""
    #                             SELECT
    #                                 b.idbrote AS idbrote,
    #                                 t.nombre AS tipo_evento, 
    #                                 b.unidadnotif, 
    #                                 b.fechultimocaso,
    #                                 d.nombre diagnostico,
    #                                 b.fechalta,
    #                                 d.periodo_incubacion,
    #                                 -- Fecha probable de alta
    #                                 CASE
    #                                     WHEN b.fechalta IS NULL
    #                                     THEN DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)
    #                                     ELSE NULL
    #                                 END AS fecha_probable_alta,
    #                                 -- Días expirados
    #                                 CASE
    #                                     WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0
    #                                     THEN DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY))
    #                                     ELSE NULL
    #                                 END AS dias_expirados,
    #                                 -- Estado actual del brote
    #                                 CASE
    #                                     WHEN b.fechalta is not null THEN 'Alta'
    #                                     WHEN b.fechalta is null and DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) > 0 THEN 'Pendiente Alta'
    #                                     ELSE 'Activo'
    #                                 END AS estado_actual
    #                             FROM tipoeventos t
    #                             INNER JOIN brotes b
    #                                 ON t.idtipoevento = b.idtipoevento
    #                             INNER JOIN diagsospecha d
    #                                 ON b.iddiag = d.iddiag
    #                             WHERE 
    #                                 b.fechalta IS NULL AND 
    #                                 DATEDIFF(CURDATE(), DATE_ADD(b.fechultimocaso, INTERVAL d.periodo_incubacion DAY)) <= 0
    #                             order by b.idbrote                               
    #                            """)
    #             return cursor.fetchall()
    #     finally:
    #         conn.close()
            
            
            
#----------- 3. FUNCIONES UPDATE ------------------------------------
    #Metodo para actulizar brote
    @staticmethod
    def actualizar_brote(idbrote, data, ids):
        conn = MySQLConnection().connect()
        if not conn:
            raise Exception("No se pudo establecer conexión a la BD")
        
        try:
            with conn.cursor() as cursor:

                # 1) Obtener año actual del brote
                cursor.execute("SELECT anio FROM brotes WHERE idbrote = %s", (idbrote,))
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"No existe brote con idbrote={idbrote}")

                anio_actual = row["anio"]

                # 2) Validar fechinicio (necesaria) y calcular anio_nuevo desde MySQL
                fechinicio = data.get("fechinicio")
                if not fechinicio:
                    raise ValueError("fechinicio es obligatoria para editar (regla: año no editable)")

                cursor.execute("SELECT YEAR(%s) AS anio_nuevo", (fechinicio,))

                anio_nuevo = cursor.fetchone()["anio_nuevo"]

                if not anio_nuevo:
                    raise ValueError("No se pudo calcular el año a partir de fechinicio")

                # 3) Regla segura: NO permitir cambio de año
                # if anio_actual is not None and int(anio_nuevo) != int(anio_actual):
                #     raise ValueError(
                #         f"No se permite cambiar el año del brote. "
                #         f"Año actual: {anio_actual}, año solicitado: {anio_nuevo}. "
                #         f"Si necesitas cambiarlo, se requiere un proceso especial."
                #     )

                sql = """
                    UPDATE brotes SET 
                        anio = %s,
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
                    int(anio_nuevo),
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
            
            


#---METODOS PARA ELIMINAR REGISTROS
    @staticmethod
    def eliminar_brote(brote_id):
        """
        Elimina un brote y todos sus documentos asociados
        """
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql_verficar = "SELECT idbrote FROM brotes WHERE idbrote = %s"
                cursor.execute(sql_verficar, (brote_id,))
                brote = cursor.fetchone()
                
                if not brote:
                    raise ValueError(f"No existe el brote con ID {brote_id}")
                
                # Eliminar carpeta completa del brote con todos sus archivos
                carpeta_brote = os.path.join(Config.UPLOAD_FOLDER, f"brote_{brote_id}")

                archivos_eliminados = 0
                error_archivos = None

                if os.path.exists(carpeta_brote):
                    try:
                        # Contar archivos antes de eliminar
                        archivos_eliminados = len([f for f in os.listdir(carpeta_brote) if os.path.isfile(os.path.join(carpeta_brote, f))])

                        # Eliminar carpeta completa con todos los archivos
                        shutil.rmtree(carpeta_brote)
                        logger.info(f"Carpeta eliminada: {carpeta_brote} ({archivos_eliminados} archivos)")

                    except Exception as e:
                        error_archivos = str(e)
                        logger.error(f"Error CRÍTICO al eliminar carpeta {carpeta_brote}: {error_archivos}")
                        # No continuar si falla eliminar archivos
                        raise Exception(f"No se pudieron eliminar los archivos físicos del brote {brote_id}: {error_archivos}")
                else:
                    logger.warning(f"Carpeta no encontrada: {carpeta_brote} - Se procederá a eliminar solo registros de BD")

                # Solo llegar aquí si los archivos se eliminaron exitosamente o no existían
                # Eliminar registros de documentos de la BD
                sql_docs = "DELETE FROM documentos WHERE brote_id = %s"
                cursor.execute(sql_docs, (brote_id,))
                docs_bd_eliminados = cursor.rowcount
                
                sql_brote = "DELETE FROM brotes WHERE idbrote = %s"
                cursor.execute(sql_brote, (brote_id,))               
                
                conn.commit()
                logger.info(f"Brote {brote_id} eliminado: {docs_bd_eliminados} registros BD, {archivos_eliminados} archivos físicos")
                return True
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al eliminar el brote {brote_id}: {str(e)}")
            raise e
        finally:
            conn.close()
        
        
        
 
 
 
 #---METODOS PARA DESCARGAR Y ELIMINAR DOCUMENTOS
    @staticmethod
    def obtener_documento_por_id(iddocumento):
        """Obtiene un documento específico por su ID"""
        conn = None
        try:
            logger.debug(f"Obteniendo documento {iddocumento} de BD")
            conn = MySQLConnection().connect()

            if not conn:
                logger.error("No se pudo establecer conexión a la BD")
                return None

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT iddocumento, brote_id, nombre_archivo, path,
                        tipo_notificacion, folionotinmed, fechnotinmed,
                        fechacarga, fechmodificacion
                    FROM documentos
                    WHERE iddocumento = %s
                """, (iddocumento,))

                resultado = cursor.fetchone()

                if not resultado:
                    logger.warning(f"Documento {iddocumento} no encontrado en la BD")
                    return None

                # Ya es un diccionario, retornarlo directamente o normalizarlo
                documento = {
                    'iddocumento': resultado['iddocumento'],
                    'brote_id': resultado['brote_id'],
                    'nombre_archivo': resultado['nombre_archivo'],
                    'path': resultado['path'],
                    'tipo_notificacion': resultado['tipo_notificacion'],
                    'folionotinmed': resultado['folionotinmed'],
                    'fechnotinmed': resultado['fechnotinmed'],
                    'fechacarga': resultado['fechacarga'],
                    'fechmodificacion': resultado['fechmodificacion']
                }                
                return documento
                
        except Exception as e:
            logger.error(f"Error al obtener documento {iddocumento}: {str(e)}", exc_info=True)
            return None
            
        finally:
            if conn:
                conn.close()
                


    @staticmethod
    def eliminar_documento(iddocumento):
        """Elimina un documento de la BD y el archivo físico"""
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:                
                cursor.execute("""
                    SELECT path, nombre_archivo 
                    FROM documentos 
                    WHERE iddocumento = %s
                """, (iddocumento,))
                
                documento = cursor.fetchone()
                
                if not documento:
                    raise ValueError(f"No existe el documento con ID {iddocumento}")
                
                ruta_archivo = documento['path']
                nombre_archivo = documento['nombre_archivo']                               
                
                # Intentar eliminar el archivo físico
                if ruta_archivo:
                    try:                        
                        from flask import current_app                        
                        # Opción 1: Si tu app está en la raíz del proyecto
                        ruta_completa = os.path.join(current_app.root_path, ruta_archivo)                                                                       
                        ruta_completa = os.path.normpath(ruta_completa)                                               
                        
                        if os.path.exists(ruta_completa):
                            os.remove(ruta_completa)                            
                        else:
                            # Intentar rutas alternativas
                            rutas_alternativas = [
                                os.path.join(os.getcwd(), ruta_archivo),
                                os.path.join(current_app.root_path, ruta_archivo),
                                os.path.abspath(ruta_archivo)
                            ]
                            
                            logger.warning(f"Archivo no encontrado en: {ruta_completa}")
                            logger.info(f"Intentando rutas alternativas...")
                            
                            archivo_eliminado = False
                            for ruta_alt in rutas_alternativas:
                                ruta_alt = os.path.normpath(ruta_alt)
                                logger.info(f"Probando: {ruta_alt} - Existe: {os.path.exists(ruta_alt)}")
                                
                                if os.path.exists(ruta_alt):
                                    os.remove(ruta_alt)
                                    logger.info(f"Archivo eliminado desde ruta alternativa: {ruta_alt}")
                                    archivo_eliminado = True
                                    break
                            
                            if not archivo_eliminado:
                                logger.error(f"No se pudo encontrar el archivo en ninguna ruta: {nombre_archivo}")
                                # IMPORTANTE: No eliminar de BD si el archivo no se pudo eliminar
                                raise Exception(f"No se pudo encontrar el archivo físico: {nombre_archivo}")

                    except Exception as e:
                        logger.error(f"Error al eliminar archivo físico: {str(e)}", exc_info=True)
                        # Re-lanzar la excepción para evitar eliminar registro de BD
                        raise Exception(f"Error al eliminar archivo físico: {str(e)}")
                
                # Eliminar registro de la BD
                cursor.execute("DELETE FROM documentos WHERE iddocumento = %s", (iddocumento,))
                
                if cursor.rowcount == 0:
                    raise ValueError(f"No se pudo eliminar el documento")
                
                conn.commit()
                logger.info(f"Documento {iddocumento} ({nombre_archivo}) eliminado de la BD")
                return True
                
        except ValueError as ve:
            logger.warning(str(ve))
            raise ve
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al eliminar documento {iddocumento}: {str(e)}", exc_info=True)
            raise e

        finally:
            conn.close()




# ============================================================================
# CRUD DE DIAGNÓSTICOS DE SOSPECHA
# ============================================================================

    # -------------------- CREATE --------------------
    @staticmethod
    def crear_diagnostico(nombre, periodo_incubacion):
        """Crea un nuevo diagnóstico de sospecha"""
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO diagsospecha (nombre, periodo_incubacion)
                    VALUES (%s, %s)
                """
                cursor.execute(sql, (nombre, periodo_incubacion))
                conn.commit()
                diagnostico_id = cursor.lastrowid
                logger.info(f"Diagnóstico creado con ID {diagnostico_id}")
                return diagnostico_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al crear diagnóstico: {str(e)}")
            raise e
        finally:
            conn.close()


    # -------------------- READ --------------------
    @staticmethod
    def obtener_todos_diagnosticos():
        """Obtiene todos los diagnósticos de sospecha"""
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT iddiag, nombre, periodo_incubacion
                    FROM diagsospecha
                    ORDER BY nombre ASC
                """)
                return cursor.fetchall()
        finally:
            conn.close()


    @staticmethod
    def obtener_diagnostico_por_id(iddiag):        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT iddiag, nombre, periodo_incubacion
                    FROM diagsospecha
                    WHERE iddiag = %s
                """, (iddiag,))
                return cursor.fetchone()
        finally:
            conn.close()
            
    
    @staticmethod
    def obtener_diagnostico_por_nombre(nombre):        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT iddiag, nombre, periodo_incubacion
                    FROM diagsospecha
                    WHERE nombre = %s
                """, (nombre,))
                return cursor.fetchone()
        finally:
            conn.close()   

    


    # -------------------- UPDATE --------------------
    @staticmethod
    def actualizar_diagnostico(iddiag, nombre, periodo_incubacion):
        """Actualiza un diagnóstico existente"""
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE diagsospecha
                    SET nombre = %s,
                        periodo_incubacion = %s
                    WHERE iddiag = %s
                """
                cursor.execute(sql, (nombre, periodo_incubacion, iddiag))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Diagnóstico {iddiag} actualizado correctamente")
                else:
                    logger.warning(f"Diagnóstico {iddiag} no encontrado")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error al actualizar diagnóstico {iddiag}: {str(e)}")
            raise e
        finally:
            conn.close()


    # -------------------- DELETE --------------------
    @staticmethod
    def eliminar_diagnostico(iddiag):
        """Elimina un diagnóstico de sospecha"""
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                # Verificar si existe
                cursor.execute("SELECT iddiag FROM diagsospecha WHERE iddiag = %s", (iddiag,))
                diagnostico = cursor.fetchone()

                if not diagnostico:
                    raise ValueError(f"No existe el diagnóstico con ID {iddiag}")

                # Eliminar
                cursor.execute("DELETE FROM diagsospecha WHERE iddiag = %s", (iddiag,))
                conn.commit()
                logger.info(f"Diagnóstico {iddiag} eliminado correctamente")
                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error al eliminar diagnóstico {iddiag}: {str(e)}")
            raise e
        finally:
            conn.close()
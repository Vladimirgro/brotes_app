from app.models.mysql_connection import MySQLConnection

class UnidadModel:

    @staticmethod
    def obtener_todas_para_gis():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        clues,
                        nombre_comercial AS nombre_unidad,
                        nombre_institucion AS institucion,
                        municipio,
                        jurisdiccion,
                        nivel_atencion,
                        latitud,
                        longitud
                    FROM unidades_salud
                    WHERE estatus_operacion = 'EN OPERACION'
                    AND latitud IS NOT NULL
                    AND longitud IS NOT NULL
                """)
                return cursor.fetchall()
        finally:
            conn.close()


    @staticmethod
    def obtener_municipios_distintos():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT municipio
                    FROM unidades_salud
                    WHERE municipio IS NOT NULL
                    ORDER BY municipio ASC
                """)
                return cursor.fetchall()
        finally:
            conn.close()


    #MÉTODO PARA JURISDICCIONES
    @staticmethod
    def obtener_municipios_por_jurisdiccion():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT
                        jurisdiccion,
                        municipio
                    FROM unidades_salud
                    WHERE jurisdiccion IS NOT NULL
                    AND municipio IS NOT NULL
                    AND estatus_operacion = 'EN OPERACION'
                    ORDER BY jurisdiccion, municipio
                """)
                return cursor.fetchall()
        finally:
            conn.close()
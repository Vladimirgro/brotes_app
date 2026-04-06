from app.models.mysql_connection import MySQLConnection
import pymysql

class IndicadoresModel:

    @staticmethod
    def obtener_oportunidad_notificacion(fecha_inicio, fecha_final):
        db = MySQLConnection()
        conn = db.connect()

        if not conn:
            return []

        try:
            with conn.cursor() as cursor:

                query = """
                    SELECT
                        i.nombre AS institucion,
                        COUNT(b.idbrote) AS total_brotes,

                        SUM(
                            CASE
                                WHEN EXISTS (
                                    SELECT 1
                                    FROM documentos d
                                    WHERE d.brote_id = b.idbrote
                                    AND d.tipo_notificacion = 'INICIAL'
                                    AND DATEDIFF(d.fechnotinmed, b.fechinicio) <= 1
                                )
                                THEN 1 ELSE 0
                            END
                        ) AS brotes_oportunos,

                        ROUND(
                            (
                                SUM(
                                    CASE
                                        WHEN EXISTS (
                                            SELECT 1
                                            FROM documentos d
                                            WHERE d.brote_id = b.idbrote
                                            AND d.tipo_notificacion = 'INICIAL'
                                            AND DATEDIFF(d.fechnotinmed, b.fechinicio) <= 1
                                        )
                                        THEN 1 ELSE 0
                                    END
                                ) / COUNT(b.idbrote)
                            ) * 100,
                            2
                        ) AS porcentaje_oportunidad

                    FROM brotes b
                    INNER JOIN instituciones i
                        ON b.idinstitucion = i.idinstitucion

                    WHERE b.fechinicio BETWEEN %s AND %s

                    GROUP BY i.nombre
                    ORDER BY porcentaje_oportunidad DESC
                """

                cursor.execute(query, (fecha_inicio, fecha_final))
                resultados = cursor.fetchall()

                return resultados

        except pymysql.MySQLError as e:
            print(f"Error en consulta indicador oportunidad: {e}")
            return []

        finally:
            db.close()



    @staticmethod
    def _consulta_oportunidad(fecha_inicio, fecha_fin, columna_fecha):

        db = MySQLConnection()
        conn = db.connect()

        try:
            with conn.cursor() as cursor:

                query = f"""
                    SELECT
                        i.nombre AS institucion,
                        COUNT(b.idbrote) AS total_brotes,

                        SUM(
                            CASE
                                WHEN EXISTS (
                                    SELECT 1
                                    FROM documentos d
                                    WHERE d.brote_id = b.idbrote
                                    AND d.tipo_notificacion = 'INICIAL'
                                    AND DATEDIFF(d.fechnotinmed, {columna_fecha}) <= 1
                                )
                                THEN 1 ELSE 0
                            END
                        ) AS brotes_oportunos

                    FROM brotes b
                    INNER JOIN instituciones i
                        ON b.idinstitucion = i.idinstitucion

                    WHERE b.fechinicio BETWEEN %s AND %s

                    GROUP BY i.nombre
                """

                cursor.execute(query, (fecha_inicio, fecha_fin))
                resultados = cursor.fetchall()

                # 🔹 Calcular totales backend
                total_brotes = sum(r["total_brotes"] for r in resultados)
                total_oportunos = sum(r["brotes_oportunos"] for r in resultados)

                porcentaje = 0
                if total_brotes > 0:
                    porcentaje = round((total_oportunos / total_brotes) * 100, 2)

                return {
                    "detalle": resultados,
                    "totales": {
                        "total_brotes": total_brotes,
                        "total_oportunos": total_oportunos,
                        "porcentaje": porcentaje
                    }
                }

        finally:
            db.close()



    @staticmethod
    def obtener_oportunidad_triple(fecha_inicio, fecha_fin):

        return {
            "por_inicio": IndicadoresModel._consulta_oportunidad(
                fecha_inicio, fecha_fin, "b.fechinicio"
            ),
            "por_consulta": IndicadoresModel._consulta_oportunidad(
                fecha_inicio, fecha_fin, "b.fecha_consulta"
            ),
            "por_notificacion": IndicadoresModel._consulta_oportunidad(
                fecha_inicio, fecha_fin, "b.fechnotifica"
            ),
        }
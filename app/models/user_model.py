from app.models.mysql_connection import MySQLConnection, pymysql
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
import logging

# Crear logger para este módulo
logger = logging.getLogger(__name__)


class User(UserMixin):
    def __init__(self, id, nombre, email, password_hash, rol, activo, **kwargs):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash
        self.rol = rol
        self.activo = activo

    def get_id(self):
        return str(self.id)
    
    
class UserModel:
    @staticmethod
    def parse_user(data):
        return User(
            id=data['id'],
            nombre=data['nombre'],
            email=data['email'],
            password_hash=data['password_hash'],
            rol=data['rol'],
            activo=data['activo']
        )
        
    @staticmethod
    def find_by_email(email):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                                SELECT id, nombre, email, password_hash, rol, activo
                                FROM usuarios
                                WHERE email = %s AND activo = 1
                            """, (email,))
                user_data = cursor.fetchone()
                if user_data:
                    logger.info(f"Usuario encontrado: {email}")
                    return UserModel.parse_user(user_data)
                else:
                    logger.warning(f"Usuario no encontrado o inactivo: {email}")
                    return None
        except Exception as e:
            logger.error(f"Error al buscar usuario por email {email}: {str(e)}", exc_info=True)
            return None
        finally:
            conn.close()

    @staticmethod
    def create_user(nombre, email, password, rol):
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
                    VALUES (%s, %s, %s, %s, 1)
                """, (nombre, email, password_hash, rol))
                conn.commit()
                logger.info(f"Usuario creado exitosamente: {email} con rol {rol}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al crear usuario {email}: {str(e)}", exc_info=True)
            raise e
        finally:
            conn.close()

    
    #Funcion para validar password del login
    @staticmethod
    def validate_password(stored_hash, password_input):
        return check_password_hash(stored_hash, password_input)
    
    
    
    #Funcion para listar usuarios registrados
    @staticmethod
    def obtener_todos():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre, email, rol, activo, created_at
                    FROM usuarios
                    ORDER BY created_at DESC
                """)
                return cursor.fetchall()
        finally:
            conn.close()
            
            
    #Obtener Id para actualizar usuarios       
    @staticmethod
    def obtener_por_id(user_id):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    return UserModel.parse_user(user_data)
        finally:
            conn.close()


    #Actualizar usuarios
    @staticmethod
    def actualizar_usuario(id_usuario, nombre, email, rol):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE usuarios
                    SET nombre = %s, email = %s, rol = %s
                    WHERE id = %s
                """, (nombre, email, rol, id_usuario))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"Usuario {id_usuario} actualizado: {email} - {rol}")
                else:
                    logger.warning(f"Usuario {id_usuario} no encontrado para actualizar")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al actualizar usuario {id_usuario}: {str(e)}", exc_info=True)
            raise e
        finally:
            conn.close()


    #Cambiar estado de usuario en editar
    @staticmethod
    def cambiar_estado(id_usuario, nuevo_estado):
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE usuarios SET activo = %s WHERE id = %s", (nuevo_estado, id_usuario))
                conn.commit()

                if cursor.rowcount > 0:
                    estado_texto = "activo" if nuevo_estado == 1 else "inactivo"
                    logger.info(f"Estado de usuario {id_usuario} cambiado a {estado_texto}")
                else:
                    logger.warning(f"Usuario {id_usuario} no encontrado para cambiar estado")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al cambiar estado de usuario {id_usuario}: {str(e)}", exc_info=True)
            raise e
        finally:
            conn.close()
            
    
    #Funcion para contar usuarios y crear super Usuario        
    @staticmethod
    def total_usuarios():
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM usuarios")
                resultado = cursor.fetchone()
                return resultado['total']
        finally:
            conn.close()
            
            
    #Crear el superusuario
    @staticmethod
    def crear_usuario(data):        
        conn = MySQLConnection().connect()
        try:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO usuarios (nombre, email, password_hash, rol, activo)
                VALUES (%(nombre)s, %(email)s, %(password)s, %(rol)s, %(activo)s)
                """
                cursor.execute(sql, data)
                conn.commit()
                return cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error al crear usuario: {e}")
            return None
        finally:
            conn.close()



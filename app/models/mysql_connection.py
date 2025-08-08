import pymysql
from config import DB_CONFIG

# Ensure DB_CONFIG contains the necessary keys
required_keys = ['host', 'user', 'password', 'db']
for key in required_keys:
    if key not in DB_CONFIG:
        raise KeyError(f"Missing required DB_CONFIG key: {key}")


class MySQLConnection:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=DB_CONFIG['host'], 
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'], 
                db=DB_CONFIG['db'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )            
            return self.connection  # Retorna la conexión si es exitosa
        except pymysql.MySQLError as e:
            print(f"Error al conectar con la base de datos: {e}")
            return None  # Retorna None si hay un error en la conexión
    
    def close(self):
        if self.connection:
            try:
                self.connection.close()
                print("Conexión cerrada correctamente")
            except pymysql.MySQLError as e:
                print(f"Error al cerrar la conexión: {e}")
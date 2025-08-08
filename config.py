from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'vladimir'),
    'db': os.getenv('DB_NAME', 'brotes_app'),
    'ssl_ca': "/path/to/ca-cert.pem",
    'charset': "utf8mb4"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Esto apunta a la carpeta raíz del proyecto (donde está config.py)
APP_DIR = os.path.join(BASE_DIR, 'app')  # ← Esto apunta a la carpeta app


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'f43afbca9a1a7d436fc1baf66e20cda47fb300f73a25b1c5')
    # app.config['WTF_CSRF_ENABLED'] = True  PENDIETE CONFIGURAR
    
    BASE_DIR = APP_DIR  # ← Añade esto
    UPLOAD_FOLDER = os.path.join(APP_DIR, 'static', 'uploads')  # ← Corrección aquí
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
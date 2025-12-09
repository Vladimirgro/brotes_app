from dotenv import load_dotenv
import os
from datetime import timedelta

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

    # Protección CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Sin límite de tiempo para desarrollo
    WTF_CSRF_SSL_STRICT = False  # True en producción con HTTPS

    BASE_DIR = APP_DIR  # ← Añade esto
    UPLOAD_FOLDER = os.path.join(APP_DIR, 'static', 'uploads')
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    
    ALLOWED_EXTENSIONS = {'.docx', '.doc', '.xlsx', '.xlsm', '.xls', '.pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
        
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # True en producción
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Flask-Login básico        
    REMEMBER_COOKIE_DURATION = timedelta(days=1)
    REMEMBER_COOKIE_SECURE = False  # True en producción
    REMEMBER_COOKIE_HTTPONLY = True
    
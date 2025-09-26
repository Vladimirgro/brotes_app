from flask import Flask
from flask_login import LoginManager
from app.models.user_model import UserModel
import logging
from logging.handlers import RotatingFileHandler
import os

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configuración
    from config import Config
    app.config.from_object(Config)

    # CONFIGURAR LOGGER ANTES DE USARLO
    configure_logger(app)
    
    # Inicializa LoginManager
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user_model import UserModel
        return UserModel.obtener_por_id(user_id)

    login_manager.login_view = 'auth_bp.login' 
    
    # Importar Blueprints
    from app.controllers.main_controller import main_bp
    from app.controllers.brotes_controller import brotes_bp
    from app.controllers.auth_controller import auth_bp
    
    
    app.register_blueprint(auth_bp, url_prefix='/auth')    
    app.register_blueprint(main_bp)
    app.register_blueprint(brotes_bp, url_prefix='/brotes')
    
    # Log de inicio de aplicación
    app.logger.info('=== Aplicación Brotes iniciada exitosamente ===')
    app.logger.info(f'Modo: {app.config.get("ENV", "development")}')
    app.logger.info(f'Debug mode: {app.debug}')
    
    return app

def configure_logger(app):
    """Configurar logging para la aplicación"""
    
    # Crear directorio de logs
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("Directorio 'logs' creado")

    try:
        # Limpiar handlers existentes para evitar duplicados
        if app.logger.handlers:
            app.logger.handlers.clear()
        
        # Configurar nivel base del logger
        app.logger.setLevel(logging.INFO)
        
        # Formatter para logs
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s():%(lineno)d - %(message)s'
        )
        
        # Handler para archivo principal (INFO y superior)
        file_handler = RotatingFileHandler(
            'logs/brotes.log', 
            maxBytes=10*1024*1024,  # 10MB (no 10KB)
            backupCount=5,
            encoding='utf-8'  # Importante para caracteres especiales
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Handler para errores específicos
        error_handler = RotatingFileHandler(
            'logs/errors.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)
        
        # Handler para consola (solo en desarrollo)
        if app.debug or app.config.get('ENV') == 'development':
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(levelname)s - %(name)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            app.logger.addHandler(console_handler)
            print("Handler de consola agregado (modo desarrollo)")
        
        # Configurar logging para SQLAlchemy si está en debug
        if app.debug:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        
        # Log inicial de configuración
        app.logger.info('Logger configurado correctamente')
        print("Logger configurado exitosamente")

    except PermissionError as e:
        error_msg = f"Error de permisos al crear archivo de log: {e}"
        print(f"ERROR: {error_msg}")
        # En caso de error de permisos, al menos configurar consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)
        app.logger.error(error_msg)

    except Exception as e:
        error_msg = f"Error al configurar el logger: {e}"
        print(f"ERROR: {error_msg}")
        # Handler de emergencia a consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        app.logger.addHandler(console_handler)
        app.logger.error(error_msg)
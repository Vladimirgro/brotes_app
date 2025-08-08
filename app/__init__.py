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


    # Inicializa LoginManager
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return UserModel.obtener_por_id(user_id)

    login_manager.login_view = 'auth_bp.login' 
    
    # Importar Blueprints
    from app.controllers.main_controller import main_bp
    from app.controllers.brotes_controller import brotes_bp
    from app.controllers.auth_controller import auth_bp
    
    
    app.register_blueprint(auth_bp, url_prefix='/auth')    
    app.register_blueprint(main_bp)
    app.register_blueprint(brotes_bp, url_prefix='/brotes')
    

    return app

def configure_logger(app):
    # Verificar si la carpeta 'logs' existe, si no, crearla
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Crear un manejador de archivos con rotación
    try:
        file_handler = RotatingFileHandler('logs/brotes.log', maxBytes=10240, backupCount=5)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)  # o DEBUG

        # Añadir el manejador al logger de la aplicación
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Aplicación iniciada')

    except PermissionError as e:
        # Si ocurre un error de permisos, mostrar el error y proceder
        app.logger.error(f"Error de permisos al acceder al archivo de log: {e}")

    except Exception as e:
        # Manejar cualquier otro tipo de error
        app.logger.error(f"Error al configurar el logger: {e}")
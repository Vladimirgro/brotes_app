from functools import wraps
from flask import redirect, url_for, flash

from flask_login import current_user

def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión', 'warning')
                return redirect(url_for('auth_bp.login'))
            
            if current_user.rol not in roles:
                flash('Acceso denegado', 'danger')
                return redirect(url_for('brotes_bp.lista_brotes'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator
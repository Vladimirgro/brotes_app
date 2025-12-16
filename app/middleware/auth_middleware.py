from functools import wraps
from flask import redirect, url_for, request, jsonify

from flask_login import current_user

def rol_requerido(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Debes iniciar sesión', 'success': False}), 401
                return redirect(url_for('auth_bp.login'))
            
            if current_user.rol not in roles:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Acceso denegado', 'success': False}), 403
                return redirect(url_for('brotes_bp.lista_brotes'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator
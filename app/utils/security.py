from werkzeug.security import generate_password_hash, check_password_hash

def encriptar_password(password):
    """Retorna el hash seguro de la contraseña."""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verificar_password(password_plano, password_hash):
    """Verifica si la contraseña ingresada coincide con el hash almacenado."""
    return check_password_hash(password_hash, password_plano)



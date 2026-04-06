from flask import Blueprint, redirect, url_for, abort
from flask_login import current_user

gis_bp = Blueprint(
    "gis",
    __name__,
    template_folder="templates",
    static_folder="static"
)

@gis_bp.before_request
def restrict_gis_access():
    # Verificar autenticación
    if not current_user.is_authenticated:
        return redirect(url_for("auth_bp.login"))

    # Verificar rol (ajusta los roles válidos)
    if current_user.rol not in ["super_administrador", "jefe_departamento", "coordinador_estatal"]:
        abort(403)

from .controllers import gis_controller
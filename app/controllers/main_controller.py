from flask import Blueprint, redirect, url_for
from flask_login import current_user, login_required

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
@login_required
def index():
    if current_user.is_authenticated:
        return redirect(url_for('brotes_bp.dashboard'))  # Ya está logueado
    return redirect(url_for('auth_bp.login'))  # No ha iniciado sesión
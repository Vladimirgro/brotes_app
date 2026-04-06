from flask import jsonify
from flask import render_template
from flask_login import login_required
from app.middleware.auth_middleware import rol_requerido
from modules.gis import gis_bp
from modules.gis.services.gis_service import obtener_unidades_geojson
from app.models.unidad_model import UnidadModel


@gis_bp.route("/")
@login_required
@rol_requerido('super_administrador', 'jefe_departamento', 'coordinador_estatal')
def index():
    return render_template("gis/index.html")


@gis_bp.route("/api/unidades")
@login_required
@rol_requerido('super_administrador','jefe_departamento','coordinador_estatal')
def api_unidades():
    data = obtener_unidades_geojson()
    return jsonify(data)



@gis_bp.route("/api/municipios")
@login_required
@rol_requerido('super_administrador','jefe_departamento','coordinador_estatal')
def api_municipios():
    from modules.gis.services.gis_service import obtener_municipios
    data = obtener_municipios()
    return jsonify(data)


@gis_bp.route('/api/jurisdicciones')
@login_required
def obtener_jurisdicciones():
    data = UnidadModel.obtener_municipios_por_jurisdiccion()
    return jsonify(data)
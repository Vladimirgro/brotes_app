from app.models.unidad_model import UnidadModel
from app.models.unidad_model import UnidadModel


def get_unidades():
    return UnidadModel.obtener_todas_para_gis()


def get_municipios():
    return UnidadModel.obtener_municipios_distintos()

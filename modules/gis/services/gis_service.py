from modules.gis.repositories.gis_repository import get_unidades
from modules.gis.repositories.gis_repository import get_municipios


def obtener_unidades_geojson():
    unidades = get_unidades()

    features = []

    for u in unidades:
        if u['latitud'] and u['longitud']:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(u['longitud']), 
                        float(u['latitud'])
                    ]
                },
                "properties": {
                    "clues": u['clues'],
                    "nombre": u['nombre_unidad'],
                    "institucion": u['institucion'],
                    "municipio": u['municipio'],
                    "jurisdiccion": u['jurisdiccion'],
                    "nivel_atencion": u['nivel_atencion']
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }



def obtener_municipios():
    return get_municipios()
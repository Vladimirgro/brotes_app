import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.models.mysql_connection import MySQLConnection
import pandas as pd
import unicodedata

data = pd.read_excel('app/utils/files/Jurisdicciones.xlsx', usecols=['Municipio Residencia'], engine='openpyxl')

data = data.rename(columns={'Municipio Residencia': 'Municipio'})

# Convertir a mayúsculas
data['Municipio'] = data['Municipio'].str.upper()
data['Municipio'] = data['Municipio'].values.tolist()

# Quitar acentos
data['Municipio'] = data['Municipio'].apply(
    lambda x: unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('utf-8')
)

conn = MySQLConnection().connect()
cursor = conn.cursor()
sql = "INSERT INTO municipios (nombre) VALUES (%s)"
valores = [(nombre,) for nombre in data['Municipio'].values.tolist()]
cursor.executemany(sql, valores)
conn.commit()
conn.close()
print("Registros insertados correctamente.")









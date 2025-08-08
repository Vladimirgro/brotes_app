import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pymysql
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'vladimir',
    'db': 'brotes_app'
}

# Establecer la conexión
conn = pymysql.connect(
    host=DB_CONFIG['host'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    db=DB_CONFIG['db'],
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
path = 'C:/projects/brotes_app/app/files/Listado brotes.xlsx'

#path = 'C:/projects/brotes/app/files/Listado brotes.xlsx'
# Cargar el archivo de Excel
try:
    df = pd.read_excel(path, sheet_name="Base_General", engine='openpyxl', header=0)
except FileNotFoundError:
    print("El archivo no se encontró en la ruta especificada. Verifica la ruta y el nombre del archivo.")

df = df.dropna(how='all')

columnas_a_mayusculas = ['Tipo evento', 'Institución','Unidad notificante', 
                         'Dx sospecha', 
                         'Domicilio','Resultado','Observaciones', 'Lugar', 'Localidad']
df[columnas_a_mayusculas] = df[columnas_a_mayusculas].apply(lambda x: x.str.upper())

# Eliminar varias columnas
columnas_a_eliminar = ['No','Jurisdicción', 'Fecha_Alta_Programada', 'Días Expirados para pedir alta', 'Estatus',
                       'Semana epid inicio', 'Semana epid notificacion','Municipio','Población expuesta']
df = df.drop(columnas_a_eliminar, axis=1)

df['Dx sospecha'] = df['Dx sospecha'].replace('ENTEROCOLITIS POR C. DIFFICILE','ENTEROCOLITIS POR CLOSTRIDIUM DIFFICILE')

diagnosticos = {
    'PICADURA DE ABEJAS': 1,
    'SALMONELOSIS': 2,
    'MORDEDURA DE ARAÑA': 3,
    'ETI': 4,
    'INFLUENZA': 5,
    'IRAG': 6,
    'CÓLERA': 7,
    'CONJUNTIVITIS': 8,
    'EDA': 9,
    'GEPI': 10,
    'INTOXICACIÓN ALIMENTARIA': 11,
    'IRAS': 12,
    'SÍNDROME PIE MANO BOCA': 13,
    'COVID-19': 14,
    'DENGUE CON SINGNOS DE ALARMA': 15,
    'DENGUE GRAVE': 16,
    'DENGUE NO GRAVE': 17,
    'ENFERMEDAD RESPIRATORIA VIRAL': 18,
    'LEPTOSPIROSIS': 19,
    'ESAVI': 20,
    'EFE': 21,
    'TOS FERINA': 22,
    'ESCABIOSIS': 23,
    'SARAMPIÓN': 24,
    'VARICELA': 25,
    'HEPATITIS A': 26,
    'PEDICULOSIS': 27,
    'ENTEROCOLITIS POR CLOSTRIDIUM DIFFICILE': 28,
    'TUBERCULOSIS PULMONAR': 29,
    'BRONQUIOLITIS': 30,
    'BRUCELOSIS': 31,
    'CHIKUNGUNYA': 32,
    'CLUSTER': 33,
    'ESCARLATINA': 34,
    'EXANTEMA EN ESTUDIO': 35,
    'EXANTEMA VIRAL': 36,
    'FARINGITIS AGUDA': 37,
    'GINGIVOESTOMATITIS PB HERPÉTICA': 38,
    'INFECCIÓN DEL TORRENTE SANGUÍNEO': 39,
    'INFECCIÓN INCISIONAL PROFUNDA': 40,
    'INTOXICACIÓN DE ORIGEN DESCONOCIDO': 41,
    'INTOXICACIÓN POR CLEMBUTEROL': 42,
    'INTOXICACIÓN POR GAS LP': 43,
    'INTOXICACION POR HONGOS': 44,
    'INTOXICACIÓN POR MONÓXIDO DE CARBONO': 45,
    'INTOXICACIÓN POR PICADURA DE ABEJAS': 46,
    'INTOXICACIÓN POR PLAGUICIDAS': 47,
    'INTOXICACIÓN POR RATICIDA': 48,
    'IVU': 49,
    'MONONUCLEOSIS INFECCIOSA': 50,
    'NEUMONÍA': 51,
    'NEUMONIA ASOCIADA A VENTILACION MECANICA': 52,
    'NEUMONÍA NOSOCOMIAL': 53,
    'NEUMONÍA POR PSEUDOMONA AERUGINOSA': 54,
    'PAROTIDITIS': 55,
    'SEPSIS': 56,
    'SEPSIS POR ENTEROBACTERIAS': 57,
    'SÍFILIS': 58,
    'SÍNDROME COQUELUCHOIDE': 59,
    'SÍNDROME DIARREICO': 60,
    'TRIPANOSOMIASIS': 61,
    'VIRUELA SIMICA': 62,
    'ZIKA': 63,
    'AMIGDALITIS': 65,
    'TUBERCULOSIS': 66,
    'GEPI POR SALMONELLA': 67,
    'HISTOPLASMOSIS': 68,
    'SÍFILIS LATENTE': 69,
    'BACTEREMIA': 70,
    'PB. CÓLERA': 71,
    'MICETISMO': 72,
    'MPOX': 73,
    'RINOFARINGITIS': 74,
    'INTOXICACIÓN POR SUSTANCIA NO ESPECIFICADA': 75
}

mapeo_tipo_evento = {
    'BROTE COMUNITARIO' : 1,
    'BROTE ESCOLAR' : 2,
    'BROTE FAMILIAR' : 3,
    'BROTE FORÁNEO' : 4,
    'BROTE LOCALIZADO' : 5,
    'BROTE NOSOCOMIAL' : 6,
    'CLUSTER' : 7
}

mapeo_tipo_inst = {
    'SSA' : 1,
    'IMSS BIENESTAR' : 2,
    'IMSS OPD' : 3,
    'IMSS RO' : 4,
    'ISSSTE' : 5,
    'DIF' : 6,
    'PEMEX' : 7,
    'OTRAS' : 8
}

print(df['Tipo evento'].unique())
print(df['Institución'].unique())

print(df['Dx sospecha'].unique())


df['Tipo evento'] = df['Tipo evento'].map(mapeo_tipo_evento)

df['Institución'] = df['Institución'].map(mapeo_tipo_inst)

df['Dx sospecha'] = df['Dx sospecha'].map(diagnosticos)

#df['Tipo evento'] = df['Tipo evento'].unique()

print(df['Tipo evento'].unique())
print(df['Institución'].unique())

print(df['Dx sospecha'].unique())


# Reordenar columnas
nuevo_orden = ['Tipo evento',
               'Lugar',
               'Institución', 
               'Unidad notificante',
               'Domicilio', 
               'Localidad',
               'No_Municipio',
               'No_Juris', 
               'Dx sospecha', 
               'Fecha not',
               'Fecha ini',
               'Casos probables', 
               'Casos confirmados',
               'Defunciones',
               'Fecha Último Caso', 
               'Resultado', 
               'Fecha Alta',
               'Observaciones',
                'M',
                'F'
                ]
df = df[nuevo_orden]

df = df.where(pd.notnull(df), None)

#Reemplazar NaN en columnas específicas
# Columnas numéricas
numeric_columns = ['Casos probables', 'M', 'F']
df[numeric_columns] = df[numeric_columns].fillna(0)

for column in numeric_columns:
    df[column] = df[column].astype(int)

# Columnas de texto
text_columns = ['Resultado']
df[text_columns] = df[text_columns].fillna('')

# Mostrar los primeros registros para verificar que los datos se cargaron correctamente
#df['Fecha y hora de alta'] = df['Fecha y hora de alta'].str.strip()

# Verificar si la columna tiene datos y convertir solo esos valores a formato de fecha
columns_to_format = [
                    'Fecha ini', 
                    'Fecha not', 
                    'Fecha Último Caso',                     
                    #'Fecha y hora de alta'
                ]

for col in columns_to_format:
    df[col] = df[col].apply(lambda x: pd.to_datetime(x, dayfirst=True, errors='coerce').strftime('%Y-%m-%d') if pd.notna(x) else x)
    
print(df)

try:
    with conn.cursor() as cursor:                
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE brotes")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        cursor.execute("ALTER TABLE brotes AUTO_INCREMENT = 1")
        for index, row in df.iterrows():
            sql = """
            INSERT INTO brotes (
                            idtipoevento,
                            lugar,
                            idinstitucion,
                            unidadnotif,
                            domicilio,
                            localidad, 
                            idmunicipio, 
                            idjurisdiccion,
                            iddiag, 
                            fechnotifica, 
                            fechinicio, 
                            casosprob, 
                            casosconf, 
                            defunciones,
                            fechultimocaso, 
                            resultado, 
                            fechalta, 
                            observaciones,
                            pobmascexp, 
                            pobfemexp                            
                        ) 
            VALUES (%s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, tuple(None if pd.isna(x) else x for x in row))
        conn.commit()
        print("Datos importados con éxito")
except pymysql.MySQLError as e:
    print(f"Error al importar datos: {e}")
finally:
    conn.close() 
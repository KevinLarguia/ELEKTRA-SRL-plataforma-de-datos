import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

password = quote_plus(os.getenv('DB_PASSWORD'))
engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{password}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("Cargando EQUIPOS...")
df = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='EQUIPOS',
    engine='xlrd',
    header=0
)
print(f"  Filas originales: {df.shape[0]} | Columnas: {df.shape[1]}")

# Renombrar columnas (col 9 y 18 son Unnamed, col 10 es ARTICULO duplicado)
df.columns = [
    'codigo', 'nombre', 'clasificacion',
    'costo_iva_inc', 'margen',
    'precio_publico_iva_cdo', 'precio_publico_iva_cc',
    'precio_publico_usd_cdo', 'precio_publico_usd_cc',
    '_drop1',
    '_articulo_dup',
    'dto_distribuidor',
    'precio_distribuidor_iva_cdo', 'precio_distribuidor_iva_cc',
    'precio_distribuidor_usd_cdo', 'precio_distribuidor_usd_cc',
    'dolar_compra', 'tasa_iva',
    '_drop2'
]

# Eliminar columnas duplicadas y sin datos útiles
df.drop(columns=['_drop1', '_articulo_dup', '_drop2'], inplace=True)

# Eliminar filas completamente vacías
df.dropna(how='all', inplace=True)

# Eliminar filas sin código ni nombre
df = df[df['codigo'].notna() & df['nombre'].notna()]

# Tipos de datos
numeric_cols = [
    'codigo', 'costo_iva_inc', 'margen',
    'precio_publico_iva_cdo', 'precio_publico_iva_cc',
    'precio_publico_usd_cdo', 'precio_publico_usd_cc',
    'dto_distribuidor',
    'precio_distribuidor_iva_cdo', 'precio_distribuidor_iva_cc',
    'precio_distribuidor_usd_cdo', 'precio_distribuidor_usd_cc',
    'dolar_compra', 'tasa_iva'
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['codigo'] = df['codigo'].astype('Int64')

# Normalizar texto
for col in ['nombre', 'clasificacion']:
    df[col] = df[col].astype(str).str.strip().str.upper()
    df[col] = df[col].replace('nan', pd.NA)

# Eliminar duplicados por código
df.drop_duplicates(subset=['codigo'], keep='last', inplace=True)
df.reset_index(drop=True, inplace=True)

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Clasificaciones: {df['clasificacion'].dropna().unique()}")
print(f"\nMuestra:")
print(df[['codigo', 'nombre', 'clasificacion', 'costo_iva_inc', 'precio_publico_iva_cdo', 'tasa_iva']].head(5).to_string())

output_path = '../data/equipos_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV guardado en: {output_path}")

print("Cargando a PostgreSQL...")
df.to_sql('equipos', engine, if_exists='replace', index=False)
print("Tabla 'equipos' cargada correctamente.")

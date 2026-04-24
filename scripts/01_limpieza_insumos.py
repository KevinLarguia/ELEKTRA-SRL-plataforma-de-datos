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

print("Cargando INSUMOS...")
df = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='INSUMOS',
    engine='xlrd',
    header=0
)
print(f"  Filas originales: {df.shape[0]} | Columnas: {df.shape[1]}")

# Renombrar columnas (la última [19] es un número flotante erróneo del Excel)
df.columns = [
    'codigo', 'descripcion', 'unidad', 'tipo_unidad',
    'precio_usd', 'precio_ars', 'precio_ars_iva',
    'oferta_dto', 'precio_final_iva',
    'proveedor_codigo', 'rubro',
    'sup_pintura', 'medidas', 'sup_chapa',
    'fecha_actualizacion', 'proveedor',
    'cotizacion_dolar', 'stock', 'us_tot',
    'columna_extra'
]

# Eliminar la columna extra sin nombre real
df.drop(columns=['columna_extra'], inplace=True)

# Eliminar filas completamente vacías
df.dropna(how='all', inplace=True)

# Eliminar filas sin código ni descripción (son filas de separación en el Excel)
df = df[df['codigo'].notna() & df['descripcion'].notna()]

# Tipos de datos
df['codigo'] = pd.to_numeric(df['codigo'], errors='coerce').astype('Int64')
df['precio_usd'] = pd.to_numeric(df['precio_usd'], errors='coerce')
df['precio_ars'] = pd.to_numeric(df['precio_ars'], errors='coerce')
df['precio_ars_iva'] = pd.to_numeric(df['precio_ars_iva'], errors='coerce')
df['oferta_dto'] = pd.to_numeric(df['oferta_dto'], errors='coerce').fillna(0)
df['precio_final_iva'] = pd.to_numeric(df['precio_final_iva'], errors='coerce')
df['proveedor_codigo'] = pd.to_numeric(df['proveedor_codigo'], errors='coerce').astype('Int64')
df['cotizacion_dolar'] = pd.to_numeric(df['cotizacion_dolar'], errors='coerce')
df['stock'] = pd.to_numeric(df['stock'], errors='coerce')
df['us_tot'] = pd.to_numeric(df['us_tot'], errors='coerce')
df['unidad'] = pd.to_numeric(df['unidad'], errors='coerce')

# Fechas
df['fecha_actualizacion'] = pd.to_datetime(df['fecha_actualizacion'], errors='coerce')

# Normalizar texto
for col in ['descripcion', 'tipo_unidad', 'rubro', 'medidas', 'proveedor']:
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].replace('nan', pd.NA)

df['descripcion'] = df['descripcion'].str.upper()
df['rubro'] = df['rubro'].str.upper()
df['proveedor'] = df['proveedor'].str.upper()

# Eliminar duplicados por código
df.drop_duplicates(subset=['codigo'], keep='last', inplace=True)

df.reset_index(drop=True, inplace=True)

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Nulls por columna:\n{df.isnull().sum()[df.isnull().sum() > 0].to_string()}")
print(f"\nMuestra:")
print(df[['codigo', 'descripcion', 'precio_usd', 'precio_ars', 'proveedor', 'fecha_actualizacion']].head(5).to_string())

# Guardar CSV
output_path = '../data/insumos_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV guardado en: {output_path}")

# Cargar a PostgreSQL
print("Cargando a PostgreSQL...")
df.to_sql('insumos', engine, if_exists='replace', index=False)
print("Tabla 'insumos' cargada correctamente.")

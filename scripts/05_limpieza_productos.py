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

print("Cargando PRODUCTOS...")
df = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='PRODUCTOS',
    engine='xlrd',
    header=0
)
print(f"  Filas originales: {df.shape[0]} | Columnas: {df.shape[1]}")

df.columns = [
    'id', 'nombre', 'precio_base',
    'tasa_iva', 'precio_iva',
    'precio_dolares', 'precio_distribuidor', 'precio_distribuidor_iva',
    'categoria_id', 'categoria', 'descuento'
]

# Eliminar filas vacías
df.dropna(how='all', inplace=True)
df = df[df['id'].notna() & df['nombre'].notna()]

# Tipos
df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
df['categoria_id'] = pd.to_numeric(df['categoria_id'], errors='coerce').astype('Int64')

numeric_cols = [
    'precio_base', 'tasa_iva', 'precio_iva',
    'precio_dolares', 'precio_distribuidor', 'precio_distribuidor_iva',
    'descuento'
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Normalizar texto
df['nombre'] = df['nombre'].astype(str).str.strip().str.upper()
df['nombre'] = df['nombre'].replace('NAN', pd.NA)
df['categoria'] = df['categoria'].astype(str).str.strip().str.upper()
df['categoria'] = df['categoria'].replace('NAN', pd.NA)

# Eliminar duplicados por id
df.drop_duplicates(subset=['id'], keep='last', inplace=True)
df.reset_index(drop=True, inplace=True)

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Categorías: {df['categoria'].dropna().unique()}")
print(f"\nMuestra:")
print(df[['id', 'nombre', 'categoria', 'precio_base', 'precio_iva', 'precio_dolares']].head(5).to_string())

# También limpiar y cargar CATEGORIAS
print("\nCargando CATEGORIAS...")
df_cat = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='CATEGORIAS',
    engine='xlrd',
    header=0
)
# Tomar las primeras dos columnas útiles
df_cat = df_cat.iloc[:, :2].copy()
df_cat.columns = ['id', 'nombre']
df_cat.dropna(subset=['id', 'nombre'], inplace=True)
df_cat['id'] = pd.to_numeric(df_cat['id'], errors='coerce').astype('Int64')
df_cat['nombre'] = df_cat['nombre'].astype(str).str.strip().str.upper()
print(f"  Categorías encontradas: {df_cat.shape[0]}")
print(df_cat.to_string(index=False))

output_path = '../data/productos_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV productos guardado en: {output_path}")

df_cat.to_csv('../data/categorias_limpio.csv', index=False, encoding='utf-8-sig')
print("CSV categorias guardado en: ../data/categorias_limpio.csv")

print("Cargando a PostgreSQL...")
df_cat.to_sql('categorias', engine, if_exists='replace', index=False)
df.to_sql('productos', engine, if_exists='replace', index=False)
print("Tablas 'categorias' y 'productos' cargadas correctamente.")

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

print("Cargando PROVEEDORES...")
df = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='PROVEEDORES',
    engine='xlrd',
    header=0
)
print(f"  Filas originales: {df.shape[0]} | Columnas: {df.shape[1]}")

df.columns = [
    'codigo', 'empresa', 'cotizacion_dolar',
    'telefono', 'direccion', 'codigo_postal',
    'ciudad', 'provincia', 'rubro',
    'email', 'contacto', 'cuit',
    'sitio_web', 'fecha_modificacion', 'ultimo_aumento_pct'
]

# Eliminar filas vacías y sin código
df.dropna(how='all', inplace=True)
df = df[df['codigo'].notna() & df['empresa'].notna()]

# Tipos
df['codigo'] = pd.to_numeric(df['codigo'], errors='coerce').astype('Int64')
df['cotizacion_dolar'] = pd.to_numeric(df['cotizacion_dolar'], errors='coerce')
df['ultimo_aumento_pct'] = pd.to_numeric(df['ultimo_aumento_pct'], errors='coerce')
df['fecha_modificacion'] = pd.to_datetime(df['fecha_modificacion'], errors='coerce')
df['codigo_postal'] = df['codigo_postal'].astype(str).str.strip().replace('nan', pd.NA)

# Normalizar texto
text_cols = ['empresa', 'telefono', 'direccion', 'ciudad', 'provincia', 'rubro', 'contacto']
for col in text_cols:
    df[col] = df[col].astype(str).str.strip().str.upper()
    df[col] = df[col].replace('NAN', pd.NA)

for col in ['email', 'sitio_web', 'cuit']:
    df[col] = df[col].astype(str).str.strip().str.lower()
    df[col] = df[col].replace('nan', pd.NA)

# Eliminar duplicados
df.drop_duplicates(subset=['codigo'], keep='last', inplace=True)
df.reset_index(drop=True, inplace=True)

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Rubros: {df['rubro'].dropna().unique()}")
print(f"\nMuestra:")
print(df[['codigo', 'empresa', 'ciudad', 'provincia', 'rubro', 'cotizacion_dolar']].head(5).to_string())

output_path = '../data/proveedores_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV guardado en: {output_path}")

print("Cargando a PostgreSQL...")
df.to_sql('proveedores', engine, if_exists='replace', index=False)
print("Tabla 'proveedores' cargada correctamente.")

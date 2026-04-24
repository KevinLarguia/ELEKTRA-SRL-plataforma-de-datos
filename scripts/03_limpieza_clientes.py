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

print("Cargando CLIENTES...")
# Sin header: la hoja no tiene fila de títulos, los datos empiezan directo
df_raw = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='CLIENTES',
    engine='xlrd',
    header=None
)
print(f"  Filas originales: {df_raw.shape[0]} | Columnas: {df_raw.shape[1]}")

# Columnas útiles identificadas inspeccionando la hoja:
# 1=codigo, 2=nombre, 3=fantasia, 4=contacto, 5=direccion,
# 6=codigo_postal, 7=ciudad, 9=area_tel, 10=telefono,
# 30=area_tel2, 31=telefono2, 39=cuit, 170=tipo_iva, 171=provincia
df = pd.DataFrame({
    'codigo':         df_raw[1],
    'nombre':         df_raw[2],
    'fantasia':       df_raw[3],
    'contacto':       df_raw[4],
    'direccion':      df_raw[5],
    'codigo_postal':  df_raw[6],
    'ciudad':         df_raw[7],
    'area_tel':       df_raw[9],
    'telefono':       df_raw[10],
    'area_tel2':      df_raw[30],
    'telefono2':      df_raw[31],
    'cuit':           df_raw[39],
    'tipo_iva':       df_raw[170],
    'provincia':      df_raw[171],
})

# Eliminar filas sin código ni nombre
df = df[df['codigo'].notna() & df['nombre'].notna()]

# codigo como entero
df['codigo'] = pd.to_numeric(df['codigo'], errors='coerce').astype('Int64')
df['codigo_postal'] = df['codigo_postal'].astype(str).str.strip().replace('nan', pd.NA)

# Construir teléfono completo combinando area + número
def build_phone(area, num):
    area = str(area).strip() if pd.notna(area) else ''
    num = str(num).strip() if pd.notna(num) else ''
    if area and num:
        return f"{area}-{num}"
    return num or None

df['telefono'] = df.apply(lambda r: build_phone(r['area_tel'], r['telefono']), axis=1)
df['telefono2'] = df.apply(lambda r: build_phone(r['area_tel2'], r['telefono2']), axis=1)
df.drop(columns=['area_tel', 'area_tel2'], inplace=True)

# Normalizar texto
text_cols = ['nombre', 'fantasia', 'contacto', 'direccion', 'ciudad', 'tipo_iva', 'provincia']
for col in text_cols:
    df[col] = df[col].astype(str).str.strip().str.upper()
    df[col] = df[col].replace('NAN', pd.NA)

# CUIT: limpiar formato
df['cuit'] = df['cuit'].astype(str).str.strip().replace('nan', pd.NA)

# Eliminar duplicados por código
df.drop_duplicates(subset=['codigo'], keep='last', inplace=True)
df.reset_index(drop=True, inplace=True)

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Tipos IVA: {df['tipo_iva'].dropna().unique()}")
print(f"  Provincias: {df['provincia'].dropna().nunique()} distintas")
print(f"\nMuestra:")
print(df[['codigo', 'nombre', 'ciudad', 'provincia', 'tipo_iva', 'cuit']].head(5).to_string())

output_path = '../data/clientes_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV guardado en: {output_path}")

print("Cargando a PostgreSQL...")
df.to_sql('clientes', engine, if_exists='replace', index=False)
print("Tabla 'clientes' cargada correctamente.")

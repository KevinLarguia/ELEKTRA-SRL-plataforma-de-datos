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

print("Cargando COSTOS...")
df_raw = pd.read_excel(
    '../ELEKTRA 2026.xls',
    sheet_name='COSTOS',
    engine='xlrd',
    header=None
)
print(f"  Filas raw: {df_raw.shape[0]}")

# Estructura de la hoja:
# - Fila de equipo: col[0]=NaN, col[1]=nombre_equipo, col[3]=numero, col[5]=costo_total
# - Fila de detalle: col[0]=codigo_material (numerico), col[1]=cantidad, col[2]=material, col[4]=c_unit, col[5]=costo
# - Filas de header/separador: col[0]='CODMAT' o NaN con col[1]='EQUIPO' → ignorar

rows = []
equipo_actual = None

for _, row in df_raw.iterrows():
    col0 = row[0]
    col1 = row[1]
    col5 = row[5]

    # Detectar fila de equipo: col0 es NaN, col1 es string no vacío y no es 'EQUIPO'
    if pd.isna(col0) and pd.notna(col1) and str(col1).strip() not in ('', 'EQUIPO'):
        equipo_actual = str(col1).strip().upper()
        continue

    # Detectar fila de detalle: col0 es numérico
    try:
        codigo = int(float(col0))
    except (ValueError, TypeError):
        continue  # saltear headers y separadores

    if equipo_actual is None:
        continue

    cantidad = pd.to_numeric(row[1], errors='coerce')
    material = str(row[2]).strip() if pd.notna(row[2]) else None
    c_unit = pd.to_numeric(row[4], errors='coerce')
    costo = pd.to_numeric(row[5], errors='coerce')

    rows.append({
        'equipo_nombre': equipo_actual,
        'material_codigo': codigo,
        'material_descripcion': material,
        'cantidad': cantidad,
        'costo_unitario': c_unit,
        'costo_total': costo,
    })

df = pd.DataFrame(rows)
df.reset_index(drop=True, inplace=True)
df.index.name = 'id'
df.reset_index(inplace=True)

# Filtrar filas sin datos útiles
df = df[df['cantidad'].notna() & df['costo_unitario'].notna()]

print(f"  Filas limpias: {df.shape[0]}")
print(f"  Equipos distintos: {df['equipo_nombre'].nunique()}")
print(f"  Equipos: {sorted(df['equipo_nombre'].unique())}")
print(f"\nMuestra:")
print(df[['equipo_nombre', 'material_codigo', 'material_descripcion', 'cantidad', 'costo_unitario', 'costo_total']].head(8).to_string())

output_path = '../data/costos_limpio.csv'
df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\nCSV guardado en: {output_path}")

print("Cargando a PostgreSQL...")
df.to_sql('costos_equipos', engine, if_exists='replace', index=False)
print("Tabla 'costos_equipos' cargada correctamente.")

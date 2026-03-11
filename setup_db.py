import pandas as pd
import sqlite3
import os
import requests

# ── Rutas ───────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, 'data')
DB_PATH   = os.path.join(BASE_DIR, 'database', 'erillam.db')
CSV_PATH  = os.path.join(DATA_DIR, 'inventario_issste.csv')

os.makedirs(DATA_DIR,                          exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

# ── Descargar datos si no existen ───────────────
if not os.path.exists(CSV_PATH):
    print("📥 Descargando datos del ISSSTE...")
    url = "https://www.datos.gob.mx/dataset/abasto_medicamentos_material_curacion/resource/09fbbed0-9bb8-401c-8dfd-e6775dc7aa06"
    r = requests.get(url)
    with open(CSV_PATH, 'wb') as f:
        f.write(r.content)
    print("✅ Datos descargados")
else:
    print("✅ Datos ya existentes, omitiendo descarga")

# ── Leer y limpiar datos ────────────────────────
print("🔄 Procesando datos...")
df = pd.read_csv(CSV_PATH)

df['descripcion']       = df['descripcion'].str.strip().str.lower()
df['tipo_insumo']       = df['tipo_insumo'].str.strip().str.lower()
df['grupo_terapeutico'] = df['grupo_terapeutico'].str.strip().str.lower()
df['fecha_corte']       = pd.to_datetime(df['fecha_corte'])

df = df.dropna(subset=['clave_insumo', 
                        'inventario_piezas', 
                        'demanda_mensual_nacional'])

# ── Calcular indicadores ────────────────────────
df['dias_cobertura'] = (
    df['inventario_piezas'] / 
    (df['demanda_mensual_nacional'] / 30)
).round(2)

def clasificar_stock(dias):
    if dias <= 7:   return 'critico'
    elif dias <= 15: return 'bajo'
    elif dias <= 30: return 'normal'
    else:            return 'optimo'

df['estatus_stock'] = df['dias_cobertura'].apply(clasificar_stock)

# ── Crear base de datos ─────────────────────────
print("🗄️  Creando base de datos...")
conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
    clave_insumo        TEXT UNIQUE NOT NULL,
    descripcion         TEXT NOT NULL,
    tipo_insumo         TEXT,
    grupo_terapeutico   TEXT,
    activo              INTEGER DEFAULT 1
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS inventario_diario (
    clave_insumo                TEXT NOT NULL,
    fecha_corte                 TEXT NOT NULL,
    inventario_piezas           INTEGER,
    demanda_mensual_nacional    INTEGER,
    dias_cobertura              REAL,
    estatus_stock               TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS alertas_desabasto (
    clave_insumo        TEXT NOT NULL,
    fecha_alerta        TEXT NOT NULL,
    tipo_alerta         TEXT,
    dias_cobertura      REAL,
    mensaje             TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS resumen_grupos (
    grupo_terapeutico       TEXT NOT NULL,
    fecha_corte             TEXT NOT NULL,
    total_productos         INTEGER,
    productos_criticos      INTEGER,
    productos_bajo_stock    INTEGER,
    inventario_total        INTEGER,
    demanda_total           INTEGER
)''')

conn.commit()

# ── Cargar datos ────────────────────────────────
productos = df[['clave_insumo', 'descripcion',
                'tipo_insumo', 'grupo_terapeutico']
               ].drop_duplicates(subset='clave_insumo')
productos.to_sql('productos', conn, 
                 if_exists='replace', index=False)

inventario = df[['clave_insumo', 'fecha_corte',
                 'inventario_piezas',
                 'demanda_mensual_nacional',
                 'dias_cobertura',
                 'estatus_stock']].copy()
inventario['fecha_corte'] = inventario['fecha_corte'].astype(str)
inventario.to_sql('inventario_diario', conn,
                  if_exists='replace', index=False)

alertas = df[df['estatus_stock'].isin(['critico', 'bajo'])][
    ['clave_insumo', 'fecha_corte',
     'estatus_stock', 'dias_cobertura']].copy()
alertas['fecha_corte'] = alertas['fecha_corte'].astype(str)
alertas['mensaje'] = alertas.apply(
    lambda r: f"Stock crítico: {r['dias_cobertura']} días de cobertura"
    if r['estatus_stock'] == 'critico'
    else f"Stock bajo: {r['dias_cobertura']} días de cobertura", axis=1)
alertas.rename(columns={'estatus_stock': 'tipo_alerta',
                         'fecha_corte':  'fecha_alerta'}, inplace=True)
alertas.to_sql('alertas_desabasto', conn,
               if_exists='replace', index=False)

resumen = df.groupby(['grupo_terapeutico', 'fecha_corte']).agg(
    total_productos      =('clave_insumo',  'nunique'),
    productos_criticos   =('estatus_stock', lambda x: (x == 'critico').sum()),
    productos_bajo_stock =('estatus_stock', lambda x: (x == 'bajo').sum()),
    inventario_total     =('inventario_piezas', 'sum'),
    demanda_total        =('demanda_mensual_nacional', 'sum')
).reset_index()
resumen['fecha_corte'] = resumen['fecha_corte'].astype(str)
resumen.to_sql('resumen_grupos', conn,
               if_exists='replace', index=False)

conn.close()
print("🎉 Base de datos lista")
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import os

# ── Configuración ───────────────────────────────
st.set_page_config(
    page_title="Análisis de Abasto Médico · ISSSTE",
    page_icon="🏥",
    layout="wide",
)

# ── Rutas ───────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'database', 'erillam.db')

# ── Carga de datos ──────────────────────────────
@st.cache_data
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    inventario = pd.read_sql("""
        SELECT i.*, p.descripcion, p.tipo_insumo, p.grupo_terapeutico
        FROM inventario_diario i
        JOIN productos p ON i.clave_insumo = p.clave_insumo
    """, conn)
    alertas = pd.read_sql("""
        SELECT a.*, p.descripcion, p.grupo_terapeutico
        FROM alertas_desabasto a
        JOIN productos p ON a.clave_insumo = p.clave_insumo
    """, conn)
    resumen = pd.read_sql("SELECT * FROM resumen_grupos", conn)
    conn.close()
    return inventario, alertas, resumen

inventario, alertas, resumen = cargar_datos()
ultimo_dia = inventario['fecha_corte'].max()
inv_hoy    = inventario[inventario['fecha_corte'] == ultimo_dia].copy()

# ════════════════════════════════════════════════
# TÍTULO Y CONTEXTO METODOLÓGICO
# ════════════════════════════════════════════════
st.title("🏥 Sistema de Análisis de Abasto Médico")
st.caption(f"ISSSTE — Almacén Central Nacional · Corte: **{ultimo_dia}** · {inv_hoy['clave_insumo'].nunique():,} productos analizados")

st.markdown("""
Este dashboard analiza el inventario diario del Almacén Central del ISSSTE para identificar
riesgos de desabasto de medicamentos y material de curación a nivel nacional.
El indicador central es el **índice de días de cobertura**: cuántos días puede sostenerse
la demanda con el inventario actual. Un producto con menos de 7 días de cobertura
entra en estado crítico y requiere acción inmediata de abastecimiento.
""")

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 1 — EXPLORACIÓN INTERACTIVA
# ════════════════════════════════════════════════
st.header("1 · Exploración por días de cobertura")

st.markdown("""
Selecciona un rango de **días de cobertura** para filtrar los productos.
Esto permite enfocar el análisis en los niveles de riesgo que te interesen:
menos de 7 días es crítico, entre 7 y 15 días es bajo stock.
""")

# Slider de días de cobertura — estilo Seattle
dias_min = float(inv_hoy['dias_cobertura'].min())
dias_max = float(inv_hoy['dias_cobertura'].quantile(0.95))

rango_dias = st.slider(
    "Rango de días de cobertura a mostrar",
    min_value=0.0,
    max_value=round(dias_max, 1),
    value=(0.0, round(dias_max, 1)),
    step=0.5,
    format="%.1f días"
)

inv_rango = inv_hoy[
    (inv_hoy['dias_cobertura'] >= rango_dias[0]) &
    (inv_hoy['dias_cobertura'] <= rango_dias[1])
].copy()

tipo_options = ['Todos'] + sorted(inventario['tipo_insumo'].dropna().unique().tolist())
tipo_sel     = st.selectbox("Filtrar por tipo de insumo", tipo_options)
if tipo_sel != 'Todos':
    inv_rango = inv_rango[inv_rango['tipo_insumo'] == tipo_sel]

st.caption(f"**{len(inv_rango):,} productos** dentro del rango seleccionado")

# Histograma de área — distribución de días de cobertura
hist_data = inv_rango['dias_cobertura'].dropna()

fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(
    x=hist_data,
    nbinsx=40,
    marker_color='rgba(59,130,246,0.15)',
    marker_line_color='rgba(59,130,246,0.6)',
    marker_line_width=1,
    name='Productos'
))

for umbral, color, etiqueta in [
    (7,  'rgba(239,68,68,0.7)',  'Crítico ≤7d'),
    (15, 'rgba(245,158,11,0.7)', 'Bajo ≤15d'),
    (30, 'rgba(59,130,246,0.5)', 'Normal ≤30d'),
]:
    if umbral <= rango_dias[1]:
        fig_hist.add_vline(
            x=umbral,
            line_dash='dash',
            line_color=color,
            annotation_text=etiqueta,
            annotation_font_size=11,
            annotation_position='top right'
        )

fig_hist.update_layout(
    height=280,
    margin=dict(l=10, r=10, t=30, b=10),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(title='Días de cobertura', showgrid=False, zeroline=False),
    yaxis=dict(title='Número de productos', showgrid=True,
               gridcolor='rgba(128,128,128,0.1)', zeroline=False),
    bargap=0.05,
    showlegend=False,
)
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 2 — TENDENCIA TEMPORAL
# ════════════════════════════════════════════════
st.header("2 · Tendencia de productos en riesgo")

st.markdown("""
La siguiente gráfica muestra la evolución diaria de productos en estado **crítico** y **bajo stock**
durante el período analizado. Un aumento sostenido en productos críticos señala un deterioro
sistémico del abasto que requiere intervención a nivel de política de compras.
""")

tend_critico = (
    inventario[inventario['estatus_stock'] == 'critico']
    .groupby('fecha_corte').size().reset_index(name='critico')
)
tend_bajo = (
    inventario[inventario['estatus_stock'] == 'bajo']
    .groupby('fecha_corte').size().reset_index(name='bajo')
)
tendencia = tend_critico.merge(tend_bajo, on='fecha_corte', how='outer').fillna(0)
tendencia = tendencia.sort_values('fecha_corte')

fig_tend = go.Figure()

fig_tend.add_trace(go.Scatter(
    x=tendencia['fecha_corte'],
    y=tendencia['bajo'],
    name='Bajo stock',
    mode='lines',
    fill='tozeroy',
    fillcolor='rgba(245,158,11,0.08)',
    line=dict(color='rgba(245,158,11,0.6)', width=1.5),
    hovertemplate='<b>%{x}</b><br>Bajo stock: %{y}<extra></extra>'
))

fig_tend.add_trace(go.Scatter(
    x=tendencia['fecha_corte'],
    y=tendencia['critico'],
    name='Crítico',
    mode='lines',
    fill='tozeroy',
    fillcolor='rgba(239,68,68,0.12)',
    line=dict(color='#EF4444', width=2),
    hovertemplate='<b>%{x}</b><br>Crítico: %{y}<extra></extra>'
))

prom_critico = tendencia['critico'].mean()
fig_tend.add_hline(
    y=prom_critico,
    line_dash='dot',
    line_color='rgba(128,128,128,0.35)',
    annotation_text=f'Promedio crítico: {prom_critico:.0f}',
    annotation_font_size=11,
)

fig_tend.update_layout(
    height=300,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)',
               zeroline=False, title='Productos'),
    hovermode='x unified'
)
st.plotly_chart(fig_tend, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 3 — GRUPOS TERAPÉUTICOS
# ════════════════════════════════════════════════
st.header("3 · Riesgo por grupo terapéutico")

st.markdown("""
La siguiente gráfica muestra cuántos productos críticos concentra cada grupo terapéutico,
con el porcentaje respecto al total del grupo. Los grupos con mayor **porcentaje** de
productos críticos —no solo mayor número— representan el riesgo sistémico más alto.
""")

resumen_hoy = resumen[resumen['fecha_corte'] == ultimo_dia].copy()
resumen_hoy = resumen_hoy[resumen_hoy['total_productos'] > 0]
resumen_hoy['pct_critico'] = (
    resumen_hoy['productos_criticos'] / resumen_hoy['total_productos'] * 100
).round(1)
resumen_hoy['grupo_corto'] = resumen_hoy['grupo_terapeutico'].str.title().str[:30]

min_criticos = st.slider(
    "Mostrar grupos con al menos N productos críticos",
    min_value=0,
    max_value=int(resumen_hoy['productos_criticos'].max()),
    value=0,
    step=1
)
resumen_fil = resumen_hoy[resumen_hoy['productos_criticos'] >= min_criticos]\
    .sort_values('productos_criticos', ascending=True)

fig_grupos = go.Figure()
fig_grupos.add_trace(go.Bar(
    x=resumen_fil['productos_criticos'],
    y=resumen_fil['grupo_corto'],
    orientation='h',
    text=resumen_fil.apply(
        lambda r: f"{int(r['productos_criticos'])} ({r['pct_critico']}%)", axis=1
    ),
    textposition='outside',
    textfont=dict(size=11),
    marker=dict(
        color=resumen_fil['pct_critico'],
        colorscale=[[0, 'rgba(239,68,68,0.15)'], [0.5, 'rgba(239,68,68,0.5)'], [1, '#EF4444']],
        line_width=0,
        showscale=True,
        colorbar=dict(title='% crítico', thickness=12, len=0.8)
    ),
    hovertemplate='<b>%{y}</b><br>Productos críticos: %{x}<extra></extra>'
))
fig_grupos.update_layout(
    height=max(300, len(resumen_fil) * 28),
    margin=dict(l=10, r=80, t=20, b=10),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)',
               zeroline=False, title='Productos en estado crítico'),
    yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11)),
    showlegend=False
)
st.plotly_chart(fig_grupos, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 4 — ALERTAS CRÍTICAS
# ════════════════════════════════════════════════
st.header("4 · Alertas críticas — acción inmediata")

st.markdown("""
Productos con **menos de 7 días de cobertura** al corte más reciente,
ordenados de menor a mayor cobertura. Los marcados como 🔴 URGENTE
tienen menos de 1 día disponible: el desabasto es inminente.
""")

alertas_hoy = alertas[
    (alertas['fecha_alerta'] == ultimo_dia) &
    (alertas['tipo_alerta']  == 'critico')
].copy()

def semaforo(d):
    if d <= 1:   return '🔴 URGENTE'
    elif d <= 3: return '🟠 CRÍTICO'
    else:        return '🟡 ALERTA'

alertas_hoy['Prioridad']      = alertas_hoy['dias_cobertura'].apply(semaforo)
alertas_hoy['Producto']       = alertas_hoy['descripcion'].str.title().str[:70]
alertas_hoy['Grupo']          = alertas_hoy['grupo_terapeutico'].str.title()
alertas_hoy['Días Cobertura'] = alertas_hoy['dias_cobertura']

tabla_alertas = (
    alertas_hoy[['Prioridad', 'Producto', 'Grupo', 'Días Cobertura']]
    .sort_values('Días Cobertura')
    .reset_index(drop=True)
)

st.dataframe(
    tabla_alertas,
    use_container_width=True,
    height=320,
    column_config={
        'Días Cobertura': st.column_config.NumberColumn(format='%.2f días')
    }
)

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 5 — RAW DATA (estilo Seattle Weather)
# ════════════════════════════════════════════════
st.header("5 · Datos en bruto")

st.markdown("""
Los datos crudos permiten validar los cálculos, buscar productos específicos
e identificar casos de interés. La columna `Días Cobertura` es el indicador
construido por el pipeline ETL: `inventario_piezas ÷ (demanda_mensual ÷ 30)`.
""")

if st.checkbox("Mostrar datos del inventario completo (último corte)"):
    cols_mostrar = [
        'clave_insumo', 'descripcion', 'tipo_insumo',
        'grupo_terapeutico', 'inventario_piezas',
        'demanda_mensual_nacional', 'dias_cobertura', 'estatus_stock'
    ]
    df_raw = inv_hoy[cols_mostrar].copy()
    df_raw['descripcion']       = df_raw['descripcion'].str.title()
    df_raw['grupo_terapeutico'] = df_raw['grupo_terapeutico'].str.title()
    df_raw['tipo_insumo']       = df_raw['tipo_insumo'].str.title()
    df_raw = df_raw.sort_values('dias_cobertura').reset_index(drop=True)

    st.dataframe(
        df_raw,
        use_container_width=True,
        height=400,
        column_config={
            'clave_insumo':             st.column_config.TextColumn('Clave'),
            'descripcion':              st.column_config.TextColumn('Descripción'),
            'tipo_insumo':              st.column_config.TextColumn('Tipo'),
            'grupo_terapeutico':        st.column_config.TextColumn('Grupo Terapéutico'),
            'inventario_piezas':        st.column_config.NumberColumn('Inventario', format='%d pzs'),
            'demanda_mensual_nacional': st.column_config.NumberColumn('Demanda/mes', format='%d pzs'),
            'dias_cobertura':           st.column_config.NumberColumn('Días Cobertura', format='%.2f'),
            'estatus_stock':            st.column_config.TextColumn('Estatus'),
        }
    )
    st.caption(f"{len(df_raw):,} registros · Corte: {ultimo_dia}")

st.divider()

# ════════════════════════════════════════════════
# SECCIÓN 6 — METODOLOGÍA Y README
# ════════════════════════════════════════════════
st.header("6 · Metodología y documentación")

with st.expander("📐 Ver metodología completa del proyecto", expanded=False):
    st.markdown("""
## Pregunta de negocio

> ¿Qué productos del Almacén Central del ISSSTE están en riesgo de desabasto
> y qué grupos terapéuticos concentran el mayor número de casos críticos?

---

## Pipeline ETL

El proceso de datos sigue tres etapas:

**1. Extracción**
Descarga del CSV oficial desde el portal de datos abiertos del gobierno mexicano
(`datos.gob.mx`). El archivo contiene registros diarios de inventario por producto,
incluyendo claves ISSSTE, existencias y demanda mensual histórica.

**2. Transformación**
- Limpieza: normalización de strings, eliminación de nulos en campos críticos
- Cálculo del **índice de días de cobertura**: `inventario_piezas / (demanda_mensual / 30)`
- Clasificación de estatus: *crítico* (≤7d), *bajo* (≤15d), *normal* (≤30d), *óptimo* (>30d)
- Generación de alertas y agregados por grupo terapéutico

**3. Carga**
Persistencia en base de datos relacional SQLite con 4 tablas normalizadas:

| Tabla | Descripción | Registros |
|-------|------------|-----------|
| `productos` | Catálogo maestro de insumos | 966 |
| `inventario_diario` | Snapshot diario con indicadores calculados | 26,750 |
| `alertas_desabasto` | Productos en riesgo | 1,464 |
| `resumen_grupos` | Agregado por grupo terapéutico y fecha | 1,609 |

---

## Indicador principal: Días de cobertura

```
dias_cobertura = inventario_piezas / (demanda_mensual_nacional / 30)
```

| Rango | Clasificación | Acción recomendada |
|-------|--------------|-------------------|
| ≤ 7 días | 🔴 Crítico | Compra de emergencia |
| 8 – 15 días | 🟡 Bajo | Iniciar proceso de compra |
| 16 – 30 días | 🔵 Normal | Monitoreo rutinario |
| > 30 días | 🟢 Óptimo | Sin acción requerida |

---

## Hallazgos principales

- **21 productos en estado crítico** con menos de 7 días de cobertura al 30 de abril 2025
- **Anestesiología** concentra el 25% de sus productos en riesgo — la tasa más alta entre grupos
- **Nalbufina** (analgesia): 0.11 días de cobertura — desabasto inminente
- **Daunorubicina** (oncología): 0.18 días — medicamento de quimioterapia en riesgo crítico
- **Abemaciclib** (oncología): 0.49 días — terapia dirigida para cáncer de mama

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.11 |
| ETL y análisis | Pandas |
| Base de datos | SQLite |
| Dashboard | Streamlit |
| Visualización | Plotly |
| Deploy | Railway |
| Datos | ISSSTE — datos.gob.mx |

---

## Fuente de datos

Datos abiertos del ISSSTE — Abasto de Medicamentos y Material de Curación.
Última actualización del dataset: **abril 2025**.

[Ver fuente original →](https://www.datos.gob.mx/dataset/abasto_medicamentos_material_curacion/resource/09fbbed0-9bb8-401c-8dfd-e6775dc7aa06)
""")

# ════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════
st.markdown("---")
cols_footer = st.columns([3, 1, 1])
with cols_footer[0]:
    st.caption("Desarrollado por **Eduardo Cabrera Gutiérrez** · Analista de Datos y Negocio")
with cols_footer[1]:
    st.markdown("[🌐 Portafolio](https://portafolio-de-eduardo-cabrera.webflow.io/)")
with cols_footer[2]:
    st.markdown("[📦 GitHub](https://github.com/CabardoZ/Sistema.analisis-abasto-medico)")

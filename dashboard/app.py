import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# ── Configuración de la página ──────────────────
st.set_page_config(
    page_title="Sistema de Análisis de Abasto Médico",
    page_icon="🏥",
    layout="wide"
)

# ── Estilos personalizados ──────────────────────
st.markdown("""
<style>
    .descripcion-proyecto {
        background-color: #1E293B;
        border-left: 4px solid #3B82F6;
        padding: 16px 20px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .tag {
        background-color: #1D4ED8;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 6px;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #94A3B8;
        font-size: 13px;
        border-top: 1px solid #334155;
        margin-top: 30px;
    }
    .alerta-critica { color: #EF4444; font-weight: bold; }
    .alerta-baja    { color: #F59E0B; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Conexión a la base de datos ─────────────────
@st.cache_data
def cargar_datos():
    conn = sqlite3.connect('../database/erillam.db')
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
inv_hoy    = inventario[inventario['fecha_corte'] == ultimo_dia]

# ════════════════════════════════════════════════
# HEADER + DESCRIPCIÓN DEL PROYECTO
# ════════════════════════════════════════════════
st.title("🏥 Sistema de Análisis de Abasto Médico")
st.caption(f"Fuente: ISSSTE — Almacén Central | Fecha de corte: {ultimo_dia}")

st.markdown("""
<div class="descripcion-proyecto">
<b>📋 Descripción del Proyecto</b><br><br>
Este sistema analiza el inventario diario del Almacén Central del ISSSTE para identificar 
riesgos de desabasto de medicamentos y material de curación a nivel nacional. 
A partir de datos abiertos del gobierno mexicano, el pipeline ETL extrae, transforma y carga 
la información en una base de datos relacional, calculando automáticamente días de cobertura 
y generando alertas por producto y grupo terapéutico.<br><br>
<span class="tag">Python</span>
<span class="tag">ETL</span>
<span class="tag">SQLite</span>
<span class="tag">Streamlit</span>
<span class="tag">Plotly</span>
<span class="tag">Datos Abiertos ISSSTE</span>
<span class="tag">Analista de Negocio</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════
# FILA 1: KPIs
# ════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)

total_productos = inv_hoy['clave_insumo'].nunique()
criticos        = inv_hoy[inv_hoy['estatus_stock'] == 'critico']
bajo_stock      = inv_hoy[inv_hoy['estatus_stock'] == 'bajo']
optimos         = inv_hoy[inv_hoy['estatus_stock'] == 'optimo']

col1.metric("📦 Total Productos",  f"{total_productos:,}")
col2.metric("🔴 Estado Crítico",   f"{len(criticos)}",
            delta=f"{round(len(criticos)/total_productos*100,1)}% del total",
            delta_color="inverse")
col3.metric("🟡 Bajo Stock",       f"{len(bajo_stock)}",
            delta=f"{round(len(bajo_stock)/total_productos*100,1)}% del total",
            delta_color="inverse")
col4.metric("🟢 Stock Óptimo",     f"{len(optimos)}",
            delta=f"{round(len(optimos)/total_productos*100,1)}% del total")

st.divider()

# ════════════════════════════════════════════════
# FILA 2: Filtros
# ════════════════════════════════════════════════
col_f1, col_f2 = st.columns(2)

tipo_options  = ['Todos'] + sorted(inventario['tipo_insumo'].unique().tolist())
tipo_sel      = col_f1.selectbox("🔎 Tipo de insumo", tipo_options)

grupo_options = ['Todos'] + sorted(inventario['grupo_terapeutico'].unique().tolist())
grupo_sel     = col_f2.selectbox("🔎 Grupo terapéutico", grupo_options)

inv_filtrado = inv_hoy.copy()
if tipo_sel  != 'Todos':
    inv_filtrado = inv_filtrado[inv_filtrado['tipo_insumo']       == tipo_sel]
if grupo_sel != 'Todos':
    inv_filtrado = inv_filtrado[inv_filtrado['grupo_terapeutico'] == grupo_sel]

st.divider()

# ════════════════════════════════════════════════
# FILA 3: Gráficas principales
# ════════════════════════════════════════════════
col_g1, col_g2 = st.columns(2)

# Gráfica 1: Distribución de estatus — siempre muestra los 4 estatus
with col_g1:
    st.subheader("📊 Distribución de Estatus de Stock")
    todos_estatus = ['critico', 'bajo', 'normal', 'optimo']
    colores = {
        'critico': '#EF4444',
        'bajo':    '#F59E0B',
        'normal':  '#3B82F6',
        'optimo':  '#10B981'
    }
    conteo_real = inv_filtrado['estatus_stock'].value_counts()
    conteo = pd.DataFrame({
        'estatus':  todos_estatus,
        'cantidad': [conteo_real.get(e, 0) for e in todos_estatus]
    })
    fig1 = px.bar(conteo, x='estatus', y='cantidad',
                  color='estatus',
                  color_discrete_map=colores,
                  text='cantidad')
    fig1.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig1, use_container_width=True)

# Gráfica 2: Grupos con mayor riesgo
with col_g2:
    st.subheader("🔴 Grupos con Mayor Riesgo de Desabasto")
    resumen_hoy = resumen[resumen['fecha_corte'] == ultimo_dia]
    resumen_hoy = resumen_hoy[resumen_hoy['productos_criticos'] > 0]
    resumen_hoy = resumen_hoy.sort_values('productos_criticos', ascending=True)

    fig2 = px.bar(resumen_hoy,
                  x='productos_criticos',
                  y='grupo_terapeutico',
                  orientation='h',
                  color='productos_criticos',
                  color_continuous_scale='Reds',
                  text='productos_criticos')
    fig2.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════
# FILA 4: Tendencia
# ════════════════════════════════════════════════
st.subheader("📈 Tendencia de Productos Críticos por Día")

tendencia = inventario[inventario['estatus_stock'] == 'critico'].groupby(
    'fecha_corte').size().reset_index()
tendencia.columns = ['fecha', 'productos_criticos']

fig3 = px.line(tendencia, x='fecha', y='productos_criticos',
               markers=True,
               color_discrete_sequence=['#EF4444'])
fig3.update_layout(height=300)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════
# FILA 5: Tabla de alertas con semáforo
# ════════════════════════════════════════════════
st.subheader("🚨 Alertas Críticas — Acción Inmediata Requerida")

alertas_hoy = alertas[
    (alertas['fecha_alerta'] == ultimo_dia) &
    (alertas['tipo_alerta']  == 'critico')
].copy()

# Acortar descripción del producto
alertas_hoy['producto_corto'] = alertas_hoy['descripcion'].apply(
    lambda x: x[:60] + '...' if len(x) > 60 else x
)

# Semáforo por días de cobertura
def semaforo(dias):
    if dias <= 1:
        return '🔴 URGENTE'
    elif dias <= 3:
        return '🟠 CRÍTICO'
    else:
        return '🟡 ALERTA'

alertas_hoy['prioridad'] = alertas_hoy['dias_cobertura'].apply(semaforo)

tabla = alertas_hoy[[
    'prioridad', 'producto_corto',
    'grupo_terapeutico', 'dias_cobertura'
]].sort_values('dias_cobertura')

tabla.columns = ['Prioridad', 'Producto', 
                 'Grupo Terapéutico', 'Días Cobertura']

st.dataframe(tabla, use_container_width=True, height=320)

st.divider()

# ════════════════════════════════════════════════
# FOOTER
# ════════════════════════════════════════════════
st.markdown("""
<div class="footer">
    Sistema de Análisis Operativo de Distribución Médica &nbsp;|&nbsp; 
    Desarrollado por <b>Eduardo Cabrera Gutiérrez</b> &nbsp;|&nbsp;
    <a href="https://portafolio-de-eduardo-cabrera.webflow.io/" 
       target="_blank" style="color:#3B82F6;">
       🌐 Portafolio
    </a>
    &nbsp;|&nbsp;
    <a href="https://www.datos.gob.mx/dataset/abasto_medicamentos_material_curacion/resource/09fbbed0-9bb8-401c-8dfd-e6775dc7aa06" 
       target="_blank" style="color:#64748B;">
       📂 Fuente de Datos: ISSSTE — datos.gob.mx
    </a>
</div>
""", unsafe_allow_html=True)
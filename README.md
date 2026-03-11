# 🏥 Sistema de Análisis de Abasto Médico

Dashboard interactivo para el monitoreo y análisis de inventario 
de medicamentos y material de curación con datos reales del ISSSTE.

Desarrollado por **Eduardo Cabrera Gutiérrez**  
🌐 [Portafolio](https://portafolio-de-eduardo-cabrera.webflow.io/)

---

## 📋 Descripción

Este proyecto analiza el inventario diario del Almacén Central 
del ISSSTE para identificar riesgos de desabasto a nivel nacional.

A partir de datos abiertos del gobierno mexicano, el sistema:
- Extrae y transforma datos reales mediante un pipeline ETL
- Calcula automáticamente días de cobertura por producto
- Genera alertas de desabasto por grupo terapéutico
- Visualiza la información en un dashboard interactivo

---

## 🛠️ Tecnologías

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.11 |
| ETL | Pandas |
| Base de datos | SQLite + SQLAlchemy |
| Dashboard | Streamlit |
| Visualización | Plotly |
| Control de versiones | Git + GitHub |

---

## 📊 Fuente de Datos

Datos abiertos del ISSSTE — Abasto de Medicamentos y Material de Curación  
🔗 [datos.gob.mx](https://www.datos.gob.mx/dataset/abasto_medicamentos_material_curacion/resource/09fbbed0-9bb8-401c-8dfd-e6775dc7aa06)

- 26,750 registros diarios
- 966 productos únicos
- 54 grupos terapéuticos
- Período: Abril 2025

---

## 🚀 Cómo ejecutar el proyecto

### 1. Clonar el repositorio
```bash
git clone https://github.com/CabardoZ/Sistema.analisis-abasto-medico.git
cd Sistema.analisis-abasto-medico
```

### 2. Crear entorno e instalar dependencias
```bash
conda create -n erillam-analytics python=3.11 -y
conda activate erillam-analytics
pip install pandas sqlalchemy faker fastapi uvicorn streamlit plotly requests openpyxl jupyter
```

### 3. Ejecutar el ETL
Abre y ejecuta el notebook `etl/02_etl.ipynb` en Jupyter

### 4. Lanzar el dashboard
```bash
cd dashboard
streamlit run app.py
```

---

## 📁 Estructura del Proyecto
```
📦 sistema-analisis-abasto-medico/
├── 📁 data/          → Dataset real del ISSSTE
├── 📁 etl/           → Pipeline ETL con Pandas
├── 📁 database/      → Modelo de datos SQLite
├── 📁 dashboard/     → Dashboard Streamlit + Plotly
└── README.md
```

---

## 💡 Hallazgos principales

- **21 productos en estado crítico** con menos de 7 días de cobertura
- **Anestesiología** tiene el 25% de sus productos en estado crítico
- **Oncología** con medicamentos de alto costo en riesgo de desabasto
- **Nalbufina** (analgésico): solo 0.11 días de cobertura disponibles

---

*Proyecto desarrollado como parte del portafolio profesional de 
Eduardo Cabrera Gutiérrez — Analista de Datos y Negocio*
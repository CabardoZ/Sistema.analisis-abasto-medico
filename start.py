import os
import subprocess

# Ejecutar ETL primero
print("🚀 Iniciando setup...")
subprocess.run(['python', 'setup_db.py'], check=True)

# Lanzar dashboard
print("🌐 Lanzando dashboard...")
port = os.environ.get('PORT', '8501')
subprocess.run([
    'streamlit', 'run', 'dashboard/app.py',
    '--server.port', port,
    '--server.address', '0.0.0.0',
    '--server.headless', 'true'
])
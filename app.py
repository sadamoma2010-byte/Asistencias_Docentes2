from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

# Se configura el directorio actual como raíz de templates para respetar tu estructura de carpetas
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'clave_secreta_institucional' # Reemplazar con variable de entorno en producción

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE BASE DE DATOS (POSTGRESQL)
# ═══════════════════════════════════════════════════════════════════════
DB_HOST = "localhost"
DB_NAME = "asistencia_qr"
DB_USER = "postgres"
DB_PASS = "Admin123*" # Ajustar según las credenciales de tu entorno

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════
# RUTAS DE INTERFAZ GRÁFICA (VISTAS HTML)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inicio')
def inicio():
    return render_template('inicio.html')

@app.route('/iniciar', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        # Aquí implementaremos más adelante la validación bcrypt contra la tabla 'usuarios'
        pass
    return render_template('iniciar.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Lógica para registrar un nuevo docente o usuario en el sistema
        pass
    return render_template('registro.html')

@app.route('/dashboard')
def dashboard():
    # Más adelante inyectaremos aquí la vista SQL "v_resumen_docente"
    # para renderizar las estadísticas de asistencia y puntualidad.
    return render_template('dashboard.html')

@app.route('/asistencias')
def asistencias():
    # Usaremos la vista "v_asistencia_detallada" para llenar la tabla
    # Nota: Tu estructura tiene esto en la carpeta Templates/
    return render_template('Templates/asistencias.html')

@app.route('/excusas')
def excusas():
    return render_template('excusas.html')

@app.route('/qr_institucional')
def qr_institucional():
    return render_template('codigo qr institucional.html')

# ═══════════════════════════════════════════════════════════════════════
# RUTAS DE API (PROCESAMIENTO DE DATOS Y LECTURA QR)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/marcar_asistencia', methods=['POST'])
def marcar_asistencia():
    """
    Endpoint principal para recibir los datos del escaneo del Código QR.
    """
    data = request.get_json()
    codigo_docente = data.get('codigo_docente')
    
    if not codigo_docente:
        return jsonify({"status": "error", "message": "Código no proporcionado"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Error de conexión a la base de datos"}), 500
        
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Validar que el docente existe y está activo
        cursor.execute("SELECT id FROM docentes WHERE codigo = %s AND estado = 'ACTIVO'", (codigo_docente,))
        docente = cursor.fetchone()
        
        if not docente:
            return jsonify({"status": "error", "message": "Docente no encontrado o inactivo"}), 404
            
        docente_id = docente['id']
        
        # 2. Aquí añadiremos la lógica que cruza la hora actual con la tabla 'horarios'
        # y utiliza la función SQL fn_evaluar_puntualidad para registrar la entrada/salida.
        
        # Por ahora simulamos un éxito en la respuesta
        return jsonify({
            "status": "success", 
            "message": "Asistencia registrada correctamente",
            "tipo": "ENTRADA" # O SALIDA
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    # Se levanta en el puerto 3000 como indica la configuración 'qr.public_url' en el SQL
    app.run(debug=True, port=3000)

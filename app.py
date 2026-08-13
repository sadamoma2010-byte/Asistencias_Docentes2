import os
import time
import pyotp
import qrcode
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from permisos import (
    login_requerido, requerir_roles, requerir_permiso,
    ROLE_ADMIN, ROLE_COORDINADOR, ROLE_DOCENTE
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_clave_secreta_institucional_12345")

# Base de datos simulada (Reemplazar por consultas SQL reales)
USERS_DB = {
    "admin1": {
        "id": 1,
        "username": "admin1",
        "password": "123", # Usar hashes en producción (werkzeug.security)
        "nombre": "Rectoría / Admin",
        "role": ROLE_ADMIN
    },
    "coord1": {
        "id": 2,
        "username": "coord1",
        "password": "123",
        "nombre": "Coordinador Académico",
        "role": ROLE_COORDINADOR
    },
    "docente1": {
        "id": 3,
        "username": "docente1",
        "password": "123",
        "nombre": "Profesor Mateo Ortiz",
        "role": ROLE_DOCENTE
    }
}

# Clave secreta para generación de tokens TOTP con PyOTP
TOTP_SECRET = pyotp.random_base32()
totp = pyotp.TOTP(TOTP_SECRET, interval=86400) # Cambia cada 24 horas (86400 segundos)

# --- RUTAS DE AUTENTICACIÓN ---

@app.route("/")
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = USERS_DB.get(username)
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["nombre"] = user["nombre"]
            session["role"] = user["role"]
            flash(f"Bienvenido/a {user['nombre']}", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")
            
    return render_template("login.html") if os.path.exists("templates/login.html") else """
        <h2>Iniciar Sesión</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Usuario" required><br><br>
            <input type="password" name="password" placeholder="Contraseña" required><br><br>
            <button type="submit">Ingresar</button>
        </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))

# --- DASHBOARD PRINCIPAL ---

@app.route("/dashboard")
@login_requerido
def dashboard():
    rol = session.get("role")
    return f"""
        <h1>Panel de Control</h1>
        <p>Hola, <b>{session.get('nombre')}</b> ({rol})</p>
        <ul>
            <li><a href="/escanear-qr">Escanear QR de Asistencia</a></li>
            <li><a href="/mis-excusas">Gestionar Mis Excusas / Permisos</a></li>
            {"<li><a href='/coordinacion'>Panel de Coordinación (Alertas / Aulas)</a></li>" if rol in [ROLE_COORDINADOR, ROLE_ADMIN] else ""}
            {"<li><a href='/admin/usuarios'>Gestión de Usuarios (Rector)</a></li>" if rol == ROLE_ADMIN else ""}
            {"<li><a href='/pantalla-qr'>Ver Pantalla LCD de Código QR</a></li>" if rol in [ROLE_ADMIN, ROLE_COORDINADOR] else ""}
        </ul>
        <a href="/logout">Cerrar Sesión</a>
    """

# --- GENERACIÓN Y PANTALLA DE CÓDIGO QR ---

@app.route("/pantalla-qr")
@requerir_roles(ROLE_ADMIN, ROLE_COORDINADOR)
def pantalla_qr():
    """Pantalla orientada a la estación/pantalla LCD que genera el QR dinámico."""
    return """
        <h2>Código QR Dinámico de Asistencia</h2>
        <p>Este código se actualiza automáticamente.</p>
        <img src="/generar-qr" id="qr-img" width="300" height="300"><br><br>
        <script>
            // Recargar imagen QR periódicamente
            setInterval(() => {
                document.getElementById('qr-img').src = '/generar-qr?' + new Date().getTime();
            }, 30000); // Refresco visual cada 30 seg
        </script>
    """

@app.route("/generar-qr")
def generar_qr():
    """Genera la imagen del QR basándose en el token actual de PyOTP."""
    token_actual = totp.now()
    url_validacion = url_for('validar_asistencia', token=token_actual, _external=True)
    
    img = qrcode.make(url_validacion)
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# --- REGISTRO Y VALIDACIÓN DE ASISTENCIA ---

@app.route("/escanear-qr")
@login_requerido
def escanear_qr():
    """Vista desde el móvil del profesor para pedir ubicación y enviar token."""
    return """
        <h3>Registro de Asistencia Vía QR</h3>
        <p id="status">Obteniendo ubicación...</p>
        <button onclick="registrar()">Confirmar Entrada con Ubicación</button>
        <script>
            function registrar() {
                if (!navigator.geolocation) {
                    alert('La geolocalización no está soportada por tu navegador.');
                    return;
                }
                navigator.geolocation.getCurrentPosition((pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    alert('Ubicación obtenida: ' + lat + ', ' + lon + '. Escanea el QR para finalizar.');
                }, (err) => {
                    alert('Error obteniendo ubicación: ' + err.message);
                });
            }
        </script>
    """

@app.route("/validar-asistencia/<token>", methods=["GET", "POST"])
@login_requerido
def validar_asistencia(token):
    """Verifica el token TOTP enviado desde el QR e ingresa el registro."""
    es_valido = totp.verify(token)
    if not es_valido:
        flash("El código QR ha expirado o es inválido.", "danger")
        return redirect(url_for('dashboard'))
    
    # Aquí se guardaría en la base de datos SQL con fecha, hora, latitud y longitud
    flash("¡Asistencia registrada con éxito en el sistema!", "success")
    return redirect(url_for('dashboard'))

# --- PANELES SEGÚN ROLES ---

@app.route("/coordinacion")
@requerir_roles(ROLE_COORDINADOR, ROLE_ADMIN)
def panel_coordinacion():
    return "<h2>Panel de Coordinación: Reporte de Tardanzas y Excusas Pendientes</h2>"

@app.route("/admin/usuarios")
@requerir_roles(ROLE_ADMIN)
def gestion_usuarios():
    return "<h2>Panel de Rectoría: Gestión Global de Usuarios y Roles</h2>"

@app.route("/mis-excusas")
@login_requerido
def mis_excusas():
    return "<h2>Módulo de Carga y Gestión Digital de Excusas / Permisos</h2>"

if __name__ == "__main__":
    app.run(debug=True, port=5000)

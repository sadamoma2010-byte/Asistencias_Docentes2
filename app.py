from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    send_file
)

import os
import io
import uuid
import bcrypt
import psycopg2

from psycopg2.extras import RealDictCursor
from datetime import datetime, date


# ============================================================
# CONFIGURACIÓN DE FLASK
# ============================================================

app = Flask(
    __name__,
    template_folder="Templates",
    static_folder=".",
    static_url_path=""
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "clave_secreta_institucional"
)

app.config["JSON_AS_ASCII"] = False


# ============================================================
# CONFIGURACIÓN POSTGRESQL
# ============================================================

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "asistencia_qr")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "Admin123*")


def get_db_connection():
    """
    Crea una conexión nueva con PostgreSQL.
    """
    try:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    except psycopg2.Error as e:
        print("ERROR PostgreSQL:", e)
        return None


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_usuario_actual():
    """
    Devuelve la información detallada del usuario autenticado.
    """
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT
                u.id,
                u.nombre,
                u.apellido,
                u.documento,
                u.correo,
                u.telefono,
                u.estado,
                u.rol_id,
                r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON r.id = u.rol_id
            WHERE u.id = %s
              AND u.estado = 'ACTIVO'
              AND u.eliminado_en IS NULL
            """,
            (usuario_id,)
        )
        return cursor.fetchone()
    except psycopg2.Error as e:
        print("ERROR obteniendo usuario:", e)
        return None
    finally:
        if cursor:
            cursor.close()
        conn.close()


def login_requerido():
    """
    Verifica si existe una sesión activa.
    """
    return "usuario_id" in session


def registrar_auditoria(usuario_id, accion, modulo, descripcion, id_entidad=None):
    """
    Registra un evento dentro de la tabla de auditoría.
    """
    conn = get_db_connection()
    if not conn:
        return

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO registros_auditoria
            (
                id, usuario_id, user_email, user_name, accion, modulo,
                id_entidad, descripcion, direccion_ip, agente_usuario,
                dispositivo, metadatos, creado_en, actualizado_en
            )
            SELECT
                %s, u.id, u.correo, CONCAT(u.nombre, ' ', u.apellido),
                %s::accion_auditoria, %s, %s, %s, %s, %s, %s, '{}'::jsonb, NOW(), NOW()
            FROM usuarios u
            WHERE u.id = %s
            """,
            (
                str(uuid.uuid4()),
                accion,
                modulo,
                id_entidad,
                descripcion,
                request.remote_addr,
                request.headers.get("User-Agent", ""),
                request.headers.get("X-Device", ""),
                usuario_id
            )
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Aviso: no se pudo registrar auditoría:", e)
    finally:
        if cursor:
            cursor.close()
        conn.close()


# Importar el blueprint y decorador de permisos
from permisos import permisos_bp, requerir_permiso


# ============================================================
# RUTAS DE VISTAS (PÁGINAS HTML)
# ============================================================

@app.route("/")
def index():
    """
    Página principal de bienvenida (index.html).
    """
    return render_template("index.html")


@app.route("/iniciar", methods=["GET", "POST"])
def iniciar_sesion():
    """
    Pantalla de Iniciar Sesión (iniciar.html) y lógica de autenticación.
    """
    if request.method == "GET":
        if login_requerido():
            return redirect(url_for("inicio"))
        return render_template("iniciar.html")

    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"status": "error", "message": "Por favor completa todos los campos."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "No fue posible conectar con la base de datos."}), 500

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT
                u.id, u.nombre, u.apellido, u.documento, u.correo,
                u.contrasena, u.estado, u.rol_id, u.intentos_inicio_fallidos,
                u.bloqueado_hasta, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON r.id = u.rol_id
            WHERE LOWER(u.correo) = LOWER(%s) AND u.eliminado_en IS NULL
            """,
            (email,)
        )
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({"status": "error", "message": "El usuario no existe."}), 404

        if usuario["estado"] != "ACTIVO":
            return jsonify({"status": "error", "message": "La cuenta está inactiva."}), 403

        if usuario["bloqueado_hasta"]:
            ahora = datetime.now(usuario["bloqueado_hasta"].tzinfo) if usuario["bloqueado_hasta"].tzinfo else datetime.now()
            if usuario["bloqueado_hasta"] > ahora:
                return jsonify({"status": "error", "message": "La cuenta se encuentra bloqueada temporalmente."}), 403

        contrasena_db = usuario["contrasena"]
        es_valida = False

        try:
            if contrasena_db.startswith("$2"):
                es_valida = bcrypt.checkpw(password.encode("utf-8"), contrasena_db.encode("utf-8"))
            else:
                es_valida = password == contrasena_db
        except Exception:
            es_valida = False

        if not es_valida:
            nuevos_intentos = int(usuario["intentos_inicio_fallidos"] or 0) + 1
            bloqueado_hasta = None
            if nuevos_intentos >= 5:
                from datetime import timedelta
                bloqueado_hasta = datetime.now() + timedelta(minutes=15)
                nuevos_intentos = 0

            cursor.execute(
                """
                UPDATE usuarios
                SET intentos_inicio_fallidos = %s, bloqueado_hasta = %s, actualizado_en = NOW()
                WHERE id = %s
                """,
                (nuevos_intentos, bloqueado_hasta, usuario["id"])
            )
            conn.commit()
            return jsonify({"status": "error", "message": "Contraseña incorrecta."}), 401

        cursor.execute(
            """
            UPDATE usuarios
            SET intentos_inicio_fallidos = 0, bloqueado_hasta = NULL, ultimo_inicio_sesion = NOW(), actualizado_en = NOW()
            WHERE id = %s
            """,
            (usuario["id"],)
        )
        conn.commit()

        session.clear()
        session["usuario_id"] = str(usuario["id"])
        session["usuario_nombre"] = usuario["nombre"]
        session["usuario_apellido"] = usuario["apellido"]
        session["usuario_correo"] = usuario["correo"]
        session["rol_id"] = str(usuario["rol_id"])
        session["rol_nombre"] = usuario["rol_nombre"]

        registrar_auditoria(str(usuario["id"]), "INICIO_SESION", "autenticacion", "Inicio de sesión exitoso.")

        return jsonify({"status": "success", "message": "Acceso concedido.", "redirect": "/inicio"})

    except Exception as e:
        conn.rollback()
        print("ERROR LOGIN:", e)
        return jsonify({"status": "error", "message": "Ocurrió un error al iniciar sesión."}), 500
    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/registro", methods=["GET", "POST"])
def registro():
    """
    Pantalla de Registro de usuarios (registro.html).
    """
    if request.method == "GET":
        return render_template("registro.html")

    data = request.get_json(silent=True) or request.form
    nombre = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    documento = (data.get("documento") or "").strip()
    correo = (data.get("correo") or "").strip().lower()
    telefono = (data.get("telefono") or "").strip()
    password = data.get("password") or data.get("contrasena") or ""

    if not all([nombre, apellido, documento, correo, password]):
        return jsonify({"status": "error", "message": "Faltan campos obligatorios."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "No fue posible conectar con la base de datos."}), 500

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM usuarios WHERE correo = %s OR documento = %s LIMIT 1", (correo, documento))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "El correo o documento ya está registrado."}), 409

        cursor.execute("SELECT id FROM roles WHERE nombre = 'DOCENTE' AND estado = 'ACTIVO' LIMIT 1")
        rol = cursor.fetchone()
        if not rol:
            return jsonify({"status": "error", "message": "No existe el rol DOCENTE configurado."}), 500

        hash_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        usuario_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO usuarios (id, nombre, apellido, documento, correo, telefono, contrasena, estado, rol_id, debe_cambiar_contrasena, creado_en, actualizado_en)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVO', %s, FALSE, NOW(), NOW())
            """,
            (usuario_id, nombre, apellido, documento, correo, telefono or None, hash_password, rol["id"])
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Usuario registrado correctamente.", "redirect": "/iniciar"}), 201

    except psycopg2.Error as e:
        conn.rollback()
        print("ERROR REGISTRO:", e)
        return jsonify({"status": "error", "message": "No fue posible registrar el usuario."}), 500
    finally:
        if cursor:
            cursor.close()
        conn.close()


@app.route("/inicio")
def inicio():
    """
    Panel principal de bienvenida post-login (inicio.html).
    """
    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))
    usuario = obtener_usuario_actual()
    if not usuario:
        session.clear()
        return redirect(url_for("iniciar_sesion"))
    return render_template("inicio.html", usuario=usuario)


@app.route("/dashboard")
@requerir_permiso("dashboard")
def dashboard():
    """
    Módulo del Dashboard de administración (dashboard.html).
    """
    usuario = obtener_usuario_actual()
    return render_template("dashboard.html", usuario=usuario)


@app.route("/asistencias")
@requerir_permiso("asistencias")
def asistencias():
    """
    Módulo de consulta y registro de asistencias (asistencias.html).
    """
    usuario = obtener_usuario_actual()
    return render_template("asistencias.html", usuario=usuario)


@app.route("/excusas")
@requerir_permiso("excusas")
def excusas():
    """
    Módulo de gestión de excusas médicas (excusas.html).
    """
    usuario = obtener_usuario_actual()
    return render_template("excusas.html", usuario=usuario)


@app.route("/qr_institucional")
@requerir_permiso("qr_institucional")
def qr_institucional():
    """
    Generación de código QR (codigo qr institucional.html).
    """
    usuario = obtener_usuario_actual()
    return render_template("codigo qr institucional.html", usuario=usuario)


@app.route("/marcar", methods=["GET"])
def marcar():
    """
    Vista pública donde redirige el lector de QR al escanear.
    """
    return render_template("asistencias.html")


@app.route("/cerrar_sesion")
@app.route("/logout")
def cerrar_sesion():
    """
    Cierra la sesión del usuario.
    """
    usuario_id = session.get("usuario_id")
    if usuario_id:
        registrar_auditoria(usuario_id, "CIERRE_SESION", "autenticacion", "Cierre de sesión.")
    session.clear()
    return redirect(url_for("iniciar_sesion"))


# ============================================================
# API - REGISTRAR ASISTENCIA (POR QR)
# ============================================================

@app.route("/api/marcar_asistencia", methods=["POST"])
def marcar_asistencia():
    data = request.get_json(silent=True) or request.form
    codigo_docente = (data.get("codigo_docente") or data.get("codigo") or "").strip()

    if not codigo_docente:
        return jsonify({"status": "error", "message": "Código de docente no proporcionado."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Error al conectar con la base de datos."}), 500

    cursor = None
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT id, codigo, nombre, apellido, estado
            FROM docentes
            WHERE codigo = %s AND estado = 'ACTIVO' AND eliminado_en IS NULL
            LIMIT 1
            """,
            (codigo_docente,)
        )
        docente = cursor.fetchone()

        if not docente:
            return jsonify({"status": "error", "message": "Docente no encontrado o inactivo."}), 404

        ahora = datetime.now()

        cursor.execute(
            """
            INSERT INTO registros_asistencia (id, docente_id, fecha, hora_ingreso, estado_puntualidad, creado_en)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (str(uuid.uuid4()), docente["id"], ahora.date(), ahora.time(), "A_TIEMPO")
        )
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Asistencia registrada con éxito para {docente['nombre']} {docente['apellido']}."
        }), 200

    except Exception as e:
        conn.rollback()
        print("ERROR MARCAR ASISTENCIA:", e)
        return jsonify({"status": "error", "message": "Error al registrar la asistencia."}), 500
    finally:
        if cursor:
            cursor.close()
        conn.close()


# Registramos el Blueprint de permisos
app.register_blueprint(permisos_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timedelta

import bcrypt
import psycopg2
from flask import (
    Flask, abort, jsonify, redirect, render_template, request,
    send_file, session, url_for
)
from psycopg2.extras import RealDictCursor

from permisos import (
    MENU,
    obtener_permisos_usuario,
    requiere_permiso,
    tiene_permiso,
)


# ============================================================
# FLASK
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "Templates"),
    static_folder=BASE_DIR,
    static_url_path="",
)

app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")
app.config["JSON_AS_ASCII"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ============================================================
# POSTGRESQL
# ============================================================

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "asistencia_qr")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "Admin123*")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )


# ============================================================
# USUARIO / SESIÓN
# ============================================================

def obtener_usuario_actual():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
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
                JOIN roles r ON r.id = u.rol_id
                WHERE u.id = %s
                  AND u.estado = 'ACTIVO'
                  AND u.eliminado_en IS NULL
                  AND r.estado = 'ACTIVO'
                  AND r.eliminado_en IS NULL
                """,
                (usuario_id,),
            )
            return cur.fetchone()
    except psycopg2.Error:
        return None
    finally:
        if conn:
            conn.close()


def login_requerido():
    return bool(session.get("usuario_id"))


@app.context_processor
def contexto_global():
    usuario = obtener_usuario_actual() if login_requerido() else None
    permisos = obtener_permisos_usuario(usuario["id"]) if usuario else set()

    def can(codigo):
        return codigo in permisos

    def menu_visible():
        return [item for item in MENU if item["permiso"] is None or can(item["permiso"])]

    return {
        "usuario_actual": usuario,
        "permisos_usuario": permisos,
        "tiene_permiso": can,
        "menu_visible": menu_visible,
    }


def proteger_pagina(permiso=None):
    """Protección común para las rutas HTML."""
    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()
    if not usuario:
        session.clear()
        return redirect(url_for("iniciar_sesion"))

    if permiso and not tiene_permiso(usuario["id"], permiso):
        abort(403)

    return None


# ============================================================
# AUDITORÍA
# ============================================================

def registrar_auditoria(usuario_id, accion, modulo, descripcion, id_entidad=None):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registros_auditoria
                (
                    id, usuario_id, user_email, user_name, accion, modulo,
                    id_entidad, descripcion, direccion_ip, agente_usuario,
                    dispositivo, metadatos, creado_en, actualizado_en
                )
                SELECT
                    %s, u.id, u.correo,
                    CONCAT(u.nombre, ' ', u.apellido),
                    %s::accion_auditoria, %s, %s, %s, %s, %s, %s,
                    '{}'::jsonb, NOW(), NOW()
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
                    usuario_id,
                ),
            )
            conn.commit()
    except Exception:
        # La auditoría nunca debe impedir el funcionamiento principal.
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


# ============================================================
# HTML
# ============================================================

@app.route("/")
def index():
    # index.html está en la raíz del proyecto, no dentro de Templates.
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/inicio")
def inicio():
    error = proteger_pagina()
    if error:
        return error
    return render_template("inicio.html")


@app.route("/dashboard")
@requiere_permiso("panel.consultar")
def dashboard():
    return render_template("dashboard.html")


@app.route("/asistencias")
def asistencias():
    error = proteger_pagina()
    if error:
        return error
    usuario = obtener_usuario_actual()

    # Un docente solo puede consultar su propia asistencia.
    if usuario["rol_nombre"] == "DOCENTE":
        if not tiene_permiso(usuario["id"], "asistencia.propia"):
            abort(403)
    elif not tiene_permiso(usuario["id"], "asistencia.consultar"):
        abort(403)

    return render_template("asistencias.html")


@app.route("/excusas")
def excusas():
    error = proteger_pagina()
    if error:
        return error
    return render_template("excusas.html")


@app.route("/qr_institucional")
@requiere_permiso("asistencia.consultar")
def qr_institucional():
    return render_template("codigo qr institucional.html")


@app.route("/marcar")
def marcar():
    # Página pública: el QR institucional debe poder abrirse sin iniciar sesión.
    return render_template("asistencias.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
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

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id
                FROM usuarios
                WHERE (LOWER(correo) = LOWER(%s) OR documento = %s)
                  AND eliminado_en IS NULL
                LIMIT 1
                """,
                (correo, documento),
            )
            if cur.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "El correo o documento ya está registrado.",
                }), 409

            cur.execute(
                """
                SELECT id
                FROM roles
                WHERE nombre = 'DOCENTE'
                  AND estado = 'ACTIVO'
                  AND eliminado_en IS NULL
                LIMIT 1
                """
            )
            rol = cur.fetchone()
            if not rol:
                return jsonify({
                    "status": "error",
                    "message": "No existe el rol DOCENTE.",
                }), 500

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            usuario_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO usuarios
                    (id, nombre, apellido, documento, correo, telefono,
                     contrasena, estado, rol_id, debe_cambiar_contrasena,
                     creado_en, actualizado_en)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, 'ACTIVO', %s, FALSE, NOW(), NOW())
                """,
                (
                    usuario_id, nombre, apellido, documento, correo,
                    telefono or None, password_hash, rol["id"],
                ),
            )
            conn.commit()

        return jsonify({
            "status": "success",
            "message": "Usuario registrado correctamente.",
            "redirect": "/iniciar",
        }), 201

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": "No fue posible registrar el usuario.",
        }), 500
    finally:
        if conn:
            conn.close()


@app.route("/iniciar", methods=["GET", "POST"])
def iniciar_sesion():
    if request.method == "GET":
        if login_requerido():
            return redirect(url_for("inicio"))
        return render_template("iniciar.html")

    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Por favor completa todos los campos.",
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    u.id, u.nombre, u.apellido, u.correo, u.contrasena,
                    u.estado, u.rol_id, u.intentos_inicio_fallidos,
                    u.bloqueado_hasta, u.debe_cambiar_contrasena,
                    r.nombre AS rol_nombre
                FROM usuarios u
                JOIN roles r ON r.id = u.rol_id
                WHERE LOWER(u.correo) = LOWER(%s)
                  AND u.eliminado_en IS NULL
                  AND r.eliminado_en IS NULL
                """,
                (email,),
            )
            usuario = cur.fetchone()

            if not usuario:
                return jsonify({
                    "status": "error",
                    "message": "El usuario no existe.",
                }), 404

            if usuario["estado"] != "ACTIVO":
                return jsonify({
                    "status": "error",
                    "message": "La cuenta está inactiva.",
                }), 403

            bloqueado = usuario["bloqueado_hasta"]
            if bloqueado:
                ahora = datetime.now(bloqueado.tzinfo) if bloqueado.tzinfo else datetime.now()
                if bloqueado > ahora:
                    return jsonify({
                        "status": "error",
                        "message": "La cuenta está bloqueada temporalmente.",
                    }), 403

            try:
                password_ok = bcrypt.checkpw(
                    password.encode("utf-8"),
                    usuario["contrasena"].encode("utf-8"),
                )
            except Exception:
                password_ok = False

            if not password_ok:
                intentos = int(usuario["intentos_inicio_fallidos"] or 0) + 1
                bloqueado_hasta = None
                if intentos >= 5:
                    bloqueado_hasta = datetime.now() + timedelta(minutes=15)
                    intentos = 0

                cur.execute(
                    """
                    UPDATE usuarios
                    SET intentos_inicio_fallidos = %s,
                        bloqueado_hasta = %s,
                        actualizado_en = NOW()
                    WHERE id = %s
                    """,
                    (intentos, bloqueado_hasta, usuario["id"]),
                )
                conn.commit()

                return jsonify({
                    "status": "error",
                    "message": "Contraseña incorrecta.",
                }), 401

            cur.execute(
                """
                UPDATE usuarios
                SET intentos_inicio_fallidos = 0,
                    bloqueado_hasta = NULL,
                    ultimo_inicio_sesion = NOW(),
                    actualizado_en = NOW()
                WHERE id = %s
                """,
                (usuario["id"],),
            )
            conn.commit()

        session.clear()
        session["usuario_id"] = str(usuario["id"])
        session["usuario_nombre"] = usuario["nombre"]
        session["usuario_apellido"] = usuario["apellido"]
        session["usuario_correo"] = usuario["correo"]
        session["rol_id"] = str(usuario["rol_id"])
        session["rol_nombre"] = usuario["rol_nombre"]

        try:
            registrar_auditoria(
                str(usuario["id"]),
                "INICIO_SESION",
                "autenticacion",
                "Inicio de sesión exitoso.",
            )
        except Exception:
            pass

        return jsonify({
            "status": "success",
            "message": "Acceso concedido.",
            "redirect": "/inicio",
        })

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": "Ocurrió un error al iniciar sesión.",
        }), 500
    finally:
        if conn:
            conn.close()


@app.route("/cerrar_sesion")
@app.route("/logout")
def cerrar_sesion():
    usuario_id = session.get("usuario_id")
    if usuario_id:
        registrar_auditoria(
            usuario_id,
            "CIERRE_SESION",
            "autenticacion",
            "Cierre de sesión.",
        )
    session.clear()
    return redirect(url_for("iniciar_sesion"))


# ============================================================
# API DE PERMISOS
# ============================================================

@app.route("/api/permisos_usuario")
def api_permisos_usuario():
    error = proteger_pagina()
    if error:
        return error

    usuario = obtener_usuario_actual()
    permisos = obtener_permisos_usuario(usuario["id"])

    return jsonify({
        "status": "success",
        "usuario": {
            "id": str(usuario["id"]),
            "nombre": f"{usuario['nombre']} {usuario['apellido']}",
            "correo": usuario["correo"],
            "rol": usuario["rol_nombre"],
        },
        "permisos": sorted(permisos),
        "menu": [
            item for item in MENU
            if item["permiso"] is None or item["permiso"] in permisos
        ],
    })


# ============================================================
# API - MARCAR ASISTENCIA
# ============================================================

@app.route("/api/marcar_asistencia", methods=["POST"])
def marcar_asistencia():
    data = request.get_json(silent=True) or request.form

    codigo = (data.get("codigo_docente") or data.get("codigo") or "").strip()
    tipo = (data.get("tipo") or "ENTRADA").strip().upper()

    if not codigo:
        return jsonify({
            "status": "error",
            "message": "Código de docente no proporcionado.",
        }), 400

    if tipo not in {"ENTRADA", "SALIDA"}:
        return jsonify({
            "status": "error",
            "message": "El tipo debe ser ENTRADA o SALIDA.",
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, codigo, nombre, apellido, estado
                FROM docentes
                WHERE codigo = %s
                  AND estado = 'ACTIVO'
                  AND eliminado_en IS NULL
                LIMIT 1
                """,
                (codigo,),
            )
            docente = cur.fetchone()

            if not docente:
                return jsonify({
                    "status": "error",
                    "message": "Docente no encontrado o inactivo.",
                }), 404

            ahora = datetime.now()
            dia_semana = (ahora.weekday() + 1) % 7
            hora_actual = ahora.strftime("%H:%M")

            cur.execute(
                """
                SELECT
                    h.id AS horario_id,
                    h.hora_entrada,
                    h.hora_salida,
                    h.minutos_tolerancia
                FROM horarios h
                WHERE h.docente_id = %s
                  AND h.estado = 'ACTIVO'
                  AND h.eliminado_en IS NULL
                  AND (h.dia_semana IS NULL OR h.dia_semana = %s)
                ORDER BY
                    ABS(
                        (
                            split_part(
                                CASE WHEN %s = 'ENTRADA'
                                     THEN h.hora_entrada
                                     ELSE h.hora_salida
                                END, ':', 1
                            )::int * 60
                            +
                            split_part(
                                CASE WHEN %s = 'ENTRADA'
                                     THEN h.hora_entrada
                                     ELSE h.hora_salida
                                END, ':', 2
                            )::int
                        )
                        -
                        (
                            split_part(%s, ':', 1)::int * 60
                            + split_part(%s, ':', 2)::int
                        )
                    )
                LIMIT 1
                """,
                (docente["id"], dia_semana, tipo, tipo, hora_actual, hora_actual),
            )
            horario = cur.fetchone()

            hora_esperada = None
            diferencia = 0
            estado = "A_TIEMPO"
            horario_id = None

            if horario:
                horario_id = horario["horario_id"]
                hora_esperada = (
                    horario["hora_entrada"]
                    if tipo == "ENTRADA"
                    else horario["hora_salida"]
                )

                def minutos(h):
                    hh, mm = str(h).split(":")[:2]
                    return int(hh) * 60 + int(mm)

                diferencia = minutos(hora_actual) - minutos(hora_esperada)
                if diferencia > int(horario["minutos_tolerancia"] or 0):
                    estado = "TARDE"

            cur.execute(
                """
                INSERT INTO asistencias
                (
                    id, docente_id, horario_id, tipo, estado, fecha,
                    registrado_en, hora_esperada, diferencia_minutos,
                    direccion_ip, agente_usuario, dispositivo,
                    registrado_por_id, creado_en, actualizado_en
                )
                VALUES
                (
                    %s, %s, %s, %s::tipo_asistencia, %s::estado_asistencia,
                    %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
                """,
                (
                    str(uuid.uuid4()),
                    docente["id"],
                    horario_id,
                    tipo,
                    estado,
                    ahora.date(),
                    ahora,
                    hora_esperada,
                    diferencia,
                    request.remote_addr,
                    request.headers.get("User-Agent", ""),
                    request.headers.get("X-Device", ""),
                    session.get("usuario_id"),
                ),
            )
            conn.commit()

        return jsonify({
            "status": "success",
            "message": (
                f"{tipo.capitalize()} registrada para "
                f"{docente['nombre']} {docente['apellido']}."
            ),
            "estado": estado,
            "diferencia_minutos": diferencia,
        })

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": "No fue posible registrar la asistencia.",
            "detail": str(e) if app.debug else None,
        }), 500
    finally:
        if conn:
            conn.close()


# ============================================================
# CONSULTA DE ASISTENCIAS
# ============================================================

@app.route("/api/asistencias")
def api_asistencias():
    error = proteger_pagina()
    if error:
        return error

    usuario = obtener_usuario_actual()
    conn = None

    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if usuario["rol_nombre"] == "DOCENTE":
                cur.execute(
                    """
                    SELECT *
                    FROM v_asistencia_detallada
                    WHERE docente_id = (
                        SELECT id FROM docentes WHERE usuario_id = %s
                    )
                    ORDER BY fecha DESC, registrado_en DESC
                    """,
                    (usuario["id"],),
                )
            else:
                if not tiene_permiso(usuario["id"], "asistencia.consultar"):
                    abort(403)

                cur.execute(
                    """
                    SELECT *
                    FROM v_asistencia_detallada
                    ORDER BY fecha DESC, registrado_en DESC
                    """
                )

            rows = cur.fetchall()

        return jsonify({
            "status": "success",
            "data": rows,
        })

    except psycopg2.Error:
        return jsonify({
            "status": "error",
            "message": "No fue posible consultar las asistencias.",
        }), 500
    finally:
        if conn:
            conn.close()


@app.errorhandler(403)
def forbidden(_error):
    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "message": "No tienes permisos para realizar esta acción.",
        }), 403
    return render_template(
        "inicio.html",
        error_permiso="No tienes permisos para acceder a esta opción.",
    ), 403


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "message": "Recurso no encontrado.",
        }), 404
    return "Página no encontrada", 404


if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )

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

# IMPORTANTE:
# En producción debes definir SECRET_KEY como variable de entorno.
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
    Devuelve el usuario actualmente autenticado.
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
            LEFT JOIN roles r
                ON r.id = u.rol_id
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
    Comprueba si existe una sesión activa.
    """

    return "usuario_id" in session


def hora_a_minutos(hora):
    """
    Convierte HH:MM a minutos.
    """

    try:
        partes = str(hora).split(":")

        return int(partes[0]) * 60 + int(partes[1])

    except Exception:
        return 0


def calcular_diferencia_minutos(hora_real, hora_esperada):
    """
    Diferencia positiva = llegó tarde.
    Diferencia negativa = llegó antes.
    """

    return (
        hora_a_minutos(hora_real)
        - hora_a_minutos(hora_esperada)
    )


def evaluar_puntualidad(hora_real, hora_esperada, tolerancia):
    """
    Replica la función fn_evaluar_puntualidad de PostgreSQL.
    """

    diferencia = calcular_diferencia_minutos(
        hora_real,
        hora_esperada
    )

    if diferencia > int(tolerancia or 0):
        return "TARDE"

    return "A_TIEMPO"


def registrar_auditoria(
    usuario_id,
    accion,
    modulo,
    descripcion,
    id_entidad=None
):
    """
    Registra una acción si la tabla de auditoría existe.
    No detiene el funcionamiento de la aplicación si falla.
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
                id,
                usuario_id,
                user_email,
                user_name,
                accion,
                modulo,
                id_entidad,
                descripcion,
                direccion_ip,
                agente_usuario,
                dispositivo,
                metadatos,
                creado_en,
                actualizado_en
            )
            SELECT
                %s,
                u.id,
                u.correo,
                CONCAT(u.nombre, ' ', u.apellido),
                %s::accion_auditoria,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                '{}'::jsonb,
                NOW(),
                NOW()
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


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/inicio")
def inicio():

    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()

    if not usuario:
        session.clear()
        return redirect(url_for("iniciar_sesion"))

    return render_template(
        "inicio.html",
        usuario=usuario
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/iniciar", methods=["GET", "POST"])
def iniciar_sesion():

    if request.method == "GET":

        if login_requerido():
            return redirect(url_for("inicio"))

        return render_template("iniciar.html")

    data = request.get_json(silent=True) or request.form

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:

        return jsonify({
            "status": "error",
            "message": "Por favor completa todos los campos."
        }), 400

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "No fue posible conectar con PostgreSQL."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute(
            """
            SELECT
                u.id,
                u.nombre,
                u.apellido,
                u.documento,
                u.correo,
                u.contrasena,
                u.estado,
                u.rol_id,
                u.intentos_inicio_fallidos,
                u.bloqueado_hasta,
                u.debe_cambiar_contrasena,
                r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r
                ON r.id = u.rol_id
            WHERE LOWER(u.correo) = LOWER(%s)
              AND u.eliminado_en IS NULL
            """,
            (email,)
        )

        usuario = cursor.fetchone()

        if not usuario:

            return jsonify({
                "status": "error",
                "message": "El usuario no existe."
            }), 404

        if usuario["estado"] != "ACTIVO":

            return jsonify({
                "status": "error",
                "message": "La cuenta está inactiva."
            }), 403

        # Comprobar bloqueo
        if usuario["bloqueado_hasta"]:

            ahora = datetime.now(
                usuario["bloqueado_hasta"].tzinfo
            ) if usuario["bloqueado_hasta"].tzinfo else datetime.now()

            if usuario["bloqueado_hasta"] > ahora:

                return jsonify({
                    "status": "error",
                    "message": "La cuenta se encuentra temporalmente bloqueada."
                }), 403

        contrasena_db = usuario["contrasena"]

        es_valida = False

        try:

            if contrasena_db.startswith("$2"):

                es_valida = bcrypt.checkpw(
                    password.encode("utf-8"),
                    contrasena_db.encode("utf-8")
                )

            else:
                # Compatibilidad temporal con contraseñas antiguas
                es_valida = password == contrasena_db

        except Exception:
            es_valida = False

        if not es_valida:

            nuevos_intentos = int(
                usuario["intentos_inicio_fallidos"] or 0
            ) + 1

            bloqueado_hasta = None

            if nuevos_intentos >= 5:

                from datetime import timedelta

                bloqueado_hasta = datetime.now() + timedelta(
                    minutes=15
                )

                nuevos_intentos = 0

            cursor.execute(
                """
                UPDATE usuarios
                SET
                    intentos_inicio_fallidos = %s,
                    bloqueado_hasta = %s,
                    actualizado_en = NOW()
                WHERE id = %s
                """,
                (
                    nuevos_intentos,
                    bloqueado_hasta,
                    usuario["id"]
                )
            )

            conn.commit()

            return jsonify({
                "status": "error",
                "message": "Contraseña incorrecta."
            }), 401

        # Reiniciar intentos
        cursor.execute(
            """
            UPDATE usuarios
            SET
                intentos_inicio_fallidos = 0,
                bloqueado_hasta = NULL,
                ultimo_inicio_sesion = NOW(),
                actualizado_en = NOW()
            WHERE id = %s
            """,
            (usuario["id"],)
        )

        conn.commit()

        # Crear sesión
        session.clear()

        session["usuario_id"] = str(usuario["id"])
        session["usuario_nombre"] = usuario["nombre"]
        session["usuario_apellido"] = usuario["apellido"]
        session["usuario_correo"] = usuario["correo"]
        session["rol_id"] = str(usuario["rol_id"])
        session["rol_nombre"] = usuario["rol_nombre"]

        # Auditoría
        registrar_auditoria(
            str(usuario["id"]),
            "INICIO_SESION",
            "autenticacion",
            "Inicio de sesión exitoso."
        )

        return jsonify({
            "status": "success",
            "message": "Acceso concedido.",
            "redirect": "/inicio"
        })

    except Exception as e:

        conn.rollback()

        print("ERROR LOGIN:", e)

        return jsonify({
            "status": "error",
            "message": "Ocurrió un error al iniciar sesión."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# CERRAR SESIÓN
# ============================================================

@app.route("/cerrar_sesion")
@app.route("/logout")
def cerrar_sesion():

    usuario_id = session.get("usuario_id")

    if usuario_id:

        registrar_auditoria(
            usuario_id,
            "CIERRE_SESION",
            "autenticacion",
            "Cierre de sesión."
        )

    session.clear()

    return redirect(url_for("iniciar_sesion"))


# ============================================================
# REGISTRO DE USUARIOS
# ============================================================

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

    if not all([
        nombre,
        apellido,
        documento,
        correo,
        password
    ]):

        return jsonify({
            "status": "error",
            "message": "Faltan campos obligatorios."
        }), 400

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "No fue posible conectar con PostgreSQL."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        # Comprobar correo/documento
        cursor.execute(
            """
            SELECT id
            FROM usuarios
            WHERE correo = %s
               OR documento = %s
            LIMIT 1
            """,
            (correo, documento)
        )

        if cursor.fetchone():

            return jsonify({
                "status": "error",
                "message": "El correo o documento ya está registrado."
            }), 409

        # Buscar rol DOCENTE
        cursor.execute(
            """
            SELECT id
            FROM roles
            WHERE nombre = 'DOCENTE'
              AND estado = 'ACTIVO'
            LIMIT 1
            """
        )

        rol = cursor.fetchone()

        if not rol:

            return jsonify({
                "status": "error",
                "message": "No existe el rol DOCENTE."
            }), 500

        hash_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        usuario_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO usuarios
            (
                id,
                nombre,
                apellido,
                documento,
                correo,
                telefono,
                contrasena,
                estado,
                rol_id,
                debe_cambiar_contrasena,
                creado_en,
                actualizado_en
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'ACTIVO',
                %s,
                FALSE,
                NOW(),
                NOW()
            )
            """,
            (
                usuario_id,
                nombre,
                apellido,
                documento,
                correo,
                telefono or None,
                hash_password,
                rol["id"]
            )
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Usuario registrado correctamente.",
            "redirect": "/iniciar"
        }), 201

    except psycopg2.Error as e:

        conn.rollback()

        print("ERROR REGISTRO:", e)

        return jsonify({
            "status": "error",
            "message": "No fue posible registrar el usuario."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()

    if not usuario:

        session.clear()

        return redirect(url_for("iniciar_sesion"))

    return render_template(
        "dashboard.html",
        usuario=usuario
    )


# ============================================================
# ASISTENCIAS
# ============================================================

@app.route("/asistencias")
def asistencias():

    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()

    if not usuario:

        session.clear()

        return redirect(url_for("iniciar_sesion"))

    return render_template(
        "asistencias.html",
        usuario=usuario
    )


# ============================================================
# EXCUSAS
# ============================================================

@app.route("/excusas")
def excusas():

    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()

    return render_template(
        "excusas.html",
        usuario=usuario
    )


# ============================================================
# QR INSTITUCIONAL
# ============================================================

@app.route("/qr_institucional")
def qr_institucional():

    if not login_requerido():
        return redirect(url_for("iniciar_sesion"))

    usuario = obtener_usuario_actual()

    return render_template(
        "codigo qr institucional.html",
        usuario=usuario
    )


# ============================================================
# RUTA PÚBLICA DEL QR
# ============================================================

@app.route("/marcar", methods=["GET"])
def marcar():

    """
    Esta es la URL que debe utilizar el QR.

    El docente llega aquí después de escanear.
    """

    return render_template("asistencias.html")


# ============================================================
# API - MARCAR ASISTENCIA
# ============================================================

@app.route("/api/marcar_asistencia", methods=["POST"])
def marcar_asistencia():

    data = request.get_json(silent=True) or request.form

    codigo_docente = (
        data.get("codigo_docente")
        or data.get("codigo")
        or ""
    ).strip()

    if not codigo_docente:

        return jsonify({
            "status": "error",
            "message": "Código de docente no proporcionado."
        }), 400

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "Error conectando con PostgreSQL."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        # ----------------------------------------------------
        # 1. Buscar docente
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                codigo,
                nombre,
                apellido,
                estado
            FROM docentes
            WHERE codigo = %s
              AND estado = 'ACTIVO'
              AND eliminado_en IS NULL
            LIMIT 1
            """,
            (codigo_docente,)
        )

        docente = cursor.fetchone()

        if not docente:

            return jsonify({
                "status": "error",
                "message": "Docente no encontrado o inactivo."
            }), 404

        docente_id = docente["id"]

        ahora = datetime.now()

        fecha_actual = ahora.date()

        hora_actual = ahora.strftime("%H:%M")

        # PostgreSQL:
        # 1=lunes
        # 2=martes
        # ...
        # 7=domingo
        dia_semana = ahora.isoweekday()

        # ----------------------------------------------------
        # 2. Buscar horario correspondiente
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                h.id,
                h.hora_entrada,
                h.hora_salida,
                h.minutos_tolerancia,
                h.asignatura_id,
                h.jornada_id
            FROM horarios h
            WHERE h.docente_id = %s
              AND h.dia_semana = %s
              AND h.estado = 'ACTIVO'
              AND h.eliminado_en IS NULL
            ORDER BY h.hora_entrada
            """,
            (
                docente_id,
                dia_semana
            )
        )

        horarios = cursor.fetchall()

        if not horarios:

            return jsonify({
                "status": "error",
                "message": "El docente no tiene horario configurado para hoy."
            }), 404

        # ----------------------------------------------------
        # 3. Determinar el horario actual
        # ----------------------------------------------------

        horario = None

        minutos_actuales = hora_a_minutos(hora_actual)

        for h in horarios:

            entrada = hora_a_minutos(
                h["hora_entrada"]
            )

            salida = hora_a_minutos(
                h["hora_salida"]
            )

            # Permitimos marcar entrada
            # hasta cierto margen antes de la entrada
            if (
                entrada - 120
                <= minutos_actuales
                <= salida + 120
            ):
                horario = h
                break

        if not horario:

            horario = horarios[0]

        horario_id = horario["id"]

        hora_entrada = horario["hora_entrada"]
        hora_salida = horario["hora_salida"]
        tolerancia = horario["minutos_tolerancia"]

        # ----------------------------------------------------
        # 4. Verificar marcaciones del día
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                tipo,
                estado,
                fecha,
                registrado_en,
                hora_esperada
            FROM asistencias
            WHERE docente_id = %s
              AND fecha = %s
              AND horario_id = %s
              AND eliminado_en IS NULL
            ORDER BY registrado_en
            """,
            (
                docente_id,
                fecha_actual,
                horario_id
            )
        )

        marcaciones = cursor.fetchall()

        # ----------------------------------------------------
        # 5. Determinar ENTRADA o SALIDA
        # ----------------------------------------------------

        tiene_entrada = any(
            m["tipo"] == "ENTRADA"
            for m in marcaciones
        )

        tiene_salida = any(
            m["tipo"] == "SALIDA"
            for m in marcaciones
        )

        if not tiene_entrada:

            tipo = "ENTRADA"

            hora_esperada = hora_entrada

            diferencia = calcular_diferencia_minutos(
                hora_actual,
                hora_esperada
            )

            estado = evaluar_puntualidad(
                hora_actual,
                hora_esperada,
                tolerancia
            )

        elif not tiene_salida:

            tipo = "SALIDA"

            hora_esperada = hora_salida

            diferencia = calcular_diferencia_minutos(
                hora_actual,
                hora_esperada
            )

            # Para salida:
            # si sale antes de la hora esperada,
            # se marca como SALIDA_ANTICIPADA.
            if diferencia < 0:

                estado = "SALIDA_ANTICIPADA"

            else:

                estado = "A_TIEMPO"

        else:

            return jsonify({
                "status": "error",
                "message": "La asistencia de este horario ya tiene entrada y salida registradas."
            }), 409

        # ----------------------------------------------------
        # 6. Registrar asistencia
        # ----------------------------------------------------

        asistencia_id = str(uuid.uuid4())

        usuario_registrador = session.get(
            "usuario_id"
        )

        cursor.execute(
            """
            INSERT INTO asistencias
            (
                id,
                docente_id,
                horario_id,
                tipo,
                estado,
                fecha,
                registrado_en,
                hora_esperada,
                diferencia_minutos,
                direccion_ip,
                agente_usuario,
                dispositivo,
                notas,
                registrado_por_id,
                creado_en,
                actualizado_en
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s::tipo_asistencia,
                %s::estado_asistencia,
                %s,
                NOW(),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                NOW(),
                NOW()
            )
            """,
            (
                asistencia_id,
                docente_id,
                horario_id,
                tipo,
                estado,
                fecha_actual,
                hora_esperada,
                diferencia,
                request.remote_addr,
                request.headers.get(
                    "User-Agent",
                    ""
                ),
                request.headers.get(
                    "X-Device",
                    ""
                ),
                f"Marcación QR - {tipo}",
                usuario_registrador
            )
        )

        conn.commit()

        # ----------------------------------------------------
        # 7. Auditoría
        # ----------------------------------------------------

        if usuario_registrador:

            registrar_auditoria(
                usuario_registrador,
                "ASISTENCIA",
                "asistencia",
                f"Asistencia {tipo} registrada para {docente['nombre']} {docente['apellido']}.",
                asistencia_id
            )

        return jsonify({

            "status": "success",

            "message": (
                f"{tipo.capitalize()} registrada correctamente."
            ),

            "tipo": tipo,

            "estado": estado,

            "docente": (
                f"{docente['nombre']} "
                f"{docente['apellido']}"
            ),

            "codigo": docente["codigo"],

            "fecha": str(fecha_actual),

            "hora": hora_actual,

            "hora_esperada": hora_esperada,

            "diferencia_minutos": diferencia

        }), 201

    except psycopg2.Error as e:

        conn.rollback()

        print("ERROR MARCANDO ASISTENCIA:", e)

        return jsonify({
            "status": "error",
            "message": "No fue posible registrar la asistencia."
        }), 500

    except Exception as e:

        conn.rollback()

        print("ERROR GENERAL:", e)

        return jsonify({
            "status": "error",
            "message": "Ocurrió un error procesando la asistencia."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# API - LISTAR ASISTENCIAS
# ============================================================

@app.route("/api/asistencias", methods=["GET"])
def api_asistencias():

    if not login_requerido():

        return jsonify({
            "status": "error",
            "message": "Sesión requerida."
        }), 401

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "Error de conexión."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        limite = request.args.get(
            "limit",
            default=100,
            type=int
        )

        limite = min(
            max(limite, 1),
            500
        )

        cursor.execute(
            """
            SELECT
                a.id,
                a.fecha,
                a.registrado_en,
                a.tipo,
                a.estado,
                a.hora_esperada,
                a.diferencia_minutos,
                d.codigo,
                d.nombre,
                d.apellido,
                h.hora_entrada,
                h.hora_salida
            FROM asistencias a
            INNER JOIN docentes d
                ON d.id = a.docente_id
            LEFT JOIN horarios h
                ON h.id = a.horario_id
            WHERE a.eliminado_en IS NULL
            ORDER BY a.registrado_en DESC
            LIMIT %s
            """,
            (limite,)
        )

        filas = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": filas
        })

    except Exception as e:

        print("ERROR API ASISTENCIAS:", e)

        return jsonify({
            "status": "error",
            "message": "No fue posible consultar las asistencias."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# API - ESTADÍSTICAS DASHBOARD
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():

    if not login_requerido():

        return jsonify({
            "status": "error",
            "message": "Sesión requerida."
        }), 401

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "Error de conexión."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE estado = 'A_TIEMPO'
                ) AS a_tiempo,
                COUNT(*) FILTER (
                    WHERE estado = 'TARDE'
                ) AS tarde,
                COUNT(*) FILTER (
                    WHERE estado = 'SALIDA_ANTICIPADA'
                ) AS salida_anticipada,
                COUNT(*) FILTER (
                    WHERE tipo = 'ENTRADA'
                ) AS entradas,
                COUNT(*) FILTER (
                    WHERE tipo = 'SALIDA'
                ) AS salidas
            FROM asistencias
            WHERE eliminado_en IS NULL
            """
        )

        resumen = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                fecha,
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE estado = 'A_TIEMPO'
                ) AS a_tiempo,
                COUNT(*) FILTER (
                    WHERE estado = 'TARDE'
                ) AS tarde
            FROM asistencias
            WHERE eliminado_en IS NULL
            GROUP BY fecha
            ORDER BY fecha DESC
            LIMIT 30
            """
        )

        por_fecha = cursor.fetchall()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM docentes
            WHERE estado = 'ACTIVO'
              AND eliminado_en IS NULL
            """
        )

        docentes = cursor.fetchone()

        return jsonify({
            "status": "success",
            "resumen": resumen,
            "docentes_activos": docentes["total"],
            "por_fecha": por_fecha
        })

    except Exception as e:

        print("ERROR DASHBOARD:", e)

        return jsonify({
            "status": "error",
            "message": "No fue posible cargar las estadísticas."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# API - PERFIL
# ============================================================

@app.route("/api/usuario_actual", methods=["GET"])
def api_usuario_actual():

    if not login_requerido():

        return jsonify({
            "status": "error",
            "message": "Sesión requerida."
        }), 401

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "status": "error",
            "message": "Usuario no encontrado."
        }), 404

    return jsonify({
        "status": "success",
        "usuario": usuario
    })


# ============================================================
# API - DOCENTES
# ============================================================

@app.route("/api/docentes", methods=["GET"])
def api_docentes():

    if not login_requerido():

        return jsonify({
            "status": "error",
            "message": "Sesión requerida."
        }), 401

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "message": "Error de conexión."
        }), 500

    cursor = None

    try:

        cursor = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute(
            """
            SELECT
                id,
                codigo,
                nombre,
                apellido,
                documento,
                correo,
                telefono,
                estado
            FROM docentes
            WHERE eliminado_en IS NULL
            ORDER BY nombre, apellido
            """
        )

        docentes = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": docentes
        })

    except Exception as e:

        print("ERROR DOCENTES:", e)

        return jsonify({
            "status": "error",
            "message": "No fue posible consultar los docentes."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conn.close()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    conn = get_db_connection()

    if not conn:

        return jsonify({
            "status": "error",
            "database": "offline"
        }), 503

    try:

        cursor = conn.cursor()

        cursor.execute("SELECT 1")

        cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "database": "online",
            "time": datetime.now().isoformat()
        })

    except Exception as e:

        try:
            conn.close()
        except Exception:
            pass

        return jsonify({
            "status": "error",
            "database": "offline",
            "message": str(e)
        }), 503


# ============================================================
# MANEJO DE ERRORES
# ============================================================

@app.errorhandler(404)
def pagina_no_encontrada(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "status": "error",
            "message": "Ruta API no encontrada."
        }), 404

    return "Página no encontrada.", 404


@app.errorhandler(500)
def error_servidor(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "status": "error",
            "message": "Error interno del servidor."
        }), 500

    return "Error interno del servidor.", 500


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(" SISTEMA DE ASISTENCIAS DOCENTES")
    print("=" * 60)
    print(f" PostgreSQL: {DB_HOST}:{DB_PORT}")
    print(f" Base de datos: {DB_NAME}")
    print(" Servidor: http://127.0.0.1:3000")
    print(" QR: http://127.0.0.1:3000/marcar")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=3000,
        debug=True
    )
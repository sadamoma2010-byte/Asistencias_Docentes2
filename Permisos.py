from functools import wraps
from flask import Blueprint, jsonify, session, redirect, url_for

permisos_bp = Blueprint("permisos", __name__)

# ============================================================
# MATRIZ DE PERMISOS POR ROL
# ============================================================

PERMISOS_POR_ROL = {
    "ADMINISTRADOR": {
        "modulos": ["inicio", "dashboard", "asistencias", "excusas", "qr_institucional", "docentes", "reportes"],
        "acciones": ["crear", "editar", "eliminar", "consultar", "aprobar_excusas", "generar_qr"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "dashboard", "label": "Panel de Control", "url": "/dashboard", "icono": "dashboard"},
            {"id": "asistencias", "label": "Gestión de Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Gestión de Excusas", "url": "/excusas", "icono": "file-text"},
            {"id": "qr_institucional", "label": "Código QR Institucional", "url": "/qr_institucional", "icono": "qr-code"},
        ]
    },
    "COORDINADOR": {
        "modulos": ["inicio", "dashboard", "asistencias", "excusas", "qr_institucional"],
        "acciones": ["consultar", "aprobar_excusas", "generar_qr"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "dashboard", "label": "Dashboard", "url": "/dashboard", "icono": "dashboard"},
            {"id": "asistencias", "label": "Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Revisar Excusas", "url": "/excusas", "icono": "file-text"},
            {"id": "qr_institucional", "label": "QR Institucional", "url": "/qr_institucional", "icono": "qr-code"},
        ]
    },
    "DOCENTE": {
        "modulos": ["inicio", "asistencias", "excusas"],
        "acciones": ["marcar_asistencia", "subir_excusa", "consultar_propio"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "asistencias", "label": "Mis Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Mis Excusas", "url": "/excusas", "icono": "file-text"},
        ]
    }
}


# ============================================================
# ENDPOINT PARA EL FRONTEND
# ============================================================

@permisos_bp.route("/api/permisos_usuario", methods=["GET"])
def obtener_permisos_usuario():
    """
    Retorna el menú y los permisos en JSON para que el Javascript
    del Frontend dibuje las opciones disponibles.
    """
    if "usuario_id" not in session:
        return jsonify({"status": "error", "message": "Sesión no iniciada"}), 401

    rol_nombre = (session.get("rol_nombre") or "DOCENTE").upper()
    config = PERMISOS_POR_ROL.get(rol_nombre, PERMISOS_POR_ROL["DOCENTE"])

    return jsonify({
        "status": "success",
        "usuario": {
            "id": session.get("usuario_id"),
            "nombre": f"{session.get('usuario_nombre', '')} {session.get('usuario_apellido', '')}".strip(),
            "correo": session.get("usuario_correo"),
            "rol": rol_nombre
        },
        "modulos": config["modulos"],
        "acciones": config["acciones"],
        "menu": config["menu"]
    }), 200


# ============================================================
# DECORADOR PARA PROTEGER VISTAS EN EL BACKEND
# ============================================================

def requerir_permiso(modulo_requerido):
    """
    Decorador Python para restringir vistas según el módulo asignado al rol.
    Uso: @requerir_permiso('dashboard')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("iniciar_sesion"))

            rol = (session.get("rol_nombre") or "DOCENTE").upper()
            permisos_rol = PERMISOS_POR_ROL.get(rol, PERMISOS_POR_ROL["DOCENTE"])

            if modulo_requerido not in permisos_rol["modulos"]:
                return redirect(url_for("inicio"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
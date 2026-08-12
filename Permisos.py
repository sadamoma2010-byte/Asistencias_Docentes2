# permisos.py
from flask import Blueprint, jsonify, session
from app import obtener_usuario_actual, login_requerido

permisos_bp = Blueprint('permisos', __name__)

# Definición de permisos por Rol
PERMISOS_POR_ROL = {
    "ADMINISTRADOR": {
        "modulos": ["dashboard", "asistencias", "excusas", "qr_institucional", "docentes", "reportes", "configuracion"],
        "acciones": ["crear", "editar", "eliminar", "consultar", "exportar"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "dashboard", "label": "Panel Control", "url": "/dashboard", "icono": "dashboard"},
            {"id": "asistencias", "label": "Gestión Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Gestión Excusas", "url": "/excusas", "icono": "file-text"},
            {"id": "qr_institucional", "label": "Generar QR", "url": "/qr_institucional", "icono": "qr-code"},
            {"id": "reportes", "label": "Reportes Globales", "url": "/reportes", "icono": "bar-chart"}
        ]
    },
    "COORDINADOR": {
        "modulos": ["dashboard", "asistencias", "excusas", "qr_institucional", "reportes"],
        "acciones": ["consultar", "aprobar_excusas", "exportar"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "dashboard", "label": "Dashboard", "url": "/dashboard", "icono": "dashboard"},
            {"id": "asistencias", "label": "Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Revisar Excusas", "url": "/excusas", "icono": "file-text"},
            {"id": "qr_institucional", "label": "QR Institucional", "url": "/qr_institucional", "icono": "qr-code"}
        ]
    },
    "DOCENTE": {
        "modulos": ["inicio", "asistencias", "excusas"],
        "acciones": ["marcar_asistencia", "subir_excusa", "consultar_propio"],
        "menu": [
            {"id": "inicio", "label": "Inicio", "url": "/inicio", "icono": "home"},
            {"id": "asistencias", "label": "Mis Asistencias", "url": "/asistencias", "icono": "calendar"},
            {"id": "excusas", "label": "Mis Excusas", "url": "/excusas", "icono": "file-text"}
        ]
    }
}

@permisos_bp.route("/api/permisos_usuario", methods=["GET"])
def obtener_permisos_usuario():
    """
    Endpoint que responde al Frontend las opciones de interfaz habilitadas.
    """
    if not login_requerido():
        return jsonify({"status": "error", "message": "Sesión no iniciada"}), 401

    usuario = obtener_usuario_actual()
    if not usuario:
        return jsonify({"status": "error", "message": "Usuario invalido o inactivo"}), 403

    rol = (usuario.get("rol_nombre") or "DOCENTE").upper()
    config_permisos = PERMISOS_POR_ROL.get(rol, PERMISOS_POR_ROL["DOCENTE"])

    return jsonify({
        "status": "success",
        "usuario": {
            "id": usuario["id"],
            "nombre": f"{usuario['nombre']} {usuario['apellido']}",
            "correo": usuario["correo"],
            "rol": rol
        },
        "modulos_permitidos": config_permisos["modulos"],
        "acciones": config_permisos["acciones"],
        "menu": config_permisos["menu"]
    }), 200

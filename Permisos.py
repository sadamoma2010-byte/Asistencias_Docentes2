from functools import wraps
from flask import session, redirect, url_for, flash, render_template

# Definición de Roles del Sistema
ROLE_ADMIN = "ADMIN"          # Rector / Administrador
ROLE_COORDINADOR = "COORDINADOR" # Moderador / Coordinador
ROLE_DOCENTE = "DOCENTE"      # Usuario / Profesor / Administrativo

# Jerarquía y mapa de permisos
PERMISOS_POR_ROL = {
    ROLE_ADMIN: [
        "gestionar_usuarios",
        "ver_reportes_globales",
        "ver_graficas",
        "ver_asistencias",
        "gestionar_excusas",
        "registrar_asistencia"
    ],
    ROLE_COORDINADOR: [
        "ver_asistencias",
        "ver_alertas_tardanza",
        "gestionar_excusas",
        "ver_reportes_area"
    ],
    ROLE_DOCENTE: [
        "registrar_asistencia",
        "subir_excusa",
        "ver_asistencia_propia"
    ]
}

def login_requerido(f):
    """Decorador para asegurar que el usuario haya iniciado sesión."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Debes iniciar sesión para acceder a esta sección.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def requerir_roles(*roles_permitidos):
    """
    Decorador para restringir rutas a roles específicos.
    Ejemplo: @requerir_roles(ROLE_ADMIN, ROLE_COORDINADOR)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Por favor, inicia sesión.", "warning")
                return redirect(url_for('login'))
            
            rol_usuario = session.get('role')
            if rol_usuario not in roles_permitidos:
                flash("No tienes permisos suficientes para acceder a este módulo.", "danger")
                return redirect(url_for('dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requerir_permiso(permiso):
    """
    Decorador granular basado en la matriz de permisos.
    Ejemplo: @requerir_permiso('gestionar_usuarios')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Por favor, inicia sesión.", "warning")
                return redirect(url_for('login'))
                
            rol_usuario = session.get('role')
            permisos = PERMISOS_POR_ROL.get(rol_usuario, [])
            
            if permiso not in permisos:
                flash("Acceso denegado: Operación no autorizada para tu rol.", "danger")
                return redirect(url_for('dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

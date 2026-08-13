<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Asistencia QR - Control de Roles</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Estilo para ocultar elementos según permisos */
        .permiso-oculto { display: none !important; }
    </style>
</head>
<body class="p-8">

    <header class="bg-white p-6 rounded-lg shadow-md mb-6 flex justify-between items-center border-l-4 border-blue-500">
        <div>
            <h1 class="text-2xl font-bold text-gray-800">Sistema de Asistencia QR</h1>
            <p class="text-sm text-gray-500" id="infoUsuarioActual">Usuario actual: Cargando...</p>
        </div>
        <div class="bg-blue-50 p-3 rounded-md border border-blue-100">
            <label class="font-bold text-blue-800 text-sm mr-2">Simular vista como:</label>
            <select id="selectorRol" class="p-2 rounded border border-blue-300 bg-white" onchange="cambiarSesion()">
                <option value="rector">Rector (Administrador total - Puede crear cuentas)</option>
                <option value="coordinador">Coordinador (Moderador - Solo Iniciar Sesión)</option>
                <option value="docente">Docente (Usuario - Solo Iniciar Sesión)</option>
            </select>
        </div>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div class="space-y-6">
            
            <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-blue-600">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Acceso al Sistema</h3>
                
                <form onsubmit="event.preventDefault();" class="space-y-3">
                    <div>
                        <label class="block text-xs font-bold text-gray-600 uppercase mb-1">Correo Institucional</label>
                        <input type="email" placeholder="usuario@colegio.edu.co" class="w-full p-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-600 uppercase mb-1">Contraseña</label>
                        <input type="password" placeholder="••••••••" class="w-full p-2 border border-gray-300 rounded text-sm focus:outline-none focus:border-blue-500">
                    </div>
                    <button class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded text-sm transition">
                        🔑 Iniciar Sesión
                    </button>
                </form>

                <div data-permiso="CREAR_CUENTA_NUEVA" class="mt-4 pt-4 border-t border-gray-200">
                    <p class="text-xs text-amber-700 bg-amber-50 p-2 rounded mb-2 border border-amber-200 font-medium">
                        🛡️ Modulo restringido: Creación de usuarios
                    </p>
                    <button class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 rounded text-sm transition flex items-center justify-center gap-1">
                        ➕ Crear Nueva Cuenta de Usuario
                    </button>
                </div>
            </div>

            <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-green-500" data-permiso="VER_ASISTENCIA_PROPIA">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Mi Asistencia (Hoy)</h3>
                <div class="space-y-2 mb-4">
                    <p class="text-sm">Hora llegada: <span id="horaLlegada" class="font-bold text-gray-700">--:--</span></p>
                    <p class="text-sm">Hora salida: <span id="horaSalida" class="font-bold text-gray-700">--:--</span></p>
                    <p class="text-sm">Estado: <span id="estadoAsistencia" class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-bold">Sin registro</span></p>
                </div>
                <button data-permiso="REGISTRAR_ASISTENCIA_QR" class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded flex items-center justify-center gap-2">
                    📱 Escanear QR
                </button>
                <button data-permiso="VER_HISTORIAL_ASISTENCIA_PROPIA" class="w-full mt-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-2 px-4 rounded">
                    Ver mi historial
                </button>
            </div>

            <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-indigo-500" data-permiso="VER_REPORTES_DOCENTES">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Reportes de Asistencia</h3>
                <button data-permiso="GENERAR_REPORTE_ASISTENCIA" class="w-full bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-bold py-2 px-4 rounded mb-2">
                    📊 Generar Reporte
                </button>
                <button data-permiso="EXPORTAR_REPORTE_DOCENTES" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">
                    📥 Exportar Excel/PDF
                </button>
            </div>

            <section class="bg-gray-800 p-6 rounded-lg shadow-md text-white" data-permiso="ACCESO_ADMIN_PANEL">
                <h2 class="text-lg font-bold mb-4 flex items-center gap-2">⚙️ Panel Administrativo</h2>
                <div class="space-y-2">
                    <button data-permiso="GESTIONAR_USUARIOS" class="w-full bg-gray-700 hover:bg-gray-600 text-left py-2 px-4 rounded text-sm">
                        👥 Gestionar Usuarios
                    </button>
                    <button data-permiso="VER_ESTADISTICAS_GENERALES" class="w-full bg-gray-700 hover:bg-gray-600 text-left py-2 px-4 rounded text-sm">
                        📈 Estadísticas Generales
                    </button>
                </div>
            </section>
        </div>

        <div class="md:col-span-2 space-y-6">
            <div class="bg-white p-6 rounded-lg shadow-md" data-permiso="VER_ASISTENCIAS_DOCENTES">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-gray-800">Registros Generales de Asistencia</h3>
                    <span class="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">Hoy</span>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full bg-white">
                        <thead class="bg-gray-50 text-gray-600 text-sm uppercase font-semibold">
                            <tr>
                                <th class="py-3 px-4 text-left">Docente</th>
                                <th class="py-3 px-4 text-left">Rol</th>
                                <th class="py-3 px-4 text-left">Llegada</th>
                                <th class="py-3 px-4 text-left">Salida</th>
                                <th class="py-3 px-4 text-left">Estado</th>
                                <th class="py-3 px-4 text-center th-acciones">Acciones</th>
                            </tr>
                        </thead>
                        <tbody id="tablaAsistencias" class="text-sm divide-y divide-gray-100">
                            </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 1. MAPEO DE PERMISOS ACTUALIZADO
        const PERMISOS_POR_ROL = {
            rector: [
                'CREAR_CUENTA_NUEVA', // Permiso exclusivo del Rector
                'VER_TODAS_ASISTENCIAS_DOCENTES',
                'VER_ASISTENCIAS_DOCENTES',
                'VER_ASISTENCIA_RECTOR',
                'VER_REPORTES_DOCENTES',
                'EDITAR_REGISTRO_ASISTENCIA',
                'ELIMINAR_REGISTRO_ASISTENCIA',
                'EXPORTAR_REPORTES',
                'GENERAR_REPORTE_ASISTENCIA',
                'EXPORTAR_REPORTE_DOCENTES',
                'GESTIONAR_USUARIOS',
                'VER_ESTADISTICAS_GENERALES',
                'ACCESO_ADMIN_PANEL'
            ],
            coordinador: [
                'VER_ASISTENCIAS_DOCENTES',
                'VER_REPORTES_DOCENTES',
                'GENERAR_REPORTE_ASISTENCIA',
                'EXPORTAR_REPORTE_DOCENTES'
            ],
            docente: [
                'VER_ASISTENCIA_PROPIA',
                'REGISTRAR_ASISTENCIA_QR',
                'VER_HISTORIAL_ASISTENCIA_PROPIA'
            ]
        };

        // 2. BASE DE DATOS SIMULADA
        const dbAsistencias = [
            { id: 1, idDocente: 101, nombre: "Juan Pérez", rol: "docente", llegada: "06:50 AM", salida: "02:00 PM", estado: "Asistió completo" },
            { id: 2, idDocente: 102, nombre: "María Gómez", rol: "docente", llegada: "07:15 AM", salida: "--:--", estado: "Llegó tarde" },
            { id: 3, idDocente: 103, nombre: "Carlos Ruiz", rol: "docente", llegada: "--:--", salida: "--:--", estado: "Faltó" },
            { id: 4, idDocente: 201, nombre: "Laura Martínez", rol: "coordinador", llegada: "06:30 AM", salida: "03:00 PM", estado: "Asistió completo" },
            { id: 5, idDocente: 999, nombre: "Dr. Alfonso (Rector)", rol: "rector", llegada: "08:00 AM", salida: "12:00 PM", estado: "Asistió completo" }
        ];

        let sesionActual = {
            rol: 'rector',
            idUsuario: 999
        };

        // 3. VALIDACIÓN DE PERMISOS
        function tienePermiso(rolUsuario, permiso) {
            return PERMISOS_POR_ROL[rolUsuario]?.includes(permiso) || false;
        }

        // 4. CONTROL DE VISIBILIDAD HTML
        function aplicarPermisosVisibilidad() {
            document.querySelectorAll('[data-permiso]').forEach(elemento => {
                const permisoRequerido = elemento.getAttribute('data-permiso');
                
                if (tienePermiso(sesionActual.rol, permisoRequerido)) {
                    elemento.classList.remove('permiso-oculto');
                } else {
                    elemento.classList.add('permiso-oculto');
                }
            });

            // Visibilidad de columna de acciones en la tabla
            const thAcciones = document.querySelector('.th-acciones');
            if (thAcciones) {
                thAcciones.style.display = tienePermiso(sesionActual.rol, 'EDITAR_REGISTRO_ASISTENCIA') ? 'table-cell' : 'none';
            }
        }

        // 5. FILTRADO DE ASISTENCIAS
        function filtrarAsistencias(rolUsuario, asistencias, idDocenteActual) {
            if (rolUsuario === 'rector') {
                return asistencias;
            } else if (rolUsuario === 'coordinador') {
                return asistencias.filter(a => a.rol !== 'rector');
            } else if (rolUsuario === 'docente') {
                return asistencias.filter(a => a.idDocente === idDocenteActual);
            }
            return [];
        }

        // 6. RENDERIZADO EN PANTALLA
        function renderizarDatos() {
            const asistenciasFiltradas = filtrarAsistencias(sesionActual.rol, dbAsistencias, sesionActual.idUsuario);
            const tbody = document.getElementById('tablaAsistencias');
            tbody.innerHTML = '';

            asistenciasFiltradas.forEach(registro => {
                let badgeClass = registro.estado === 'Asistió completo' ? 'bg-green-100 text-green-800' : 
                                 registro.estado === 'Llegó tarde' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800';
                
                let fila = `<tr class="hover:bg-gray-50">
                    <td class="py-3 px-4 font-medium">${registro.nombre}</td>
                    <td class="py-3 px-4 text-gray-500 capitalize">${registro.rol}</td>
                    <td class="py-3 px-4">${registro.llegada}</td>
                    <td class="py-3 px-4">${registro.salida}</td>
                    <td class="py-3 px-4"><span class="px-2 py-1 rounded text-xs font-bold ${badgeClass}">${registro.estado}</span></td>`;
                
                if (tienePermiso(sesionActual.rol, 'EDITAR_REGISTRO_ASISTENCIA')) {
                    fila += `<td class="py-3 px-4 text-center">
                        <button class="text-blue-500 hover:text-blue-700 mr-2" title="Editar">✏️</button>
                        <button class="text-red-500 hover:text-red-700" title="Eliminar">🗑️</button>
                    </td>`;
                }
                
                fila += `</tr>`;
                tbody.innerHTML += fila;
            });

            if (sesionActual.rol === 'docente') {
                const miRegistro = asistenciasFiltradas[0];
                if (miRegistro) {
                    document.getElementById('horaLlegada').textContent = miRegistro.llegada;
                    document.getElementById('horaSalida').textContent = miRegistro.salida;
                    document.getElementById('estadoAsistencia').textContent = miRegistro.estado;
                }
            }
        }

        // CAMBIO DE SESIÓN (SIMULADOR)
        function cambiarSesion() {
            const selector = document.getElementById('selectorRol');
            const nuevoRol = selector.value;
            
            if (nuevoRol === 'rector') sesionActual = { rol: nuevoRol, idUsuario: 999 };
            if (nuevoRol === 'coordinador') sesionActual = { rol: nuevoRol, idUsuario: 201 };
            if (nuevoRol === 'docente') sesionActual = { rol: nuevoRol, idUsuario: 101 };

            document.getElementById('infoUsuarioActual').innerHTML = 
                `Usuario actual: <strong>${nuevoRol.toUpperCase()}</strong> (ID: ${sesionActual.idUsuario})`;

            aplicarPermisosVisibilidad();
            renderizarDatos();
        }

        window.addEventListener('DOMContentLoaded', () => {
            cambiarSesion();
        });
    </script>
</body>
</html>

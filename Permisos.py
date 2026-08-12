<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Asistencia QR - Control de Roles</title>
    <!-- Usamos Tailwind CSS para un diseño limpio y rápido -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Estilos base */
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; }
        .permiso-oculto { display: none !important; }
    </style>
</head>
<body class="p-8">

    <!-- CABECERA Y SIMULADOR DE ROLES (Solo para pruebas) -->
    <header class="bg-white p-6 rounded-lg shadow-md mb-6 flex justify-between items-center border-l-4 border-blue-500">
        <div>
            <h1 class="text-2xl font-bold text-gray-800">Sistema de Asistencia QR</h1>
            <p class="text-sm text-gray-500" id="infoUsuarioActual">Usuario actual: Cargando...</p>
        </div>
        <div class="bg-blue-50 p-3 rounded-md border border-blue-100">
            <label class="font-bold text-blue-800 text-sm mr-2">Simular vista como:</label>
            <select id="selectorRol" class="p-2 rounded border border-blue-300 bg-white" onchange="cambiarSesion()">
                <option value="admin">Administrador (Ve todo + Editar/Eliminar)</option>
                <option value="coordinador">Coordinador (Ve todos EXCEPTO Rector)</option>
                <option value="docente">Docente (Solo ve su propia asistencia)</option>
            </select>
        </div>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <!-- COLUMNA IZQUIERDA: Acciones Específicas del Rol -->
        <div class="space-y-6">
            
            <!-- PANEL DE DOCENTE -->
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

            <!-- PANEL DE REPORTES (ADMIN / COORDINADOR) -->
            <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-indigo-500" data-permiso="VER_REPORTES_DOCENTES">
                <h3 class="text-lg font-bold text-gray-800 mb-4">Reportes de Asistencia</h3>
                <button data-permiso="GENERAR_REPORTE_ASISTENCIA" class="w-full bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-bold py-2 px-4 rounded mb-2">
                    📊 Generar Reporte
                </button>
                <button data-permiso="EXPORTAR_REPORTE_DOCENTES" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">
                    📥 Exportar Excel/PDF
                </button>
            </div>

            <!-- PANEL ADMINISTRATIVO (SOLO ADMIN) -->
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

        <!-- COLUMNA DERECHA: Lista de Asistencias (Admin / Coordinador) -->
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
                                <!-- Esta columna se oculta por JS si no hay permisos de edición -->
                                <th class="py-3 px-4 text-center th-acciones">Acciones</th>
                            </tr>
                        </thead>
                        <tbody id="tablaAsistencias" class="text-sm divide-y divide-gray-100">
                            <!-- Filas generadas dinámicamente con JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
            
        </div>
    </div>

    <!-- ==========================================
         LÓGICA DE JAVASCRIPT Y CONTROL DE ROLES
         ========================================== -->
    <script>
        // 1. MAPEO DE PERMISOS DEFINIDO
        const PERMISOS_POR_ROL = {
            admin: [
                'VER_TODAS_ASISTENCIAS_DOCENTES',
                'VER_ASISTENCIAS_DOCENTES', // Agregado para ver la tabla
                'VER_ASISTENCIA_RECTOR',
                'VER_REPORTES_DOCENTES', // Agregado para ver sección reportes
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

        // 2. BASE DE DATOS SIMULADA (Mock Data)
        const dbAsistencias = [
            { id: 1, idDocente: 101, nombre: "Juan Pérez (Tú)", rol: "docente", llegada: "06:50 AM", salida: "02:00 PM", estado: "Asistió completo" },
            { id: 2, idDocente: 102, nombre: "María Gómez", rol: "docente", llegada: "07:15 AM", salida: "--:--", estado: "Llegó tarde" },
            { id: 3, idDocente: 103, nombre: "Carlos Ruiz", rol: "docente", llegada: "--:--", salida: "--:--", estado: "Faltó" },
            { id: 4, idDocente: 201, nombre: "Laura Martínez", rol: "coordinador", llegada: "06:30 AM", salida: "03:00 PM", estado: "Asistió completo" },
            { id: 5, idDocente: 999, nombre: "Dr. Alfonso (Rector)", rol: "rector", llegada: "08:00 AM", salida: "12:00 PM", estado: "Asistió completo" }
        ];

        // Variables de sesión actual
        let sesionActual = {
            rol: 'admin',
            idUsuario: 1 // Si es admin
        };

        // 3. FUNCIÓN DE VALIDACIÓN DE PERMISOS
        function tienePermiso(rolUsuario, permiso) {
            return PERMISOS_POR_ROL[rolUsuario]?.includes(permiso) || false;
        }

        // 4. CONTROL DE VISIBILIDAD EN HTML
        function aplicarPermisosVisibilidad() {
            document.querySelectorAll('[data-permiso]').forEach(elemento => {
                const permisoRequerido = elemento.getAttribute('data-permiso');
                
                if (tienePermiso(sesionActual.rol, permisoRequerido)) {
                    elemento.classList.remove('permiso-oculto');
                } else {
                    elemento.classList.add('permiso-oculto');
                }
            });

            // Manejo especial de la columna de acciones en la tabla
            const thAcciones = document.querySelector('.th-acciones');
            if (tienePermiso(sesionActual.rol, 'EDITAR_REGISTRO_ASISTENCIA')) {
                thAcciones.style.display = 'table-cell';
            } else {
                thAcciones.style.display = 'none';
            }
        }

        // 5. LÓGICA DE FILTRADO ESPECÍFICA
        function filtrarAsistencias(rolUsuario, asistencias, idDocenteActual) {
            if (rolUsuario === 'admin') {
                return asistencias; // El admin ve todo sin filtros
            } 
            else if (rolUsuario === 'coordinador') {
                // Coordinador ve todos EXCEPTO al rector
                return asistencias.filter(a => a.rol !== 'rector');
            } 
            else if (rolUsuario === 'docente') {
                // Docente solo se ve a sí mismo
                return asistencias.filter(a => a.idDocente === idDocenteActual);
            }
            return [];
        }

        // 6. RENDERIZAR DATOS EN PANTALLA
        function renderizarDatos() {
            // A. Filtrar asistencias según rol
            const asistenciasFiltradas = filtrarAsistencias(sesionActual.rol, dbAsistencias, sesionActual.idUsuario);
            
            // B. Poblar tabla (Para Admin y Coordinador)
            const tbody = document.getElementById('tablaAsistencias');
            tbody.innerHTML = ''; // Limpiar tabla
            
            asistenciasFiltradas.forEach(registro => {
                let badgeClass = registro.estado === 'Asistió completo' ? 'bg-green-100 text-green-800' : 
                                 registro.estado === 'Llegó tarde' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800';
                
                let fila = `<tr class="hover:bg-gray-50">
                    <td class="py-3 px-4 font-medium">${registro.nombre}</td>
                    <td class="py-3 px-4 text-gray-500 capitalize">${registro.rol}</td>
                    <td class="py-3 px-4">${registro.llegada}</td>
                    <td class="py-3 px-4">${registro.salida}</td>
                    <td class="py-3 px-4"><span class="px-2 py-1 rounded text-xs font-bold ${badgeClass}">${registro.estado}</span></td>`;
                
                // Botones de acción (solo si tiene permiso de editar/eliminar)
                if (tienePermiso(sesionActual.rol, 'EDITAR_REGISTRO_ASISTENCIA')) {
                    fila += `<td class="py-3 px-4 text-center">
                        <button class="text-blue-500 hover:text-blue-700 mr-2" title="Editar">✏️</button>
                        <button class="text-red-500 hover:text-red-700" title="Eliminar">🗑️</button>
                    </td>`;
                }
                
                fila += `</tr>`;
                tbody.innerHTML += fila;
            });

            // C. Poblar tarjeta personal (Para Docente)
            if (sesionActual.rol === 'docente') {
                const miRegistro = asistenciasFiltradas[0]; // Como filtramos por su ID, el registro 0 es el suyo
                if (miRegistro) {
                    document.getElementById('horaLlegada').textContent = miRegistro.llegada;
                    document.getElementById('horaSalida').textContent = miRegistro.salida;
                    document.getElementById('estadoAsistencia').textContent = miRegistro.estado;
                    document.getElementById('estadoAsistencia').className = miRegistro.estado === 'Asistió completo' 
                        ? 'px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-bold' 
                        : 'px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-bold';
                }
            }
        }

        // FUNCIONES DE UTILIDAD PARA EL SIMULADOR
        function cambiarSesion() {
            const selector = document.getElementById('selectorRol');
            const nuevoRol = selector.value;
            
            // Asignar ID ficticio dependiendo del rol para simular el inicio de sesión
            if (nuevoRol === 'admin') sesionActual = { rol: nuevoRol, idUsuario: 1 };
            if (nuevoRol === 'coordinador') sesionActual = { rol: nuevoRol, idUsuario: 201 };
            if (nuevoRol === 'docente') sesionActual = { rol: nuevoRol, idUsuario: 101 };

            document.getElementById('infoUsuarioActual').innerHTML = 
                `Usuario actual: <strong>${nuevoRol.toUpperCase()}</strong> (ID: ${sesionActual.idUsuario})`;

            // RE-EJECUTAR LÓGICA CORE AL CAMBIAR DE ROL
            aplicarPermisosVisibilidad();
            renderizarDatos();
        }

        // Ejecutar al cargar la página por primera vez
        window.addEventListener('DOMContentLoaded', () => {
            cambiarSesion(); // Inicializa con el rol seleccionado por defecto en el select
        });

    </script>
</body>
</html>

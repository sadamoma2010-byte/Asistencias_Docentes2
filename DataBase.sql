-- ═══════════════════════════════════════════════════════════════════════
--  Sistema Web de Asistencia Docente por Código QR
--  Estructura completa de la base de datos · PostgreSQL 14+
-- ═══════════════════════════════════════════════════════════════════════
--
--  Este archivo reconstruye la base de datos desde cero: tipos, tablas,
--  claves, restricciones, índices, vistas, funciones y datos iniciales.
--
--  Ejecución:
--    createdb -U postgres asistencia_qr
--    psql -U postgres -d asistencia_qr -f database.sql
--
--  Acceso inicial:  admin@datly.local  /  Admin123*
--
--  Generado el 2026-08-10 a partir de backend/prisma/schema.prisma
-- ═══════════════════════════════════════════════════════════════════════

BEGIN;

-- ─────────────────────────── RECREACIÓN ──────────────────────────────
-- Este script deja la base completamente limpia antes de crear el
-- esquema. Úselo sobre una base dedicada al sistema.
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- ─────────────────────────── Extensiones ──────────────────────────────
-- gen_random_uuid() para los identificadores; unaccent para búsquedas
-- que deban ignorar tildes.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ══════════════════ ESTRUCTURA (generada del esquema) ═════════════════

-- CreateEnum
CREATE TYPE "estado_registro" AS ENUM ('ACTIVO', 'INACTIVO');

-- CreateEnum
CREATE TYPE "tipo_asistencia" AS ENUM ('ENTRADA', 'SALIDA');

-- CreateEnum
CREATE TYPE "estado_asistencia" AS ENUM ('A_TIEMPO', 'TARDE', 'SALIDA_ANTICIPADA');

-- CreateEnum
CREATE TYPE "accion_auditoria" AS ENUM ('CREAR', 'ACTUALIZAR', 'ELIMINAR', 'ACTIVAR', 'DESACTIVAR', 'INICIO_SESION', 'CIERRE_SESION', 'ASISTENCIA');

-- CreateEnum
CREATE TYPE "tipo_configuracion" AS ENUM ('CADENA', 'NUMERO', 'BOOLEANO', 'JSON');

-- CreateTable
CREATE TABLE "usuarios" (
    "id" UUID NOT NULL,
    "nombre" VARCHAR(120) NOT NULL,
    "apellido" VARCHAR(120) NOT NULL,
    "documento" VARCHAR(40) NOT NULL,
    "correo" VARCHAR(180) NOT NULL,
    "telefono" VARCHAR(30),
    "contrasena" VARCHAR(255) NOT NULL,
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "rol_id" UUID NOT NULL,
    "ultimo_inicio_sesion" TIMESTAMPTZ(3),
    "intentos_inicio_fallidos" SMALLINT NOT NULL DEFAULT 0,
    "bloqueado_hasta" TIMESTAMPTZ(3),
    "debe_cambiar_contrasena" BOOLEAN NOT NULL DEFAULT false,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "usuarios_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tokens_actualizacion" (
    "id" UUID NOT NULL,
    "hash_token" VARCHAR(255) NOT NULL,
    "usuario_id" UUID NOT NULL,
    "expira_en" TIMESTAMPTZ(3) NOT NULL,
    "revocado_en" TIMESTAMPTZ(3),
    "direccion_ip" VARCHAR(60),
    "agente_usuario" VARCHAR(400),
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tokens_actualizacion_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "roles" (
    "id" UUID NOT NULL,
    "nombre" VARCHAR(60) NOT NULL,
    "descripcion" VARCHAR(300),
    "es_sistema" BOOLEAN NOT NULL DEFAULT false,
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "permisos" (
    "id" UUID NOT NULL,
    "codigo" VARCHAR(80) NOT NULL,
    "nombre" VARCHAR(120) NOT NULL,
    "modulo" VARCHAR(60) NOT NULL,
    "descripcion" VARCHAR(300),
    "es_sistema" BOOLEAN NOT NULL DEFAULT false,
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "permisos_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rol_permisos" (
    "rol_id" UUID NOT NULL,
    "permiso_id" UUID NOT NULL,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rol_permisos_pkey" PRIMARY KEY ("rol_id","permiso_id")
);

-- CreateTable
CREATE TABLE "docentes" (
    "id" UUID NOT NULL,
    "codigo" VARCHAR(40) NOT NULL,
    "nombre" VARCHAR(120) NOT NULL,
    "apellido" VARCHAR(120) NOT NULL,
    "documento" VARCHAR(40) NOT NULL,
    "correo" VARCHAR(200) NOT NULL,
    "telefono" VARCHAR(30),
    -- Ruta publica desde la que se sirve la fotografia
    "url_foto" VARCHAR(300),
    -- La fotografia se guarda aqui, no en el disco: asi viaja con el
    -- respaldo de la base y no quedan archivos huerfanos al eliminar.
    -- Se normaliza a WEBP de 512x512, unos 10 KB por docente.
    "foto" BYTEA,
    "tipo_mime_foto" VARCHAR(40),
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "usuario_id" UUID,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "docentes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "asignaturas" (
    "id" UUID NOT NULL,
    "codigo" VARCHAR(40) NOT NULL,
    "nombre" VARCHAR(120) NOT NULL,
    "descripcion" VARCHAR(300),
    "horas_semanales" SMALLINT,
    "color" VARCHAR(7) DEFAULT '#4F46E5',
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "asignaturas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "docente_asignaturas" (
    "docente_id" UUID NOT NULL,
    "asignatura_id" UUID NOT NULL,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "docente_asignaturas_pkey" PRIMARY KEY ("docente_id","asignatura_id")
);

-- CreateTable
CREATE TABLE "jornadas" (
    "id" UUID NOT NULL,
    "nombre" VARCHAR(80) NOT NULL,
    "descripcion" VARCHAR(300),
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "jornadas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "horarios" (
    "id" UUID NOT NULL,
    "docente_id" UUID NOT NULL,
    "jornada_id" UUID NOT NULL,
    "asignatura_id" UUID,
    "dia_semana" SMALLINT,
    "hora_entrada" VARCHAR(5) NOT NULL,
    "hora_salida" VARCHAR(5) NOT NULL,
    "minutos_tolerancia" SMALLINT NOT NULL DEFAULT 10,
    "estado" "estado_registro" NOT NULL DEFAULT 'ACTIVO',
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "horarios_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "asistencias" (
    "id" UUID NOT NULL,
    "docente_id" UUID NOT NULL,
    "horario_id" UUID,
    "tipo" "tipo_asistencia" NOT NULL,
    "estado" "estado_asistencia" NOT NULL,
    "fecha" DATE NOT NULL,
    "registrado_en" TIMESTAMPTZ(3) NOT NULL,
    "hora_esperada" VARCHAR(5),
    "diferencia_minutos" SMALLINT NOT NULL DEFAULT 0,
    "direccion_ip" VARCHAR(60),
    "agente_usuario" VARCHAR(400),
    "dispositivo" VARCHAR(120),
    "notas" VARCHAR(400),
    "registrado_por_id" UUID,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "asistencias_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "registros_auditoria" (
    "id" UUID NOT NULL,
    "usuario_id" UUID,
    "user_email" VARCHAR(180),
    "user_name" VARCHAR(240),
    "accion" "accion_auditoria" NOT NULL,
    "modulo" VARCHAR(80) NOT NULL,
    "id_entidad" UUID,
    "descripcion" VARCHAR(500),
    "direccion_ip" VARCHAR(60),
    "agente_usuario" VARCHAR(400),
    "dispositivo" VARCHAR(120),
    "metadatos" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,

    CONSTRAINT "registros_auditoria_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "registros_auditoria_usuario_id_idx" ON "registros_auditoria"("usuario_id");
CREATE INDEX "registros_auditoria_accion_idx" ON "registros_auditoria"("accion");
CREATE INDEX "registros_auditoria_modulo_idx" ON "registros_auditoria"("modulo");
CREATE INDEX "registros_auditoria_creado_en_idx" ON "registros_auditoria"("creado_en");

-- CreateTable
CREATE TABLE "configuraciones" (
    "id" UUID NOT NULL,
    "clave" VARCHAR(80) NOT NULL,
    "valor" TEXT NOT NULL,
    "tipo" "tipo_configuracion" NOT NULL DEFAULT 'CADENA',
    "grupo" VARCHAR(60) NOT NULL DEFAULT 'general',
    "etiqueta" VARCHAR(160) NOT NULL,
    "descripcion" VARCHAR(400),
    "es_publico" BOOLEAN NOT NULL DEFAULT false,
    "es_sistema" BOOLEAN NOT NULL DEFAULT false,
    "creado_en" TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMPTZ(3) NOT NULL,
    "eliminado_en" TIMESTAMPTZ(3),

    CONSTRAINT "configuraciones_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "usuarios_document_key" ON "usuarios"("documento");

-- CreateIndex
CREATE UNIQUE INDEX "usuarios_email_key" ON "usuarios"("correo");

-- CreateIndex
CREATE INDEX "usuarios_status_deleted_at_idx" ON "usuarios"("estado", "eliminado_en");

-- CreateIndex
CREATE INDEX "usuarios_role_id_idx" ON "usuarios"("rol_id");

-- CreateIndex
CREATE INDEX "usuarios_email_idx" ON "usuarios"("correo");

-- CreateIndex
CREATE INDEX "tokens_actualizacion_user_id_revoked_at_idx" ON "tokens_actualizacion"("usuario_id", "revocado_en");

-- CreateIndex
CREATE INDEX "tokens_actualizacion_expires_at_idx" ON "tokens_actualizacion"("expira_en");

-- CreateIndex
CREATE UNIQUE INDEX "roles_name_key" ON "roles"("nombre");

-- CreateIndex
CREATE INDEX "roles_status_deleted_at_idx" ON "roles"("estado", "eliminado_en");

-- CreateIndex
CREATE UNIQUE INDEX "permisos_code_key" ON "permisos"("codigo");

-- CreateIndex
CREATE INDEX "permisos_module_idx" ON "permisos"("modulo");

-- CreateIndex
CREATE INDEX "permisos_status_deleted_at_idx" ON "permisos"("estado", "eliminado_en");

-- CreateIndex
CREATE INDEX "rol_permisos_permission_id_idx" ON "rol_permisos"("permiso_id");

-- CreateIndex
CREATE UNIQUE INDEX "docentes_code_key" ON "docentes"("codigo");

-- CreateIndex
CREATE UNIQUE INDEX "docentes_document_key" ON "docentes"("documento");

-- CreateIndex
CREATE UNIQUE INDEX "docentes_email_key" ON "docentes"("correo");

-- CreateIndex
CREATE UNIQUE INDEX "docentes_user_id_key" ON "docentes"("usuario_id");

-- CreateIndex
CREATE INDEX "docentes_status_deleted_at_idx" ON "docentes"("estado", "eliminado_en");

-- CreateIndex
CREATE INDEX "docentes_code_idx" ON "docentes"("codigo");

-- CreateIndex
CREATE INDEX "docentes_last_name_first_name_idx" ON "docentes"("apellido", "nombre");

-- CreateIndex
CREATE UNIQUE INDEX "asignaturas_code_key" ON "asignaturas"("codigo");

-- CreateIndex
CREATE INDEX "asignaturas_status_deleted_at_idx" ON "asignaturas"("estado", "eliminado_en");

-- CreateIndex
CREATE INDEX "asignaturas_code_idx" ON "asignaturas"("codigo");

-- CreateIndex
CREATE INDEX "docente_asignaturas_subject_id_idx" ON "docente_asignaturas"("asignatura_id");

-- CreateIndex
CREATE UNIQUE INDEX "jornadas_name_key" ON "jornadas"("nombre");

-- CreateIndex
CREATE INDEX "jornadas_status_deleted_at_idx" ON "jornadas"("estado", "eliminado_en");

-- CreateIndex
CREATE INDEX "horarios_teacher_id_status_idx" ON "horarios"("docente_id", "estado");

-- CreateIndex
CREATE INDEX "horarios_teacher_id_day_of_week_idx" ON "horarios"("docente_id", "dia_semana");

-- CreateIndex
CREATE INDEX "horarios_shift_id_idx" ON "horarios"("jornada_id");

-- CreateIndex
CREATE INDEX "horarios_subject_id_idx" ON "horarios"("asignatura_id");

-- CreateIndex
CREATE INDEX "asistencias_teacher_id_date_idx" ON "asistencias"("docente_id", "fecha");

-- CreateIndex
CREATE INDEX "asistencias_date_type_idx" ON "asistencias"("fecha", "tipo");

-- CreateIndex
CREATE INDEX "asistencias_status_idx" ON "asistencias"("estado");

-- CreateIndex
CREATE INDEX "asistencias_schedule_id_idx" ON "asistencias"("horario_id");

-- CreateIndex
CREATE INDEX "asistencias_deleted_at_idx" ON "asistencias"("eliminado_en");

-- CreateIndex

-- CreateIndex

-- CreateIndex

-- CreateIndex

-- CreateIndex
CREATE UNIQUE INDEX "configuraciones_key_key" ON "configuraciones"("clave");

-- CreateIndex
CREATE INDEX "configuraciones_group_idx" ON "configuraciones"("grupo");

-- AddForeignKey
ALTER TABLE "usuarios" ADD CONSTRAINT "usuarios_role_id_fkey" FOREIGN KEY ("rol_id") REFERENCES "roles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tokens_actualizacion" ADD CONSTRAINT "tokens_actualizacion_user_id_fkey" FOREIGN KEY ("usuario_id") REFERENCES "usuarios"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rol_permisos" ADD CONSTRAINT "rol_permisos_role_id_fkey" FOREIGN KEY ("rol_id") REFERENCES "roles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rol_permisos" ADD CONSTRAINT "rol_permisos_permission_id_fkey" FOREIGN KEY ("permiso_id") REFERENCES "permisos"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "docentes" ADD CONSTRAINT "docentes_user_id_fkey" FOREIGN KEY ("usuario_id") REFERENCES "usuarios"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "docente_asignaturas" ADD CONSTRAINT "docente_asignaturas_teacher_id_fkey" FOREIGN KEY ("docente_id") REFERENCES "docentes"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "docente_asignaturas" ADD CONSTRAINT "docente_asignaturas_subject_id_fkey" FOREIGN KEY ("asignatura_id") REFERENCES "asignaturas"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_teacher_id_fkey" FOREIGN KEY ("docente_id") REFERENCES "docentes"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_shift_id_fkey" FOREIGN KEY ("jornada_id") REFERENCES "jornadas"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_subject_id_fkey" FOREIGN KEY ("asignatura_id") REFERENCES "asignaturas"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "asistencias" ADD CONSTRAINT "asistencias_teacher_id_fkey" FOREIGN KEY ("docente_id") REFERENCES "docentes"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "asistencias" ADD CONSTRAINT "asistencias_schedule_id_fkey" FOREIGN KEY ("horario_id") REFERENCES "horarios"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "registros_auditoria" ADD CONSTRAINT "registros_auditoria_usuario_id_fkey" FOREIGN KEY ("usuario_id") REFERENCES "usuarios"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- ═══════════════════ GENERACIÓN DE IDENTIFICADORES ════════════════════
-- La aplicación genera los UUID, pero al insertar directamente por SQL
-- conviene que la base también sepa hacerlo.

ALTER TABLE "usuarios" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "tokens_actualizacion" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "roles" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "permisos" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "docentes" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "asignaturas" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "jornadas" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "horarios" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "asistencias" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "configuraciones" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();
ALTER TABLE "registros_auditoria" ALTER COLUMN "id" SET DEFAULT gen_random_uuid();


-- ═════════════════════ RESTRICCIONES DE VALIDACIÓN ════════════════════
-- Las reglas viven también en la base: si algún día otro programa
-- escribe en estas tablas, los datos siguen siendo coherentes.

-- Formato HH:mm de 24 horas en los horarios
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_check_in_time_formato"
  CHECK ("hora_entrada" ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$');
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_check_out_time_formato"
  CHECK ("hora_salida" ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$');

-- La salida debe ser posterior a la entrada
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_salida_posterior"
  CHECK ("hora_salida" > "hora_entrada");

-- Día de la semana válido: 0 = domingo … 6 = sábado
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_dia_valido"
  CHECK ("dia_semana" IS NULL OR "dia_semana" BETWEEN 0 AND 6);

-- Tolerancia dentro de un rango razonable (RN007)
ALTER TABLE "horarios" ADD CONSTRAINT "horarios_tolerancia_valida"
  CHECK ("minutos_tolerancia" BETWEEN 0 AND 120);

-- Intensidad horaria semanal positiva
ALTER TABLE "asignaturas" ADD CONSTRAINT "asignaturas_horas_validas"
  CHECK ("horas_semanales" IS NULL OR "horas_semanales" BETWEEN 1 AND 60);

-- Color hexadecimal de la asignatura
ALTER TABLE "asignaturas" ADD CONSTRAINT "asignaturas_color_formato"
  CHECK ("color" IS NULL OR "color" ~ '^#[0-9A-Fa-f]{6}$');

-- Correos con formato mínimo verificable
ALTER TABLE "usuarios" ADD CONSTRAINT "usuarios_correo_formato"
  CHECK ("correo" ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$');
ALTER TABLE "docentes" ADD CONSTRAINT "docentes_correo_formato"
  CHECK ("correo" ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$');

-- Los intentos fallidos nunca son negativos
ALTER TABLE "usuarios" ADD CONSTRAINT "usuarios_intentos_no_negativos"
  CHECK ("intentos_inicio_fallidos" >= 0);

-- Hora esperada de la marcación, si se registró
ALTER TABLE "asistencias" ADD CONSTRAINT "asistencias_hora_esperada_formato"
  CHECK ("hora_esperada" IS NULL OR "hora_esperada" ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$');


-- ══════════════════════ ÍNDICES PARA SOFT DELETE ══════════════════════
-- Casi toda consulta del sistema filtra por "deleted_at IS NULL". Un
-- índice parcial solo cubre esas filas: ocupa menos y se recorre más
-- rápido que uno completo, porque los registros eliminados no entran.

CREATE INDEX "usuarios_vigentes_idx"       ON "usuarios" ("estado") WHERE "eliminado_en" IS NULL;
CREATE INDEX "docentes_vigentes_idx"    ON "docentes" ("estado") WHERE "eliminado_en" IS NULL;
CREATE INDEX "asignaturas_vigentes_idx"    ON "asignaturas" ("estado") WHERE "eliminado_en" IS NULL;
CREATE INDEX "jornadas_vigentes_idx"      ON "jornadas" ("estado") WHERE "eliminado_en" IS NULL;
CREATE INDEX "horarios_vigentes_idx"   ON "horarios" ("docente_id", "dia_semana") WHERE "eliminado_en" IS NULL;
CREATE INDEX "asistencias_vigentes_idx" ON "asistencias" ("docente_id", "fecha") WHERE "eliminado_en" IS NULL;

-- Búsqueda por texto en los listados, insensible a mayúsculas
CREATE INDEX "docentes_busqueda_idx" ON "docentes" (lower("apellido"), lower("nombre"));
CREATE INDEX "asignaturas_busqueda_idx" ON "asignaturas" (lower("nombre"));



-- ════════════════════════════════ VISTAS ══════════════════════════════

-- Marcaciones con los nombres ya resueltos: evita repetir los mismos
-- JOIN en cada informe.
CREATE OR REPLACE VIEW "v_asistencia_detallada" AS
SELECT
  a."id",
  a."docente_id" AS docente_id,
  a."fecha"                                        AS fecha,
  a."registrado_en"                               AS registrado_en,
  t."codigo"                                        AS codigo_docente,
  t."nombre" || ' ' || t."apellido"          AS docente,
  t."documento"                                    AS documento,
  s."nombre"                                        AS jornada,
  m."nombre"                                        AS asignatura,
  a."tipo"                                        AS tipo,
  a."estado"                                      AS estado,
  a."hora_esperada"                               AS hora_esperada,
  a."diferencia_minutos"                                AS diferencia_minutos,
  a."direccion_ip"                                  AS direccion_ip,
  a."dispositivo"                                      AS dispositivo
FROM "asistencias" a
  JOIN "docentes"  t ON t."id" = a."docente_id"
  LEFT JOIN "horarios" h ON h."id" = a."horario_id"
  LEFT JOIN "jornadas"    s ON s."id" = h."jornada_id"
  LEFT JOIN "asignaturas"  m ON m."id" = h."asignatura_id"
WHERE a."eliminado_en" IS NULL;

COMMENT ON VIEW "v_asistencia_detallada" IS
  'Marcaciones vigentes con docente, jornada y asignatura ya resueltos.';

-- Consolidado de puntualidad por docente, base de los reportes.
CREATE OR REPLACE VIEW "v_resumen_docente" AS
SELECT
  t."id"                                          AS docente_id,
  t."codigo"                                        AS codigo,
  t."nombre" || ' ' || t."apellido"          AS docente,
  COUNT(a."id")                                   AS total_marcaciones,
  COUNT(*) FILTER (WHERE a."tipo" = 'ENTRADA')   AS entradas,
  COUNT(*) FILTER (WHERE a."tipo" = 'SALIDA')  AS salidas,
  COUNT(*) FILTER (WHERE a."estado" = 'A_TIEMPO')  AS puntuales,
  COUNT(*) FILTER (WHERE a."estado" = 'TARDE')     AS tardanzas,
  COALESCE(SUM(a."diferencia_minutos") FILTER (WHERE a."estado" = 'TARDE'), 0) AS minutos_retraso,
  CASE WHEN COUNT(a."id") = 0 THEN 100
       ELSE ROUND(COUNT(*) FILTER (WHERE a."estado" = 'A_TIEMPO') * 100.0 / COUNT(a."id"))
  END                                             AS porcentaje_puntualidad
FROM "docentes" t
  LEFT JOIN "asistencias" a ON a."docente_id" = t."id" AND a."eliminado_en" IS NULL
WHERE t."eliminado_en" IS NULL
GROUP BY t."id", t."codigo", t."nombre", t."apellido";

COMMENT ON VIEW "v_resumen_docente" IS
  'Totales de asistencia y porcentaje de puntualidad por docente.';


-- ═══════════════════════════════ FUNCIONES ════════════════════════════

-- Evalúa la puntualidad de una entrada (RN007 y RN008). La aplicación
-- aplica la misma regla; tenerla aquí permite recalcular o auditar
-- marcaciones directamente desde SQL.
CREATE OR REPLACE FUNCTION fn_evaluar_puntualidad(
  p_hora_real      VARCHAR(5),
  p_hora_esperada  VARCHAR(5),
  p_tolerancia     SMALLINT
) RETURNS "estado_asistencia" AS $$
DECLARE
  v_diferencia INTEGER;
BEGIN
  v_diferencia :=
    (split_part(p_hora_real, ':', 1)::INT * 60 + split_part(p_hora_real, ':', 2)::INT) -
    (split_part(p_hora_esperada, ':', 1)::INT * 60 + split_part(p_hora_esperada, ':', 2)::INT);

  IF v_diferencia > p_tolerancia THEN
    RETURN 'TARDE';
  END IF;

  RETURN 'A_TIEMPO';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION fn_evaluar_puntualidad IS
  'Devuelve LATE si se supera la tolerancia, ON_TIME en caso contrario (RN007/RN008).';

-- Diferencia en minutos entre dos horas HH:mm. Positivo = más tarde.
CREATE OR REPLACE FUNCTION fn_diferencia_minutos(
  p_hora_a VARCHAR(5),
  p_hora_b VARCHAR(5)
) RETURNS INTEGER AS $$
BEGIN
  RETURN
    (split_part(p_hora_a, ':', 1)::INT * 60 + split_part(p_hora_a, ':', 2)::INT) -
    (split_part(p_hora_b, ':', 1)::INT * 60 + split_part(p_hora_b, ':', 2)::INT);
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ═════════════════════ DOCUMENTACIÓN DE LAS TABLAS ════════════════════

COMMENT ON TABLE "usuarios" IS 'Cuentas de acceso al sistema. La contraseña se guarda como hash bcrypt.';
COMMENT ON TABLE "tokens_actualizacion" IS 'Tokens de renovación de sesión, hasheados y con rotación en cada uso.';
COMMENT ON TABLE "roles" IS 'Perfiles de acceso. Los marcados como del sistema no pueden eliminarse.';
COMMENT ON TABLE "permisos" IS 'Catálogo de capacidades granulares con formato modulo.accion.';
COMMENT ON TABLE "rol_permisos" IS 'Tabla puente que asigna permisos a cada rol.';
COMMENT ON TABLE "docentes" IS 'Personal docente sujeto al control de asistencia.';
COMMENT ON TABLE "asignaturas" IS 'Asignaturas que se imparten en la institución.';
COMMENT ON TABLE "docente_asignaturas" IS 'Asignaturas que dicta cada docente (muchos a muchos).';
COMMENT ON TABLE "jornadas" IS 'Jornadas institucionales sobre las que se arman los horarios.';
COMMENT ON TABLE "horarios" IS 'Franja horaria de un docente. Contra ella se mide la puntualidad.';
COMMENT ON TABLE "asistencias" IS 'Marcaciones de entrada y salida. Es la evidencia del sistema.';
COMMENT ON TABLE "configuraciones" IS 'Parámetros del sistema editables sin desplegar código.';
COMMENT ON TABLE "registros_auditoria" IS 'Registro de acciones importantes realizadas por los usuarios.';


-- ═══════════════════════════ DATOS INICIALES ══════════════════════════
-- Mínimo imprescindible para que el sistema arranque y se pueda entrar.

-- ── Permisos ──
INSERT INTO "permisos" ("id", "codigo", "nombre", "modulo", "es_sistema", "estado", "creado_en", "actualizado_en") VALUES
  (gen_random_uuid(), 'usuarios.consultar', 'Consultar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.crear', 'Crear usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.editar', 'Editar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.eliminar', 'Eliminar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.activar', 'Activar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.inactivar', 'Inactivar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.exportar', 'Exportar usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'usuarios.restablecer-contrasena', 'Restablecer contraseña usuarios', 'Usuarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.consultar', 'Consultar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.crear', 'Crear roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.editar', 'Editar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.eliminar', 'Eliminar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.activar', 'Activar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.inactivar', 'Inactivar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'roles.exportar', 'Exportar roles', 'Roles', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.consultar', 'Consultar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.crear', 'Crear permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.editar', 'Editar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.eliminar', 'Eliminar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.activar', 'Activar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.inactivar', 'Inactivar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'permisos.exportar', 'Exportar permisos', 'Permisos', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.consultar', 'Consultar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.crear', 'Crear docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.editar', 'Editar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.eliminar', 'Eliminar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.activar', 'Activar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.inactivar', 'Inactivar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'docentes.exportar', 'Exportar docentes', 'Docentes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.consultar', 'Consultar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.crear', 'Crear asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.editar', 'Editar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.eliminar', 'Eliminar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.activar', 'Activar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.inactivar', 'Inactivar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asignaturas.exportar', 'Exportar asignaturas', 'Asignaturas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.consultar', 'Consultar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.crear', 'Crear jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.editar', 'Editar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.eliminar', 'Eliminar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.activar', 'Activar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.inactivar', 'Inactivar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'jornadas.exportar', 'Exportar jornadas', 'Jornadas', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.consultar', 'Consultar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.crear', 'Crear horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.editar', 'Editar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.eliminar', 'Eliminar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.activar', 'Activar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.inactivar', 'Inactivar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'horarios.exportar', 'Exportar horarios', 'Horarios', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asistencia.consultar', 'Consultar asistencia', 'Asistencia', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asistencia.crear', 'Crear asistencia', 'Asistencia', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asistencia.exportar', 'Exportar asistencia', 'Asistencia', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asistencia.propia', 'Registrar propia asistencia asistencia', 'Asistencia', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'asistencia.eliminar', 'Eliminar asistencia', 'Asistencia', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'reportes.consultar', 'Consultar reportes', 'Reportes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'reportes.exportar', 'Exportar reportes', 'Reportes', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'configuracion.consultar', 'Consultar configuración', 'Configuración', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'configuracion.editar', 'Editar configuración', 'Configuración', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'panel.consultar', 'Consultar dashboard', 'Panel', TRUE, 'ACTIVO', NOW(), NOW());

-- ── Roles ──
INSERT INTO "roles" ("id", "nombre", "descripcion", "es_sistema", "estado", "creado_en", "actualizado_en") VALUES
  (gen_random_uuid(), 'SUPER_ADMIN', 'Control total del sistema. Acceso irrestricto a todos los módulos.', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'ADMINISTRADOR', 'Gestión operativa completa. No administra el catálogo de permisos.', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'COORDINADOR', 'Supervisa docentes, horarios, asistencia y reportes. Sin gestión de usuarios.', TRUE, 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'DOCENTE', 'Registra su propia entrada y salida y consulta su historial.', TRUE, 'ACTIVO', NOW(), NOW());

-- ── Asignación de permisos a cada rol ──
-- SUPER_ADMIN: todos los permisos activos.
INSERT INTO "rol_permisos" ("rol_id", "permiso_id", "creado_en")
SELECT r."id", p."id", NOW()
FROM "roles" r CROSS JOIN "permisos" p
WHERE r."nombre" = 'SUPER_ADMIN';

-- ADMINISTRADOR: gestión operativa completa; no administra el catálogo
-- de permisos. Tampoco puede eliminar/inactivar roles del sistema.
INSERT INTO "rol_permisos" ("rol_id", "permiso_id", "creado_en")
SELECT r."id", p."id", NOW()
FROM "roles" r CROSS JOIN "permisos" p
WHERE r."nombre" = 'ADMINISTRADOR'
  AND p."codigo" NOT LIKE 'permisos.%'
  AND p."codigo" NOT IN ('roles.eliminar', 'roles.inactivar');

-- COORDINADOR: supervisa docentes, horarios, asistencia y reportes,
-- además de consultar asignaturas/jornadas y el panel.
INSERT INTO "rol_permisos" ("rol_id", "permiso_id", "creado_en")
SELECT r."id", p."id", NOW()
FROM "roles" r CROSS JOIN "permisos" p
WHERE r."nombre" = 'COORDINADOR'
  AND p."codigo" IN (
    'panel.consultar',
    'docentes.consultar', 'docentes.crear', 'docentes.editar',
    'docentes.activar', 'docentes.inactivar', 'docentes.exportar',
    'asignaturas.consultar',
    'jornadas.consultar',
    'horarios.consultar', 'horarios.crear', 'horarios.editar',
    'horarios.exportar',
    'asistencia.consultar', 'asistencia.crear', 'asistencia.exportar',
    'reportes.consultar', 'reportes.exportar'
  );

-- DOCENTE: únicamente registra su propia asistencia.
INSERT INTO "rol_permisos" ("rol_id", "permiso_id", "creado_en")
SELECT r."id", p."id", NOW()
FROM "roles" r CROSS JOIN "permisos" p
WHERE r."nombre" = 'DOCENTE'
  AND p."codigo" = 'asistencia.propia';

-- ── Usuario inicial (SUPER_ADMIN) ──
-- Contraseña: Admin123*  — cámbiela tras el primer ingreso.
INSERT INTO "usuarios" ("id", "nombre", "apellido", "documento", "correo", "contrasena", "estado", "rol_id", "creado_en", "actualizado_en")
SELECT gen_random_uuid(), 'Super', 'Admin', '1000000000', 'admin@datly.local', '$2b$12$9D8cDSxvVcEgUOrcXAyJT.i0wzWfLRpnOZaUfG/01UdgYMwCPv/Fm', 'ACTIVO', r."id", NOW(), NOW()
FROM "roles" r WHERE r."nombre" = 'SUPER_ADMIN';

-- ── Configuración ──
INSERT INTO "configuraciones" ("id", "clave", "valor", "tipo", "grupo", "etiqueta", "descripcion", "es_publico", "es_sistema", "creado_en", "actualizado_en") VALUES
  (gen_random_uuid(), 'qr.public_url', 'http://localhost:3000/marcar', 'CADENA'::"tipo_configuracion", 'qr', 'URL pública del QR institucional', 'Destino al que apunta el código QR único de la institución.', TRUE, FALSE, NOW(), NOW()),
  (gen_random_uuid(), 'qr.institution_name', 'Institución Educativa', 'CADENA'::"tipo_configuracion", 'qr', 'Nombre institucional', 'Se muestra bajo el código QR al descargarlo.', TRUE, FALSE, NOW(), NOW()),
  (gen_random_uuid(), 'attendance.default_tolerance_minutes', '10', 'NUMERO'::"tipo_configuracion", 'attendance', 'Tolerancia por defecto (minutos)', 'Se aplica a los horarios que no definen una tolerancia propia.', FALSE, FALSE, NOW(), NOW()),
  (gen_random_uuid(), 'attendance.window_minutes', '180', 'NUMERO'::"tipo_configuracion", 'attendance', 'Ventana de marcación (minutos)', 'Margen máximo respecto a la hora del horario para aceptar una marcación.', FALSE, FALSE, NOW(), NOW()),
  (gen_random_uuid(), 'app.timezone', 'America/Bogota', 'CADENA'::"tipo_configuracion", 'general', 'Zona horaria institucional', 'Determina el cálculo de puntualidad y el corte de día.', TRUE, TRUE, NOW(), NOW()),
  (gen_random_uuid(), 'app.institution_short_name', 'Asistencia Docente', 'CADENA'::"tipo_configuracion", 'general', 'Nombre corto institucional', 'Se muestra en la cabecera de la aplicación.', TRUE, FALSE, NOW(), NOW());

-- ── Jornadas ──
INSERT INTO "jornadas" ("id", "nombre", "descripcion", "estado", "creado_en", "actualizado_en") VALUES
  (gen_random_uuid(), 'Mañana', 'Jornada de la mañana', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'Tarde', 'Jornada de la tarde', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'Noche', 'Jornada nocturna', 'ACTIVO', NOW(), NOW());

-- ── Asignaturas de ejemplo ──
INSERT INTO "asignaturas" ("id", "codigo", "nombre", "horas_semanales", "color", "estado", "creado_en", "actualizado_en") VALUES
  (gen_random_uuid(), 'MAT-101', 'Matemáticas', 6, '#4F46E5', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'LEN-201', 'Lengua Castellana', 5, '#0EA5E9', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'CNA-110', 'Ciencias Naturales', 4, '#10B981', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'SOC-120', 'Ciencias Sociales', 4, '#F59E0B', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'TEC-305', 'Tecnología e Informática', 3, '#8B5CF6', 'ACTIVO', NOW(), NOW()),
  (gen_random_uuid(), 'EFI-140', 'Educación Física', 2, '#EF4444', 'ACTIVO', NOW(), NOW());

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════
--  Comprobación rápida tras la ejecución:
--
--    SELECT COUNT(*) FROM "permisos";    -- esperado: 60
--    SELECT COUNT(*) FROM "roles";       -- esperado: 4
--    SELECT COUNT(*) FROM "usuarios";    -- esperado: 1
--    SELECT COUNT(*) FROM "jornadas";    -- esperado: 3
--    SELECT COUNT(*) FROM "asignaturas"; -- esperado: 6
--    SELECT r."nombre", COUNT(rp."permiso_id")
--    FROM "roles" r LEFT JOIN "rol_permisos" rp ON rp."rol_id"=r."id"
--    GROUP BY r."nombre" ORDER BY r."nombre";
-- ═══════════════════════════════════════════════════════════════════════

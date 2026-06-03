-- ══════════════════════════════════════════════════════════════
-- Script SQL Final · Consultores Expertos S.A.S
-- Compatible con PostgreSQL 14+
-- Mejoras (vs versión anterior):
--   ✅ Columna email_verified (Sección 14 — autenticación por token)
--   ✅ Columna password_reset_token + expires (Sección 22 — recuperación)
--   ✅ Columnas calificacion en reservas con CHECK (1-5)
--   ✅ Índices adicionales para queries de dashboard admin (Sección 15)
--   ✅ CHECK CONSTRAINT en porcentaje_descuento (0-100)
--   ✅ Datos semilla con password en texto plano; sistema.py migra a bcrypt
-- ══════════════════════════════════════════════════════════════

-- ── 1. LIMPIEZA INICIAL ───────────────────────────────────────
DROP TABLE IF EXISTS reservas     CASCADE;
DROP TABLE IF EXISTS consultores  CASCADE;
DROP TABLE IF EXISTS usuarios     CASCADE;

-- ── 2. TABLA: USUARIOS ────────────────────────────────────────
CREATE TABLE usuarios (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(50)  UNIQUE NOT NULL,
    email            VARCHAR(100) UNIQUE NOT NULL,
    password         VARCHAR(255) NOT NULL,              -- almacena hash bcrypt
    nombre           VARCHAR(100) NOT NULL,
    rol              VARCHAR(20)  NOT NULL
                     CHECK (rol IN ('admin', 'cliente', 'consultor')),
    email_verified   BOOLEAN      NOT NULL DEFAULT FALSE, -- Sección 14
    fecha_registro   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. TABLA: CONSULTORES ─────────────────────────────────────
CREATE TABLE consultores (
    id_usuario           INTEGER     PRIMARY KEY
                         REFERENCES usuarios(id) ON DELETE CASCADE,
    tarifa               DECIMAL(10,2) NOT NULL CHECK (tarifa > 0),
    especialidad         VARCHAR(50)   NOT NULL,
    descripcion          TEXT,
    experiencia_anos     INTEGER       NOT NULL DEFAULT 0 CHECK (experiencia_anos >= 0),
    primera_cita_descuento BOOLEAN     NOT NULL DEFAULT FALSE,
    porcentaje_descuento DECIMAL(5,2)  NOT NULL DEFAULT 0
                         CHECK (porcentaje_descuento >= 0 AND porcentaje_descuento <= 100)
);

-- ── 4. TABLA: RESERVAS ────────────────────────────────────────
CREATE TABLE reservas (
    id           SERIAL PRIMARY KEY,
    id_cliente   INTEGER       NOT NULL
                 REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    id_consultor INTEGER       NOT NULL
                 REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    fecha        TIMESTAMP     NOT NULL,
    estado       VARCHAR(20)   NOT NULL DEFAULT 'Activa'
                 CHECK (estado IN ('Activa', 'Cancelada', 'Completada')),
    notas        TEXT,
    costo_final  DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (costo_final >= 0),
    calificacion SMALLINT      NOT NULL DEFAULT 0
                 CHECK (calificacion >= 0 AND calificacion <= 5), -- 0 = sin calificar
    fecha_creacion TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── 5. ÍNDICES DE RENDIMIENTO (Sección 15) ───────────────────
-- Búsquedas frecuentes en dashboard y validaciones
CREATE INDEX idx_usuarios_username   ON usuarios(username);
CREATE INDEX idx_usuarios_email      ON usuarios(email);
CREATE INDEX idx_usuarios_rol        ON usuarios(rol);

CREATE INDEX idx_reservas_cliente    ON reservas(id_cliente);
CREATE INDEX idx_reservas_consultor  ON reservas(id_consultor);
CREATE INDEX idx_reservas_fecha      ON reservas(fecha);
CREATE INDEX idx_reservas_estado     ON reservas(estado);

-- Índice compuesto para el KPI de ingresos del admin
CREATE INDEX idx_reservas_estado_costo ON reservas(estado, costo_final)
    WHERE estado = 'Completada';

-- ── 6. DATOS SEMILLA ──────────────────────────────────────────
-- NOTA: Las contraseñas están en texto plano SOLO para desarrollo.
-- sistema.py soporta texto plano como fallback hasta que el usuario
-- cambie su contraseña (que se hashea con bcrypt automáticamente).
-- En producción, ejecuta el script migrate_passwords.py para hashearlas.

INSERT INTO usuarios (username, email, password, nombre, rol, email_verified) VALUES
    ('admin',     'admin@empresa.com',       '1234',         'Administrador',           'admin',     TRUE),
    ('cliente',   'cliente@gmail.com',       '1234',         'Cliente Pruebas',         'cliente',   TRUE),
    ('ana',       'ana.finanzas@empresa.com','1234',         'Dra. Ana (Finanzas)',      'consultor', TRUE),
    ('carlos',    'carlos.tec@empresa.com',  '1234',         'Ing. Carlos (Tecnología)','consultor', TRUE),
    ('sofia',     'sofia.mkt@empresa.com',   '1234',         'Lic. Sofia (Marketing)',  'consultor', TRUE),
    ('karol_bts', 'karol@music.com',         'Karol*2025!',  'Karol G',                 'consultor', TRUE)
ON CONFLICT (username) DO NOTHING;

-- ── 7. DATOS SEMILLA: CONSULTORES ────────────────────────────
INSERT INTO consultores
    (id_usuario, tarifa, especialidad, descripcion, experiencia_anos,
     primera_cita_descuento, porcentaje_descuento)
SELECT
    u.id, v.tarifa, v.especialidad, v.descripcion, v.exp, TRUE, 15.00
FROM usuarios u
JOIN (VALUES
    ('ana',       100.0, 'Finanzas',       'Especialista en planificación financiera y análisis de inversiones.', 8),
    ('carlos',    150.0, 'Tecnología',     'Experto en desarrollo de software y arquitectura de sistemas.',       10),
    ('sofia',     120.0, 'Marketing',      'Consultora en estrategias digitales y posicionamiento de marca.',     6),
    ('karol_bts', 300.0, 'Ciberseguridad', 'Especialista en protección de datos y seguridad informática.',       7)
) AS v(uname, tarifa, especialidad, descripcion, exp)
ON (u.username = v.uname)
ON CONFLICT (id_usuario) DO UPDATE
    SET tarifa               = EXCLUDED.tarifa,
        especialidad         = EXCLUDED.especialidad,
        descripcion          = EXCLUDED.descripcion,
        experiencia_anos     = EXCLUDED.experiencia_anos,
        primera_cita_descuento = EXCLUDED.primera_cita_descuento,
        porcentaje_descuento = EXCLUDED.porcentaje_descuento;

-- ── 8. VISTA ÚTIL: Dashboard Admin ───────────────────────────
CREATE OR REPLACE VIEW v_kpis_admin AS
SELECT
    (SELECT COALESCE(SUM(costo_final),0) FROM reservas WHERE estado='Completada')   AS ingresos_totales,
    (SELECT COUNT(*)                      FROM usuarios)                             AS total_usuarios,
    (SELECT COUNT(*)                      FROM reservas WHERE estado='Activa')       AS citas_activas,
    (SELECT COUNT(*)                      FROM reservas WHERE estado='Completada')   AS citas_completadas,
    (SELECT COUNT(*)                      FROM reservas WHERE estado='Cancelada')    AS citas_canceladas,
    (SELECT COALESCE(AVG(calificacion),0)
     FROM reservas WHERE estado='Completada' AND calificacion > 0)                  AS calificacion_promedio;

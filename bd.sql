-- Script SQL Final Corregido - Consultores Expertos S.A.S
-- Compatible con PostgreSQL

-- 1. LIMPIEZA INICIAL (Opcional, para reiniciar todo limpio si quieres)
-- DROP TABLE IF EXISTS reservas;
-- DROP TABLE IF EXISTS consultores;
-- DROP TABLE IF EXISTS usuarios;

-- 2. CREACIÓN DE TABLAS

-- Tabla: USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'cliente', 'consultor')),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: CONSULTORES (Información extra solo para los expertos)
CREATE TABLE IF NOT EXISTS consultores (
    id_usuario INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    tarifa DECIMAL(10, 2) NOT NULL CHECK (tarifa > 0),
    especialidad VARCHAR(50) NOT NULL
);

-- Tabla: RESERVAS (Citas)
CREATE TABLE IF NOT EXISTS reservas (
    id SERIAL PRIMARY KEY,
    id_cliente INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    id_consultor INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    fecha TIMESTAMP NOT NULL, 
    estado VARCHAR(20) NOT NULL DEFAULT 'Activa' CHECK (estado IN ('Activa', 'Cancelada', 'Completada')),
    notas TEXT -- Agregado directamente aquí
);

-- 3. ÍNDICES (Para que la web vuele)
CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
CREATE INDEX IF NOT EXISTS idx_reservas_fecha ON reservas(fecha);

-- 4. DATOS SEMILLA (Usuarios Base)

INSERT INTO usuarios (username, email, password, nombre, rol) VALUES
    ('admin', 'admin@empresa.com', '1234', 'Administrador', 'admin'),
    ('cliente', 'cliente@gmail.com', '1234', 'Cliente Pruebas', 'cliente'),
    ('ana', 'ana.finanzas@empresa.com', '1234', 'Dra. Ana (Finanzas)', 'consultor'),
    ('carlos', 'carlos.tec@empresa.com', '1234', 'Ing. Carlos (Tecnología)', 'consultor'),
    ('sofia', 'sofia.mkt@empresa.com', '1234', 'Lic. Sofia (Marketing)', 'consultor'),
    ('karol_bts', 'karol@music.com', '1234', 'Karol G', 'cliente') -- La creamos como cliente primero
ON CONFLICT (username) DO NOTHING;

-- 5. RELACIONAR CONSULTORES (Llenar la tabla 'consultores')

-- Insertamos datos de Ana
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 100.0, 'Finanzas' FROM usuarios WHERE username = 'ana'
ON CONFLICT (id_usuario) DO NOTHING;

-- Insertamos datos de Carlos
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 150.0, 'Tecnología' FROM usuarios WHERE username = 'carlos'
ON CONFLICT (id_usuario) DO NOTHING;

-- Insertamos datos de Sofia
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 120.0, 'Marketing' FROM usuarios WHERE username = 'sofia'
ON CONFLICT (id_usuario) DO NOTHING;


-- =========================================================================
--  CORRECCIÓN IMPORTANTE: EL CASO DE KAROL_BTS
-- =========================================================================
-- No se puede hacer un solo UPDATE porque los datos están en dos tablas diferentes.
-- Aquí tienes la forma correcta de convertirla en Consultora:

-- PASO 1: Actualizar su Rol en la tabla principal
UPDATE usuarios 
SET rol = 'consultor' 
WHERE username = 'karol_bts'; -- Ojo: la columna es 'username', no 'usuario'

-- PASO 2: Insertar sus detalles en la tabla secundaria
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 300.0, 'Ciberseguridad' 
FROM usuarios 
WHERE username = 'karol_bts'
ON CONFLICT (id_usuario) 
DO UPDATE SET tarifa = 300.0, especialidad = 'Ciberseguridad'; -- Si ya existe, actualiza


ALTER TABLE reservas DROP CONSTRAINT IF EXISTS reservas_fecha_check;

-- 1. Agregamos columna para saber cuánto costó realmente (con descuento)
ALTER TABLE reservas ADD COLUMN costo_final DECIMAL(10, 2) DEFAULT 0;

-- 2. Agregamos columna para que el cliente califique (1 a 5)
ALTER TABLE reservas ADD COLUMN calificacion INTEGER DEFAULT 0;
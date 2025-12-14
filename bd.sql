-- Script SQL Final Unificado - Consultores Expertos S.A.S
-- Compatible con PostgreSQL y Python

-- 1. LIMPIEZA INICIAL (Para asegurar que creamos todo con la nueva estructura)
DROP TABLE IF EXISTS reservas CASCADE;
DROP TABLE IF EXISTS consultores CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- 2. CREACIÓN DE TABLAS (Ya con TODAS las columnas fusionadas)

-- Tabla: USUARIOS
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'cliente', 'consultor')),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: CONSULTORES (Estructura Tuya + Estructura de tu Compañero)
CREATE TABLE consultores (
    id_usuario INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    tarifa DECIMAL(10, 2) NOT NULL CHECK (tarifa > 0),
    especialidad VARCHAR(50) NOT NULL,
    
    -- Agregados de tu compañero (definidos desde el inicio):
    descripcion TEXT,
    experiencia_anos INTEGER DEFAULT 0, -- Sin 'ñ' para Python
    primera_cita_descuento BOOLEAN DEFAULT FALSE,
    porcentaje_descuento DECIMAL(5,2) DEFAULT 0
);

-- Tabla: RESERVAS (Con tus mejoras financieras)
CREATE TABLE reservas (
    id SERIAL PRIMARY KEY,
    id_cliente INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    id_consultor INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    fecha TIMESTAMP NOT NULL, 
    estado VARCHAR(20) NOT NULL DEFAULT 'Activa' CHECK (estado IN ('Activa', 'Cancelada', 'Completada')),
    notas TEXT,
    
    -- Tus columnas financieras y de feedback:
    costo_final DECIMAL(10, 2) DEFAULT 0,
    calificacion INTEGER DEFAULT 0
);

-- 3. ÍNDICES DE RENDIMIENTO
CREATE INDEX idx_usuarios_username ON usuarios(username);
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_reservas_fecha ON reservas(fecha);

-- 4. DATOS SEMILLA (Usuarios Base)

INSERT INTO usuarios (username, email, password, nombre, rol) VALUES
    ('admin', 'admin@empresa.com', '1234', 'Administrador', 'admin'),
    ('cliente', 'cliente@gmail.com', '1234', 'Cliente Pruebas', 'cliente'),
    ('ana', 'ana.finanzas@empresa.com', '1234', 'Dra. Ana (Finanzas)', 'consultor'),
    ('carlos', 'carlos.tec@empresa.com', '1234', 'Ing. Carlos (Tecnología)', 'consultor'),
    ('sofia', 'sofia.mkt@empresa.com', '1234', 'Lic. Sofia (Marketing)', 'consultor'),
    ('karol_bts', 'karol@music.com', '1234', 'Karol G', 'cliente') 
ON CONFLICT (username) DO NOTHING;

-- 5. RELACIONAR CONSULTORES INICIALES
-- Nota: Como pusimos DEFAULT 0 en las columnas nuevas, no fallará al insertar solo lo básico.

INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 100.0, 'Finanzas' FROM usuarios WHERE username = 'ana'
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 150.0, 'Tecnología' FROM usuarios WHERE username = 'carlos'
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 120.0, 'Marketing' FROM usuarios WHERE username = 'sofia'
ON CONFLICT (id_usuario) DO NOTHING;

-- 6. CASO ESPECIAL: KAROL G (Tu corrección perfecta)

-- Paso A: Convertirla en consultora
UPDATE usuarios SET rol = 'consultor' WHERE username = 'karol_bts';

-- Paso B: Insertar sus datos base
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 300.0, 'Ciberseguridad' 
FROM usuarios WHERE username = 'karol_bts'
ON CONFLICT (id_usuario) 
DO UPDATE SET tarifa = 300.0, especialidad = 'Ciberseguridad';

-- 7. AUTO-COMPLETADO INTELIGENTE (La magia de tu compañero)
-- Esto llena automáticamente la descripción y experiencia basándose en la especialidad.

UPDATE consultores 
SET descripcion = CASE 
    WHEN especialidad = 'Finanzas' THEN 'Especialista en planificación financiera y análisis de inversiones'
    WHEN especialidad = 'Tecnología' THEN 'Experto en desarrollo de software y arquitectura de sistemas'
    WHEN especialidad = 'Marketing' THEN 'Consultor en estrategias digitales y posicionamiento de marca'
    WHEN especialidad = 'Ciberseguridad' THEN 'Especialista en protección de datos y seguridad informática'
    ELSE 'Profesional experimentado en ' || especialidad
END,
experiencia_anos = CASE 
    WHEN especialidad = 'Finanzas' THEN 8
    WHEN especialidad = 'Tecnología' THEN 10
    WHEN especialidad = 'Marketing' THEN 6
    WHEN especialidad = 'Ciberseguridad' THEN 7
    ELSE 5
END,
primera_cita_descuento = TRUE,
porcentaje_descuento = 15.00
WHERE descripcion IS NULL; -- Solo llena si está vacío
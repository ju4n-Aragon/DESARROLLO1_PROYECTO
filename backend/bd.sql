-- Script SQL Actualizado para Consultores Expertos S.A.S
-- Compatible con PostgreSQL

-- 1. CONFIGURACIÓN DE BASE DE DATOS
-- Ejecutar este bloque solo si la BD no existe.
-- CREATE DATABASE consultores_db
--     WITH 
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     CONNECTION LIMIT = -1;

-- \c consultores_db  <-- Descomentar si usas línea de comandos

-- 2. CREACIÓN DE TABLAS

-- Tabla: USUARIOS
-- Se añadió 'email' y 'fecha_registro'
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,  -- ¡NUEVO! Requisito para registro con correo
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'cliente', 'consultor')),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Útil para auditoría
);

-- Tabla: CONSULTORES (Herencia)
-- Se mantiene igual, vinculada al ID de usuario
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
    fecha TIMESTAMP NOT NULL CHECK (fecha > CURRENT_TIMESTAMP), 
    estado VARCHAR(20) NOT NULL DEFAULT 'Activa' CHECK (estado IN ('Activa', 'Cancelada', 'Completada'))
);

-- 3. ÍNDICES (Optimización)
CREATE INDEX idx_usuarios_username ON usuarios(username);
CREATE INDEX idx_usuarios_email ON usuarios(email); -- ¡NUEVO! Para búsquedas rápidas por correo
CREATE INDEX idx_reservas_fecha ON reservas(fecha);
CREATE INDEX idx_reservas_cliente ON reservas(id_cliente);
CREATE INDEX idx_reservas_consultor ON reservas(id_consultor);

-- 4. DATOS INICIALES (Semilla)

-- Insertamos usuarios con sus CORREOS
INSERT INTO usuarios (username, email, password, nombre, rol) VALUES
    ('admin', 'admin@empresa.com', '1234', 'Administrador', 'admin'),
    ('cliente', 'cliente@gmail.com', '1234', 'Cliente Pruebas', 'cliente'),
    ('ana', 'ana.finanzas@empresa.com', '1234', 'Dra. Ana (Finanzas)', 'consultor'),
    ('carlos', 'carlos.tec@empresa.com', '1234', 'Ing. Carlos (Tecnología)', 'consultor'),
    ('sofia', 'sofia.mkt@empresa.com', '1234', 'Lic. Sofia (Marketing)', 'consultor')
ON CONFLICT (username) DO NOTHING;

-- Insertamos los detalles de los consultores
-- Usamos subconsultas para obtener el ID dinámicamente basado en el username
INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 100.0, 'Finanzas' FROM usuarios WHERE username = 'ana'
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 150.0, 'Tecnología' FROM usuarios WHERE username = 'carlos'
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO consultores (id_usuario, tarifa, especialidad)
SELECT id, 120.0, 'Marketing' FROM usuarios WHERE username = 'sofia'
ON CONFLICT (id_usuario) DO NOTHING;


-- =========================================================================
--  SECCIÓN DE CONSULTAS ÚTILES PARA TU BACKEND (PYTHON)
-- =========================================================================

-- A. REGISTRAR UN NUEVO CONSULTOR (Transacción de 2 pasos)
-- Paso 1: Insertar en usuarios
-- INSERT INTO usuarios (username, email, password, nombre, rol) 
-- VALUES ('nuevo_cons', 'nuevo@email.com', '1234', 'Nuevo Consultor', 'consultor') 
-- RETURNING id; 
-- Paso 2: Usar el ID retornado para insertar en consultores
-- INSERT INTO consultores (id_usuario, tarifa, especialidad) VALUES (ID_RETORNADO, 200.0, 'Legal');


-- B. CONSULTA PARA EL PANEL DEL CONSULTOR (Ver sus citas)
-- Esta query trae: ID Cita, Nombre del Cliente, Correo del Cliente, Fecha y Estado.
-- Reemplaza 'ana' por el usuario logueado.

/* SELECT 
    r.id AS id_reserva,
    u_cli.nombre AS nombre_cliente,
    u_cli.email AS email_cliente,  -- ¡NUEVO! El consultor puede ver el contacto del cliente
    r.fecha,
    r.estado
FROM reservas r
JOIN usuarios u_cli ON r.id_cliente = u_cli.id          -- Unimos para sacar datos del cliente
JOIN usuarios u_cons ON r.id_consultor = u_cons.id      -- Unimos para filtrar por consultor
WHERE u_cons.username = 'ana'                           -- <--- AQUÍ VA LA VARIABLE DE PYTHON
ORDER BY r.fecha ASC;
*/


-- C. VALIDAR LOGIN CON CORREO O USERNAME
-- Permite que el usuario entre usando su usuario O su correo
/*
SELECT rol, nombre, id 
FROM usuarios 
WHERE (username = 'ana' OR email = 'ana.finanzas@empresa.com') 
AND password = '1234';
*/
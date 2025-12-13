# Información del Proyecto

## Integrantes

- **Juan Sebastián Aragón Campo** – `2359449` – `3743`
- **Bolaños Isiquita Diego Andres** – `2379918` – `3743`
- **Tunubala Dagua Jesús Alberto** – `2379924` – `3743`

---

## Docente

**Saenz Hurtado Didiany**

---

## Asignatura

**Desarrollo de Software I**

---

## Universidad

**Universidad del Valle**  
**Ingeniería de Sistemas**  
**Sede Tuluá**  
**Año: 2025**





# Sistema de Gestión para Consultores Expertos S.A.S

Sistema de escritorio desarrollado en Python para la gestión de reservas de citas entre clientes y consultores especializados. El sistema permite roles diferenciados, gestión de agenda y persistencia de datos en PostgreSQL.

## 📋 Características Principales

### 👤 Módulo de Clientes
* **Registro y Autenticación:** Creación de cuenta con validación de correo y contraseña.
* **Reserva de Citas:** Interfaz con calendario visual (`tkcalendar`) para seleccionar fecha y hora.
* **Gestión:** Visualización de historial de citas y posibilidad de **cancelar** reservas (con validación de regla de 24 horas).

### 💼 Módulo de Consultores
* **Perfil Profesional:** Visualización de especialidad y tarifa por hora.
* **Agenda:** Vista centralizada de todas las citas programadas por los clientes.
* **Gestión de Citas:** Funcionalidad para marcar citas como **"Completadas"** y registrar notas/conclusiones de la sesión.

### 🛡️ Backend & Seguridad
* **Base de Datos Relacional:** PostgreSQL con integridad referencial y herencia de tablas.
* **Seguridad:** Uso de consultas parametrizadas para prevenir Inyección SQL.
* **Arquitectura:** Estructura modular (Separación de Lógica y Vista).

## 🛠️ Tecnologías Utilizadas
* **Lenguaje:** Python 3.12+
* **Interfaz Gráfica (GUI):** Tkinter, TTK
* **Base de Datos:** PostgreSQL 16/18
* **Librerías Clave:**
    * `psycopg2`: Conexión a BD.
    * `tkcalendar`: Widget de calendario.
    * `Pillow`: Manejo de imágenes.

## 🚀 Instrucciones de Instalación

1. **Clonar o descargar el proyecto.**

2. **Crear el Entorno Virtual (Opcional pero recomendado):**
   ```bash
   python -m venv env
   # Activar en Windows: .\env\Scripts\activate
# Información del Proyecto

## Integrantes

- **Juan Sebastián Aragón Campo** – `2359449` – `3743`


---

## Docente

**Saenz Hurtado Didiany**

---

## Asignatura

**Desarrollo de Software I**

---

## Universidad

**Universidad del Valle** **Ingeniería de Sistemas** **Sede Tuluá** **Año: 2025**

---

# 🌐 Sistema de Gestión para Consultores Expertos S.A.S (Versión Web)

Aplicación Web desarrollada en **Python (Flask)** para la gestión integral de reservas entre clientes y consultores. El sistema implementa una arquitectura Modelo-Vista-Controlador (MVC) utilizando **PostgreSQL** para la persistencia de datos y **Bootstrap 5** para una interfaz moderna y responsiva.

## ⚠️ IMPORTANTE PARA LA REVISIÓN

El proyecto ha migrado de una arquitectura de escritorio a una **Arquitectura Web** para permitir mejor escalabilidad y manejo de sesiones.

### 🌟 Nuevas Funcionalidades Implementadas:

1.  **Lógica de Negocio "Vida Real":**
    * **Cancelaciones:** Si un consultor o cliente cancela una cita, el costo final se ajusta automáticamente a **$0.00** en la base de datos (nadie cobra por un servicio no prestado).
    * **Pagos:** Si la cita se completa, el pago se libera al 100% independientemente de la calificación, garantizando el pago por trabajo realizado.
2.  **Seguridad Mejorada:**
    * Validación estricta de contraseñas en el Backend (Mínimo 8 caracteres + 1 Mayúscula o Carácter Especial).
    * Manejo transaccional (`commit`/`rollback`) para asegurar la integridad de los datos al registrar usuarios y reservas.
3.  **Sistema de Descuentos Dinámicos:**
    * Los consultores pueden configurar descuentos para primeras citas, los cuales se calculan y reflejan automáticamente en la interfaz del cliente antes del pago.

---

## 📋 Características Principales

### 👤 Módulo de Clientes
* **Registro Avanzado:** Formulario con selección de rol visual y validación de seguridad.
* **Reserva Inteligente:** Visualización de perfiles de consultores con tarifas, especialidad y cálculo automático de descuentos.
* **Simulación de Pagos:** Interfaz de pago con tarjeta (simulada) integrada en el flujo de reserva.
* **Calificación:** Sistema de calificación (1 a 5 estrellas) que queda registrado en el historial.

### 💼 Módulo de Consultores
* **Perfil Profesional:** Configuración de tarifa, especialidad, biografía y años de experiencia.
* **Gestión de Agenda:** Panel para visualizar citas entrantes.
* **Manejo de Emergencias:** Botón para cancelar citas en caso de imprevistos (notificando al sistema y anulando el cobro).

### 📊 Panel Administrativo (KPIs)
* Visualización en tiempo real de:
    * Ingresos Totales.
    * Usuarios Activos.
    * Consultor Estrella (Top Rated).

## 🛠️ Tecnologías Utilizadas

* **Backend:** Python 3.12+, Flask (Framework Web).
* **Base de Datos:** PostgreSQL con librería `psycopg2`.
* **Frontend:** HTML5, Jinja2, CSS3, Bootstrap 5 (Responsive).
* **Control de Versiones:** Git.

## 🚀 Instrucciones de Ejecución

Para probar el proyecto correctamente, siga estos pasos:

1.  **Base de Datos:**
    * Abra su cliente SQL (pgAdmin o psql).
    * Ejecute el script `bd.sql` proporcionado para crear las tablas y los usuarios semilla (Admin, Karol G, etc.).

2.  **Entorno Python:**
    ```bash
    # Instalar dependencias
    pip install flask psycopg2
    ```

3.  **Ejecutar la Aplicación:**
    ```bash
    python app.py
    ```

4.  **Acceso:**
    * Abra su navegador en: `http: '......................."`
    * **Usuario Admin:** `admin` / `1234`
   

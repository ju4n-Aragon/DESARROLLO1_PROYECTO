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

## ♿ Accesibilidad e inclusión

La aplicación debe cumplir con normas básicas de accesibilidad e inclusión para asegurar su uso por personas con discapacidades. Se aplicarán las siguientes buenas prácticas mínimas:

- Usar etiquetas `label` asociadas a controles de formulario (`for` / `id`) y atributos `aria` cuando sea necesario.
- Proveer navegación por teclado (enlaces de salto, elementos interactivos con `tabindex` y roles correctos).
- Asegurar contraste suficiente entre texto y fondo y estados visibles de foco (`:focus` / `:focus-visible`).
- Incluir textos alternativos (`alt`) para imágenes informativas y descripciones claras en elementos interactivos.
- Evitar dependencias exclusivas de color para transmitir información; usar iconos y texto junto con color.
- Mantener una estructura semántica clara (`header`, `main`, `nav`, `footer`, encabezados ordenados).

Ver [ACCESSIBILITY.md](ACCESSIBILITY.md) para una guía práctica y lista de verificación que el equipo debe seguir al desarrollar nuevas vistas.

## 🔒 Seguridad básica

La aplicación debe implementar medidas básicas de seguridad para proteger los datos personales y la información sensible. El repositorio incluye una guía con medidas recomendadas en [SECURITY.md](SECURITY.md).

Puntos clave:

- Mantener `SECRET_KEY`, credenciales de la BD y claves SMTP fuera del código (usar variables de entorno).
- Almacenar contraseñas con hash seguro (bcrypt) — ya implementado en `backend/sistema.py`.
- Usar HTTPS en producción y establecer cookies de sesión como `HttpOnly` y `Secure`.
- Activar protección CSRF en formularios (recomendada: `Flask-WTF`).

Ver [SECURITY.md](SECURITY.md) para detalles y lista de verificación.

## 17. Multiplataforma

La aplicación está diseñada para funcionar en navegadores modernos y sistemas operativos principales (Windows, macOS, Linux, iOS, Android). Recomendaciones para asegurar compatibilidad:

- Usar HTML5/CSS3 estándar y Bootstrap 5 para responsividad y consistencia entre navegadores.
- Probar en Chrome, Firefox, Edge y Safari (móvil y escritorio) y verificar tareas clave (login, registro, reservas, notificaciones).
- Evitar APIs específicas de plataforma sin polifills o degradado aceptable.

## 18. Localización e internacionalización

Se incluyó un mecanismo i18n mínimo (`translations.py`) y un selector de idioma (`/set_language/<lang>`). Las plantillas usan la función `_()` para traducir cadenas clave. Para mejorar:

- Migrar a `Flask-Babel` para soporte completo de locales, fechas y pluralización.
- Mantener archivos de traducción externos (.po/.mo) y flujo de actualización para cadenas nuevas.

## 19. Optimización SEO

Implementaciones y recomendaciones básicas:

- `sitemap.xml` y `robots.txt` proporcionados por rutas en la app para facilitar indexación.
- Meta `description`, `canonical` y `robots` añadidos en plantillas principales para mejorar indexación.
- Usar URLs limpias y semánticas; usar encabezados `h1`..`h6` de forma ordenada en nuevas páginas.
- Para producción: habilitar SSR donde aplique, asegurarse de tiempos de respuesta rápidos y agregar OpenGraph/Twitter meta tags para compartir.

---
Si quieres, puedo:
- Añadir traducciones completas para todas las cadenas en las plantillas, o
- Integrar `Flask-Babel` con archivos `.po` y ejemplo de build de traducciones.

## 21. Integración con APIs externas

Se añadieron puntos de integración opcionales:

- **Stripe (pagos):** ruta `POST /create-payment-intent` crea un PaymentIntent si `STRIPE_API_KEY` está en las variables de entorno; devuelve un `client_secret` simulado si no está configurado.
- **WorldTimeAPI** ya se utiliza para sincronizar la hora (recordatorios y reloj en dashboard).

Para probar Stripe en modo real configure `STRIPE_API_KEY` en el entorno y use la ruta para obtener el `client_secret`.

## 22. Soporte para notificaciones push

Se implementó soporte básico de Web Push:

- Service worker: `static/sw.js`.
- Endpoints: `/vapid_public_key` (devuelve la clave pública VAPID), `/push/subscribe` (guardar suscripción), `/api/send-test-push` (enviar prueba).
- Generación/uso de VAPID keys: exporte `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` y `VAPID_CLAIMS` en el entorno para que el servidor envíe notificaciones reales; si no están, el envío hace fallback a logs.

En el `dashboard` hay un botón "Activar notificaciones" que registra el service worker y solicita la suscripción push.
   

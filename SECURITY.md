# SECURITY.md — Seguridad básica y checklist

Este documento resume las medidas de seguridad ya implementadas y las recomendaciones mínimas para asegurar la aplicación.

## Estado actual (implementado en el repo)

- Hash de contraseñas con `bcrypt` (ver `backend/sistema.py`).
- Restablecimiento de contraseña por token de un solo uso con expiración corta.
- Uso de variables de entorno para `SECRET_KEY`, conexión a BD y credenciales SMTP.
- Emails transaccionales enviados de forma asíncrona para no bloquear peticiones.
- Validaciones básicas en backend (email, longitud y complejidad de contraseñas).

## Recomendaciones y medidas mínimas a mantener/implementar

1. Protección de datos personales
   - Almacenar solo los datos necesarios y cifrar en reposo la información sensible cuando aplique.
   - Evitar registrar (logs) contraseñas, tokens o información personal sin anonimizar.

2. Autenticación y sesiones
   - Mantener hashing seguro (`bcrypt`) y forzar políticas de contraseña (ya implementadas).
   - Configurar cookies de sesión con `HttpOnly`, `Secure` y `SameSite=Lax` o `Strict` en producción.
   - Limitar la duración de la sesión (`PERMANENT_SESSION_LIFETIME`) y ofrecer logout efectivo.
   - Implementar protección CSRF en formularios (`Flask-WTF`) y validación de origen en endpoints críticos.

3. Encriptación
   - Usar HTTPS (TLS) en entornos productivos y configurar HSTS.
   - Cifrar credenciales y secretos en el entorno (ej. Azure Key Vault, AWS Secrets Manager, o archivos `.env` protegidos).

4. Cabezeras de seguridad HTTP
   - Establecer `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` y una política CSP adecuada.

5. Registro, monitoreo y límites
   - Añadir logging de seguridad (accesos, intentos fallidos de login) sin exponer datos sensibles.
   - Aplicar rate-limiting en endpoints de autenticación para mitigar ataques de fuerza bruta.

6. Backups y privacidad
   - Asegurar backups cifrados y accesos restringidos.
   - Cumplir con la normativa local sobre protección de datos personales (por ejemplo, obligaciones de notificación en caso de incidentes).

## Checklist para PRs (seguridad mínima)

- [ ] ¿Se usaron variables de entorno para secretos y credenciales?
- [ ] ¿Se validaron entradas del usuario en el backend y se evitaron inyecciones SQL (usar queries parametrizadas)?
- [ ] ¿Se evita mostrar información sensible en errores o logs?
- [ ] ¿Se confirmó la configuración de cookies de sesión (`HttpOnly`, `Secure`, `SameSite`)?
- [ ] ¿Se añadió protección CSRF para formularios que mutan datos?
- [ ] ¿Se documentaron cambios que impactan a la seguridad (migraciones, configuración de servidor)?

## Cómo mejorar rápidamente (prioridad alta)

- Habilitar `Flask-WTF` y agregar CSRFProtection a las rutas de mutación.
- Forzar HTTPS usando proxy inverso (NGINX) con certificados válidos y configurar `Strict-Transport-Security`.
- Implementar rate-limiting en `/` (login) usando `Flask-Limiter`.

---

Mantener este archivo actualizado y usarlo como referencia en revisiones de código y despliegues.

## Notas sobre Web Push y claves VAPID

- Mantener las claves VAPID fuera del código (variables de entorno `VAPID_PUBLIC_KEY` y `VAPID_PRIVATE_KEY`).
- Protege el endpoint de suscripción (`/push/subscribe`) y valida la sesión del usuario.
- No registrar información sensible dentro del objeto de suscripción.

## Notas sobre integraciones externas (ej. Stripe)

- Las claves de proveedor (ej. `STRIPE_API_KEY`) deben guardarse en variables de entorno y rotarse cuando sea necesario.
- Validar y verificar webhooks usando el `signing secret` del proveedor.


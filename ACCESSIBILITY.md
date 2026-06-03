# Accesibilidad e inclusión — Guía y lista de verificación

Este documento contiene pautas prácticas mínimas para que la aplicación cumpla con requisitos básicos de accesibilidad e inclusión.

## Principios generales

- Usabilidad por teclado: todos los controles interactivos deben ser alcanzables y operables mediante teclado (`Tab`, `Enter`, `Space`).
- Estructura semántica: emplear elementos HTML5 (`header`, `main`, `nav`, `footer`, `button`, `form`, `label`) y encabezados ordenados.
- Roles y atributos ARIA: usar `role`, `aria-label`, `aria-pressed`, `aria-hidden` y otros solo cuando la semántica nativa no sea suficiente.
- Contraste: garantizar contraste suficiente entre texto y fondo (mínimo WCAG AA: 4.5:1 para texto normal).
- Indicadores de foco visibles: estilos claros en `:focus` / `:focus-visible` para que los usuarios de teclado identifiquen el elemento activo.
- Texto alternativo: todas las imágenes informativas deben tener `alt` descriptivo; imágenes decorativas usar `alt=""` o `aria-hidden="true"`.
- Texto claro y legible: evitar jergas, proveer instrucciones sencillas y accesibles.

## Recomendaciones técnicas (rápidas)

- Asociar siempre `label for="id"` a inputs y selects.
- Añadir `id="main-content"` al contenedor principal y un enlace de salto (`<a href="#main-content" class="skip-link">Saltar al contenido</a>`) al inicio del `body`.
- Para elementos no nativos interactivos (ej. tarjetas clicables), añadir `role="button" tabindex="0"` y gestionar `keydown` para `Enter`/`Space`.
- Validación y mensajes: notificaciones y errores deben anunciarse con `role="alert"` o `aria-live="polite"` según la prioridad.
- Formularios: usar `autocomplete`, atributos `inputmode` cuando aplique y `aria-describedby` para mensajes de ayuda.

## Lista de verificación para PRs

- [ ] Labels asociados a inputs.
- [ ] Navegación por teclado verificada en pantallas clave (login, registro, dashboard, reservar).
- [ ] Estados de foco visibles y contraste verificados.
- [ ] Textos alternativos en imágenes.
- [ ] Mensajes dinámicos anunciados con `aria-live` o `role="alert"`.
- [ ] No usar color solo para transmitir información.

## Recursos

- WCAG Quick Reference: https://www.w3.org/WAI/WCAG21/quickref/
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/

---

Guardar esta guía en el repositorio ayuda a mantener la accesibilidad como un requisito funcional del proyecto.
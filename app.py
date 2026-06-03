"""
app.py — Capa de presentación (Flask) · Consultores Expertos S.A.S
===================================================================
Mejoras sobre la versión anterior:
  ✅ Rutas de recuperación y restablecimiento de contraseña (Sección 14/22)
  ✅ Recordatorios 24h via APScheduler (Sección 22) — opcional
  ✅ Protección CSRF básica con Flask-WTF (recomendado agregar)
  ✅ Separación de get_hora_colombia() al módulo utils (queda aquí por simplicidad)
  ✅ Manejo explícito de errores 404 / 500
  ✅ Variables de entorno para SECRET_KEY
"""

import os
from datetime import datetime, timedelta
import anthropic


import requests as http_requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from urllib.parse import urlparse

try:
    from translations import TRANSLATIONS
except Exception:
    TRANSLATIONS = {}


# ── Scheduler opcional (instala: pip install apscheduler) ──
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_DISPONIBLE = True
except ImportError:
    SCHEDULER_DISPONIBLE = False

try:
    from backend.sistema import SistemaBackend
except ImportError:
    from sistema import SistemaBackend

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia_esto_en_produccion_con_openssl_rand")

# Seguridad de sesión y cookies (ajustar `SESSION_COOKIE_SECURE` a True en producción HTTPS)
app.config.update({
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "SESSION_COOKIE_SECURE": os.getenv("FLASK_ENV", "development") == "production",
})
app.permanent_session_lifetime = timedelta(hours=2)


@app.after_request
def set_secure_headers(response):
    """Añade cabeceras HTTP de seguridad básicas."""
    # HSTS: solo si está detrás de HTTPS en producción
    if app.config.get("SESSION_COOKIE_SECURE"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
    # CSP mínimo — ajustar según recursos externos usados
    response.headers.setdefault("Content-Security-Policy", "default-src 'self' https:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;")
    return response


# ══════════════════════════════════════════════════════════════
# DECORADOR: Verificar sesión activa (moved up para evitar NameError)
# ══════════════════════════════════════════════════════════════

def login_requerido(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario" not in session:
            flash("⚠️ Debes iniciar sesión primero.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ── Internacionalización mínima
SUPPORTED_LANGS = ["es", "en"]

def _get_locale():
    # Prioriza la sesión, luego parámetro `lang`, luego Accept-Language (simple)
    lang = session.get('lang') or request.args.get('lang')
    if lang and lang in SUPPORTED_LANGS:
        return lang
    # Intento sencillo: revisar Accept-Language
    al = request.headers.get('Accept-Language', '')
    if al.startswith('en'):
        return 'en'
    return 'es'


@app.context_processor
def inject_i18n():
    def _(key: str) -> str:
        lang = _get_locale()
        return TRANSLATIONS.get(lang, {}).get(key, key)
    return dict(_=_)


@app.route('/set_language/<lang>')
def set_language(lang: str):
    lang = lang if lang in SUPPORTED_LANGS else 'es'
    session['lang'] = lang
    # Redirigir a la página previa si existe
    ref = request.referrer
    if ref:
        parsed = urlparse(ref)
        return redirect(parsed.path)
    return redirect(url_for('login'))


@app.route('/sitemap.xml')
def sitemap():
    # Simple sitemap estático para SEO básico
    base = os.getenv('APP_URL', 'http://localhost:5000')
    urls = ['/', '/registro', '/dashboard']
    sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap_xml.append('<url>')
        sitemap_xml.append(f'<loc>{base}{u}</loc>')
        sitemap_xml.append('</url>')
    sitemap_xml.append('</urlset>')
    return app.response_class('\n'.join(sitemap_xml), mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    base = os.getenv('APP_URL', 'http://localhost:5000')
    content = f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n"
    return app.response_class(content, mimetype='text/plain')


@app.route('/vapid_public_key')
def vapid_public_key():
    return jsonify({ 'publicKey': os.getenv('VAPID_PUBLIC_KEY', '') })


@app.route('/push/subscribe', methods=['POST'])
@login_requerido
def push_subscribe():
    data = request.get_json() or {}
    sub = data.get('subscription')
    if not sub:
        return jsonify({'ok': False, 'error': 'No subscription provided.'}), 400
    usuario = session.get('usuario')
    ok = db.add_push_subscription(usuario, sub)
    return jsonify({'ok': bool(ok)})


@app.route('/api/send-test-push', methods=['POST'])
@login_requerido
def send_test_push():
    titulo = request.json.get('title', 'Prueba')
    cuerpo  = request.json.get('body', 'Mensaje de prueba')
    usuario = session.get('usuario')
    subs = db._push_subscriptions.get(usuario, [])
    if not subs:
        return jsonify({'ok': False, 'error': 'No subscriptions'}), 400
    for s in subs:
        try:
            db._send_webpush(s, {'title': titulo, 'body': cuerpo, 'url': url_for('dashboard', _external=True)})
        except Exception as e:
            print(f"[test push error] {e}")
    return jsonify({'ok': True})


@app.route('/create-payment-intent', methods=['POST'])
@login_requerido
def create_payment_intent():
    # Integración opcional con Stripe: si STRIPE_API_KEY no está, devolver simulado
    stripe_key = os.getenv('STRIPE_API_KEY')
    amount = int(float(request.json.get('amount', 0)) * 100)
    currency = request.json.get('currency', 'usd')
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            intent = stripe.PaymentIntent.create(amount=amount, currency=currency)
            return jsonify({'client_secret': intent.client_secret})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    # Fallback simulado
    return jsonify({'client_secret': 'simulated_client_secret', 'amount': amount, 'currency': currency})

# Conexión al backend
db = SistemaBackend()


# ══════════════════════════════════════════════════════════════
# UTILIDAD: Hora Colombia (WorldTimeAPI — Sección 21)
# ══════════════════════════════════════════════════════════════

def get_hora_colombia() -> datetime:
    """
    Obtiene la hora actual de Colombia (America/Bogota) desde WorldTimeAPI.
    Si falla, usa datetime.now() como fallback seguro.
    """
    try:
        resp = http_requests.get(
            "https://worldtimeapi.org/api/timezone/America/Bogota",
            timeout=3
        )
        data = resp.json()
        return datetime.fromisoformat(data["datetime"][:19])
    except Exception:
        return datetime.now()


# ══════════════════════════════════════════════════════════════
# SCHEDULER: Recordatorios automáticos 24h (Sección 22)
# ══════════════════════════════════════════════════════════════

if SCHEDULER_DISPONIBLE:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: db.enviar_recordatorios_24h(get_hora_colombia()),
        trigger="interval",
        hours=1,
        id="recordatorios_24h",
    )
    scheduler.start()
    print("✅ Scheduler de recordatorios iniciado (cada 1 hora).")


# ══════════════════════════════════════════════════════════════
# DECORADOR: Verificar sesión activa
# (definición movida más arriba para evitar NameError)
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════
# API: Hora sincronizada (para el reloj del dashboard)
# ══════════════════════════════════════════════════════════════

@app.route("/api/hora-colombia")
def api_hora_colombia():
    hora = get_hora_colombia()
    return jsonify({
        "datetime":  hora.isoformat(),
        "formatted": hora.strftime("%d/%m/%Y %H:%M"),
        "timezone":  "America/Bogota",
    })


# ══════════════════════════════════════════════════════════════
# RUTA 1: LOGIN
# ══════════════════════════════════════════════════════════════

@app.route("/", methods=["GET", "POST"])
def login():
    if "usuario" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        usuario  = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not usuario or not password:
            flash("⚠️ Completa todos los campos.")
            return render_template("login.html")

        exito, resultado = db.autenticar(usuario, password)
        if exito:
            session["usuario"] = usuario
            session["rol"]     = resultado
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Usuario o contraseña incorrectos.")

    return render_template("login.html")


# ══════════════════════════════════════════════════════════════
# RUTA 2: REGISTRO
# ══════════════════════════════════════════════════════════════

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        rol    = request.form.get("rol", "cliente")
        nombre = request.form.get("nombre", "").strip()
        email  = request.form.get("email", "").strip()
        usuario  = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        especialidad           = "General"
        tarifa                 = 0.0
        descripcion            = ""
        experiencia_anos       = 0
        primera_cita_descuento = False
        porcentaje_descuento   = 0.0

        if rol == "consultor":
            especialidad = request.form.get("especialidad", "General")
            try:
                tarifa = float(request.form.get("tarifa", 0))
            except ValueError:
                tarifa = 0.0

            descripcion = request.form.get("descripcion", "")

            try:
                experiencia_anos = int(request.form.get("experiencia_años", 0))
            except ValueError:
                experiencia_anos = 0

            val_cb = request.form.get("primera_cita_descuento")
            if val_cb in ("true", "on", "1"):
                primera_cita_descuento = True
                try:
                    porcentaje_descuento = float(request.form.get("porcentaje_descuento", 0))
                except ValueError:
                    porcentaje_descuento = 0.0

        exito, msg = db.registrar_usuario(
            usuario, password, nombre, email,
            rol=rol,
            especialidad=especialidad,
            tarifa=tarifa,
            descripcion=descripcion,
            experiencia_anos=experiencia_anos,
            primera_cita_descuento=primera_cita_descuento,
            porcentaje_descuento=porcentaje_descuento,
        )

        if exito:
            flash(f"✅ ¡Registro exitoso como {rol.capitalize()}! Revisa tu correo y luego inicia sesión.")
            return redirect(url_for("login"))
        else:
            flash(f"⚠️ Error: {msg}")

    return render_template("register.html")


# ══════════════════════════════════════════════════════════════
# RUTA 3: DASHBOARD
# ══════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_requerido
def dashboard():
    usuario = session["usuario"]
    rol     = session["rol"]

    consultores = db.get_consultores_disponibles()
    reservas    = []
    ganancias   = 0.0
    stats       = {}

    if rol == "admin":
        stats = db.obtener_estadisticas_admin()
        # DEBUG: mostrar estadísticas en consola para diagnóstico
        try:
            print("[DEBUG] Admin stats:", stats)
        except Exception:
            pass
    elif rol == "cliente":
        reservas = db.get_reservas_cliente(usuario)
    else:  # consultor
        reservas  = db.get_reservas_consultor(usuario)
        ganancias = db.calcular_ganancias_consultor(usuario)

    return render_template(
        "dashboard.html",
        usuario=usuario,
        rol=rol,
        consultores=consultores,
        reservas=reservas,
        ganancias=ganancias,
        stats=stats,
        now=get_hora_colombia(),
    )


# ══════════════════════════════════════════════════════════════
# RUTA 4: CREAR CITA
# ══════════════════════════════════════════════════════════════

@app.route("/crear_cita", methods=["POST"])
@login_requerido
def crear_cita():
    usuario         = session["usuario"]
    consultor_nombre = request.form.get("consultor", "")
    fecha_html      = request.form.get("fecha", "")

    if not consultor_nombre or not fecha_html:
        flash("⚠️ Selecciona un consultor y una fecha.")
        return redirect(url_for("dashboard"))

    hora_colombia = get_hora_colombia()
    exito, msg = db.crear_reserva(usuario, consultor_nombre, fecha_html, hora_actual=hora_colombia)

    flash(f"✅ {msg}" if exito else f"❌ Error al reservar: {msg}")
    return redirect(url_for("dashboard"))


# ══════════════════════════════════════════════════════════════
# RUTA 5: GESTIONAR CITA (Completar / Cancelar)
# ══════════════════════════════════════════════════════════════

@app.route("/gestionar_cita", methods=["POST"])
@login_requerido
def gestionar_cita():
    id_reserva  = request.form.get("id_reserva")
    accion      = request.form.get("accion")
    texto_input = request.form.get("notas", "")

    if not id_reserva or not accion:
        flash("⚠️ Solicitud inválida.")
        return redirect(url_for("dashboard"))

    hora_colombia = get_hora_colombia()

    if accion == "completar":
        try:
            calificacion = int(texto_input)
        except ValueError:
            calificacion = 5
        nota_texto = f"Cliente calificó con {calificacion} estrellas."
        exito, msg = db.actualizar_estado_cita(
            id_reserva, "Completada",
            calificacion=calificacion, notas=nota_texto,
            hora_actual=hora_colombia,
        )

    elif accion == "cancelar":
        motivo = texto_input.strip()
        if session.get("rol") == "consultor" and not motivo:
            flash("⚠️ Debes indicar el motivo de la cancelación.")
            return redirect(url_for("dashboard"))
        motivo = motivo or "Cancelada por el usuario."
        exito, msg = db.actualizar_estado_cita(
            id_reserva, "Cancelada",
            calificacion=0, notas=motivo,
            hora_actual=hora_colombia,
        )

    else:
        flash("⚠️ Acción no reconocida.")
        return redirect(url_for("dashboard"))

    flash(f"ℹ️ {msg}" if exito else f"❌ {msg}")
    return redirect(url_for("dashboard"))


# ══════════════════════════════════════════════════════════════
# RUTAS 6-7: RECUPERACIÓN DE CONTRASEÑA (Sección 14/22)
# ══════════════════════════════════════════════════════════════

@app.route("/recuperar-password", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        exito, msg = db.solicitar_recuperacion_password(email)
        flash(f"📧 {msg}")
        return redirect(url_for("login"))
    return render_template("recuperar_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        nueva = request.form.get("password", "")
        exito, msg = db.restablecer_password(token, nueva)
        if exito:
            flash(f"✅ {msg}")
            return redirect(url_for("login"))
        else:
            flash(f"❌ {msg}")
    return render_template("reset_password.html", token=token)


# ══════════════════════════════════════════════════════════════
# RUTA 8: LOGOUT
# ══════════════════════════════════════════════════════════════

@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Sesión cerrada correctamente.")
    return redirect(url_for("login"))


@app.route('/api/asistente', methods=['POST'])
@login_requerido
def asistente_ia():

    data = request.get_json()
    mensaje = data.get('mensaje', '').lower()

    if "cancel" in mensaje:

        respuesta = (
            "Puedes cancelar una cita desde la sección Mis Reservas. "
            "Recuerda que solo se permiten cancelaciones con más de 24 horas de anticipación."
        )

    elif "calificacion" in mensaje or "calificación" in mensaje or "estrella" in mensaje:

        respuesta = (
            "Al finalizar una asesoría puedes calificar al consultor con una puntuación de 1 a 5 estrellas. "
            "Estas calificaciones ayudan a medir la calidad del servicio."
        )

    elif "pago" in mensaje or "tarifa" in mensaje or "costo" in mensaje:

        respuesta = (
            "Cada consultor define su tarifa. "
            "El valor de la asesoría se muestra antes de confirmar la reserva."
        )

    elif "consultor" in mensaje:

        respuesta = (
            "En el panel principal encontrarás los consultores disponibles junto con su especialidad, experiencia y tarifa."
        )

    elif "agendar" in mensaje or "agenda" in mensaje or "reservar" in mensaje or "cita" in mensaje:

        respuesta = (
            "Para agendar una cita, selecciona un consultor disponible, elige la fecha y hora deseadas y presiona el botón Reservar."
        )

    elif "admin" in mensaje or "estadistica" in mensaje or "estadística" in mensaje:

        respuesta = (
            "Los administradores pueden consultar estadísticas, reservas realizadas, ingresos y desempeño general del sistema."
        )

    else:

        respuesta = (
            "Puedo ayudarte con reservas, cancelaciones, pagos, calificaciones, consultores y funcionamiento general de la plataforma."
        )

    return jsonify({"respuesta": respuesta})


# ══════════════════════════════════════════════════════════════
# MANEJO DE ERRORES
# ══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return "Página no encontrada", 404


@app.errorhandler(500)
def server_error(e):
    return "Error interno del servidor", 500


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode, port=int(os.getenv("PORT", 5000)))

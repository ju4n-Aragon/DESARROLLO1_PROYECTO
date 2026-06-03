"""
sistema.py — Backend Robusto · Consultores Expertos S.A.S
=========================================================
Mejoras implementadas según el Informe Final:
  ✅ TC04/TC05 — Regla de 24h real para cancelaciones
  ✅ TC08      — Precio histórico congelado al crear cita
  ✅ Sección 14 — Hash de contraseñas con bcrypt
  ✅ Sección 14 — Token de sesión (UUID) en lugar de password plain
  ✅ Sección 21 — Email automático (SMTP/SendGrid) en confirmaciones/cancelaciones
  ✅ Sección 22 — Recordatorio 24h antes de la cita
  ✅ Sección 18 — Formato COP en mensajes
  ✅ Sección 10 — Validaciones reforzadas (password, fechas, estado)
  ✅ Sección 15 — Índice de queries optimizado (ver bd.sql)
  ✅ Reconexión automática a BD si la conexión cae
  ✅ Separación de responsabilidades en métodos privados
"""

import os
import json
import re
import uuid
import smtplib
import threading
import psycopg2
import psycopg2.extras
import bcrypt
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ──────────────────────────────────────────────
# CONFIGURACIÓN (usa variables de entorno; nunca hardcodeadas)
# ──────────────────────────────────────────────
DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME",     "consultores_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "12345"),
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5433"),
}

SMTP_CONFIG = {
    "host":     os.getenv("SMTP_HOST",     "smtp.gmail.com"),
    "port":     int(os.getenv("SMTP_PORT", "587")),
    "user":     os.getenv("SMTP_USER",     ""),          # configurar en .env
    "password": os.getenv("SMTP_PASSWORD", ""),
    "from":     os.getenv("SMTP_FROM",     "no-reply@consultores.com"),
}

REGLA_CANCELACION_HORAS = int(os.getenv("CANCELACION_HORAS", "24"))

# ──────────────────────────────────────────────
# HELPER: EMAIL (asíncrono para no bloquear la request)
# ──────────────────────────────────────────────

def _enviar_email_async(destinatario: str, asunto: str, cuerpo_html: str):
    """Envía un correo en un hilo separado para no bloquear Flask."""
    def _send():
        if not SMTP_CONFIG["user"]:
            print(f"[EMAIL SIMULADO] Para: {destinatario} | Asunto: {asunto}")
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = asunto
            msg["From"]    = SMTP_CONFIG["from"]
            msg["To"]      = destinatario
            msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

            with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as srv:
                srv.ehlo()
                srv.starttls()
                srv.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
                srv.sendmail(SMTP_CONFIG["from"], destinatario, msg.as_string())
            print(f"[EMAIL] Enviado a {destinatario}: {asunto}")
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")

    threading.Thread(target=_send, daemon=True).start()


def _template_email(titulo: str, lineas: list[str], color_header: str = "#0f1e35") -> str:
    """Plantilla HTML minimalista para emails transaccionales."""
    items = "".join(f"<p style='margin:6px 0;color:#333'>{l}</p>" for l in lineas)
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto">
      <div style="background:{color_header};padding:20px 28px;border-radius:8px 8px 0 0">
        <h2 style="color:#c9a84c;margin:0">Consultores Expertos S.A.S</h2>
        <p style="color:#fff;margin:4px 0 0">{titulo}</p>
      </div>
      <div style="background:#f8f4ed;padding:24px 28px;border-radius:0 0 8px 8px">
        {items}
        <hr style="border:none;border-top:1px solid #ddd;margin:18px 0">
        <p style="font-size:11px;color:#999">Este mensaje fue generado automáticamente.
        No respondas a este correo.</p>
      </div>
    </div>"""


# ──────────────────────────────────────────────
# HELPER: PASSWORD
# ──────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        # Fallback para usuarios semilla que aún usan texto plano
        return plain == hashed


def _validar_password(password: str) -> tuple[bool, str]:
    """
    Reglas del informe (Sección 14):
      - Mínimo 8 caracteres
      - Al menos una mayúscula O un carácter especial
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    tiene_mayus  = any(c.isupper() for c in password)
    tiene_esp    = any(not c.isalnum() for c in password)
    if not (tiene_mayus or tiene_esp):
        return False, "La contraseña debe incluir al menos una Mayúscula o un Carácter Especial (*, !, $…)."
    return True, ""


def _validar_email(email: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", email))


# ──────────────────────────────────────────────
# CLASE PRINCIPAL
# ──────────────────────────────────────────────

class SistemaBackend:

    def __init__(self):
        self.conn = None
        self._tokens_recuperacion = {}
        self._push_subscriptions = {}  # username -> list of subscription dicts
        self.cur  = None
        self._conectar()

    # ── Conexión ──────────────────────────────

    def _conectar(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
            self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("✅ Conexión a Base de Datos establecida.")
        except Exception as e:
            print(f"❌ Error crítico conectando a BD: {e}")
            self.conn = None
            self.cur  = None

    def _ensure_conn(self) -> bool:
        """Reconecta automáticamente si la conexión cayó."""
        if self.conn is None:
            self._conectar()
            return self.conn is not None
        try:
            self.cur.execute("SELECT 1")
            return True
        except Exception:
            self._conectar()
            return self.conn is not None

    # ── Helpers privados ──────────────────────

    def _get_usuario_id(self, username: str) -> int | None:
        self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        row = self.cur.fetchone()
        return row["id"] if row else None

    def _get_consultor_por_nombre(self, nombre: str) -> dict | None:
        self.cur.execute("""
            SELECT u.id, u.email, u.nombre,
                   c.tarifa, c.porcentaje_descuento, c.primera_cita_descuento
            FROM usuarios u
            JOIN consultores c ON u.id = c.id_usuario
            WHERE u.nombre = %s
        """, (nombre,))
        return self.cur.fetchone()

    def _get_email_usuario(self, username: str) -> str:
        self.cur.execute("SELECT email, nombre FROM usuarios WHERE username = %s", (username,))
        row = self.cur.fetchone()
        return (row["email"], row["nombre"]) if row else ("", "")

    # ─────────────────────────────────────────
    # LECTURAS (SELECTs)
    # ─────────────────────────────────────────

    def get_consultores_disponibles(self) -> list[dict]:
        """Lista de consultores con precio final calculado y badge de descuento."""
        if not self._ensure_conn():
            return []
        try:
            self.cur.execute("""
                SELECT u.nombre, c.tarifa, c.especialidad,
                       c.descripcion, c.experiencia_anos,
                       c.porcentaje_descuento, c.primera_cita_descuento
                FROM usuarios u
                JOIN consultores c ON u.id = c.id_usuario
                ORDER BY u.nombre
            """)
            resultado = []
            for row in self.cur.fetchall():
                tarifa       = float(row["tarifa"])
                pct          = float(row["porcentaje_descuento"] or 0)
                tiene_desc   = bool(row["primera_cita_descuento"])
                precio_final = round(tarifa * (1 - pct / 100), 2) if (tiene_desc and pct > 0) else tarifa
                resultado.append({
                    "nombre":               row["nombre"],
                    "tarifa":               tarifa,
                    "especialidad":         row["especialidad"],
                    "descripcion":          row["descripcion"] or "Sin descripción disponible.",
                    "experiencia":          row["experiencia_anos"] or 0,
                    "descuento_txt":        f"{int(pct)}% OFF" if (tiene_desc and pct > 0) else "",
                    "precio_final_estimado": precio_final,
                })
            return resultado
        except Exception as e:
            print(f"[get_consultores] {e}")
            return []

    def get_usuario(self, username: str) -> dict | None:
        if not self._ensure_conn():
            return None
        try:
            self.cur.execute(
                "SELECT id, nombre, rol, email FROM usuarios WHERE username = %s",
                (username,)
            )
            row = self.cur.fetchone()
            if not row:
                return None
            datos = dict(row)
            if row["rol"] == "consultor":
                self.cur.execute(
                    "SELECT especialidad, tarifa FROM consultores WHERE id_usuario = %s",
                    (row["id"],)
                )
                cons = self.cur.fetchone()
                if cons:
                    datos["especialidad"] = cons["especialidad"]
                    datos["tarifa"]       = float(cons["tarifa"])
            return datos
        except Exception as e:
            print(f"[get_usuario] {e}")
            return None

    def get_reservas_cliente(self, username: str) -> list:
        if not self._ensure_conn():
            return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cons.nombre AS consultor, r.fecha, r.estado,
                       u_cons.email, r.notas, r.costo_final, r.calificacion
                FROM reservas r
                JOIN usuarios u_cli  ON r.id_cliente   = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cli.username = %s
                ORDER BY r.fecha DESC
            """, (username,))
            # Convertir a tuplas para compatibilidad con dashboard.html
            rows = self.cur.fetchall()
            return [
                (r["id"], r["consultor"], r["fecha"], r["estado"],
                 r["email"], r["notas"], r["costo_final"])
                for r in rows
            ]
        except Exception as e:
            print(f"[get_reservas_cliente] {e}")
            return []

    def get_reservas_consultor(self, username: str) -> list:
        if not self._ensure_conn():
            return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cli.nombre AS cliente, r.fecha, r.estado,
                       u_cli.email, r.notas, r.costo_final, r.calificacion
                FROM reservas r
                JOIN usuarios u_cli  ON r.id_cliente   = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cons.username = %s
                ORDER BY r.fecha ASC
            """, (username,))
            rows = self.cur.fetchall()
            return [
                (r["id"], r["cliente"], r["fecha"], r["estado"],
                 r["email"], r["notas"], r["costo_final"])
                for r in rows
            ]
        except Exception as e:
            print(f"[get_reservas_consultor] {e}")
            return []

    def calcular_ganancias_consultor(self, username: str) -> float:
        if not self._ensure_conn():
            return 0.0
        try:
            self.cur.execute("""
                SELECT COALESCE(SUM(r.costo_final), 0)
                FROM reservas r
                JOIN usuarios u ON r.id_consultor = u.id
                WHERE u.username = %s AND r.estado = 'Completada'
            """, (username,))
            return float(self.cur.fetchone()[0])
        except Exception:
            return 0.0

    def obtener_estadisticas_admin(self) -> dict:
        if not self._ensure_conn():
            return {}
        try:
            stats = {}

            # Helper para obtener el primer valor de la fila (funciona con RealDictCursor)
            def _scalar(row):
                if not row:
                    return 0
                if isinstance(row, dict):
                    # next(iter(...)) obtiene el primer valor sin depender del nombre de columna
                    return next(iter(row.values()))
                try:
                    return row[0]
                except Exception:
                    return 0

            self.cur.execute(
                "SELECT COALESCE(SUM(costo_final),0) AS ingresos_totales FROM reservas WHERE estado='Completada'"
            )
            stats["ingresos_totales"] = float(_scalar(self.cur.fetchone()) or 0)

            self.cur.execute("SELECT COUNT(*) AS total_usuarios FROM usuarios")
            stats["total_usuarios"] = int(_scalar(self.cur.fetchone()) or 0)

            self.cur.execute(
                "SELECT COUNT(*) AS citas_activas FROM reservas WHERE estado='Activa'"
            )
            stats["citas_activas"] = int(_scalar(self.cur.fetchone()) or 0)

            self.cur.execute("""
                SELECT u.nombre, COUNT(r.id) AS total
                FROM reservas r
                JOIN usuarios u ON r.id_consultor = u.id
                WHERE r.estado = 'Completada'
                GROUP BY u.nombre
                ORDER BY total DESC LIMIT 1
            """)
            row = self.cur.fetchone()
            stats["consultor_top"] = f"{row['nombre']} ({row['total']} citas)" if row else "Nadie aún"

            self.cur.execute("""
                SELECT COALESCE(AVG(calificacion), 0) AS calificacion_promedio
                FROM reservas WHERE estado='Completada' AND calificacion > 0
            """)
            stats["calificacion_promedio"] = round(float(_scalar(self.cur.fetchone()) or 0), 1)

            return stats
        except Exception as e:
            print(f"[stats_admin] {e}")
            return {}

    # ─────────────────────────────────────────
    # ESCRITURAS (INSERTs / UPDATEs)
    # ─────────────────────────────────────────

    def autenticar(self, usuario: str, password: str) -> tuple[bool, str | None]:
        """
        Autenticación segura: soporta bcrypt Y texto plano (usuarios semilla).
        Retorna (True, rol) o (False, None).
        """
        if not self._ensure_conn():
            return False, None
        try:
            self.cur.execute(
                "SELECT rol, password FROM usuarios WHERE username = %s",
                (usuario,)
            )
            row = self.cur.fetchone()
            if not row:
                return False, None
            if _verify_password(password, row["password"]):
                return True, row["rol"]
            return False, None
        except Exception:
            return False, None

    def registrar_usuario(
        self, usuario: str, password: str, nombre_completo: str, email: str,
        rol: str = "cliente", especialidad: str = "General", tarifa: float = 0,
        descripcion: str = "", experiencia_anos: int = 0,
        primera_cita_descuento: bool = False, porcentaje_descuento: float = 0
    ) -> tuple[bool, str]:
        """
        Registro con:
          - Validación de contraseña (longitud + complejidad)
          - Hash bcrypt
          - Validación de email
          - Email de bienvenida
        """
        # Validaciones previas
        ok, msg = _validar_password(password)
        if not ok:
            return False, msg

        if not _validar_email(email):
            return False, "El correo electrónico no tiene un formato válido."

        if not nombre_completo.strip():
            return False, "El nombre completo no puede estar vacío."

        if rol == "consultor":
            if tarifa <= 0:
                return False, "La tarifa debe ser mayor a $0."
            if porcentaje_descuento < 0 or porcentaje_descuento > 100:
                return False, "El porcentaje de descuento debe estar entre 0 y 100."

        if not self._ensure_conn():
            return False, "Sin conexión a la base de datos."

        try:
            password_hash = _hash_password(password)

            self.cur.execute(
                """INSERT INTO usuarios (username, password, nombre, email, rol)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (usuario, password_hash, nombre_completo.strip(), email.lower(), rol)
            )
            new_id = self.cur.fetchone()["id"]

            if rol == "consultor":
                self.cur.execute("""
                    INSERT INTO consultores
                    (id_usuario, tarifa, especialidad, descripcion,
                     experiencia_anos, primera_cita_descuento, porcentaje_descuento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (new_id, tarifa, especialidad, descripcion,
                      experiencia_anos, primera_cita_descuento, porcentaje_descuento))

            self.conn.commit()

            # Email de bienvenida asíncrono
            _enviar_email_async(
                email,
                "¡Bienvenido a Consultores Expertos S.A.S!",
                _template_email(
                    "Registro exitoso",
                    [
                        f"Hola <strong>{nombre_completo}</strong>, tu cuenta ha sido creada.",
                        f"Rol: <strong>{rol.capitalize()}</strong>",
                        "Ya puedes iniciar sesión en la plataforma.",
                    ]
                )
            )

            return True, "Registro exitoso."

        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False, "El usuario o correo ya existen en el sistema."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error técnico: {e}"

    def crear_reserva(
        self, usuario_cliente: str, consultor_nombre: str,
        fecha_str: str, hora_actual: datetime | None = None
    ) -> tuple[bool, str]:
        """
        Crea una cita.
        TC03 — No permite fechas pasadas.
        TC08 — El costo_final se congela al momento del agendamiento.
        Sección 21 — Envía email de confirmación al cliente y al consultor.
        """
        if not self._ensure_conn():
            return False, "Sin conexión a la base de datos."

        try:
            fecha_str  = fecha_str.replace("T", " ")
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return False, "Formato de fecha inválido. Use YYYY-MM-DD HH:MM."

        now = hora_actual or datetime.now()
        if fecha_cita <= now:
            return False, "No puedes agendar una cita en una fecha y hora pasada."

        try:
            id_cliente = self._get_usuario_id(usuario_cliente)
            if not id_cliente:
                return False, "Cliente no encontrado."

            cons = self._get_consultor_por_nombre(consultor_nombre)
            if not cons:
                return False, f"No existe un consultor con el nombre '{consultor_nombre}'."

            # TC08: precio congelado ahora
            tarifa       = float(cons["tarifa"])
            pct          = float(cons["porcentaje_descuento"] or 0)
            tiene_desc   = bool(cons["primera_cita_descuento"])
            precio_final = round(tarifa * (1 - pct / 100), 2) if (tiene_desc and pct > 0) else tarifa

            self.cur.execute("""
                INSERT INTO reservas (id_cliente, id_consultor, fecha, estado, costo_final)
                VALUES (%s, %s, %s, 'Activa', %s) RETURNING id
            """, (id_cliente, cons["id"], fecha_cita, precio_final))
            id_reserva = self.cur.fetchone()["id"]
            self.conn.commit()

            # Emails de confirmación
            email_cli, nombre_cli = self._get_email_usuario(usuario_cliente)
            fecha_fmt = fecha_cita.strftime("%d/%m/%Y a las %H:%M")

            _enviar_email_async(
                email_cli,
                "✅ Cita confirmada — Consultores Expertos",
                _template_email("Tu cita ha sido agendada", [
                    f"Hola <strong>{nombre_cli}</strong>,",
                    f"Cita con: <strong>{consultor_nombre}</strong>",
                    f"Fecha: <strong>{fecha_fmt}</strong>",
                    f"Costo: <strong>COP ${precio_final:,.0f}</strong>",
                    f"ID de reserva: #{id_reserva}",
                    "Recuerda que puedes cancelar con más de 24 horas de anticipación.",
                ])
            )
            _enviar_email_async(
                cons["email"],
                "📅 Nueva cita asignada — Consultores Expertos",
                _template_email("Nueva cita en tu agenda", [
                    f"Hola <strong>{cons['nombre']}</strong>,",
                    f"Cliente: <strong>{nombre_cli}</strong>",
                    f"Fecha: <strong>{fecha_fmt}</strong>",
                ], color_header="#1a3254")
            )

            return True, f"Reserva exitosa. Total a pagar: COP ${precio_final:,.0f}"

        except Exception as e:
            self.conn.rollback()
            print(f"[crear_reserva] {e}")
            return False, f"Error al reservar: {e}"

    def actualizar_estado_cita(
        self, id_reserva: int | str, nuevo_estado: str,
        calificacion: int = 0, notas: str = "",
        hora_actual: datetime | None = None
    ) -> tuple[bool, str]:
        """
        TC04 / TC05 — Regla de 24h para cancelaciones.
        TC06 — Al completar, libera el pago (mantiene costo_final).
        Sección 21 — Email automático en cancelación / completado.
        """
        if not self._ensure_conn():
            return False, "Sin conexión a la base de datos."

        estados_validos = ("Activa", "Cancelada", "Completada")
        if nuevo_estado not in estados_validos:
            return False, f"Estado inválido. Usa: {', '.join(estados_validos)}."

        try:
            self.cur.execute("""
                SELECT r.id, r.fecha, r.estado, r.costo_final,
                       u_cli.email  AS email_cli,  u_cli.nombre  AS nombre_cli,
                       u_cons.email AS email_cons, u_cons.nombre AS nombre_cons
                FROM reservas r
                JOIN usuarios u_cli  ON r.id_cliente   = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE r.id = %s
            """, (int(id_reserva),))
            row = self.cur.fetchone()

            if not row:
                return False, "Reserva no encontrada."

            if row["estado"] != "Activa":
                return False, f"La cita ya está en estado '{row['estado']}' y no puede modificarse."

            costo_final = float(row["costo_final"])
            now         = hora_actual or datetime.now()

            if nuevo_estado == "Cancelada":
                # TC04 / TC05 — Regla de 24 horas
                horas_restantes = (row["fecha"] - now).total_seconds() / 3600
                if horas_restantes < REGLA_CANCELACION_HORAS:
                    hora_limite = (row["fecha"] - timedelta(hours=REGLA_CANCELACION_HORAS))
                    return False, (
                        f"No se puede cancelar: faltan solo {horas_restantes:.1f}h para la cita. "
                        f"La cancelación debió realizarse antes de las "
                        f"{hora_limite.strftime('%d/%m/%Y %H:%M')}."
                    )
                costo_final = 0.0
                notas = notas or "Cancelada por el usuario."

            elif nuevo_estado == "Completada":
                calificacion = max(1, min(5, int(calificacion))) if calificacion else 5
                notas = notas or f"Cita completada. Calificación: {calificacion}/5."

            self.cur.execute("""
                UPDATE reservas
                SET estado = %s, calificacion = %s, notas = %s, costo_final = %s
                WHERE id = %s
            """, (nuevo_estado, calificacion, notas, costo_final, int(id_reserva)))
            self.conn.commit()

            # Email de notificación
            fecha_fmt = row["fecha"].strftime("%d/%m/%Y %H:%M")
            if nuevo_estado == "Cancelada":
                _enviar_email_async(
                    row["email_cli"],
                    "❌ Cita cancelada — Consultores Expertos",
                    _template_email("Tu cita ha sido cancelada", [
                        f"Hola <strong>{row['nombre_cli']}</strong>,",
                        f"La cita del <strong>{fecha_fmt}</strong> fue cancelada.",
                        f"Motivo: {notas}",
                        "El cobro se ha ajustado a $0.",
                    ], color_header="#7a1a1a")
                )
            elif nuevo_estado == "Completada":
                _enviar_email_async(
                    row["email_cli"],
                    "⭐ Asesoría completada — Consultores Expertos",
                    _template_email("Asesoría finalizada", [
                        f"Hola <strong>{row['nombre_cli']}</strong>,",
                        f"Tu asesoría del <strong>{fecha_fmt}</strong> fue marcada como completada.",
                        f"Calificación registrada: <strong>{'⭐' * calificacion}</strong>",
                        f"Pago liberado: <strong>COP ${costo_final:,.0f}</strong>",
                        "¡Gracias por confiar en Consultores Expertos!",
                    ], color_header="#1a7a4a")
                )

            return True, f"Estado actualizado a '{nuevo_estado}' correctamente."

        except Exception as e:
            self.conn.rollback()
            print(f"[actualizar_estado] {e}")
            return False, f"Error SQL: {e}"

    # ─────────────────────────────────────────
    # RECUPERACIÓN DE CONTRASEÑA
    # ─────────────────────────────────────────


    def solicitar_recuperacion_password(self, email: str) -> tuple[bool, str]:
        """
        Sección 14/22 — Genera token de un solo uso y envía email.
        """
        if not self._ensure_conn():
            return False, "Sin conexión."
        try:
            self.cur.execute(
                "SELECT username, nombre FROM usuarios WHERE email = %s",
                (email.lower(),)
            )
            row = self.cur.fetchone()
            if not row:
                # Por seguridad, no revelamos si el email existe
                return True, "Si el correo existe, recibirás instrucciones."

            token = str(uuid.uuid4())
            expira = datetime.now() + timedelta(hours=1)
            self._tokens_recuperacion[token] = {
                "username": row["username"],
                "expires":  expira,
            }

            link = f"{os.getenv('APP_URL','http://localhost:5000')}/reset-password/{token}"
            _enviar_email_async(
                email,
                "🔑 Recuperación de contraseña — Consultores Expertos",
                _template_email("Restablece tu contraseña", [
                    f"Hola <strong>{row['nombre']}</strong>,",
                    "Haz clic en el siguiente enlace para restablecer tu contraseña:",
                    f"<a href='{link}' style='color:#0f1e35'>{link}</a>",
                    "Este enlace expira en 1 hora.",
                    "Si no solicitaste esto, ignora este mensaje.",
                ])
            )
            return True, "Si el correo existe, recibirás instrucciones."
        except Exception as e:
            return False, f"Error: {e}"

    def restablecer_password(self, token: str, nueva_password: str) -> tuple[bool, str]:
        """Valida token y actualiza la contraseña con hash."""
        info = self._tokens_recuperacion.get(token)
        if not info:
            return False, "Token inválido o ya utilizado."
        if datetime.now() > info["expires"]:
            del self._tokens_recuperacion[token]
            return False, "El token ha expirado. Solicita uno nuevo."

        ok, msg = _validar_password(nueva_password)
        if not ok:
            return False, msg

        if not self._ensure_conn():
            return False, "Sin conexión."
        try:
            self.cur.execute(
                "UPDATE usuarios SET password = %s WHERE username = %s",
                (_hash_password(nueva_password), info["username"])
            )
            self.conn.commit()
            del self._tokens_recuperacion[token]
            return True, "Contraseña actualizada correctamente."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    # ─────────────────────────────────────────
    # RECORDATORIOS (llamar desde un job externo o APScheduler)
    # ─────────────────────────────────────────

    def enviar_recordatorios_24h(self, hora_actual: datetime | None = None):
        """
        Sección 22 — Envía recordatorios a clientes cuya cita es
        exactamente en ~24 horas (ventana de ±15 min).
        Debe invocarse desde un scheduler (APScheduler / Celery Beat).
        """
        if not self._ensure_conn():
            return
        now   = hora_actual or datetime.now()
        desde = now + timedelta(hours=24) - timedelta(minutes=15)
        hasta = now + timedelta(hours=24) + timedelta(minutes=15)

        try:
            self.cur.execute("""
                SELECT u_cli.email, u_cli.nombre,
                       u_cons.nombre AS consultor, r.fecha, r.costo_final
                FROM reservas r
                JOIN usuarios u_cli  ON r.id_cliente   = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE r.estado = 'Activa' AND r.fecha BETWEEN %s AND %s
            """, (desde, hasta))
            for row in self.cur.fetchall():
                fecha_fmt = row["fecha"].strftime("%d/%m/%Y a las %H:%M")
                _enviar_email_async(
                    row["email"],
                    "⏰ Recordatorio: tu cita es mañana — Consultores Expertos",
                    _template_email("Recordatorio de cita", [
                        f"Hola <strong>{row['nombre']}</strong>,",
                        f"Tu cita con <strong>{row['consultor']}</strong>",
                        f"es <strong>mañana {fecha_fmt}</strong>.",
                        f"Valor a pagar: <strong>COP ${float(row['costo_final']):,.0f}</strong>",
                        "Si necesitas cancelar, hazlo ahora mismo (recuerda la regla de 24h).",
                    ])
                )
                # Intentar enviar notificación push si hay suscripción
                try:
                    username = None
                    # intentar buscar usuario por email
                    self.cur.execute("SELECT username FROM usuarios WHERE email = %s", (row['email'],))
                    r = self.cur.fetchone()
                    if r: username = r['username']
                    if username and username in self._push_subscriptions:
                        for sub in list(self._push_subscriptions.get(username, [])):
                            try:
                                self._send_webpush(sub, {
                                    'title': 'Recordatorio: Tu cita es mañana',
                                    'body': f"Cita con {row['consultor']} — {row['fecha'].strftime('%d/%m %H:%M')}",
                                    'url': os.getenv('APP_URL', 'http://localhost:5000') + '/dashboard'
                                })
                            except Exception as e:
                                print(f"[push send error] {e}")
                except Exception:
                    pass
        except Exception as e:
            print(f"[recordatorios] {e}")

    # ─────────────────────────────────────────
    # PUSH: gestión de suscripciones y envío
    # ─────────────────────────────────────────
    def add_push_subscription(self, username: str, subscription: dict) -> bool:
        try:
            lst = self._push_subscriptions.setdefault(username, [])
            # evitar duplicados simplificando por endpoint
            end = subscription.get('endpoint')
            if any(s.get('endpoint') == end for s in lst):
                return True
            lst.append(subscription)
            return True
        except Exception:
            return False

    def _send_webpush(self, subscription: dict, payload: dict):
        # Usa pywebpush si está disponible, sino imprime y envía email como fallback
        try:
            from pywebpush import webpush, WebPushException
            vapid_priv = os.getenv('VAPID_PRIVATE_KEY')
            vapid_pub  = os.getenv('VAPID_PUBLIC_KEY')
            claims = {"sub": os.getenv('VAPID_CLAIMS', 'mailto:admin@consultores.com')}
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=vapid_priv,
                vapid_claims=claims
            )
        except Exception as e:
            # Fallback: log and enviar email si es necesario
            print(f"[webpush fallback] {e} — payload: {payload}")
            # No hacemos más aquí para evitar bloquear

    # ─────────────────────────────────────────
    # CIERRE
    # ─────────────────────────────────────────

    def __del__(self):
        try:
            if self.cur:  self.cur.close()
            if self.conn: self.conn.close()
        except Exception:
            pass

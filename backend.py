# Updated backend.py
import psycopg2
from datetime import datetime, timedelta

class SistemaBackend:
    def __init__(self):
        # Conexión a la base de datos PostgreSQL
        # Ajusta los parámetros según tu configuración (e.g., password si tiene)
        self.conn = psycopg2.connect(
            dbname="consultores_db",
            user="postgres",
            password="12345",  # Cambia si tienes contraseña
            host="localhost",
            port="5432"  # Puerto por defecto
        )
        self.cur = self.conn.cursor()

    def autenticar(self, usuario, password):
        """Valida credenciales y retorna el ROL si es exitoso"""
        self.cur.execute(
            "SELECT rol FROM usuarios WHERE username = %s AND password = %s",
            (usuario, password)
        )
        row = self.cur.fetchone()
        if row:
            return True, row[0]
        return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, rol="cliente"):
        if len(password) < 4:
            return False, "Contraseña muy corta."
        try:
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, rol) VALUES (%s, %s, %s, %s)",
                (usuario, password, nombre_completo, rol)
            )
            self.conn.commit()
            return True, "Registro exitoso."
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False, "El usuario ya existe."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"

    def get_usuario(self, username):
        """Obtiene detalles del usuario, incluyendo tarifa y especialidad si es consultor"""
        self.cur.execute(
            "SELECT id, username, password, nombre, rol FROM usuarios WHERE username = %s",
            (username,)
        )
        row = self.cur.fetchone()
        if not row:
            return None
        usuario_dict = {
            "id": row[0],
            "username": row[1],
            "password": row[2],
            "nombre": row[3],
            "rol": row[4]
        }
        if usuario_dict["rol"] == "consultor":
            self.cur.execute(
                "SELECT tarifa, especialidad FROM consultores WHERE id_usuario = %s",
                (usuario_dict["id"],)
            )
            cons_row = self.cur.fetchone()
            if cons_row:
                usuario_dict["tarifa"] = cons_row[0]
                usuario_dict["especialidad"] = cons_row[1]
        return usuario_dict

    def get_consultores_disponibles(self):
        """Obtiene lista de consultores para el combobox"""
        self.cur.execute(
            """
            SELECT u.nombre, c.tarifa, u.id
            FROM usuarios u
            JOIN consultores c ON u.id = c.id_usuario
            WHERE u.rol = 'consultor'
            """
        )
        rows = self.cur.fetchall()
        return [{"nombre": row[0], "tarifa": row[1], "id": row[2]} for row in rows]

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        try:
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            if fecha_cita < datetime.now():
                return False, "No puedes reservar en el pasado."

            # Obtener ID del cliente
            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            id_cli_row = self.cur.fetchone()
            if not id_cli_row:
                return False, "Cliente no encontrado."
            id_cli = id_cli_row[0]

            # Obtener ID del consultor por nombre
            self.cur.execute("SELECT id FROM usuarios WHERE nombre = %s", (consultor_nombre,))
            id_cons_row = self.cur.fetchone()
            if not id_cons_row:
                return False, "Consultor no encontrado."
            id_cons = id_cons_row[0]

            # Insertar reserva
            self.cur.execute(
                "INSERT INTO reservas (id_cliente, id_consultor, fecha, estado) VALUES (%s, %s, %s, 'Activa')",
                (id_cli, id_cons, fecha_cita)
            )
            self.conn.commit()
            return True, "Cita reservada con éxito."
        except ValueError:
            return False, "Formato fecha inválido."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"

    def cancelar_reserva(self, reserva_id):
        try:
            self.cur.execute("SELECT fecha FROM reservas WHERE id = %s", (reserva_id,))
            fecha_row = self.cur.fetchone()
            if not fecha_row:
                return False, "Reserva no encontrada."
            fecha = fecha_row[0]
            tiempo = fecha - datetime.now()
            if tiempo < timedelta(hours=24):
                return False, "Falta menos de 24h. Política estricta."
            self.cur.execute("UPDATE reservas SET estado = 'Cancelada' WHERE id = %s", (reserva_id,))
            self.conn.commit()
            return True, "Reserva cancelada."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"

    def obtener_estadisticas(self):
        self.cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE estado = 'Activa') AS activas
            FROM reservas
            """
        )
        row = self.cur.fetchone()
        return f"Total: {row[0]} | Activas: {row[1]}"

    def get_reservas_cliente(self, username):
        """Obtiene reservas para un cliente (para la tabla)"""
        self.cur.execute(
            """
            SELECT r.id, u_cons.nombre AS consultor, r.fecha, r.estado
            FROM reservas r
            JOIN usuarios u_cons ON r.id_consultor = u_cons.id
            JOIN usuarios u_cli ON r.id_cliente = u_cli.id
            WHERE u_cli.username = %s
            ORDER BY r.fecha DESC
            """,
            (username,)
        )
        return self.cur.fetchall()  # Lista de tuplas (id, consultor, fecha, estado)

    def get_reservas_consultor(self, username):
        """Obtiene reservas para un consultor (para la tabla)"""
        self.cur.execute(
            """
            SELECT r.id, u_cli.nombre AS cliente, r.fecha, r.estado
            FROM reservas r
            JOIN usuarios u_cli ON r.id_cliente = u_cli.id
            JOIN usuarios u_cons ON r.id_consultor = u_cons.id
            WHERE u_cons.username = %s
            ORDER BY r.fecha DESC
            """,
            (username,)
        )
        return self.cur.fetchall()  # Lista de tuplas (id, cliente, fecha, estado)

    def __del__(self):
        """Cierra la conexión al destruir el objeto"""
        if hasattr(self, 'cur'):
            self.cur.close()
        if hasattr(self, 'conn'):
            self.conn.close()
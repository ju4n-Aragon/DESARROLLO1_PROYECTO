import psycopg2
from datetime import datetime, timedelta

class SistemaBackend:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="consultores_db",
                user="postgres",
                password="1234",  # <--- TU CONTRASEÑA
                host="localhost",
                port="5432"
            )
            self.conn.autocommit = True
            self.cur = self.conn.cursor()
            print("Conexión a Base de Datos Exitosa.")
        except Exception as e:
            print(f"Error crítico conectando a BD: {e}")
            self.conn = None

    # --- MÉTODOS DE LECTURA DE DATOS ---

    def get_consultores_disponibles(self):
        """Obtiene la lista de consultores para el combobox"""
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT u.nombre, c.tarifa 
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario
            """)
            rows = self.cur.fetchall()
            return [{"nombre": row[0], "tarifa": float(row[1])} for row in rows]
        except Exception as e:
            print(f"Error buscando consultores: {e}")
            return []

    def get_usuario(self, username):
        """Busca toda la info de un usuario (cliente o consultor)"""
        if not self.conn: return None
        try:
            # 1. Buscar datos básicos
            self.cur.execute("SELECT id, nombre, rol FROM usuarios WHERE username = %s", (username,))
            row = self.cur.fetchone()
            if not row: return None
            
            datos = {"id": row[0], "nombre": row[1], "rol": row[2]}
            
            # 2. Si es consultor, buscar datos extra
            if row[2] == 'consultor':
                self.cur.execute("SELECT especialidad, tarifa FROM consultores WHERE id_usuario = %s", (row[0],))
                cons = self.cur.fetchone()
                if cons:
                    datos["especialidad"] = cons[0]
                    datos["tarifa"] = float(cons[1])
            return datos
        except Exception as e:
            print(f"Error buscando usuario: {e}")
            return None

    def get_reservas_cliente(self, username):
        """Trae las reservas de un cliente específico"""
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cons.nombre, r.fecha, r.estado 
                FROM reservas r
                JOIN usuarios u_cli ON r.id_cliente = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cli.username = %s
                ORDER BY r.fecha DESC
            """, (username,))
            return self.cur.fetchall()
        except Exception as e:
            print(e)
            return []

    def get_reservas_consultor(self, username):
        """Trae las reservas asignadas a un consultor"""
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cli.nombre, r.fecha, r.estado
                FROM reservas r
                JOIN usuarios u_cli ON r.id_cliente = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cons.username = %s
                ORDER BY r.fecha ASC
            """, (username,))
            return self.cur.fetchall()
        except Exception as e:
            print(e)
            return []

    # --- LÓGICA DE NEGOCIO ---

    def autenticar(self, usuario, password):
        if not self.conn: return False, None
        try:
            self.cur.execute(
                "SELECT rol FROM usuarios WHERE username = %s AND password = %s",
                (usuario, password)
            )
            row = self.cur.fetchone()
            if row:
                return True, row[0]
            return False, None
        except Exception as e:
            print(f"Error auth: {e}")
            return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, email, rol="cliente", especialidad="General", tarifa=0):
        if not self.conn: return False, "Sin conexión"
        try:
            # 1. Insertamos el Usuario base
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, email, rol) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (usuario, password, nombre_completo, email, rol)
            )
            new_id = self.cur.fetchone()[0]
            
            # 2. Si es CONSULTOR, guardamos sus datos profesionales reales
            if rol == 'consultor':
                self.cur.execute(
                    "INSERT INTO consultores (id_usuario, tarifa, especialidad) VALUES (%s, %s, %s)",
                    (new_id, tarifa, especialidad)
                )
            return True, "Registro exitoso."
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False, "Usuario o correo ya existe."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        if not self.conn: return False, "Sin conexión"
        try:
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            if fecha_cita < datetime.now():
                return False, "No puedes reservar en el pasado."

            # Buscar IDs
            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            id_cli = self.cur.fetchone()[0]

            self.cur.execute("SELECT id FROM usuarios WHERE nombre = %s", (consultor_nombre,))
            res_cons = self.cur.fetchone()
            if not res_cons: return False, "Consultor no encontrado"
            id_cons = res_cons[0]

            # Insertar
            self.cur.execute(
                "INSERT INTO reservas (id_cliente, id_consultor, fecha, estado) VALUES (%s, %s, %s, 'Activa')",
                (id_cli, id_cons, fecha_cita)
            )
            return True, "Cita reservada con éxito."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    def cancelar_reserva(self, reserva_id):
        # --- AQUÍ ESTABA EL ERROR (Faltaba el código) ---
        if not self.conn: return False, "Sin conexión"
        try:
            self.cur.execute("SELECT fecha FROM reservas WHERE id = %s", (reserva_id,))
            res = self.cur.fetchone()
            if not res: return False, "Reserva no encontrada"
            
            fecha_cita = res[0]
            # Asegurar formato datetime de Python
            if hasattr(fecha_cita, 'to_pydatetime'): fecha_cita = fecha_cita.to_pydatetime()
            
            # Regla de cancelación 24 horas
            horas_restantes = (fecha_cita - datetime.now()).total_seconds() / 3600
            
            if horas_restantes < 24:
                return False, f"Falta muy poco ({int(horas_restantes)}h). No se puede cancelar."

            self.cur.execute("UPDATE reservas SET estado = 'Cancelada' WHERE id = %s", (reserva_id,))
            return True, "Reserva cancelada exitosamente."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    def finalizar_reserva(self, reserva_id, notas_consultor):
        if not self.conn: return False, "Sin conexión"
        try:
            # Actualizamos estado a 'Completada' y guardamos las notas
            self.cur.execute(
                "UPDATE reservas SET estado = 'Completada', notas = %s WHERE id = %s",
                (notas_consultor, reserva_id)
            )
            return True, "Cita finalizada y notas guardadas."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    def __del__(self):
        if hasattr(self, 'cur') and self.cur: self.cur.close()
        if hasattr(self, 'conn') and self.conn: self.conn.close()
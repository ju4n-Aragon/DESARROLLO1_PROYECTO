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
                SELECT u.nombre, c.tarifa, c.especialidad 
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario
            """)
            rows = self.cur.fetchall()
            # Ahora devolvemos también la especialidad
            return [{"nombre": row[0], "tarifa": float(row[1]), "especialidad": row[2]} for row in rows]
        except Exception as e:
            print(f"Error buscando consultores: {e}")
            return []

    def get_usuario(self, username):
        """Busca toda la info de un usuario (cliente o consultor)"""
        if not self.conn: return None
        try:
            self.cur.execute("SELECT id, nombre, rol FROM usuarios WHERE username = %s", (username,))
            row = self.cur.fetchone()
            if not row: return None
            
            datos = {"id": row[0], "nombre": row[1], "rol": row[2]}
            
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
                SELECT r.id, u_cons.nombre, r.fecha, r.estado, u_cons.email, r.notas
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
            # ¡IMPORTANTE! Agregamos u_cli.email y r.notas a la consulta
            self.cur.execute("""
                SELECT r.id, u_cli.nombre, r.fecha, r.estado, u_cli.email, r.notas
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

    def calcular_ganancias_consultor(self, usuario_consultor):
        """Suma las tarifas de todas las citas completadas"""
        if not self.conn: return 0
        try:
            sql = """
                SELECT SUM(c.tarifa)
                FROM reservas r
                JOIN usuarios u ON r.id_consultor = u.id
                JOIN consultores c ON u.id = c.id_usuario
                WHERE u.username = %s AND r.estado = 'Completada';
            """
            self.cur.execute(sql, (usuario_consultor,))
            resultado = self.cur.fetchone()[0]
            return float(resultado) if resultado else 0.0
        except Exception as e:
            print(f"Error calculando ganancias: {e}")
            return 0

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
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, email, rol) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (usuario, password, nombre_completo, email, rol)
            )
            new_id = self.cur.fetchone()[0]
            
            if rol == 'consultor':
                self.cur.execute(
                    "INSERT INTO consultores (id_usuario, tarifa, especialidad) VALUES (%s, %s, %s)",
                    (new_id, tarifa, especialidad)
                )
            return True, "Registro exitoso."
        except psycopg2.IntegrityError:
            self.conn.rollback() # Importante rollback si falla
            return False, "Usuario o correo ya existe."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {e}"

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        if not self.conn: return False, "Sin conexión"
        try:
            # Pequeño ajuste por si la fecha viene con T (formato HTML) o espacio
            fecha_str = fecha_str.replace("T", " ")
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            
            if fecha_cita < datetime.now():
                return False, "No puedes reservar en el pasado."

            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            id_cli = self.cur.fetchone()[0]

            self.cur.execute("SELECT id FROM usuarios WHERE nombre = %s", (consultor_nombre,))
            res_cons = self.cur.fetchone()
            if not res_cons: return False, "Consultor no encontrado"
            id_cons = res_cons[0]

            self.cur.execute(
                "INSERT INTO reservas (id_cliente, id_consultor, fecha, estado) VALUES (%s, %s, %s, 'Activa')",
                (id_cli, id_cons, fecha_cita)
            )
            return True, "Cita reservada con éxito."
        except Exception as e:
            print(e) # Para ver el error en consola
            self.conn.rollback()
            return False, f"Error: {e}"

    def actualizar_estado_cita(self, id_reserva, nuevo_estado, notas=""):
        """Método general para Cancelar o Completar citas desde el Dashboard"""
        if not self.conn: return False, "Sin conexión"
        try:
            sql = "UPDATE reservas SET estado = %s, notas = %s WHERE id = %s"
            self.cur.execute(sql, (nuevo_estado, notas, id_reserva))
            return True, "Estado actualizado."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error SQL: {e}"

    def __del__(self):
        if hasattr(self, 'cur') and self.cur: self.cur.close()
        if hasattr(self, 'conn') and self.conn: self.conn.close()
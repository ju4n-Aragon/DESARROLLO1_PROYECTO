import psycopg2
from datetime import datetime

class SistemaBackend:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="consultores_db",
                user="postgres",
                password="1234",  # <--- VERIFICA TU CONTRASEÑA
                host="localhost",
                port="5432"
            )
            # 🔴 CAMBIO 1: ¡Quitamos el autocommit! Ahora guardaremos manualmente.
            # self.conn.autocommit = True 
            
            self.cur = self.conn.cursor()
            print("Conexión a Base de Datos Exitosa.")
        except Exception as e:
            print(f"Error crítico conectando a BD: {e}")
            self.conn = None

    # --- LECTURAS (No requieren commit) ---

    def get_consultores_disponibles(self):
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT u.nombre, c.tarifa, c.especialidad 
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario
            """)
            rows = self.cur.fetchall()
            return [{"nombre": row[0], "tarifa": float(row[1]), "especialidad": row[2]} for row in rows]
        except Exception as e:
            print(f"Error buscando consultores: {e}")
            return []

    def get_usuario(self, username):
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
                    datos["especialidad"], datos["tarifa"] = cons[0], float(cons[1])
            return datos
        except Exception as e:
            print(f"Error buscando usuario: {e}")
            return None

    def get_reservas_cliente(self, username):
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cons.nombre, r.fecha, r.estado, u_cons.email, r.notas
                FROM reservas r
                JOIN usuarios u_cli ON r.id_cliente = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cli.username = %s ORDER BY r.fecha DESC
            """, (username,))
            return self.cur.fetchall()
        except Exception as e:
            print(e); return []

    def get_reservas_consultor(self, username):
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cli.nombre, r.fecha, r.estado, u_cli.email, r.notas
                FROM reservas r
                JOIN usuarios u_cli ON r.id_cliente = u_cli.id
                JOIN usuarios u_cons ON r.id_consultor = u_cons.id
                WHERE u_cons.username = %s ORDER BY r.fecha ASC
            """, (username,))
            return self.cur.fetchall()
        except Exception as e:
            print(e); return []

    def calcular_ganancias_consultor(self, usuario_consultor):
        if not self.conn: return 0
        try:
            sql = """SELECT SUM(c.tarifa) FROM reservas r
                     JOIN usuarios u ON r.id_consultor = u.id
                     JOIN consultores c ON u.id = c.id_usuario
                     WHERE u.username = %s AND r.estado = 'Completada'"""
            self.cur.execute(sql, (usuario_consultor,))
            res = self.cur.fetchone()[0]
            return float(res) if res else 0.0
        except Exception: return 0

    # --- ESCRITURAS (Requieren COMMIT) ---

    def autenticar(self, usuario, password):
        if not self.conn: return False, None
        try:
            self.cur.execute("SELECT rol FROM usuarios WHERE username = %s AND password = %s", (usuario, password))
            row = self.cur.fetchone()
            return (True, row[0]) if row else (False, None)
        except Exception: return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, email, rol="cliente", especialidad="General", tarifa=0):
        if not self.conn: return False, "Sin conexión"
        try:
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, email, rol) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (usuario, password, nombre_completo, email, rol)
            )
            new_id = self.cur.fetchone()[0]
            if rol == 'consultor':
                self.cur.execute("INSERT INTO consultores (id_usuario, tarifa, especialidad) VALUES (%s, %s, %s)", (new_id, tarifa, especialidad))
            
            self.conn.commit() # 🟢 CAMBIO 2: Guardado Obligatorio
            return True, "Registro exitoso."
        except psycopg2.IntegrityError:
            self.conn.rollback(); return False, "Usuario ya existe."
        except Exception as e:
            self.conn.rollback(); return False, f"Error: {e}"

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        if not self.conn: return False, "Sin conexión"
        try:
            fecha_cita = datetime.strptime(fecha_str.replace("T", " "), "%Y-%m-%d %H:%M")
            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            id_cli = self.cur.fetchone()[0]
            self.cur.execute("SELECT id FROM usuarios WHERE nombre = %s", (consultor_nombre,))
            res_cons = self.cur.fetchone()
            if not res_cons: return False, "Consultor no existe"
            
            self.cur.execute("INSERT INTO reservas (id_cliente, id_consultor, fecha, estado) VALUES (%s, %s, %s, 'Activa')", 
                             (id_cli, res_cons[0], fecha_cita))
            
            self.conn.commit() # 🟢 CAMBIO 3: Guardado Obligatorio
            return True, "Cita reservada."
        except Exception as e:
            self.conn.rollback(); return False, f"Error: {e}"

    def actualizar_estado_cita(self, id_reserva, nuevo_estado, notas=""):
        if not self.conn: return False, "Sin conexión"
        try:
            # CHIVATO: Veremos esto en la terminal antes de que intente guardar
            print(f"DEBUG SQL: UPDATE reservas SET estado='{nuevo_estado}', notas='{notas}' WHERE id={id_reserva}")
            
            sql = "UPDATE reservas SET estado = %s, notas = %s WHERE id = %s"
            self.cur.execute(sql, (nuevo_estado, notas, id_reserva))
            
            # ¡EL MOMENTO DE LA VERDAD!
            self.conn.commit()
            
            # Verificar si realmente se actualizó alguna fila
            if self.cur.rowcount == 0:
                print("DEBUG: ¡OJO! La base de datos dice que se actualizaron 0 filas. ¿El ID existe?")
                return False, "No se encontró la reserva o no se pudo actualizar ."
            
            return True, "Estado actualizado correctamente."
        except Exception as e:
            self.conn.rollback()
            print(f"ERROR CRÍTICO SQL: {e}") # Si hay error, saldrá aquí
            return False, f"Error SQL: {e}"

    def __del__(self):
        if hasattr(self, 'cur') and self.cur: self.cur.close()
        if hasattr(self, 'conn') and self.conn: self.conn.close()
import psycopg2
from datetime import datetime

class SistemaBackend:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="consultores_db",
                user="postgres",
                password="1234",  
                host="localhost",
                port="5432"
            )
            
            self.conn.autocommit = False 
            self.cur = self.conn.cursor()
            print("Conexión a Base de Datos Exitosa (Modo Seguro).")
        except Exception as e:
            print(f"Error crítico conectando a BD: {e}")
            self.conn = None

    # ==========================================
    # LECTURAS (SELECTS)
    # ==========================================

    def get_consultores_disponibles(self):
        """Obtiene la lista de consultores con todos los detalles"""
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT u.nombre, c.tarifa, c.especialidad, 
                       c.descripcion, c.experiencia_anos, 
                       c.porcentaje_descuento, c.primera_cita_descuento
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario
                ORDER BY u.nombre
            """)
            rows = self.cur.fetchall()
            
            resultado = []
            for row in rows:
                tarifa = float(row[1])
                pct_descuento = float(row[5]) if row[5] else 0.0
                tiene_descuento = row[6] if row[6] is not None else False
                
                # Calculamos precio visual
                if tiene_descuento and pct_descuento > 0:
                    precio_promo = tarifa - (tarifa * (pct_descuento / 100))
                    descuento_txt = f"{int(pct_descuento)}% OFF"
                else:
                    precio_promo = tarifa
                    descuento_txt = "" 
                
                resultado.append({
                    "nombre": row[0],
                    "tarifa": tarifa,
                    "especialidad": row[2],
                    "descripcion": row[3] or "Sin descripción disponible",
                    "experiencia": row[4] or 0,
                    "descuento_txt": descuento_txt,
                    "precio_final_estimado": round(precio_promo, 2)
                })
            return resultado
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
                    datos["especialidad"] = cons[0]
                    datos["tarifa"] = float(cons[1])
            return datos
        except Exception as e:
            print(f"Error buscando usuario: {e}")
            return None

    def get_reservas_cliente(self, username):
        if not self.conn: return []
        try:
            self.cur.execute("""
                SELECT r.id, u_cons.nombre, r.fecha, r.estado, u_cons.email, r.notas, r.costo_final
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
                SELECT r.id, u_cli.nombre, r.fecha, r.estado, u_cli.email, r.notas, r.costo_final
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
            self.cur.execute("""
                SELECT SUM(r.costo_final) FROM reservas r
                JOIN usuarios u ON r.id_consultor = u.id
                WHERE u.username = %s AND r.estado = 'Completada'
            """, (usuario_consultor,))
            res = self.cur.fetchone()[0]
            return float(res) if res else 0.0
        except Exception: return 0

    def obtener_estadisticas_admin(self):
        if not self.conn: return {}
        try:
            stats = {}
            self.cur.execute("SELECT SUM(costo_final) FROM reservas WHERE estado = 'Completada'")
            res = self.cur.fetchone()[0]
            stats['ingresos_totales'] = float(res) if res else 0.0
            
            self.cur.execute("SELECT COUNT(*) FROM usuarios")
            stats['total_usuarios'] = self.cur.fetchone()[0]
            
            self.cur.execute("""
                SELECT u.nombre, COUNT(r.id) as total 
                FROM reservas r 
                JOIN usuarios u ON r.id_consultor = u.id 
                WHERE r.estado = 'Completada' 
                GROUP BY u.nombre 
                ORDER BY total DESC LIMIT 1
            """)
            row = self.cur.fetchone()
            stats['consultor_top'] = f"{row[0]} ({row[1]} citas)" if row else "Nadie aún"
            return stats
        except Exception: return {}

    # ==========================================
    # ESCRITURAS (INSERTS/UPDATES) -
    # ==========================================

    def autenticar(self, usuario, password):
        if not self.conn: return False, None
        try:
            self.cur.execute("SELECT rol, id FROM usuarios WHERE username = %s AND password = %s", (usuario, password))
            row = self.cur.fetchone()
            if row:
                return True, row[0]
            return False, None
        except Exception: return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, email, 
                          rol="cliente", especialidad="General", tarifa=0,
                          descripcion="", experiencia_anos=0, 
                          primera_cita_descuento=False, porcentaje_descuento=0):
        
        # --- VALIDACIÓN DE SEGURIDAD MEJORADA ---
        # 1. Validar Longitud
        if len(password) < 8:
            return False, "La contraseña debe tener al menos 8 caracteres."

        # 2. Validar Complejidad (Mayúscula O Carácter Especial)
        # c.isalnum() devuelve True si es letra o número. Si es False, es un símbolo (*, !, @, espacio, etc.)
        tiene_mayuscula = any(c.isupper() for c in password)
        tiene_especial = any(not c.isalnum() for c in password) 

        if not (tiene_mayuscula or tiene_especial):
            return False, "La contraseña debe incluir al menos una Mayúscula o un Carácter Especial (*, !, $, etc)."
        # ---------------------------------------

        if not self.conn: return False, "Sin conexión"
        try:
            # 1. Insertar Usuario
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, email, rol) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (usuario, password, nombre_completo, email, rol)
            )
            new_id = self.cur.fetchone()[0]
            
            # 2. Si es consultor, insertar detalles
            if rol == 'consultor':
                tiene_desc = 't' if primera_cita_descuento else 'f'
                self.cur.execute("""
                    INSERT INTO consultores 
                    (id_usuario, tarifa, especialidad, descripcion, experiencia_anos, primera_cita_descuento, porcentaje_descuento) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (new_id, tarifa, especialidad, descripcion, experiencia_anos, tiene_desc, porcentaje_descuento)
                )
            
            self.conn.commit()
            return True, "Registro exitoso."
            
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False, "El usuario o correo ya existen."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error técnico: {e}"

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        if not self.conn: return False, "Sin conexión"
        try:
            fecha_str = fecha_str.replace("T", " ")
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            if fecha_cita < datetime.now(): return False, "Fecha inválida (pasado)."

            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            row_cli = self.cur.fetchone()
            if not row_cli: return False, "Cliente no encontrado"
            id_cli = row_cli[0]

            self.cur.execute("""
                SELECT u.id, c.tarifa, c.porcentaje_descuento, c.primera_cita_descuento
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario 
                WHERE u.nombre = %s
            """, (consultor_nombre,))
            
            res_cons = self.cur.fetchone()
            if not res_cons: return False, "Consultor no existe"
            
            id_cons = res_cons[0]
            tarifa_base = float(res_cons[1])
            descuento_pct = float(res_cons[2]) if res_cons[2] else 0.0
            
            monto_descuento = tarifa_base * (descuento_pct / 100)
            precio_final = tarifa_base - monto_descuento

            self.cur.execute(
                """INSERT INTO reservas (id_cliente, id_consultor, fecha, estado, costo_final) 
                   VALUES (%s, %s, %s, 'Activa', %s)""", 
                (id_cli, id_cons, fecha_cita, precio_final)
            )
            
            self.conn.commit()
            return True, f"Reserva exitosa. Total a pagar: ${precio_final:.2f}"

        except Exception as e:
            self.conn.rollback()
            print(e)
            return False, f"Error al reservar: {e}"

    def actualizar_estado_cita(self, id_reserva, nuevo_estado, calificacion=0, notas=""):
        if not self.conn: return False, "Sin conexión"
        try:
            self.cur.execute("SELECT costo_final FROM reservas WHERE id = %s", (id_reserva,))
            row = self.cur.fetchone()
            if not row: return False, "Reserva no encontrada"
            
            costo_final = float(row[0])

            # Si se Cancela: El costo final es 0
            if nuevo_estado == 'Cancelada':
                costo_final = 0.0
                if notas == "": notas = "Cancelada por una de las partes."
            
            sql = """
                UPDATE reservas 
                SET estado = %s, calificacion = %s, notas = %s, costo_final = %s
                WHERE id = %s
            """
            self.cur.execute(sql, (nuevo_estado, int(calificacion), notas, costo_final, id_reserva))
            self.conn.commit()
            
            return True, f"Estado actualizado a '{nuevo_estado}'."
            
        except Exception as e:
            self.conn.rollback()
            return False, f"Error SQL: {e}"

    def __del__(self):
        if hasattr(self, 'cur') and self.cur: self.cur.close()
        if hasattr(self, 'conn') and self.conn: self.conn.close()
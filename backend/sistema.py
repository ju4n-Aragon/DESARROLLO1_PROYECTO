import psycopg2
from datetime import datetime, timedelta

class SistemaBackend:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="consultores_db",
                user="postgres",
                password="1234",  # <--- ASEGÚRATE DE QUE SEA LA CONTRASEÑA CORRECTA
                host="localhost",
                port="5432"
            )
            # USAMOS TU LÓGICA: Autocommit False para seguridad transaccional
            self.conn.autocommit = False 
            self.cur = self.conn.cursor()
            print("Conexión a Base de Datos Exitosa (Modo Seguro).")
        except Exception as e:
            print(f"Error crítico conectando a BD: {e}")
            self.conn = None

    # ==========================================
    # LECTURAS (SELECTS) - No requieren commit
    # ==========================================

    def get_consultores_disponibles(self):
        """Combina tu estructura con los datos detallados de tu compañero"""
        if not self.conn: return []
        try:
            # Traemos todos los datos ricos (descripción, experiencia, etc.)
            self.cur.execute("""
                SELECT u.nombre, c.tarifa, c.especialidad, 
                       c.descripcion, c.experiencia_anos, 
                       c.porcentaje_descuento
                FROM usuarios u 
                JOIN consultores c ON u.id = c.id_usuario
                ORDER BY u.nombre
            """)
            rows = self.cur.fetchall()
            
            resultado = []
            for row in rows:
                tarifa = float(row[1])
                # Lógica de él: porcentaje dinámico | Si es None, es 0
                pct_descuento = float(row[5]) if row[5] else 0.0
                
                # Calculamos precio visual para mostrar en el frontend
                precio_promo = tarifa - (tarifa * (pct_descuento / 100))
                
                resultado.append({
                    "nombre": row[0],
                    "tarifa": tarifa,
                    "especialidad": row[2],
                    "descripcion": row[3] or "Sin descripción",
                    "experiencia": row[4] or 0,
                    "descuento_txt": f"{int(pct_descuento)}%" if pct_descuento > 0 else "0%",
                    "precio_final_estimado": round(precio_promo, 2)
                })
            return resultado
        except Exception as e:
            print(f"Error buscando consultores: {e}")
            return []

    def get_usuario(self, username):
        """Busca info básica del usuario"""
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
        # Usamos TU lógica (más precisa): sumar el costo_final real guardado
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
        """Estadísticas generales (Aporte tuyo)"""
        if not self.conn: return {}
        try:
            stats = {}
            # Ingresos reales
            self.cur.execute("SELECT SUM(costo_final) FROM reservas WHERE estado = 'Completada'")
            res = self.cur.fetchone()[0]
            stats['ingresos_totales'] = float(res) if res else 0.0
            
            # Cantidad usuarios
            self.cur.execute("SELECT COUNT(*) FROM usuarios")
            stats['total_usuarios'] = self.cur.fetchone()[0]
            
            # Consultor Top
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
    # ESCRITURAS (INSERTS/UPDATES) - Requieren COMMIT
    # ==========================================

    def autenticar(self, usuario, password):
        if not self.conn: return False, None
        try:
            self.cur.execute("SELECT rol FROM usuarios WHERE username = %s AND password = %s", (usuario, password))
            row = self.cur.fetchone()
            return (True, row[0]) if row else (False, None)
        except Exception: return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, email, 
                          rol="cliente", especialidad="General", tarifa=0,
                          # Campos extra de tu compañero
                          descripcion="", experiencia_anos=0, 
                          primera_cita_descuento=False, porcentaje_descuento=0):
        
        if not self.conn: return False, "Sin conexión"
        try:
            # 1. Insertar Usuario (Tabla común)
            self.cur.execute(
                "INSERT INTO usuarios (username, password, nombre, email, rol) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (usuario, password, nombre_completo, email, rol)
            )
            new_id = self.cur.fetchone()[0]
            
            # 2. Si es consultor, insertar detalles (Fusión de ambos códigos)
            if rol == 'consultor':
                # Convertimos checkbox a booleano si viene como True/False de Python
                tiene_desc = 't' if primera_cita_descuento else 'f'
                
                self.cur.execute("""
                    INSERT INTO consultores 
                    (id_usuario, tarifa, especialidad, descripcion, experiencia_anos, primera_cita_descuento, porcentaje_descuento) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (new_id, tarifa, especialidad, descripcion, experiencia_anos, tiene_desc, porcentaje_descuento)
                )
            
            self.conn.commit() # Guardado seguro
            return True, "Registro exitoso."
            
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False, "El usuario o correo ya existen."
        except Exception as e:
            self.conn.rollback()
            return False, f"Error técnico: {e}"

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        """
        Fusión inteligente: 
        1. Usa el descuento ESPECÍFICO del consultor (idea de él).
        2. Guarda el PRECIO FINAL en la reserva (idea tuya, vital para contabilidad).
        """
        if not self.conn: return False, "Sin conexión"
        try:
            fecha_str = fecha_str.replace("T", " ")
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            if fecha_cita < datetime.now(): return False, "Fecha inválida (pasado)."

            # 1. Obtener Cliente
            self.cur.execute("SELECT id FROM usuarios WHERE username = %s", (usuario_cliente,))
            row_cli = self.cur.fetchone()
            if not row_cli: return False, "Cliente no encontrado"
            id_cli = row_cli[0]

            # 2. Obtener Consultor, Tarifa Y SU DESCUENTO PERSONALIZADO
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
            # Si tiene descuento configurado, lo usamos. Si no, es 0.
            descuento_pct = float(res_cons[2]) if res_cons[2] else 0.0
            
            # 3. Calcular Precio Final
            monto_descuento = tarifa_base * (descuento_pct / 100)
            precio_final = tarifa_base - monto_descuento

            # 4. Insertar Reserva guardando el costo histórico
            self.cur.execute(
                """INSERT INTO reservas (id_cliente, id_consultor, fecha, estado, costo_final) 
                   VALUES (%s, %s, %s, 'Activa', %s)""", 
                (id_cli, id_cons, fecha_cita, precio_final)
            )
            
            self.conn.commit()
            return True, f"Reserva exitosa. Total a pagar: ${precio_final:.2f} (Desc: {int(descuento_pct)}%)"

        except Exception as e:
            self.conn.rollback()
            print(e)
            return False, f"Error al reservar: {e}"

    def actualizar_estado_cita(self, id_reserva, nuevo_estado, calificacion=0, notas=""):
        if not self.conn: return False, "Sin conexión"
        try:
            # 1. Recuperamos el precio original pactado
            self.cur.execute("SELECT costo_final FROM reservas WHERE id = %s", (id_reserva,))
            row = self.cur.fetchone()
            if not row: return False, "Reserva no encontrada"
            
            costo_final = float(row[0])

            # 2. LÓGICA DE VIDA REAL:
            # - Si se Cancela: El costo final es 0 (nadie cobra, nadie paga).
            # - Si se Completa: El costo se mantiene (se paga lo acordado), sin importar la nota.
            
            if nuevo_estado == 'Cancelada':
                costo_final = 0.0
                if notas == "": notas = "Cancelada por una de las partes."
            
            # 3. Guardamos
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
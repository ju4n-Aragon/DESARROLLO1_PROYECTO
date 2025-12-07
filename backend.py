from datetime import datetime

class SistemaBackend:
    def __init__(self):
        # --- BASE DE DATOS SIMULADA ---
        
        # 1. USUARIOS (Simulando la clase Padre 'Usuario' del diagrama)
        self.usuarios = {
            "admin": {
                "pass": "1234", 
                "nombre": "Administrador", 
                "rol": "admin"
            },
            "cliente": {
                "pass": "1234", 
                "nombre": "Cliente Pruebas", 
                "rol": "cliente"
            },
            #Usuario Consultor (Según diagrama: hereda de Usuario)
            "ana": {
                "pass": "1234", 
                "nombre": "Dra. Ana (Finanzas)", 
                "rol": "consultor",
                "tarifa": 100.0,          # Atributo del diagrama
                "especialidad": "Finanzas" # Atributo del diagrama
            }
        }
        
        # Lista pública para el combobox (Dropdown)
        # Nota: El nombre debe coincidir con el del usuario consultor para que funcione el enlace
        self.consultores_disponibles = [
            {"id": 1, "nombre": "Dra. Ana (Finanzas)", "tarifa": 100},
            {"id": 2, "nombre": "Ing. Carlos (Tecnología)", "tarifa": 150},
            {"id": 3, "nombre": "Lic. Sofia (Marketing)", "tarifa": 120}
        ]
        
        self.reservas = [] 

    def autenticar(self, usuario, password):
        """Valida credenciales y retorna el ROL si es exitoso"""
        if usuario in self.usuarios and self.usuarios[usuario]["pass"] == password:
            return True, self.usuarios[usuario]["rol"]
        return False, None

    def registrar_usuario(self, usuario, password, nombre_completo, rol="cliente"):
        if usuario in self.usuarios:
            return False, "El usuario ya existe."
        if len(password) < 4:
            return False, "Contraseña muy corta."

        self.usuarios[usuario] = {
            "pass": password,
            "nombre": nombre_completo,
            "rol": rol # Por defecto cliente, pero escalable a consultor
        }
        return True, "Registro exitoso."

    def crear_reserva(self, usuario_cliente, consultor_nombre, fecha_str):
        try:
            fecha_cita = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
            if fecha_cita < datetime.now():
                return False, "No puedes reservar en el pasado."

            nueva_reserva = {
                "id": len(self.reservas) + 1,
                "cliente": usuario_cliente,        # Relación con Cliente
                "consultor": consultor_nombre,     # Relación con Consultor
                "fecha": fecha_cita,
                "estado": "Activa" # Enum del diagrama (pendiente/confirmada/etc)
            }
            self.reservas.append(nueva_reserva)
            return True, "Cita reservada con éxito."
        except ValueError:
            return False, "Formato fecha inválido."

    def cancelar_reserva(self, reserva_id):
        for r in self.reservas:
            if r["id"] == reserva_id:
                tiempo = r["fecha"] - datetime.now()
                horas = tiempo.total_seconds() / 3600
                if horas < 24:
                    return False, "Falta menos de 24h. Política estricta."
                r["estado"] = "Cancelada"
                return True, "Reserva cancelada."
        return False, "Reserva no encontrada."

    def obtener_estadisticas(self):
        # Lógica para Admin
        total = len(self.reservas)
        activas = len([r for r in self.reservas if r["estado"] == "Activa"])
        return f"Total: {total} | Activas: {activas}"

    # --- NUEVA LÓGICA PARA EL CONSULTOR ---
    def obtener_reservas_por_consultor(self, nombre_consultor):
        """ Filtra las citas donde el consultor es el asignado """
        mis_citas = []
        for r in self.reservas:
            # Comparamos el nombre del consultor logueado con el de la reserva
            if r["consultor"] == nombre_consultor:
                mis_citas.append(r)
        return mis_citas
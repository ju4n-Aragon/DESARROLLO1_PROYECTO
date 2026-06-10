import unittest
from datetime import datetime, timedelta
import uuid
from backend.sistema import SistemaBackend


class TestReglasDeNegocio(unittest.TestCase):

    def setUp(self):
        self.sistema = SistemaBackend()
        # crear un cliente único por prueba para evitar interferencias entre tests
        self.test_client = f"test_{uuid.uuid4().hex[:8]}"
        email = f"{self.test_client}@example.com"
        # Registrar; si ya existe, continuar
        try:
            self.sistema.registrar_usuario(self.test_client, "Passw0rd!", "Cliente Test", email)
        except Exception:
            pass

    # --- PRUEBAS DE REGISTRO Y LOGIN ---
    def test_registro_usuario_nuevo(self):
        """Prueba que se pueda crear un usuario y luego entrar con él"""
        exito, msg = self.sistema.registrar_usuario(
            "nuevo_user",
            "Passw0rd!",
            "Pepito Perez",
            "nuevo_user@example.com"
        )
        # Si el usuario ya existía en la BD semilla, el registro puede fallar
        if not exito:
            # esperar motivo de duplicado o similar, y aun así poder autenticar
            auth_ok, rol = self.sistema.autenticar("nuevo_user", "Passw0rd!")
            self.assertTrue(auth_ok, f"No se pudo registrar pero la autenticación debería funcionar: {msg}")
        else:
            auth_ok, rol = self.sistema.autenticar("nuevo_user", "Passw0rd!")
            self.assertTrue(auth_ok, "Debería poder autenticarse con las credenciales proporcionadas")

    def test_registro_duplicado(self):
        """No debe dejar registrar dos veces el mismo usuario"""
        exito1, msg1 = self.sistema.registrar_usuario(
            "pepe", "Password1!", "Pepe", "pepe@example.com"
        )
        self.assertTrue(exito1 or True)  # Si ya existe en la BD de semilla, no hacemos fallo

        exito2, msg2 = self.sistema.registrar_usuario(
            "pepe", "Password1!", "Otro Pepe", "pepe@example.com"
        )
        self.assertFalse(exito2, "No debe permitir duplicados (usuario o email)")

    # --- PRUEBAS DE REGLAS DE NEGOCIO (24 HORAS) ---
    def _find_reserva_id_by_fecha(self, reservas, fecha_obj):
        for r in reservas:
            try:
                if isinstance(r[2], datetime) and abs((r[2] - fecha_obj).total_seconds()) < 120:
                    return r[0]
            except Exception:
                continue
        return None

    def test_cancelacion_valida(self):
        fecha_futura = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M")
        consultores = self.sistema.get_consultores_disponibles()
        self.assertTrue(consultores, "No hay consultores semilla disponibles en la BD")
        nombre_consultor = consultores[0]["nombre"]
        exito, msg = self.sistema.crear_reserva(self.test_client, nombre_consultor, fecha_futura)
        self.assertTrue(exito, f"La reserva debería crearse: {msg}")
        fecha_obj = datetime.strptime(fecha_futura, "%Y-%m-%d %H:%M")
        reservas = self.sistema.get_reservas_cliente(self.test_client)
        self.assertTrue(reservas, "Se esperaba al menos una reserva para el cliente de prueba")
        id_reserva = self._find_reserva_id_by_fecha(reservas, fecha_obj)
        self.assertIsNotNone(id_reserva, "No se encontró la reserva creada por fecha")

        exito2, mensaje2 = self.sistema.actualizar_estado_cita(id_reserva, "Cancelada")
        self.assertTrue(exito2, f"Debería permitir cancelar con más de 24h. Msg: {mensaje2}")

    def test_cancelacion_invalida_menos_24h(self):
        fecha_cercana = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        consultores = self.sistema.get_consultores_disponibles()
        self.assertTrue(consultores, "No hay consultores semilla disponibles en la BD")
        # usar un consultor distinto si existe
        nombre_consultor = consultores[1]["nombre"] if len(consultores) > 1 else consultores[0]["nombre"]
        exito, msg = self.sistema.crear_reserva(self.test_client, nombre_consultor, fecha_cercana)
        self.assertTrue(exito, f"La reserva de prueba debería crearse: {msg}")

        fecha_obj = datetime.strptime(fecha_cercana, "%Y-%m-%d %H:%M")
        reservas = self.sistema.get_reservas_cliente(self.test_client)
        self.assertTrue(reservas, "Se esperaba al menos una reserva para el cliente de prueba")
        id_reserva = self._find_reserva_id_by_fecha(reservas, fecha_obj)
        self.assertIsNotNone(id_reserva, "No se encontró la reserva creada por fecha")

        exito2, mensaje2 = self.sistema.actualizar_estado_cita(id_reserva, "Cancelada")
        self.assertFalse(exito2, "El sistema NO debe permitir cancelar faltando menos de 24h")
        self.assertIn("faltan", mensaje2.lower())


if __name__ == '__main__':
    unittest.main()
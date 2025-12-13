import unittest
from datetime import datetime, timedelta
from backend import SistemaBackend

class TestReglasDeNegocio(unittest.TestCase):
    
    def setUp(self):
        self.sistema = SistemaBackend()

    # --- PRUEBAS DE REGISTRO Y LOGIN ---
    def test_registro_usuario_nuevo(self):
        """Prueba que se pueda crear un usuario y luego entrar con él"""
        # 1. Registramos
        exito, msg = self.sistema.registrar_usuario("nuevo_user", "pass123", "Pepito Perez")
        self.assertTrue(exito, "El registro debería ser exitoso")
        
        # 2. Intentamos entrar con ese usuario nuevo
        login = self.sistema.autenticar("nuevo_user", "pass123")
        self.assertTrue(login, "Debería poder loguearse con el usuario recién creado")

    def test_registro_duplicado(self):
        """No debe dejar registrar dos veces el mismo usuario"""
        self.sistema.registrar_usuario("pepe", "12345", "Pepe")
        exito, msg = self.sistema.registrar_usuario("pepe", "99999", "Otro Pepe")
        self.assertFalse(exito, "No debe permitir duplicados")

    # --- PRUEBAS DE REGLAS DE NEGOCIO (24 HORAS) ---
    def test_cancelacion_valida(self):
        # Primero necesitamos un usuario válido en el sistema nuevo
        fecha_futura = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d %H:%M")
        self.sistema.crear_reserva("admin", "Dra. Ana", fecha_futura)
        
        exito, mensaje = self.sistema.cancelar_reserva(1)
        self.assertTrue(exito, f"Debería dejar cancelar. Msg: {mensaje}")

    def test_cancelacion_invalida_menos_24h(self):
        fecha_cercana = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        self.sistema.crear_reserva("admin", "Ing. Carlos", fecha_cercana)
        
        exito, mensaje = self.sistema.cancelar_reserva(1)
        
        self.assertFalse(exito, "El sistema NO debe permitir cancelar faltando menos de 24h")
        self.assertIn("Falta menos de 24h", mensaje)

if __name__ == '__main__':
    unittest.main()
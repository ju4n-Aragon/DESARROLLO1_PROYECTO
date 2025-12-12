import tkinter as tk
# Importamos las clases de los otros archivos que creamos
from backend import SistemaBackend
from interfaz import AppInterfaz

if __name__ == "__main__":
    # 1. Inicializamos la Lógica (Backend)
    mi_sistema = SistemaBackend()
    
    # 2. Inicializamos la ventana base de Tkinter
    root = tk.Tk()
    
    # 3. Inicializamos la Interfaz y le "inyectamos" el backend
    #    Esto conecta la vista con la lógica
    app = AppInterfaz(root, mi_sistema)
    
    # 4. Arrancamos la aplicación
    root.mainloop()
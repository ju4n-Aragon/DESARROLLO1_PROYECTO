# Updated interfaz.py (con cambios para usar métodos de DB y completar registro)
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import os
from PIL import Image, ImageTk  # pip install pillow

class AppInterfaz:
    def __init__(self, root, backend):
        self.backend = backend
        self.root = root
        self.root.title("Consultores Expertos S.A.S")
        self.root.geometry("950x650")
        self.root.resizable(False, False)
        
        self.colors = {
            "primary": "#2C3E50",    # Azul oscuro corporativo
            "secondary": "#3498DB",  # Azul claro para botones
            "accent": "#E74C3C",     # Rojo para cancelar/salir
            "bg": "#ECF0F1",   # Gris muy claro para fondo
            "white": "#FFFFFF",
            "text": "#2C3E50"
        }
        
        self.usuario_actual = None
        self.rol_actual = None  # Para saber si es Cliente o Consultor

        self.container = tk.Frame(root, bg=self.colors["bg"])
        self.container.pack(fill="both", expand=True)

        self.mostrar_login()

    def limpiar(self):
        for widget in self.container.winfo_children(): widget.destroy()

    def cargar_img(self, path, size):
        if os.path.exists(path):
            return ImageTk.PhotoImage(Image.open(path).resize(size))
        return None

    # --- LOGIN ---
    def mostrar_login(self):
        self.limpiar()
        # Fondo (simulado si no hay imagen)
        self.bg_img = self.cargar_img("img/fondo_login.jpg", (950, 650))
        if self.bg_img: tk.Label(self.container, image=self.bg_img).place(x=0, y=0)
        
        card = tk.Frame(self.container, bg="white", padx=30, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=350, height=450)
        
        tk.Label(card, text="Acceso Sistema", font=("Arial", 18, "bold"), bg="white").pack(pady=10)
        tk.Label(card, text="(Prueba: ana / 1234)", font=("Arial", 8), fg="gray", bg="white").pack()

        tk.Label(card, text="Usuario", bg="white").pack(anchor="w")
        self.entry_user = ttk.Entry(card); self.entry_user.pack(fill="x", pady=5)
        
        tk.Label(card, text="Contraseña", bg="white").pack(anchor="w")
        self.entry_pass = ttk.Entry(card, show="*"); self.entry_pass.pack(fill="x", pady=5)

        tk.Button(card, text="INGRESAR", command=self.validar_login, bg=self.colors["primary"], fg="white", pady=5).pack(fill="x", pady=20)
        tk.Button(card, text="Registrarse (Cliente)", command=self.mostrar_registro, bg="white", fg=self.colors["secondary"], relief="flat").pack()

    def validar_login(self):
        user = self.entry_user.get()
        pwd = self.entry_pass.get()
        exito, rol = self.backend.autenticar(user, pwd)
        
        if exito:
            self.usuario_actual = user
            self.rol_actual = rol
            # DIRECCIONAMIENTO SEGÚN ROL (Diagrama: Usuario -> Cliente/Consultor)
            if rol == "consultor":
                self.mostrar_panel_consultor()
            else:
                self.mostrar_panel_cliente()
        else:
            messagebox.showerror("Error", "Credenciales incorrectas")

    # --- REGISTRO (Completado) ---
    def mostrar_registro(self):
        self.limpiar()
        # Fondo similar
        self.bg_img = self.cargar_img("img/fondo_login.jpg", (950, 650))
        if self.bg_img: tk.Label(self.container, image=self.bg_img).place(x=0, y=0)
        
        card = tk.Frame(self.container, bg="white", padx=30, pady=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=350, height=450)
        
        tk.Label(card, text="Registro de Cliente", font=("Arial", 18, "bold"), bg="white").pack(pady=10)

        tk.Label(card, text="Usuario", bg="white").pack(anchor="w")
        self.entry_reg_user = ttk.Entry(card); self.entry_reg_user.pack(fill="x", pady=5)
        
        tk.Label(card, text="Contraseña", bg="white").pack(anchor="w")
        self.entry_reg_pass = ttk.Entry(card, show="*"); self.entry_reg_pass.pack(fill="x", pady=5)
        
        tk.Label(card, text="Nombre Completo", bg="white").pack(anchor="w")
        self.entry_reg_nombre = ttk.Entry(card); self.entry_reg_nombre.pack(fill="x", pady=5)

        tk.Button(card, text="REGISTRAR", command=self.registrar, bg=self.colors["secondary"], fg="white", pady=5).pack(fill="x", pady=20)
        tk.Button(card, text="Volver al Login", command=self.mostrar_login, bg="white", fg=self.colors["primary"], relief="flat").pack()

    def registrar(self):
        user = self.entry_reg_user.get()
        pwd = self.entry_reg_pass.get()
        nombre = self.entry_reg_nombre.get()
        exito, msg = self.backend.registrar_usuario(user, pwd, nombre, rol="cliente")
        if exito:
            messagebox.showinfo("Éxito", msg)
            self.mostrar_login()
        else:
            messagebox.showerror("Error", msg)

    # --- PANEL CLIENTE 
    def mostrar_panel_cliente(self):
        self.limpiar()
        self.header(f"Panel Cliente: {self.usuario_actual}")
        
        content = tk.Frame(self.container, bg=self.colors["bg"], padx=20, pady=20)
        content.pack(fill="both", expand=True)

        # Izquierda: Reservar
        left = tk.Frame(content, bg="white", padx=15, pady=15)
        left.pack(side="left", fill="y", padx=10)
        
        tk.Label(left, text="Nueva Reserva", font=("Arial", 12, "bold"), bg="white").pack(anchor="w")
        
        tk.Label(left, text="Consultor:", bg="white").pack(anchor="w", pady=5)
        consultores = self.backend.get_consultores_disponibles()
        self.combo_cons = ttk.Combobox(left, values=[c["nombre"] for c in consultores])
        self.combo_cons.pack(fill="x")
        if consultores:
            self.combo_cons.current(0)
        
        tk.Label(left, text="Fecha (AAAA-MM-DD HH:MM):", bg="white").pack(anchor="w", pady=5)
        self.entry_date = ttk.Entry(left)
        self.entry_date.insert(0, (datetime.now()+timedelta(hours=48)).strftime("%Y-%m-%d %H:%M"))
        self.entry_date.pack(fill="x")
        
        tk.Button(left, text="RESERVAR", command=self.reservar, bg=self.colors["secondary"], fg="white").pack(fill="x", pady=20)

        # Derecha: Mis Reservas
        right = tk.Frame(content, bg="white", padx=15, pady=15)
        right.pack(side="left", fill="both", expand=True)
        
        tk.Label(right, text="Historial de Reservas", font=("Arial", 12, "bold"), bg="white").pack(anchor="w")
        self.tree = ttk.Treeview(right, columns=("ID", "Consultor", "Fecha", "Estado"), show="headings")
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=30)
        self.tree.heading("Consultor", text="Consultor")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.heading("Estado", text="Estado")
        self.tree.pack(fill="both", expand=True)
        
        self.llenar_tabla_cliente()

    # --- PANEL CONSULTOR 
    def mostrar_panel_consultor(self):
        self.limpiar()
        # Obtenemos datos del usuario/consultor
        datos_consultor = self.backend.get_usuario(self.usuario_actual)
        if not datos_consultor:
            messagebox.showerror("Error", "Usuario no encontrado")
            self.mostrar_login()
            return
        nombre_mostrar = datos_consultor["nombre"]
        
        self.header(f"Panel Consultor: {nombre_mostrar}")

        content = tk.Frame(self.container, bg=self.colors["bg"], padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Tarjeta de Información (Especialidad y Tarifa)
        info_frame = tk.Frame(content, bg="white", height=80, padx=20)
        info_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(info_frame, text="Mi Perfil Profesional", font=("Arial", 10, "bold"), bg="white", fg="gray").pack(anchor="w")
        tk.Label(info_frame, text=f"Especialidad: {datos_consultor.get('especialidad', 'General')}", font=("Arial", 12), bg="white").pack(side="left", padx=20)
        tk.Label(info_frame, text=f"Tarifa/Hora: ${datos_consultor.get('tarifa', 0)}", font=("Arial", 12), bg="white", fg="green").pack(side="left", padx=20)

        # Tabla de Citas Asignadas
        tk.Label(content, text="Agenda: Citas Programadas por Clientes", font=("Arial", 12, "bold"), bg=self.colors["bg"]).pack(anchor="w")
        
        cols = ("ID", "Cliente", "Fecha", "Estado")
        self.tree_cons = ttk.Treeview(content, columns=cols, show="headings")
        self.tree_cons.heading("ID", text="ID"); self.tree_cons.column("ID", width=30)
        self.tree_cons.heading("Cliente", text="Cliente Solicitante")
        self.tree_cons.heading("Fecha", text="Fecha Agendada")
        self.tree_cons.heading("Estado", text="Estado Actual")
        self.tree_cons.pack(fill="both", expand=True)

        self.llenar_tabla_consultor()

    # --- HELPERS ---
    def header(self, texto):
        head = tk.Frame(self.container, bg="white", height=50)
        head.pack(fill="x")
        tk.Label(head, text="Consultores S.A.S", font=("Arial", 14, "bold"), fg=self.colors["primary"], bg="white").pack(side="left", padx=20)
        tk.Button(head, text="Cerrar Sesión", command=self.mostrar_login, bg=self.colors["primary"], fg="white", relief="flat").pack(side="right", padx=20, pady=10)
        tk.Label(head, text=texto, bg="white").pack(side="right", padx=10)

    def reservar(self):
        cons = self.combo_cons.get()
        fecha = self.entry_date.get()
        ok, msg = self.backend.crear_reserva(self.usuario_actual, cons, fecha)
        messagebox.showinfo("Info", msg)
        if ok: self.llenar_tabla_cliente()

    def llenar_tabla_cliente(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        reservas = self.backend.get_reservas_cliente(self.usuario_actual)
        for r in reservas:
            self.tree.insert("", "end", values=r)

    def llenar_tabla_consultor(self):
        for i in self.tree_cons.get_children(): self.tree_cons.delete(i)
        reservas = self.backend.get_reservas_consultor(self.usuario_actual)
        for r in reservas:
            self.tree_cons.insert("", "end", values=r)
